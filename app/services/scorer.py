import json
from openai import AsyncOpenAI
from .sec_fetcher import get_cik_from_ticker, fetch_latest_filing_text
from .filing_processor import process_filing

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
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except Exception:
        result = {
            "error": "Invalid JSON",
            "raw": response.choices[0].message.content
        }
    return result
