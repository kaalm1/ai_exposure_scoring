import json

from app.services.llm import llm_client

from .filing_processor import process_filing
from .sec_fetcher import fetch_latest_filing_text, get_cik_from_ticker

SYSTEM_PROMPT = """
You are an expert financial analyst. 
Score companies on AI exposure using this rubric.

Return a JSON object **exactly in this structure**:

{
  "company": "Company Name",
  "scores": {
    "core_dependence": float,          # 0-10
    "revenue_from_ai": float,          # 0-10
    "strategic_investment": float,     # 0-10
    "ecosystem_dependence": float,     # 0-10
    "market_perception": float          # 0-10
  },
  "reasoning": {
    "core_dependence": "Reasoning text",
    "revenue_from_ai": "Reasoning text",
    "strategic_investment": "Reasoning text",
    "ecosystem_dependence": "Reasoning text",
    "market_perception": "Reasoning text"
  },
  "final_score": float
}

Final Score = (0.4*core_dependence + 0.25*revenue_from_ai + 
               0.2*strategic_investment + 0.1*ecosystem_dependence + 
               0.05*market_perception)
Always return valid JSON, no extra commentary.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "scores": {
            "type": "object",
            "properties": {
                "core_dependence": {"type": "number"},
                "revenue_from_ai": {"type": "number"},
                "strategic_investment": {"type": "number"},
                "ecosystem_dependence": {"type": "number"},
                "market_perception": {"type": "number"},
            },
            "required": [
                "core_dependence",
                "revenue_from_ai",
                "strategic_investment",
                "ecosystem_dependence",
                "market_perception",
            ],
        },
        "reasoning": {
            "type": "object",
            "properties": {
                "core_dependence": {"type": "string"},
                "revenue_from_ai": {"type": "string"},
                "strategic_investment": {"type": "string"},
                "ecosystem_dependence": {"type": "string"},
                "market_perception": {"type": "string"},
            },
            "required": [
                "core_dependence",
                "revenue_from_ai",
                "strategic_investment",
                "ecosystem_dependence",
                "market_perception",
            ],
        },
        "final_score": {"type": "number"},
    },
    "required": ["company", "scores", "reasoning", "final_score"],
}


async def score_company(company_name: str, ticker: str | None = None) -> dict:
    """
    Score a company on AI exposure.
    Returns structured JSON with individual scores, reasoning, and final_score.
    """
    filing_summary = ""
    if ticker:
        cik = get_cik_from_ticker(ticker)
        raw_filing = fetch_latest_filing_text(cik)
        filing_summary = await process_filing(raw_filing)

    user_prompt = f"""
Company: {company_name}
Ticker: {ticker or 'N/A'}
Context (AI-related summary from filings): {filing_summary}

Return JSON exactly as instructed in the system prompt.
"""

    # response = await llm_client.client.chat.completions.create(
    #     model=settings.llm_model,
    #     messages=[
    #         {"role": "system", "content": SYSTEM_PROMPT},
    #         {"role": "user", "content": user_prompt},
    #     ],
    #     temperature=0,
    #     response_format={
    #         "type": "json_schema",
    #         "json_schema": {
    #             "name": "ai_score_response",
    #             "schema": SCHEMA,
    #         },
    #     },
    # )

    response = await llm_client.create_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ai_score_response",
                "schema": SCHEMA,
            },
        },
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except Exception:
        result = {"error": "Invalid JSON", "raw": response.choices[0].message.content}
    return result
