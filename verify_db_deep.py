from vectordb.pinecone_client import PineconeVectorDB
import config

try:
    db = PineconeVectorDB()
    print("Verifying Pinecone DB Content (Deep Check)...")

    # 1. Count & Index Stats
    print("\n--- Index Stats ---")
    stats = db.index.describe_index_stats()
    print(f"Stats raw response: {stats}")
    print(f"Total Vector Count: {stats.get('total_vector_count', 0)}")

    # 2. Fetch a sample record by list query or dummy search
    print("\n--- Fetch Sample Record ---")
    zero_vec = [0.0] * config.EMBEDDING_DIMENSION
    results = db.search_similar(zero_vec, limit=1, min_similarity=-1.0)
    if results:
        sample = results[0]
        print(f"Record ID: {sample.get('id')}")
        print(f"Citation: {sample.get('citation')}")
        print(f"Title: {sample.get('title')}")
        print(f"Content preview: {sample.get('content_markdown', '')[:100]}...")
    else:
        print("No records retrieved from index search.")

except Exception as e:
    print(f"❌ Deep Verification Failed: {e}")
