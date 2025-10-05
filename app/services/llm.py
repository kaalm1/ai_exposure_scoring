import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)


class Provider(Enum):
    OPENROUTER = "openrouter"
    GROQ = "groq"
    GOOGLE_STUDIO = "google_studio"
    CEREBRAS = "cerebras"
    OPENAI = "openai"


@dataclass
class ProviderConfig:
    name: Provider
    base_url: str
    api_key: str
    model: str
    # Rate limits
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_minute: Optional[int] = None
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class UsageTracker:
    """Track usage with sliding windows for rate limiting."""

    minute_requests: deque = field(default_factory=deque)
    day_requests: deque = field(default_factory=deque)
    failed_until: Optional[float] = None
    lock: Lock = field(default_factory=Lock)

    def add_request(self, timestamp: float):
        """Add a request timestamp."""
        with self.lock:
            self.minute_requests.append(timestamp)
            self.day_requests.append(timestamp)

    def cleanup_old_requests(self, current_time: float):
        """Remove requests outside the tracking window."""
        with self.lock:
            # Remove requests older than 1 minute
            while self.minute_requests and current_time - self.minute_requests[0] > 60:
                self.minute_requests.popleft()

            # Remove requests older than 24 hours
            while self.day_requests and current_time - self.day_requests[0] > 86400:
                self.day_requests.popleft()

    def get_counts(self, current_time: float) -> Tuple[int, int]:
        """Get current request counts (minute, day)."""
        self.cleanup_old_requests(current_time)
        with self.lock:
            return len(self.minute_requests), len(self.day_requests)

    def mark_failed(self, duration: int):
        """Mark provider as failed for specified duration."""
        with self.lock:
            self.failed_until = time.time() + duration

    def is_failed(self) -> bool:
        """Check if provider is marked as failed."""
        with self.lock:
            if self.failed_until is None:
                return False
            if time.time() >= self.failed_until:
                self.failed_until = None
                return False
            return True


class InMemoryStore:
    """In-memory storage for rate limiting when Redis is unavailable."""

    def __init__(self):
        self.trackers: Dict[str, UsageTracker] = {}
        self.lock = Lock()

    def get_tracker(self, provider: Provider) -> UsageTracker:
        """Get or create usage tracker for a provider."""
        key = provider.value
        if key not in self.trackers:
            with self.lock:
                if key not in self.trackers:
                    self.trackers[key] = UsageTracker()
        return self.trackers[key]


