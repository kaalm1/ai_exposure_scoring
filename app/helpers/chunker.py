# app/services/sec_filing/chunker.py

from typing import List


def chunk_text(text: str, max_tokens: int = 2000) -> List[str]:
    """
    Split text into chunks of approximately max_tokens.

    Uses a rough word-to-token ratio of 1.3 words per token.

    Args:
        text: The text to chunk
        max_tokens: Maximum tokens per chunk

    Returns:
        List of text chunks
    """
    words = text.split()
    approx_chunk_size = int(max_tokens * 1.3)  # rough word/token ratio

    chunks = [
        " ".join(words[i : i + approx_chunk_size])
        for i in range(0, len(words), approx_chunk_size)
    ]

    return chunks
