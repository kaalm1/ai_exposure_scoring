# app/schemas/filing_summary.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChunkSummaryRead(BaseModel):
    """Nested schema for chunk summaries in filing summary."""

    id: int
    chunk_index: int
    chunk_text_length: Optional[int] = None
    summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class FilingSummaryBase(BaseModel):
    """Base schema for filing summary."""

    cik: str
    ticker: Optional[str] = None
    filing_type: str
    accession_number: str
    filing_date: Optional[str] = None
    summary: str


class FilingSummaryCreate(FilingSummaryBase):
    """Schema for creating a filing summary."""

    raw_text_length: Optional[int] = None
    chunk_count: Optional[int] = None


class FilingSummaryRead(FilingSummaryBase):
    """Schema for reading a filing summary."""

    id: int
    raw_text_length: Optional[int] = None
    chunk_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
