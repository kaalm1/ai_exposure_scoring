from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required env variables (from .env)
    database_url: str = (
        "postgresql+asyncpg://username:password@localhost:5432/ai_exposure"
    )
    openai_api_key: str = "default"
    llm_model: str = "gpt-4.1"

    openai_model: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    groq_api_key: str | None = None
    groq_model: str | None = None
    google_studio_api_key: str | None = None
    google_studio_model: str | None = None
    cerebras_api_key: str | None = None
    cerebras_model: str | None = None

    extra_config: dict = {}

    class Config:
        env_file = str(Path(__file__).parent.parent / ".env")  # project root
        env_file_encoding = "utf-8"


# 1️⃣ Load .env first
settings = Settings()

# 2️⃣ Load YAML
config_path = Path("configs/config.yaml")
if config_path.exists():
    with open(config_path, "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f) or {}

    # 3️⃣ Merge YAML keys, but do not override .env variables
    for key, value in yaml_config.items():
        if not hasattr(settings, key):
            settings.extra_config[key] = value
