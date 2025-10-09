# app/services/sec_filing/scorer.py

import json
import re
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

**OUTPUT FORMAT**:
YOU MUST respond with ONLY valid JSON. No markdown code blocks, no explanations, no extra text.

For "ai_proportion", use ONE of: "Minimal", "Moderate", "Substantial", "Core"
For "business_role", use ONE of: "Core", "Supporting", "Experimental"

Return exactly this structure:

{
  "company": "Company Name",
  "ai_proportion": "Minimal",
  "business_role": "Core",
  "scores": {
    "core_dependence": 0.0,
    "revenue_from_ai": 0.0,
    "strategic_investment": 0.0,
    "ecosystem_dependence": 0.0,
    "market_perception": 0.0
  },
  "reasoning": {
    "core_dependence": "Reasoning text - cite specific evidence from filing",
    "revenue_from_ai": "Reasoning text - cite specific evidence from filing",
    "strategic_investment": "Reasoning text - cite specific evidence from filing",
    "ecosystem_dependence": "Reasoning text - cite specific evidence from filing",
    "market_perception": "Reasoning text - cite specific evidence from filing"
  },
  "final_score": 0.0
}

Final Score = (0.4*core_dependence + 0.25*revenue_from_ai + 
               0.2*strategic_investment + 0.1*ecosystem_dependence + 
               0.05*market_perception)

IMPORTANT: Return ONLY the JSON object. No ```json``` markers, no explanations.
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


def parse_llm_json(response_text: str) -> dict:
    """
    Parse JSON from LLM response, handling markdown blocks and malformed JSON.

    Args:
        response_text: Raw response from LLM

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: If JSON cannot be parsed
    """
    # Remove markdown code blocks if present
    text = re.sub(r"```json\s*|\s*```", "", response_text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to extract JSON object from text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(
            f"Failed to parse JSON from response: {e}\nResponse: {response_text[:500]}"
        )


async def score_company(
    company_name: str,
    summary: str,
    ticker: Optional[str] = None,
    llm_provider: Optional[str] = None,
) -> dict:
    """
    Score a company based on AI exposure from filing summary.

    Args:
        company_name: Name of the company
        summary: AI-related summary from SEC filings
        ticker: Stock ticker (optional)
        llm_provider: Provider to use for LLM (optional, auto-detected if not provided)

    Returns:
        dict with scoring results including scores, reasoning, and final_score
    """
    # Auto-detect provider if not provided
    if not llm_provider:
        try:
            llm_provider = llm_client._manager.providers[
                llm_client._manager.current_provider_idx
            ].name.value
        except (AttributeError, IndexError):
            llm_provider = "unknown"

    user_prompt = f"""
Company: {company_name}
Ticker: {ticker or 'N/A'}
Context (AI-related summary from filings): {summary}

Return JSON exactly as instructed in the system prompt. No markdown, no explanations.
"""

    # Determine response format based on provider
    if llm_provider and llm_provider.lower() == "nvidia":
        # Nvidia only supports json_object, not json_schema
        response_format = {"type": "json_object"}
    else:
        # OpenAI and other providers support json_schema
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "ai_score_response",
                "schema": SCORING_SCHEMA,
            },
        }

    try:
        response = await llm_client.create_completion(
            messages=[
                {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format=response_format,
        )

        result = parse_llm_json(response.choices[0].message.content)
        return result

    except ValueError as e:
        # JSON parsing error
        return {
            "error": "Invalid JSON",
            "raw": (
                response.choices[0].message.content
                if "response" in locals()
                else "No response"
            ),
            "exception": str(e),
        }
    except Exception as e:
        # Other errors (API errors, etc.)
        return {
            "error": "LLM completion failed",
            "exception": str(e),
        }
