from contextlib import asynccontextmanager
from app.db import async_session_factory
from app.dal.ai_scores import AIScoreDAL


@asynccontextmanager
async def get_session():
    """Provide a transactional scope around a series of operations."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise


@asynccontextmanager
async def get_ai_score_dal():
    """Provide an AIScoreDAL with session context."""
    async with get_session() as session:
        yield AIScoreDAL(session)
