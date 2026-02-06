from vectordb.supabase_client import SupabaseVectorDB

db = SupabaseVectorDB()
print("Verifying DB Content...")

count = db.count_sections()
print(f"Count: {count}")

try:
    res = db.client.table("ccr_sections").select("section_url,embedding").limit(1).execute()
    if res.data:
        print(f"Record found: {res.data[0]['section_url']}")
        emb = res.data[0]['embedding']
        if emb:
             print(f"Embedding length: {len(emb)}")
        else:
             print("Embedding is NULL/Empty!")
    else:
        print("No records found in table!")
except Exception as e:
    print(f"Select Failed: {e}")

try:
    print("Testing RPC...")
    # zeros vector
    vec = [0.0] * 384
    res = db.client.rpc("match_ccr_sections", {
        "query_embedding": vec,
        "match_threshold": -1.0,
        "match_count": 5
    }).execute()
    print(f"RPC found: {len(res.data) if res.data else 0} items")
except Exception as e:
    print(f"RPC Failed: {e}")
