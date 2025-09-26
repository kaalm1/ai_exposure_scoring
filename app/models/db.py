from sqlalchemy import MetaData, Table, Column, Integer, Text, Float, DateTime, func

metadata = MetaData()

ai_scores = Table(
    "ai_scores",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("company_name", Text, nullable=False),
    Column("ticker", Text),
    Column("pure_play_score", Float),
    Column("product_integration_score", Float),
    Column("research_focus_score", Float),
    Column("partnership_score", Float),
    Column("final_score", Float),
    Column("reasoning_pure_play", Text),
    Column("reasoning_product_integration", Text),
    Column("reasoning_research_focus", Text),
    Column("reasoning_partnership", Text),
    Column("created_at", DateTime, server_default=func.now()),
)
