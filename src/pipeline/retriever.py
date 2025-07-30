import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pinecone_env = os.environ.get("PINECONE_ENV")
index_name = "hackrx"

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
    Fixed: Removed namespace parameter and improved error handling
    Returns a list of dicts with 'text' and 'metadata'.
    """
    try:
        # Embed query
        query_embedding = model.encode(query).tolist()

        # Query Pinecone index
        result = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )

        # Process results
        retrieved = []
        for match in result["matches"]:
            chunk_data = {
                "score": match["score"],
                "text": match["metadata"].get("text", "N/A"),
                "metadata": match["metadata"]
            }
            retrieved.append(chunk_data)

        return retrieved
    
    except Exception as e:
        print(f"Error retrieving chunks: {e}")
        return []

def retrieve_with_filter(query: str, source_filter: str = None, top_k: int = 5):
    """
    Retrieve chunks with optional source filtering
    """
    try:
        query_embedding = model.encode(query).tolist()
        
        # Build filter if provided
        filter_dict = {}
        if source_filter:
            filter_dict = {"source": {"$eq": source_filter}}
        
        result = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        retrieved = []
        for match in result["matches"]:
            chunk_data = {
                "score": match["score"],
                "text": match["metadata"].get("text", "N/A"),
                "metadata": match["metadata"]
            }
            retrieved.append(chunk_data)
            
        return retrieved
    
    except Exception as e:
        print(f"Error retrieving chunks with filter: {e}")
        return []

def get_index_stats():
    """Get statistics about the Pinecone index"""
    try:
        stats = index.describe_index_stats()
        return {
            "total_vectors": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension", 0),
            "index_fullness": stats.get("index_fullness", 0)
        }
    except Exception as e:
        print(f"Error getting index stats: {e}")
        return {"error": str(e)}

def delete_all_vectors():
    """Delete all vectors from the index (use with caution!)"""
    try:
        index.delete(delete_all=True)
        print("✅ All vectors deleted from index")
        return True
    except Exception as e:
        print(f"Error deleting vectors: {e}")
        return False

def delete_by_source(source_name: str):
    """Delete all vectors from a specific source"""
    try:
        index.delete(filter={"source": {"$eq": source_name}})
        print(f"✅ All vectors from source '{source_name}' deleted")
        return True
    except Exception as e:
        print(f"Error deleting vectors from source {source_name}: {e}")
        return False