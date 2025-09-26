import json
from openai import AsyncOpenAI
from app.dal.ai_scores import insert_score
from app.models.schemas import AIScoreCreate
from .sec_fetcher import get_cik_from_ticker, fetch_latest_filing_text
from .filing_processor import process_filing
from app.config import settings

client = AsyncOpenAI()

SYSTEM_PROMPT = """
You are an expert financial analyst. 
You score companies on AI exposure using this rubric:

1. Core Dependence (0–10)
2. Revenue from AI (0–10)
3. Strategic Investment (0–10)
4. Ecosystem Dependence (0–10)
5. Market Perception (0–10)

Return JSON:
{
  "company": "...",
  "scores": {...},
  "reasoning": {...},
  "final_score": float
}
Final Score = (0.4*Core + 0.25*Revenue + 0.2*Investment + 0.1*Ecosystem + 0.05*Perception).
"""


async def score_company(company_name: str, ticker: str | None = None):
    filing_summary = ""
    if ticker:
        cik = get_cik_from_ticker(ticker)
        raw_filing = fetch_latest_filing_text(cik)
        filing_summary = await process_filing(raw_filing)

    user_prompt = f"""
Company: {company_name}
Context (AI-related summary from filings): {filing_summary}
Return JSON only.
"""

    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except Exception:
        result = {"error": "Invalid JSON", "raw": response.choices[0].message.content}
    return result


async def save_score_to_db(result: dict, ticker: str | None = None):
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
