from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    Float,
    DateTime,
    JSON,
    func,
)
from sqlalchemy.sql import select
from app.db import database

metadata = MetaData()

# SQLAlchemy table definition (matches Alembic migration)
ai_scores = Table(
    "ai_scores",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("company_name", Text, nullable=False),
    Column("ticker", Text),
    Column("scores", JSON),
    Column("reasoning", JSON),
    Column("final_score", Float),
    Column("created_at", DateTime, server_default=func.now()),
)

# -----------------------------
# DAL functions
# -----------------------------


async def insert_score(
    company_name: str,
    ticker: str | None,
    scores: dict,
    reasoning: dict,
    final_score: float,
):
    query = ai_scores.insert().values(
        company_name=company_name,
        ticker=ticker,
        scores=scores,
        reasoning=reasoning,
        final_score=final_score,
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
