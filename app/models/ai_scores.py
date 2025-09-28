from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, func, Text, Boolean

Base = declarative_base()


class AIScore(Base):
    __tablename__ = "ai_scores"

    id = Column(Integer, primary_key=True, index=True)

    company_name = Column(String, nullable=False, index=True)
    ticker = Column(String, index=True, unique=True)
    cik = Column(String, index=True, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Filtering decision (before scoring)
    filter_decision = Column(Boolean, default=True, index=True)
    filter_reason = Column(Text, nullable=True)

    pure_play_score = Column(Float)
    product_integration_score = Column(Float)
    research_focus_score = Column(Float)
    partnership_score = Column(Float)
    final_score = Column(Float)

    reasoning_pure_play = Column(String)
    reasoning_product_integration = Column(String)
    reasoning_research_focus = Column(String)
    reasoning_partnership = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<AIScore(company_name={self.company_name}, final_score={self.final_score})>"
