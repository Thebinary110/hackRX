import os
from dotenv import load_dotenv
from src.pipeline.document_loader import load_and_clean
from src.pipeline.splitter import chunk_text
from src.pipeline.embedder import embed_and_store
from src.pipeline.retriever import retrieve_similar_chunks
from src.pipeline.formatter import format_context_and_query

load_dotenv()

def process_file(file_bytes: bytes, filename: str, query: str = "What is covered under the health insurance policy?"):
    try:
        # Load and clean
        document = load_and_clean(file_bytes, filename)

        # Chunk
        chunks = chunk_text(document)
        if not chunks:
            raise ValueError("No chunks generated from document.")

        # Embed and store in Pinecone
        embed_and_store(chunks, namespace="default")

        # Retrieve top-k relevant chunks
        results = retrieve_similar_chunks(query, namespace="default", top_k=5)

        # Format for frontend/API
        return format_context_and_query(results)

    except Exception as e:
        print(f"❌ Error processing file {filename}: {e}")
        return []

# Optional CLI entrypoint
def main():
    print("[CLI MODE] Loading documents from ./data ...")

    data_dir = "./data"
    if not os.path.exists(data_dir):
        print(f"❌ Directory {data_dir} not found.")
        return

    documents = []
    for fname in os.listdir(data_dir):
        file_path = os.path.join(data_dir, fname)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                try:
                    result = process_file(f.read(), fname)
                    print(f"\n🔍 Top Results for {fname}:\n")
                    for item in result:
                        print(f"- {item}\n")
                except Exception as e:
                    print(f"⚠️ Skipping {fname}: {e}")

if __name__ == "__main__":
    main()
