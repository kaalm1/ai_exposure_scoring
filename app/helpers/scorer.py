# app/services/sec_filing/scorer.py

import json
from typing import Optional

from app.services.llm import llm_client

SCORING_SYSTEM_PROMPT = """
You are an expert financial analyst. 
Score companies on AI exposure using this rubric.

**CRITICAL SCORING PRINCIPLES**:
1. **Weight by centrality**: A company with "Core" AI involvement and "Substantial" 
   proportion should score much higher than one with "Experimental" and "Minimal"

2. **Quantitative evidence matters**: Explicit revenue figures, customer counts, 
   or R&D spending tied to AI should increase scores significantly

3. **Depth over breadth**: One core AI product generating revenue beats ten 
   vague mentions of "exploring AI capabilities"

4. **Strategic commitment**: Multi-year investments, acquisitions, dedicated teams 
   signal higher exposure than general statements about "leveraging AI"

5. **Relative importance**: If AI appears in only 5% of the filing, even substantial 
   capabilities should be scored conservatively

SCORING RUBRIC:
- **core_dependence** (0-10): Is AI fundamental to their business model?
  - 0-3: Minimal/no AI dependency
  - 4-6: AI enhances but isn't required for core operations
  - 7-10: Company's value proposition relies heavily on AI

- **revenue_from_ai** (0-10): Quantified revenue contribution
  - 0-3: No clear revenue attribution or "exploring opportunities"
  - 4-6: AI features in products but revenue not quantified
  - 7-10: Clear data on AI-driven revenue or customer adoption

- **strategic_investment** (0-10): Resource commitment to AI
  - 0-3: Generic mentions of innovation
  - 4-6: Dedicated teams/budget but not quantified
  - 7-10: Major acquisitions, disclosed R&D spending, patent portfolios

- **ecosystem_dependence** (0-10): Reliance on AI infrastructure/platforms
  - 0-3: No significant dependencies
  - 4-6: Uses AI tools/platforms from others
  - 7-10: Core supplier to AI ecosystem or depends on AI platforms

- **market_perception** (0-10): How is company positioned re: AI?
  - 0-3: Not associated with AI in market positioning
  - 4-6: Mentions AI in product marketing
  - 7-10: Known as AI-first company or AI market leader

Return a JSON object **exactly in this structure**:

{
  "company": "Company Name",
  "ai_proportion": "Minimal/Moderate/Substantial/Core",
  "business_role": "Core/Supporting/Experimental",
  "scores": {
    "core_dependence": float,          # 0-10
    "revenue_from_ai": float,          # 0-10
    "strategic_investment": float,     # 0-10
    "ecosystem_dependence": float,     # 0-10
    "market_perception": float          # 0-10
  },
  "reasoning": {
    "core_dependence": "Reasoning text - cite specific evidence from filing",
    "revenue_from_ai": "Reasoning text - cite specific evidence from filing",
    "strategic_investment": "Reasoning text - cite specific evidence from filing",
    "ecosystem_dependence": "Reasoning text - cite specific evidence from filing",
    "market_perception": "Reasoning text - cite specific evidence from filing"
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
        "ai_proportion": {
            "type": "string",
            "enum": ["Minimal", "Moderate", "Substantial", "Core"],
        },
        "business_role": {
            "type": "string",
            "enum": ["Core", "Supporting", "Experimental"],
        },
        "scores": {
            "type": "object",
            "properties": {
                "core_dependence": {"type": "number", "minimum": 0, "maximum": 10},
                "revenue_from_ai": {"type": "number", "minimum": 0, "maximum": 10},
                "strategic_investment": {"type": "number", "minimum": 0, "maximum": 10},
                "ecosystem_dependence": {"type": "number", "minimum": 0, "maximum": 10},
                "market_perception": {"type": "number", "minimum": 0, "maximum": 10},
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
    "required": [
        "company",
        "ai_proportion",
        "business_role",
        "scores",
        "reasoning",
        "final_score",
    ],
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
