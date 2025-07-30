import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load environment variables
load_dotenv()
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pinecone_env = os.environ.get("PINECONE_ENV")

if not pinecone_api_key or not pinecone_env:
    raise ValueError("PINECONE_API_KEY or PINECONE_ENV not set in .env")

# Pinecone setup
pc = Pinecone(api_key=pinecone_api_key)
index_name = "hackrx"

# Check if index exists and get its dimensions
existing_indexes = pc.list_indexes().names()
if index_name not in existing_indexes:
    print(f"Creating new index '{index_name}' with 384 dimensions...")
    pc.create_index(
        name=index_name,
        dimension=384,  # Fixed: Changed from 1024 to 384 for all-MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print("✅ Index created successfully!")
else:
    # Check existing index dimensions
    index_info = pc.describe_index(index_name)
    existing_dimension = index_info.dimension
    print(f"📊 Existing index '{index_name}' has {existing_dimension} dimensions")
    
    if existing_dimension != 384:
        print(f"⚠️  DIMENSION MISMATCH!")
        print(f"   Index dimension: {existing_dimension}")
        print(f"   Model dimension: 384 (all-MiniLM-L6-v2)")
        print(f"   You need to either:")
        print(f"   1. Delete the existing index and recreate with 384 dimensions")
        print(f"   2. Use a different embedding model that produces {existing_dimension} dimensions")
        raise ValueError(f"Dimension mismatch: index={existing_dimension}, model=384")

index = pc.Index(index_name)

# Embedding model - produces 384-dimensional embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")

def get_model_dimension():
    """Get the actual dimension of the embedding model"""
    test_embedding = model.encode(["test"])
    return test_embedding.shape[1]

def embed_and_store(docs: list[dict]):
    """
    docs: List of dicts with keys: 'id', 'text', 'metadata'
    Example:
        [
            {
                "id": "doc1-chunk1",
                "text": "This is a chunk of text.",
                "metadata": {"source": "doc1", "chunk_index": 0}
            },
            ...
        ]
    """
    if not docs:
        print("⚠️ No documents to embed.")
        return

    print(f"🔢 Embedding {len(docs)} chunks...")
    
    # Verify model dimension
    model_dim = get_model_dimension()
    print(f"📏 Model produces {model_dim}-dimensional embeddings")
    
    texts = [doc["text"] for doc in docs]
    ids = [doc["id"] for doc in docs]
    metadata = [doc["metadata"] for doc in docs]

    # Get embeddings
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    print(f"✅ Generated embeddings with shape: {embeddings.shape}")

    # Prepare data for upsert
    to_upsert = [
        {
            "id": ids[i],
            "values": embeddings[i].tolist(),
            "metadata": {**metadata[i], "text": texts[i]}  # Store text in metadata for retrieval
        }
        for i in range(len(docs))
    ]

    # Upsert to Pinecone in batches
    print("📤 Uploading to Pinecone...")
    batch_size = 100
    for i in range(0, len(to_upsert), batch_size):
        batch = to_upsert[i:i + batch_size]
        try:
            index.upsert(vectors=batch)
            print(f"✅ Uploaded batch {i//batch_size + 1}/{(len(to_upsert)-1)//batch_size + 1}")
        except Exception as e:
            print(f"❌ Error uploading batch: {e}")
            raise
    
    print("✅ Embeddings stored successfully!")

def delete_and_recreate_index():
    """Delete the existing index and recreate with correct dimensions"""
    try:
        print(f"🗑️  Deleting existing index '{index_name}'...")
        pc.delete_index(index_name)
        print("✅ Index deleted")
        
        print("🏗️  Creating new index with 384 dimensions...")
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print("✅ New index created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error recreating index: {e}")
        return False