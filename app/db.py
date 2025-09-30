from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url, echo=True, future=True
)

# Async session factory
async_session_factory: sessionmaker[AsyncSession] = sessionmaker(  # type: ignore
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
