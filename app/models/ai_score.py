from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, func

Base = declarative_base()


class AIScore(Base):
    __tablename__ = "ai_scores"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    ticker = Column(String, index=True)

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

    def __repr__(self):
        return f"<AIScore(company_name={self.company_name}, final_score={self.final_score})>"