class RedisStore:
    """Redis-backed storage for rate limiting."""

    def __init__(self, redis_client):
        self.redis = redis_client
        # Keep in-memory cache as backup
        self.memory_store = InMemoryStore()

    def _get_redis_key(self, provider: Provider, metric: str) -> str:
        """Generate Redis key for tracking provider metrics."""
        return f"llm:provider:{provider.value}:{metric}"

    def check_rate_limit(self, provider: Provider, config: ProviderConfig) -> bool:
        """Check if provider is within rate limits."""
        try:
            now = time.time()

            # Check requests per minute
            if config.requests_per_minute:
                key = self._get_redis_key(provider, "rpm")
                count = self.redis.get(key)
                if count and int(count) >= config.requests_per_minute:
                    logger.warning(f"{provider.value} RPM limit reached")
                    return False

            # Check requests per day
            if config.requests_per_day:
                key = self._get_redis_key(provider, "rpd")
                count = self.redis.get(key)
                if count and int(count) >= config.requests_per_day:
                    logger.warning(f"{provider.value} daily limit reached")
                    return False

            return True
        except Exception as e:
            logger.warning(
                f"Redis error in check_rate_limit, falling back to memory: {e}"
            )
            return self._check_rate_limit_memory(provider, config)

    def _check_rate_limit_memory(
        self, provider: Provider, config: ProviderConfig
    ) -> bool:
        """Fallback to in-memory rate limiting."""
        tracker = self.memory_store.get_tracker(provider)
        current_time = time.time()
        minute_count, day_count = tracker.get_counts(current_time)

        if config.requests_per_minute and minute_count >= config.requests_per_minute:
            logger.warning(f"{provider.value} RPM limit reached (memory)")
            return False

        if config.requests_per_day and day_count >= config.requests_per_day:
            logger.warning(f"{provider.value} daily limit reached (memory)")
            return False

        return True

    def increment_usage(self, provider: Provider, config: ProviderConfig):
        """Increment usage counters for a provider."""
        try:
            # Increment requests per minute (expires after 60 seconds)
            if config.requests_per_minute:
                key = self._get_redis_key(provider, "rpm")
                pipe = self.redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, 60)
                pipe.execute()

            # Increment requests per day (expires after 24 hours)
            if config.requests_per_day:
                key = self._get_redis_key(provider, "rpd")
                pipe = self.redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, 86400)
                pipe.execute()
        except Exception as e:
            logger.warning(
                f"Redis error in increment_usage, falling back to memory: {e}"
            )
            self._increment_usage_memory(provider)

    def _increment_usage_memory(self, provider: Provider):
        """Fallback to in-memory usage tracking."""
        tracker = self.memory_store.get_tracker(provider)
        tracker.add_request(time.time())

    def mark_provider_failed(self, provider: Provider, duration: int):
        """Mark a provider as temporarily failed."""
        try:
            key = self._get_redis_key(provider, "failed")
            self.redis.setex(key, duration, "1")
            logger.warning(f"Marked {provider.value} as failed for {duration} seconds")
        except Exception as e:
            logger.warning(
                f"Redis error in mark_provider_failed, falling back to memory: {e}"
            )
            self._mark_failed_memory(provider, duration)

    def _mark_failed_memory(self, provider: Provider, duration: int):
        """Fallback to in-memory failed marking."""
        tracker = self.memory_store.get_tracker(provider)
        tracker.mark_failed(duration)

    def is_provider_failed(self, provider: Provider) -> bool:
        """Check if provider is marked as failed."""
        try:
            key = self._get_redis_key(provider, "failed")
            is_failed = bool(self.redis.get(key))
            return is_failed
        except Exception as e:
            logger.warning(
                f"Redis error in is_provider_failed, falling back to memory: {e}"
            )
            return self._is_failed_memory(provider)

    def _is_failed_memory(self, provider: Provider) -> bool:
        """Fallback to in-memory failed checking."""
        tracker = self.memory_store.get_tracker(provider)
        return tracker.is_failed()


