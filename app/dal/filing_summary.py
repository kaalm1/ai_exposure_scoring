# app/dal/filing_summary.py

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.filing_summary import FilingSummary


class FilingSummaryDAL:
    """Data Access Layer for filing summaries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_accession(self, accession_number: str) -> Optional[FilingSummary]:
        """Get a filing summary by accession number."""
        stmt = select(FilingSummary).where(
            FilingSummary.accession_number == accession_number
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_ticker(
        self, ticker: str, filing_type: Optional[str] = None
    ) -> Optional[FilingSummary]:
        """Get the most recent filing summary for a ticker."""
        stmt = select(FilingSummary).where(FilingSummary.ticker == ticker)

        if filing_type:
            stmt = stmt.where(FilingSummary.filing_type == filing_type)

        stmt = stmt.order_by(FilingSummary.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_cik(
        self, cik: str, filing_type: Optional[str] = None
    ) -> Optional[FilingSummary]:
        """Get the most recent filing summary for a CIK."""
        stmt = select(FilingSummary).where(FilingSummary.cik == cik)

        if filing_type:
            stmt = stmt.where(FilingSummary.filing_type == filing_type)

        stmt = stmt.order_by(FilingSummary.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_summary(self, summary: FilingSummary) -> FilingSummary:
        """Insert or update a filing summary based on cik + accession_number."""
        try:
            # Find by business key (cik + accession_number), not primary key
            result = await self.session.execute(
                select(FilingSummary).where(
                    FilingSummary.cik == summary.cik,
                    FilingSummary.accession_number == summary.accession_number,
                )
            )
            existing = result.scalars().first()

            if existing:
                # Update existing record
                for column in FilingSummary.__table__.columns:
                    column_name = column.name
                    if column_name not in ["id", "created_at"]:
                        value = getattr(summary, column_name, None)
                        if value is not None:
                            setattr(existing, column_name, value)
                filing = existing
            else:
                # Insert new record
                self.session.add(summary)
                filing = summary

            await self.session.commit()
            await self.session.refresh(filing)
            return filing

        except (IntegrityError, SQLAlchemyError) as e:
            logger.error("Error upserting filing summary: %s", e)
            await self.session.rollback()
            raise

    async def summary_exists(self, accession_number: str) -> bool:
        """Check if a summary already exists for this filing."""
        existing = await self.get_by_accession(accession_number)
        return existing is not None
