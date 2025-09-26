from pydantic import BaseModel
from typing import Optional


class ScoreRequest(BaseModel):
    company_name: str
    ticker: str | None = None


class AIScoreCreate(BaseModel):
    company_name: str
    ticker: Optional[str]
    pure_play_score: float
    product_integration_score: float
    research_focus_score: float
    partnership_score: float
    final_score: float
    reasoning_pure_play: str
    reasoning_product_integration: str
    reasoning_research_focus: str
    reasoning_partnership: str


class AIScoreRead(AIScoreCreate):
    id: int
    created_at: str
