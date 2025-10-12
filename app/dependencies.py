from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dal.ai_scores import AIScoreDAL
from app.dal.chunk_summary import ChunkSummaryDAL
from app.dal.filing_summary import FilingSummaryDAL
from app.dal.financial_data import FinancialDataDAL
from app.db import get_db_session
from app.services.ai_score_service import AIScoreService
from app.services.build_universe import UniverseBuilderService
from app.services.financial_data_service import FinancialDataService
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


async def get_financial_data_dal(
    session: AsyncSession = Depends(get_db_session),
) -> FinancialDataDAL:
    return FinancialDataDAL(session)


async def get_ai_score_service(
    dal: AIScoreDAL = Depends(get_ai_score_dal),
) -> AIScoreService:
    return AIScoreService(dal)


async def get_build_universe_service(
    dal: AIScoreDAL = Depends(get_ai_score_dal),
) -> UniverseBuilderService:
    return UniverseBuilderService(dal)


async def get_financial_data_service(
    ai_score_dal: AIScoreDAL = Depends(get_ai_score_dal),
    financial_data_dal: FinancialDataDAL = Depends(get_financial_data_dal),
    user_agent: str = "your-app-name/1.0 (your-email@example.com)",  # Replace with actual config
) -> FinancialDataService:
    return FinancialDataService(ai_score_dal, financial_data_dal, user_agent)


async def get_sec_filing_service(
    ai_score_dal: AIScoreDAL = Depends(get_ai_score_dal),
    filing_summary_dal: FilingSummaryDAL = Depends(get_filing_summary_dal),
    chunk_summary_dal: ChunkSummaryDAL = Depends(get_chunk_summary_dal),
) -> SECFilingService:
    return SECFilingService(ai_score_dal, filing_summary_dal, chunk_summary_dal)
