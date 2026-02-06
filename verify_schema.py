from vectordb.supabase_client import SupabaseVectorDB
import json

db = SupabaseVectorDB()
print("Verifying schema...")

test_record = {
    "section_url": "test_verification_url",
    "embedding": [0.1] * 384,  # 384 dimensions
    "citation": "Test Citation",
    "content_markdown": "Test content"
}

try:
    print("Attempting to insert 384-dim vector...")
    db.upsert_section(test_record)
    print("✅ SUCCESS: Schema accepts 384 dimensions.")
    # Clean up
    db.client.table("ccr_sections").delete().eq("section_url", "test_verification_url").execute()
except Exception as e:
    print(f"❌ FAILURE: {e}")
