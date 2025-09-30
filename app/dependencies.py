from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dal.ai_scores import AIScoreDAL
from app.db import get_db_session
from app.services.ai_score_service import AIScoreService
from app.services.build_universe import UniverseBuilderService


async def get_ai_score_dal(
    session: AsyncSession = Depends(get_db_session),
) -> AIScoreDAL:
    return AIScoreDAL(session)


async def get_ai_score_service(
    dal: AIScoreDAL = Depends(get_ai_score_dal),
) -> AIScoreService:
    return AIScoreService(dal)


async def get_build_universe_service(
    dal: AIScoreDAL = Depends(get_ai_score_dal),
) -> UniverseBuilderService:
    return UniverseBuilderService(dal)
