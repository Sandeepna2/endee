import os
import json
from sentence_transformers import SentenceTransformer
from endee_client import EndeeClient

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
COLLECTION_NAME = "semantic_docs"
MODEL_NAME = "all-MiniLM-L6-v2"
DOC_MAP_FILE = os.path.join(BASE_DIR, "doc_map.json")

def main():
    print("Initializing embedding model...")
    model = SentenceTransformer(MODEL_NAME)
    
    print("Initializing Endee client...")
    endee_host = os.getenv("ENDEE_HOST", "localhost")
    client = EndeeClient(base_url=f"http://{endee_host}:8080/api/v1")
    
    # 1. Read Data
    documents = []
    print("Reading documents...")
    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        if filename.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple chunking by paragraph
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                documents.extend(paragraphs)

    if not documents:
        print("No documents found to ingest.")
        return

    print(f"Found {len(documents)} text chunks to ingest.")

    # 2. Embed Data
    print("Generating embeddings...")
    embeddings = model.encode(documents).tolist()
    dimension = len(embeddings[0])
    print(f"Embedding dimension: {dimension}")

    # 3. Create Collection (Force Refresh)
    print(f"Resetting index '{COLLECTION_NAME}'...")
    client.delete_collection(COLLECTION_NAME)
    
    # Wait for deletion to propagate
    import time
    for _ in range(5):
        if COLLECTION_NAME not in client.list_indexes():
            break
        print("Waiting for deletion...")
        time.sleep(2)

    print(f"Creating index '{COLLECTION_NAME}'...")
    client.create_collection(COLLECTION_NAME, dimension)

    # 4. Insert into Endee & Save Map
    print("Inserting into Endee...")
    payloads = []
    doc_map = {}
    
    for i, doc in enumerate(documents):
        doc_id = str(i)
        payloads.append({"id": doc_id, "text": doc})
        doc_map[doc_id] = doc # Store text in local map since Endee is vector-only

    # Save mapping
    with open(DOC_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(doc_map, f)
    
    success = client.insert(COLLECTION_NAME, embeddings, payloads)
    if success:
        print("Ingestion complete!")
    else:
        print("Ingestion failed.")

if __name__ == "__main__":
    main()
