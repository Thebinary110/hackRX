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

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=hackrx,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=us-east-1)
    )

index = pc.Index(index_name)

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


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
    texts = [doc["text"] for doc in docs]
    ids = [doc["id"] for doc in docs]
    metadata = [doc["metadata"] for doc in docs]

    # Get embeddings
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    # Prepare data for upsert
    to_upsert = [
        {
            "id": ids[i],
            "values": embeddings[i].tolist(),
            "metadata": metadata[i]
        }
        for i in range(len(docs))
    ]

    # Upsert to Pinecone
    print("📤 Uploading to Pinecone...")
    index.upsert(vectors=to_upsert)
    print("✅ Embeddings stored successfully.")
