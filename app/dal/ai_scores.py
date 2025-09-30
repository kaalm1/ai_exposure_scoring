from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_scores import AIScore
from app.models.schemas import AIScoreCreate


class AIScoreDAL:
    """Data Access Layer for AIScore."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_enriched_tickers(self) -> set[str]:
        """Return a set of tickers that already have sector/industry filled."""
        result = await self.session.execute(
            select(AIScore.ticker).where(
                or_(AIScore.sector != None, AIScore.industry != None)
            )
        )
        rows = result.scalars().all()
        return set(rows)

    async def upsert(self, ticker: str, data: dict) -> AIScore:
        """
        Insert or update an AI Score company.
        Accepts a dict with keys matching column names.
        Ignores keys that are not model attributes.
        """
        result = await self.session.execute(
            select(AIScore).where(AIScore.ticker == ticker)
        )
        company = result.scalars().first()

        if company:
            # Update existing fields
            for key, value in data.items():
                if hasattr(AIScore, key):
                    setattr(company, key, value)
        else:
            # Filter dict to only valid fields
            valid_data = {k: v for k, v in data.items() if hasattr(AIScore, k)}
            company = AIScore(**valid_data)
            self.session.add(company)

        await self.session.flush()
        await self.session.commit()  # FINALIZE transaction
        await self.session.refresh(company)
        return company

    async def insert_score(self, score: AIScoreCreate) -> AIScore:
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
        self.session.add(obj)
        await self.session.flush()  # get obj.id before commit
        return obj

    async def get_recent_scores(self, limit: int = 100) -> list[AIScore]:
        result = await self.session.execute(
            select(AIScore).order_by(AIScore.created_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def get_score_by_company(self, company_name: str) -> list[AIScore]:
        result = await self.session.execute(
            select(AIScore).where(AIScore.company_name == company_name)
        )
        return result.scalars().all()
