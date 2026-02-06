from vectordb.supabase_client import SupabaseVectorDB

db = SupabaseVectorDB()
print("Probing Columns...")

try:
    print("Attempt 1: Select *")
    res = db.client.table("ccr_sections").select("*").limit(1).execute()
    if res.data:
        print(f"Success! Keys: {list(res.data[0].keys())}")
    else:
        print("Success! But table is empty.")
except Exception as e:
    print(f"Failed *: {e}")

try:
    print("\nAttempt 2: Select section_url")
    res = db.client.table("ccr_sections").select("section_url").limit(1).execute()
    print("Success section_url!")
except Exception as e:
    print(f"Failed section_url: {e}")

try:
    print("\nAttempt 3: Select url")
    res = db.client.table("ccr_sections").select("url").limit(1).execute()
    print("Success url!")
except Exception as e:
    print(f"Failed url: {e}")
