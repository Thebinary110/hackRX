from typing import List, Dict

def format_context_and_query(retrieved_chunks: List[Dict], user_query: str) -> str:
    """
    Format the retrieved context and query into a single string prompt
    suitable for LLM input.
    
    Args:
        retrieved_chunks: List of dictionaries with "text" keys (from retriever.py).
        user_query: Original query string from user.
    
    Returns:
        A formatted string prompt for LLM consumption.
    """
    context_blocks = []
    for i, chunk in enumerate(retrieved_chunks):
        context = chunk.get("text", "").strip()
        if context:
            context_blocks.append(f"[{i+1}] {context}")

    if not context_blocks:
        context_blocks.append("[No relevant context retrieved]")

    context_str = "\n\n".join(context_blocks)

    formatted_prompt = f"""You are an expert assistant. Use the following retrieved context to answer the user's question.
    
Context:
{context_str}

Question:
{user_query}

Answer:"""

    return formatted_prompt
