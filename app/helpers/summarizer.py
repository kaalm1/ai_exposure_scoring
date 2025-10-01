# app/services/sec_filing/summarizer.py

from app.services.llm import llm_client

SUMMARY_SYSTEM_PROMPT = """
You are an assistant that extracts AI-related insights from SEC filings.
Focus only on:
- Mentions of AI in products, services, or strategy
- Revenue contribution or customer dependence on AI
- R&D spending, patents, or acquisitions in AI
- Risks or limitations related to AI

Ignore boilerplate. Return a concise summary (<=200 words).
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
