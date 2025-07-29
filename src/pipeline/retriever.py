import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pinecone_env = os.environ.get("PINECONE_ENV")
index_name = "hackrx"  # change if needed

if not pinecone_api_key or not pinecone_env:
    raise ValueError("PINECONE_API_KEY or PINECONE_ENV not set in .env")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(index_name)

# Load embedding model (must match embedder.py)
model = SentenceTransformer("all-MiniLM-L6-v2")


def retrieve_similar_chunks(query: str, top_k: int = 5):
    """
    Given a user query, retrieve top_k most relevant text chunks from Pinecone.
    Returns a list of dicts with 'text' and 'metadata'.
    """
    # Embed query
    query_embedding = model.encode(query).tolist()

    # Query Pinecone index
    result = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )

    retrieved = [
        {
            "score": match["score"],
            "text": match["metadata"].get("text", "N/A"),
            "metadata": match["metadata"]
        }
        for match in result["matches"]
    ]

    return retrieved
