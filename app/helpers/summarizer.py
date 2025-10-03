# app/services/sec_filing/summarizer.py

from app.services.llm import llm_client

SUMMARY_SYSTEM_PROMPT = """
You are an assistant that extracts AI-related insights from SEC filings.

Focus only on substantive AI content in these categories:
- Mentions of AI in products, services, or strategy
- Revenue contribution or customer dependence on AI
- R&D spending, patents, or acquisitions in AI
- Risks or limitations related to AI

**Ignore boilerplate**: Skip generic risk disclosures, forward-looking statement 
disclaimers, and vague mentions without operational substance.

For each chunk, assess:
1. **AI Proportion**: What percentage of this section discusses AI vs other topics?
   - Minimal (<10%): Brief mention, tangential to main content
   - Moderate (10-40%): Regular discussion alongside other topics
   - Substantial (40-70%): Major focus with significant detail
   - Core (>70%): Dominant theme of the section

2. **Business Criticality**: How central is AI to their operations?
   - Core: AI is fundamental to their value proposition/revenue model
   - Supporting: AI enhances existing products/operations but isn't central
   - Experimental: AI is exploratory/future-focused, not yet material

Return format (<=200 words total):
---
AI Proportion: [Minimal/Moderate/Substantial/Core]
Business Role: [Core/Supporting/Experimental]

Summary: [Your concise summary organized by the categories above]
---
"""


async def summarize_chunk(chunk: str) -> str:
    """
    Summarize a single chunk of text using the LLM.

    Args:
        chunk: Text chunk to summarize

    Returns:
        AI-generated summary of the chunk
    """
    resp = await llm_client.create_completion(
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": chunk},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()
