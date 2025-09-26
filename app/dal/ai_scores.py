from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_score import AIScore
from app.models.schemas import AIScoreCreate
from app.services.db import async_session  # see below for session setup

# -----------------------------
# DAL functions
# -----------------------------


async def insert_score(score: AIScoreCreate):
    async with async_session() as session:
        async with session.begin():
            obj = AIScore(
                company_name=score.company_name,
                ticker=score.ticker,
                pure_play_score=score.pure_play_score,
                product_integration_score=score.product_integration_score,
                research_focus_score=score.research_focus_score,
                partnership_score=score.partnership_score,
                final_score=score.final_score,
                reasoning_pure_play=score.reasoning_pure_play,
                reasoning_product_integration=score.reasoning_product_integration,
                reasoning_research_focus=score.reasoning_research_focus,
                reasoning_partnership=score.reasoning_partnership,
            )
            session.add(obj)
        await session.commit()


async def get_recent_scores(limit: int = 100):
    async with async_session() as session:
        result = await session.execute(
            select(AIScore).order_by(AIScore.created_at.desc()).limit(limit)
        )
        rows = result.scalars().all()
        return [row.__dict__ for row in rows]


async def get_score_by_company(company_name: str):
    async with async_session() as session:
        result = await session.execute(
            select(AIScore).where(AIScore.company_name == company_name)
        )
        rows = result.scalars().all()
        return [row.__dict__ for row in rows]
