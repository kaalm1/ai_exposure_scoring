from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dal.ai_scores import AIScoreDAL
from app.dal.chunk_summary import ChunkSummaryDAL
from app.dal.filing_summary import FilingSummaryDAL
from app.db import get_db_session
from app.services.ai_score_service import AIScoreService
from app.services.build_universe import UniverseBuilderService
from app.services.sec_filing_service import SECFilingService


async def get_ai_score_dal(
    session: AsyncSession = Depends(get_db_session),
) -> AIScoreDAL:
    return AIScoreDAL(session)


async def get_filing_summary_dal(
    session: AsyncSession = Depends(get_db_session),
) -> FilingSummaryDAL:
    return FilingSummaryDAL(session)


async def get_chunk_summary_dal(
    session: AsyncSession = Depends(get_db_session),
) -> ChunkSummaryDAL:
    return ChunkSummaryDAL(session)


async def get_ai_score_service(
    dal: AIScoreDAL = Depends(get_ai_score_dal),
) -> AIScoreService:
    return AIScoreService(dal)


async def get_build_universe_service(
    dal: AIScoreDAL = Depends(get_ai_score_dal),
) -> UniverseBuilderService:
    return UniverseBuilderService(dal)


async def get_sec_filing_service(
    ai_score_dal: AIScoreDAL = Depends(get_ai_score_dal),
    filing_summary_dal: FilingSummaryDAL = Depends(get_filing_summary_dal),
    chunk_summary_dal: ChunkSummaryDAL = Depends(get_chunk_summary_dal),
) -> SECFilingService:
    return SECFilingService(ai_score_dal, filing_summary_dal, chunk_summary_dal)
