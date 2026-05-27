from vectordb.pinecone_client import PineconeVectorDB
import config

try:
    db = PineconeVectorDB()
    print("Verifying Pinecone schema...")
    
    test_record = {
        "section_url": "test_verification_url",
        "embedding": [0.1] * config.EMBEDDING_DIMENSION,
        "citation": "Test Citation",
        "content_markdown": "Test content"
    }
    
    print(f"Attempting to insert test vector ({config.EMBEDDING_DIMENSION} dims) into Pinecone...")
    db.upsert_section(test_record)
    print("✅ SUCCESS: Upserted test vector into Pinecone.")
    
    # Clean up
    print("Cleaning up verification record...")
    db.index.delete(ids=["test_verification_url"])
    print("✅ SUCCESS: Verification record deleted.")
except Exception as e:
    print(f"❌ FAILURE: {e}")
