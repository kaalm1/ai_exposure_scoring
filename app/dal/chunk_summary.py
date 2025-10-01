# app/dal/chunk_summary.py

from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk_summary import ChunkSummary


class ChunkSummaryDAL:
    """Data Access Layer for chunk summaries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chunk_summary(
        self,
        chunk_summary: ChunkSummary,
    ) -> ChunkSummary:
        """Insert a new chunk summary."""
        self.session.add(chunk_summary)
        await self.session.flush()  # ensures id is populated
        return chunk_summary

    async def update_chunk_summary(
        self, chunk_summary_id: int, data: dict
    ) -> Optional[ChunkSummary]:
        """
        Update a chunk summary with provided data.
        Returns the updated object, or None if not found.
        """
        result = await self.session.execute(
            select(ChunkSummary).where(ChunkSummary.id == chunk_summary_id)
        )
        chunk_summary = result.scalar_one_or_none()

        if not chunk_summary:
            return None

        for key, value in data.items():
            if hasattr(chunk_summary, key):
                setattr(chunk_summary, key, value)

        await self.session.flush()  # push updates to DB
        return chunk_summary

    async def assign_filing_summary_to_chunks(
        self, chunk_ids: List[int], filing_summary_id: int
    ) -> int:
        """
        Bulk update: assign a filing_summary_id to multiple chunks.
        Returns the number of rows updated.
        """
        if not chunk_ids:
            return 0

        stmt = (
            update(ChunkSummary)
            .where(ChunkSummary.id.in_(chunk_ids))
            .values(filing_summary_id=filing_summary_id)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_chunk_summary(self, chunk_summary_id: int) -> Optional[ChunkSummary]:
        """Fetch a single chunk summary by ID."""
        result = await self.session.execute(
            select(ChunkSummary).where(ChunkSummary.id == chunk_summary_id)
        )
        return result.scalar_one_or_none()

    async def get_by_filing_summary(self, filing_summary_id: int) -> List[ChunkSummary]:
        """Fetch all chunk summaries for a given filing summary."""
        result = await self.session.execute(
            select(ChunkSummary).where(
                ChunkSummary.filing_summary_id == filing_summary_id
            )
        )
        return result.scalars().all()

    async def delete_chunk_summary(self, chunk_summary_id: int) -> None:
        """Delete a chunk summary by ID."""
        chunk_summary = await self.get_chunk_summary(chunk_summary_id)
        if chunk_summary:
            await self.session.delete(chunk_summary)
