from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import yaml

# Load DB URL
with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)
DATABASE_URL = config["database_url"]

# Async engine
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Async session factory
async_session: sessionmaker[AsyncSession] = sessionmaker( # type: ignore
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

