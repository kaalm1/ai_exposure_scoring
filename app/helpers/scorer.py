# app/services/sec_filing/scorer.py

import json
from typing import Optional

from app.services.llm import llm_client

SCORING_SYSTEM_PROMPT = """
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

SCORING_SCHEMA = {
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


async def score_company(
    company_name: str,
    summary: str,
    ticker: Optional[str] = None,
) -> dict:
    """
    Score a company based on AI exposure from filing summary.

    Args:
        company_name: Name of the company
        summary: AI-related summary from SEC filings
        ticker: Stock ticker (optional)

    Returns:
        dict with scoring results including scores, reasoning, and final_score
    """
    user_prompt = f"""
Company: {company_name}
Ticker: {ticker or 'N/A'}
Context (AI-related summary from filings): {summary}

Return JSON exactly as instructed in the system prompt.
"""

    response = await llm_client.create_completion(
        messages=[
            {"role": "system", "content": SCORING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ai_score_response",
                "schema": SCORING_SCHEMA,
            },
        },
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except Exception as e:
        result = {
            "error": "Invalid JSON",
            "raw": response.choices[0].message.content,
            "exception": str(e),
        }

    return result
