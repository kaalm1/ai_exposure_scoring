from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class ChunkSummary(Base):
    __tablename__ = "chunk_summaries"

    id = Column(Integer, primary_key=True, index=True)

    filing_summary_id = Column(
        Integer,
        ForeignKey("filing_summaries.id", ondelete="CASCADE"),
        index=True,
        nullable=True,  # <-- can be null, not required
    )

    # Optional link directly to AIScore
    ai_score_id = Column(
        Integer,
        ForeignKey("ai_scores.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    chunk_index = Column(Integer, nullable=False)
    chunk_text_length = Column(Integer, nullable=True)
    summary = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    # Relationship back to FilingSummary (optional if you want navigation)
    filing_summary = relationship("FilingSummary", back_populates="chunk_summaries")
    ai_score = relationship("AIScore", back_populates="chunk_summaries")

    def __repr__(self):
        return (
            f"<ChunkSummary(id={self.id}, chunk_index={self.chunk_index}, "
            f"filing_summary_id={self.filing_summary_id}, ai_score_id={self.ai_score_id})>"
        )
