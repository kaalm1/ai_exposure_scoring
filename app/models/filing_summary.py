# app/models/filing_summary.py

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class FilingSummary(Base):
    """Model to store processed SEC filing summaries."""

    __tablename__ = "filing_summaries"

    id = Column(Integer, primary_key=True, index=True)

    ai_score_id = Column(
        Integer,
        ForeignKey("ai_scores.id", ondelete="CASCADE"),
        unique=True,  # <-- ensures one-to-one
        nullable=True,  # <-- optional
        index=True,
    )

    # Filing identification
    cik = Column(String, nullable=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    filing_type = Column(String, nullable=True)  # "10-K" or "10-Q"
    accession_number = Column(String, nullable=True, unique=True, index=True)
    filing_date = Column(String, nullable=True)

    # Processing results
    raw_text_length = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=True)

    # AI-extracted summary
    summary = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    ai_score = relationship("AIScore", back_populates="filing_summary", uselist=False)
    chunk_summaries = relationship(
        "ChunkSummary", back_populates="filing_summary", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<FilingSummary(ticker={self.ticker}, filing_type={self.filing_type}, accession={self.accession_number})>"
