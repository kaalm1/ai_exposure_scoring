from .chunker import chunk_text
from .summarizer import summarize_chunk


async def process_filing(text: str) -> str:
    chunks = chunk_text(text, max_tokens=2000)
    summaries = []
    for chunk in chunks:
        summary = await summarize_chunk(chunk)
        summaries.append(summary)

    combined = "\n".join(summaries)

    # compress again to final ~2k-token summary
    final_summary = await summarize_chunk(combined)
    return final_summary
