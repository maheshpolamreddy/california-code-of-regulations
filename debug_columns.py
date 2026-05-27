from vectordb.pinecone_client import PineconeVectorDB
import config

try:
    db = PineconeVectorDB()
    print("Probing Pinecone Metadata columns/keys...")
    zero_vec = [0.0] * config.EMBEDDING_DIMENSION
    res = db.search_similar(zero_vec, limit=1, min_similarity=-1.0)
    if res:
        print(f"Success! Keys returned by mapper: {list(res[0].keys())}")
        print(f"Raw metadata keys in Pinecone: {list(res[0]['metadata'].keys())}")
    else:
        print("Success! But Pinecone index search returned no records.")
except Exception as e:
    print(f"Failed probing Pinecone: {e}")
