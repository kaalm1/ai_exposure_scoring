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

        stmt = stmt.order_by(FilingSummary.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def insert_summary(self, summary: FilingSummary) -> FilingSummary:
        """Insert a new filing summary."""
        self.session.add(summary)
        await self.session.commit()
        await self.session.refresh(summary)
        return summary

    async def summary_exists(self, accession_number: str) -> bool:
        """Check if a summary already exists for this filing."""
        existing = await self.get_by_accession(accession_number)
        return existing is not None
