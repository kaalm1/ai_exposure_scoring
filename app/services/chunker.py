from typing import List

def chunk_text(text: str, max_tokens: int = 2000) -> List[str]:
    words = text.split()
    approx_chunk_size = int(max_tokens * 1.3)  # rough word/token ratio
    return [
        " ".join(words[i:i + approx_chunk_size])
        for i in range(0, len(words), approx_chunk_size)
    ]
