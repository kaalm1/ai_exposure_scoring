from typing import List, Optional

from app.dal.ai_scores import get_recent_scores, get_score_by_company, insert_score
from app.models.schemas import AIScoreCreate, AIScoreRead


class AIScoreService:
    """
    Service layer for AI exposure scoring.
    Encapsulates business logic and DAL calls.
    """

    @staticmethod
    async def submit_score(result: dict, ticker: Optional[str] = None) -> None:
        """
        Converts LLM result dict into AIScoreCreate and saves via DAL.
        Expects `result` to contain 'company', 'scores', 'reasoning', 'final_score'.
        """
        score_obj = AIScoreCreate(
            company_name=result["company"],
            ticker=ticker,
            pure_play_score=result["scores"]["pure_play"],
            product_integration_score=result["scores"]["product_integration"],
            research_focus_score=result["scores"]["research_focus"],
            partnership_score=result["scores"]["partnership"],
            final_score=result["final_score"],
            reasoning_pure_play=result["reasoning"]["pure_play"],
            reasoning_product_integration=result["reasoning"]["product_integration"],
            reasoning_research_focus=result["reasoning"]["research_focus"],
            reasoning_partnership=result["reasoning"]["partnership"],
        )
        await insert_score(score_obj)

    @staticmethod
    async def get_recent_scores(limit: int = 100) -> List[AIScoreRead]:
        """
        Returns recent AI scores.
        """
        rows = await get_recent_scores(limit)
        return [AIScoreRead(**row) for row in rows]

    @staticmethod
    async def get_scores_by_company(company_name: str) -> List[AIScoreRead]:
        """
        Returns scores for a specific company.
        """
        rows = await get_score_by_company(company_name)
        return [AIScoreRead(**row) for row in rows]
