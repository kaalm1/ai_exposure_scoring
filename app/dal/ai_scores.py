from app.models.db import ai_scores
from app.models.schemas import AIScoreCreate
from app.services.db import database
from sqlalchemy import select


async def insert_score(score: AIScoreCreate):
    query = ai_scores.insert().values(
        company_name=score.company_name,
        ticker=score.ticker,
        pure_play_score=score.pure_play_score,
        product_integration_score=score.product_integration_score,
        research_focus_score=score.research_focus_score,
        partnership_score=score.partnership_score,
        final_score=score.final_score,
        reasoning_pure_play=score.reasoning_pure_play,
        reasoning_product_integration=score.reasoning_product_integration,
        reasoning_research_focus=score.reasoning_research_focus,
        reasoning_partnership=score.reasoning_partnership,
    )
    await database.execute(query)


async def get_recent_scores(limit: int = 100):
    query = select(ai_scores).order_by(ai_scores.c.created_at.desc()).limit(limit)
    rows = await database.fetch_all(query)
    return [dict(row) for row in rows]


async def get_score_by_company(company_name: str):
    query = select(ai_scores).where(ai_scores.c.company_name == company_name)
    rows = await database.fetch_all(query)
    return [dict(row) for row in rows]
