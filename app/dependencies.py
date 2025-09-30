from fastapi import Depends

from app.dal.ai_scores import AIScoreDAL
from app.services.ai_score_service import AIScoreService
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db_session


async def get_ai_score_dal(
    session: AsyncSession = Depends(get_db_session),
) -> AIScoreDAL:
    return AIScoreDAL(session)


async def get_ai_score_service(
    dal: AIScoreDAL = Depends(get_ai_score_dal),
) -> AIScoreService:
    return AIScoreService(dal)
