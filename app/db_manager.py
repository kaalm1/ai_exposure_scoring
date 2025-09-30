import logging
from urllib.parse import urlparse
import yaml
import asyncio
import os

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import create_engine, text, inspect
from alembic import command
from alembic.config import Config
from app.config import settings

logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    """Async database manager with auto-create user and DB."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.database_url: str = settings.database_url
        here = os.path.dirname(os.path.abspath(__file__))  # app/
        self.alembic_cfg = Config(os.path.join(here, "alembic.ini"))
        self.engine: AsyncEngine = create_async_engine(
            self.database_url, future=True, echo=True
        )

    def _get_db_name_from_url(self) -> str:
        parsed = urlparse(self.database_url)
        return parsed.path.lstrip("/")

    def _get_user_password(self) -> tuple[str, str]:
        parsed = urlparse(self.database_url)
        return parsed.username, parsed.password

    def _get_admin_url(self) -> str:
        # Connect as superuser (assume 'postgres')
        parsed = urlparse(self.database_url)
        return f"{parsed.scheme}://postgres:postgres@{parsed.hostname}:{parsed.port}/postgres"

    def _get_admin_url_sync(self):
        parsed = urlparse(self.database_url)
        return f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"

    def ensure_user_and_db(self):
        """Use synchronous engine in AUTOCOMMIT mode to create user/database."""
        user, password = self._get_user_password()
        db_name = self._get_db_name_from_url()
        admin_url = self._get_admin_url_sync()

        # Synchronous engine for autocommit
        sync_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with sync_engine.connect() as conn:
            # Create user if not exists
            result = conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :user"), {"user": user}
            )
            if not result.scalar():
                logger.info(f"Creating user {user}")
                conn.execute(text(f"CREATE USER {user} WITH PASSWORD '{password}'"))

            # Create database if not exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": db_name},
            )
            if not result.scalar():
                logger.info(f"Creating database {db_name}")
                conn.execute(text(f'CREATE DATABASE "{db_name}" OWNER {user}'))

        sync_engine.dispose()

    async def ensure_user_and_db_async(self):
        """Run synchronous ensure_user_and_db in a separate thread to avoid blocking."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.ensure_user_and_db)

    async def database_exists(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.debug(f"DB not accessible yet: {e}")
            return False

    async def needs_migration(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                def check_tables(sync_conn):
                    inspector = inspect(sync_conn)
                    return inspector.get_table_names()

                tables = await conn.run_sync(check_tables)
                if "alembic_version" not in tables:
                    logger.info("No alembic_version table found - migrations needed")
                    return True
            return False
        except Exception as e:
            logger.warning(f"Could not check migration status: {e}")
            return True

    async def run_migrations(self) -> None:
        loop = asyncio.get_event_loop()
        # Run Alembic migration in separate thread (sync code)
        await loop.run_in_executor(None, command.upgrade, self.alembic_cfg, "head")
        logger.info("✓ Migrations completed successfully")

    async def initialize_database(self) -> None:
        logger.info("=" * 50)
        logger.info("Initializing PostgreSQL database...")
        logger.info("=" * 50)

        # Step 0: Ensure user and DB exist (sync)
        await self.ensure_user_and_db_async()

        # Step 1: Verify async connection
        if not await self.database_exists():
            logger.error("Database exists but cannot connect asynchronously")
            raise RuntimeError("Cannot connect to database after creation")
        else:
            logger.info("✓ Database connection verified")

        # Step 2: Run migrations if needed
        if await self.needs_migration():
            logger.info("Migrations needed. Running migrations...")
            await self.run_migrations()
        else:
            logger.info("✓ Database schema is up to date")

        logger.info("=" * 50)
        logger.info("Database initialization complete!")
        logger.info("=" * 50)

    async def dispose(self):
        await self.engine.dispose()
