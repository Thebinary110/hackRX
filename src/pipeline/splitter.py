import tiktoken
from typing import List

ENCODER_NAME = "cl100k_base" 
DEFAULT_CHUNK_SIZE = 400
DEFAULT_CHUNK_OVERLAP = 50

def num_tokens(text: str, model: str = ENCODER_NAME) -> int:
    encoding = tiktoken.get_encoding(model)
    return len(encoding.encode(text))

def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    model: str = ENCODER_NAME
) -> List[str]:
    encoding = tiktoken.get_encoding(model)
    tokens = encoding.encode(text)

    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        start += chunk_size - chunk_overlap

    return chunks
