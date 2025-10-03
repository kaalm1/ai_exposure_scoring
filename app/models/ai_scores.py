from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class AIScore(Base):
    __tablename__ = "ai_scores"

    id = Column(Integer, primary_key=True, index=True)

    # Core identification
    ticker = Column(String, index=True, unique=True)
    company_name = Column(String, nullable=False, index=True)
    cik = Column(String, index=True, nullable=True)

    # Classification / context
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Additional enriched fields from Yahoo Finance
    market_cap = Column(Float, nullable=True)
    enterprise_value = Column(Float, nullable=True)
    employees = Column(Integer, nullable=True)
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    beta = Column(Float, nullable=True)
    recommendation_key = Column(String, nullable=True)
    recommendation_mean = Column(Float, nullable=True)
    hq_city = Column(String, nullable=True)
    hq_state = Column(String, nullable=True)

    # Filtering decision (before scoring)
    # True means that it should be filtered out
    filter_decision = Column(Boolean, default=True, index=True)
    filter_reason = Column(Text, nullable=True)

    # AI exposure scores
    pure_play_score = Column(Float)
    product_integration_score = Column(Float)
    research_focus_score = Column(Float)
    partnership_score = Column(Float)
    final_score = Column(Float)

    # AI reasoning
    reasoning_pure_play = Column(Text)
    reasoning_product_integration = Column(Text)
    reasoning_research_focus = Column(Text)
    reasoning_partnership = Column(Text)

    # AI Misc
    ai_proportion = Column(Text)
    business_role = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    filing_summary = relationship(
        "FilingSummary", back_populates="ai_score", uselist=False
    )
    chunk_summaries = relationship(
        "ChunkSummary", back_populates="ai_score", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<AIScore(company_name={self.company_name}, final_score={self.final_score})>"
