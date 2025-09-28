from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Async engine
engine: AsyncEngine = create_async_engine(settings.database_url, echo=True, future=True)

# Async session factory
async_session_factory: sessionmaker[AsyncSession] = sessionmaker(  # type: ignore
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