class ProviderManager:
    """Manages multiple LLM providers with automatic failover and rate limiting."""

    def __init__(self, store: Optional[Any] = None):
        self.store = store or InMemoryStore()
        self.providers = self._initialize_providers()
        self.current_provider_idx = 0
        self._clients: Dict[Provider, AsyncOpenAI] = {}

        if isinstance(self.store, InMemoryStore):
            logger.info("Using in-memory rate limiting (Redis not available)")
        else:
            logger.info("Using Redis-backed rate limiting")

    def _initialize_providers(self) -> List[ProviderConfig]:
        """Initialize provider configurations from settings."""
        providers = []

        # OpenRouter - Free tier: varies by model
        if hasattr(settings, "openrouter_api_key") and settings.openrouter_api_key:
            providers.append(
                ProviderConfig(
                    name=Provider.OPENROUTER,
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.openrouter_api_key,
                    model=getattr(
                        settings,
                        "openrouter_model",
                        "meta-llama/llama-3.2-3b-instruct:free",
                    ),
                    requests_per_minute=20,
                    requests_per_day=200,
                )
            )

        # Groq - Free tier: 30 requests/minute, 14,400/day
        if hasattr(settings, "groq_api_key") and settings.groq_api_key:
            providers.append(
                ProviderConfig(
                    name=Provider.GROQ,
                    base_url="https://api.groq.com/openai/v1",
                    api_key=settings.groq_api_key,
                    model=getattr(settings, "groq_model", "llama-3.1-8b-instant"),
                    requests_per_minute=30,
                    requests_per_day=14400,
                )
            )

        # Google AI Studio - Free tier: 15 requests/minute
        if (
            hasattr(settings, "google_studio_api_key")
            and settings.google_studio_api_key
        ):
            providers.append(
                ProviderConfig(
                    name=Provider.GOOGLE_STUDIO,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                    api_key=settings.google_studio_api_key,
                    model=getattr(settings, "google_studio_model", "gemini-1.5-flash"),
                    requests_per_minute=15,
                    requests_per_day=1500,
                )
            )

        # Cerebras - Free tier: generous limits
        if hasattr(settings, "cerebras_api_key") and settings.cerebras_api_key:
            providers.append(
                ProviderConfig(
                    name=Provider.CEREBRAS,
                    base_url="https://api.cerebras.ai/v1",
                    api_key=settings.cerebras_api_key,
                    model=getattr(settings, "cerebras_model", "llama3.1-8b"),
                    requests_per_minute=30,
                )
            )

        # OpenAI - fallback if configured
        if hasattr(settings, "openai_api_key") and settings.openai_api_key:
            providers.append(
                ProviderConfig(
                    name=Provider.OPENAI,
                    base_url=getattr(
                        settings, "openai_base_url", "https://api.openai.com/v1"
                    ),
                    api_key=settings.openai_api_key,
                    model=getattr(settings, "openai_model", "gpt-3.5-turbo"),
                )
            )

        if not providers:
            raise ValueError(
                "No LLM providers configured. Please add API keys to settings."
            )

        logger.info(
            f"Initialized {len(providers)} providers: {[p.name.value for p in providers]}"
        )
        return providers

    def _check_rate_limit(self, config: ProviderConfig) -> bool:
        """Check if provider is within rate limits."""
        if isinstance(self.store, RedisStore):
            return self.store.check_rate_limit(config.name, config)
        else:
            # In-memory store
            tracker = self.store.get_tracker(config.name)
            current_time = time.time()
            minute_count, day_count = tracker.get_counts(current_time)

            if (
                config.requests_per_minute
                and minute_count >= config.requests_per_minute
            ):
                logger.warning(f"{config.name.value} RPM limit reached")
                return False

            if config.requests_per_day and day_count >= config.requests_per_day:
                logger.warning(f"{config.name.value} daily limit reached")
                return False

            return True

    def _increment_usage(self, config: ProviderConfig):
        """Increment usage counters for a provider."""
        if isinstance(self.store, RedisStore):
            self.store.increment_usage(config.name, config)
        else:
            # In-memory store
            tracker = self.store.get_tracker(config.name)
            tracker.add_request(time.time())

    def _mark_provider_failed(self, config: ProviderConfig, duration: int = 300):
        """Mark a provider as temporarily failed."""
        if isinstance(self.store, RedisStore):
            self.store.mark_provider_failed(config.name, duration)
        else:
            # In-memory store
            tracker = self.store.get_tracker(config.name)
            tracker.mark_failed(duration)
            logger.warning(
                f"Marked {config.name.value} as failed for {duration} seconds"
            )

    def _is_provider_failed(self, config: ProviderConfig) -> bool:
        """Check if provider is marked as failed."""
        if isinstance(self.store, RedisStore):
            return self.store.is_provider_failed(config.name)
        else:
            # In-memory store
            tracker = self.store.get_tracker(config.name)
            return tracker.is_failed()

    def _get_client(self, config: ProviderConfig) -> AsyncOpenAI:
        """Get or create OpenAI client for provider."""
        if config.name not in self._clients:
            self._clients[config.name] = AsyncOpenAI(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout=30.0,
            )
        return self._clients[config.name]

    async def _try_provider(self, config: ProviderConfig, **kwargs) -> Any:
        """Attempt to make a request with a specific provider."""
        # Check if provider is temporarily failed
        if self._is_provider_failed(config):
            raise Exception(f"Provider {config.name.value} is temporarily unavailable")

        # Check rate limits
        if not self._check_rate_limit(config):
            raise RateLimitError(f"Rate limit exceeded for {config.name.value}")

        client = self._get_client(config)

        # Set model if not provided
        if "model" not in kwargs:
            kwargs["model"] = config.model

        try:
            # Increment usage before making request
            self._increment_usage(config)

            # logger.info(
            #     f"Making request to {config.name.value} with model {kwargs['model']}"
            # )
            response = await client.chat.completions.create(**kwargs)

            # logger.info(f"Successfully received response from {config.name.value}")
            return response

        except RateLimitError as e:
            logger.warning(f"{config.name.value} rate limit hit: {e}")
            self._mark_provider_failed(config, duration=60)
            raise
        except Exception as e:
            # Check if it's an API error with status code
            if hasattr(e, 'status_code'):
                if e.status_code == 429:  # Rate limit
                    logger.warning(f"{config.name.value} returned 429: {e}")
                    self._mark_provider_failed(config, duration=60)
                elif e.status_code >= 500:  # Server error
                    logger.error(f"{config.name.value} server error: {e}")
                    self._mark_provider_failed(config, duration=300)
                else:
                    logger.error(f"{config.name.value} API error: {e}")
            else:
                logger.error(f"{config.name.value} unexpected error: {e}")
            raise

    async def create_completion(self, **kwargs) -> Any:
        """
        Create a chat completion, automatically rotating through providers on failure.

        Args:
            **kwargs: Arguments to pass to the OpenAI chat completion API

        Returns:
            Chat completion response

        Raises:
            Exception: If all providers fail
        """
        last_error = None

        # Try each provider in order
        for attempt in range(len(self.providers)):
            config = self.providers[self.current_provider_idx]

            try:
                response = await self._try_provider(config, **kwargs)
                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Provider {config.name.value} failed (attempt {attempt + 1}/{len(self.providers)}): {e}"
                )

                # Move to next provider
                self.current_provider_idx = (self.current_provider_idx + 1) % len(
                    self.providers
                )

                # Add small delay before trying next provider
                if attempt < len(self.providers) - 1:
                    await asyncio.sleep(0.5)

        # All providers failed
        raise Exception(
            f"All {len(self.providers)} providers failed. Last error: {last_error}"
        )

    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get current usage statistics for all providers."""
        stats = {}
        current_time = time.time()

        for config in self.providers:
            if isinstance(self.store, InMemoryStore):
                tracker = self.store.get_tracker(config.name)
                minute_count, day_count = tracker.get_counts(current_time)
                stats[config.name.value] = {
                    "requests_last_minute": minute_count,
                    "requests_last_day": day_count,
                    "is_failed": tracker.is_failed(),
                }

        return stats


class LLMClient:
    """Smart LLM client with automatic provider rotation."""

    def __init__(self, store: Optional[Any] = None):
        self._manager = ProviderManager(store)

    async def create_completion(self, **kwargs) -> Any:
        """
        Create a chat completion.

        Example:
            response = await llm_client.create_completion(
                messages=[{"role": "user", "content": "Hello!"}],
                temperature=0.7,
                max_tokens=100
            )
        """
        return await self._manager.create_completion(**kwargs)

    async def create_streaming_completion(self, **kwargs):
        """
        Create a streaming chat completion.

        Example:
            async for chunk in llm_client.create_streaming_completion(
                messages=[{"role": "user", "content": "Hello!"}],
                stream=True
            ):
                print(chunk.choices[0].delta.content)
        """
        kwargs["stream"] = True
        return await self._manager.create_completion(**kwargs)

    def get_available_providers(self) -> List[str]:
        """Get list of configured provider names."""
        return [p.name.value for p in self._manager.providers]

    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get current usage statistics for all providers."""
        return self._manager.get_usage_stats()


# Singleton instance - initialize with Redis if available
def create_llm_client() -> LLMClient:
    """Factory function to create LLM client with optional Redis."""
    store = None

    if hasattr(settings, "redis_url") and settings.redis_url:
        try:
            from redis import Redis

            redis_client = Redis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=5
            )
            redis_client.ping()
            store = RedisStore(redis_client)
            logger.info("Redis connection established for LLM client")
        except ImportError:
            logger.warning("Redis package not installed, using in-memory storage")
            store = InMemoryStore()
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory storage: {e}")
            store = InMemoryStore()
    else:
        logger.info("Redis not configured, using in-memory storage")
        store = InMemoryStore()

    return LLMClient(store)


# Global instance
llm_client = create_llm_client()
