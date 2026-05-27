from vectordb.pinecone_client import PineconeVectorDB
import config

try:
    db = PineconeVectorDB()
    print("Verifying Pinecone DB Content...")

    count = db.count_sections()
    print(f"Count: {count}")

    # Try listing indexes to verify general connection
    indexes = db.client.list_indexes()
    print(f"Indexes: {[idx.name for idx in indexes]}")

    # Run a test query with a dummy zero vector
    print("Testing similarity search query...")
    vec = [0.0] * config.EMBEDDING_DIMENSION
    res = db.search_similar(vec, limit=5, min_similarity=-1.0)
    print(f"Query found: {len(res)} items")
    if res:
        print(f"Top citation: {res[0].get('citation')}")
        print(f"Top URL: {res[0].get('url')}")
except Exception as e:
    print(f"Verification Failed: {e}")
