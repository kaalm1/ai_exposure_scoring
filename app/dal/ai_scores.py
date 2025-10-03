import logging
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_scores import AIScore

logger = logging.getLogger(__name__)


class AIScoreDAL:
    """Data Access Layer for AIScore."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_scores(self) -> list[AIScore]:
        result = await self.session.execute(select(AIScore))
        return result.scalars().all()

    async def get_enriched_tickers(self) -> set[str]:
        """Return a set of tickers that already have sector/industry filled."""
        result = await self.session.execute(
            select(AIScore.ticker).where(
                or_(AIScore.sector != None, AIScore.industry != None)
            )
        )
        rows = result.scalars().all()
        return set(rows)

    async def upsert(self, ticker: str, data: dict) -> Optional[AIScore]:
        """
        Insert or update an AI Score company.
        Accepts a dict with keys matching column names.
        Ignores keys that are not model attributes.
        """
        try:
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
                if "company_name" not in data or not data["company_name"]:
                    # Skip insert
                    return None
                # Filter dict to only valid fields
                valid_data = {k: v for k, v in data.items() if hasattr(AIScore, k)}
                valid_data["ticker"] = ticker
                company = AIScore(**valid_data)
                self.session.add(company)

            await self.session.flush()
            await self.session.commit()  # FINALIZE transaction
            await self.session.refresh(company)
            return company

        except (IntegrityError, SQLAlchemyError) as e:
            logger.error("Error upserting data for %s: %s", ticker, e)
            await self.session.rollback()  # rollback only the failed transaction
            return None

    async def upsert_model(self, ai_score: AIScore) -> Optional[AIScore]:
        """
        Insert or update an AI Score company.
        Accepts an AIScore model instance.
        """
        try:
            # Check if record exists by ticker (business key)
            result = await self.session.execute(
                select(AIScore).where(AIScore.ticker == ai_score.ticker)
            )
            existing = result.scalars().first()

            if existing:
                # Update existing record
                for column in AIScore.__table__.columns:
                    column_name = column.name
                    # Skip primary key or auto-generated fields
                    if column_name not in ["id", "created_at"]:
                        value = getattr(ai_score, column_name, None)
                        if value is not None:
                            setattr(existing, column_name, value)
                company = existing
            else:
                # Insert new record - validate company_name is required
                if not ai_score.company_name:
                    logger.warning(
                        "Skipping insert for %s: missing company_name", ai_score.ticker
                    )
                    return None

                self.session.add(ai_score)
                company = ai_score

            await self.session.commit()
            await self.session.refresh(company)
            return company

        except (IntegrityError, SQLAlchemyError) as e:
            logger.error("Error upserting data for %s: %s", ai_score.ticker, e)
            await self.session.rollback()
            return None

    async def get_recent_scores(self, limit: int = 100) -> list[AIScore]:
        result = await self.session.execute(
            select(AIScore).order_by(AIScore.created_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def get_score(
        self,
        *,
        cik: Optional[str] = None,
        company_name: Optional[str] = None,
        ticker: Optional[str] = None,
    ) -> List[AIScore]:
        """
        Fetch AIScore(s) by cik, company_name, or ticker.
        At least one argument must be provided.
        """
        if not any([cik, company_name, ticker]):
            raise ValueError("Must provide at least one of: cik, company_name, ticker")

        filters = []
        if cik:
            filters.append(AIScore.cik == cik)
        if company_name:
            filters.append(AIScore.company_name == company_name)
        if ticker:
            filters.append(AIScore.ticker == ticker)

        stmt = select(AIScore).where(or_(*filters))
        result = await self.session.execute(stmt)
        return result.scalars().all()
