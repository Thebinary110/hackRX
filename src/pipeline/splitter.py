import tiktoken
from typing import List, Dict
import hashlib

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
    model: str = ENCODER_NAME,
    source_filename: str = "unknown"
) -> List[Dict[str, any]]:
    """
    Fixed: Now returns list of dictionaries with proper format for embedder
    """
    if not text or not text.strip():
        return []
    
    encoding = tiktoken.get_encoding(model)
    tokens = encoding.encode(text)
    
    if len(tokens) == 0:
        return []

    chunks = []
    start = 0
    chunk_index = 0
    
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        # Skip empty chunks
        if chunk_text.strip():
            # Generate unique ID for each chunk
            chunk_id = f"{source_filename}-chunk-{chunk_index}"
            
            # Create chunk dictionary in expected format
            chunk_dict = {
                "id": chunk_id,
                "text": chunk_text.strip(),
                "metadata": {
                    "source": source_filename,
                    "chunk_index": chunk_index,
                    "start_token": start,
                    "end_token": end,
                    "token_count": len(chunk_tokens)
                }
            }
            chunks.append(chunk_dict)
            chunk_index += 1
        
        start += chunk_size - chunk_overlap

    return chunks

def smart_chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    source_filename: str = "unknown"
) -> List[Dict[str, any]]:
    """
    Advanced chunking that tries to respect sentence boundaries
    """
    if not text or not text.strip():
        return []
    
    # First, try to split by paragraphs
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    chunk_index = 0
    
    encoding = tiktoken.get_encoding(ENCODER_NAME)
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Check if adding this paragraph would exceed chunk size
        test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
        test_tokens = len(encoding.encode(test_chunk))
        
        if test_tokens <= chunk_size:
            current_chunk = test_chunk
        else:
            # Save current chunk if it exists
            if current_chunk.strip():
                chunk_id = f"{source_filename}-chunk-{chunk_index}"
                chunks.append({
                    "id": chunk_id,
                    "text": current_chunk.strip(),
                    "metadata": {
                        "source": source_filename,
                        "chunk_index": chunk_index,
                        "token_count": len(encoding.encode(current_chunk))
                    }
                })
                chunk_index += 1
            
            # Start new chunk with current paragraph
            if len(encoding.encode(paragraph)) <= chunk_size:
                current_chunk = paragraph
            else:
                # Paragraph is too long, split it using token-based chunking
                para_chunks = chunk_text(paragraph, chunk_size, chunk_overlap, ENCODER_NAME, source_filename)
                for i, para_chunk in enumerate(para_chunks):
                    para_chunk["id"] = f"{source_filename}-chunk-{chunk_index}"
                    para_chunk["metadata"]["chunk_index"] = chunk_index
                    chunks.append(para_chunk)
                    chunk_index += 1
                current_chunk = ""
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunk_id = f"{source_filename}-chunk-{chunk_index}"
        chunks.append({
            "id": chunk_id,
            "text": current_chunk.strip(),
            "metadata": {
                "source": source_filename,
                "chunk_index": chunk_index,
                "token_count": len(encoding.encode(current_chunk))
            }
        })
    
    return chunks