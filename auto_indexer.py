
"""
Auto-Indexer Service
Continuously monitors extracted_sections.jsonl and indexes new content into Supabase.
Runs in the background to provide real-time updates to the UI.
"""

import time
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from index_pipeline import IndexPipeline
import config

def auto_index_loop():
    print("\n" + "="*50)
    print("🔄 REAL-TIME AUTO-INDEXER STARTED")
    print("="*50)
    print("Monitoring for new sections every 60 seconds...\n")

    pipeline = IndexPipeline()
    
    while True:
        try:
            # Run the indexing pipeline
            # The pipeline automatically checks what's new vs what's in DB
            # But normally it re-reads the whole file. 
            # Ideally we would track file pointer, but IndexPipeline uses file read.
            # However, `load_extracted_sections` reads everything.
            # Optimization: check if file size changed?
            
            # Simple approach: Run it. The pipeline handles "upsert" which updates existing/adds new.
            # To be more efficient, we could limit to new items, but current implementation 
            # of index_pipeline.py processes "batches".
            
            # Let's rely on the user's current pipeline logic which is robust but maybe redundant.
            # BUT, we should catch errors so this loop doesn't die.
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for updates...")
            
            # Run indexing (this might be heavy if re-doing work, but ensures consistency)
            # The IndexPipeline logic basically reads sections and upserts them.
            # Upsert is safe (idempotent).
            
            # Since we can't easily modify IndexPipeline to "resume" without code changes,
            # we will blindly run it. It will process all 1300+ sections each time.
            # This is OK for < 10,000 sections.
            
            pipeline = IndexPipeline() # Re-init to clear state if needed
            sections = pipeline.load_extracted_sections()
            
            # Optimization: Check count in DB vs File
            # This is hard because file has duplicates/failures sometimes.
            
            # Just run it.
            pipeline.index_sections(sections)
            
            print(f"✅ Update complete. Waiting 60 seconds...")
            
        except Exception as e:
            print(f"⚠️ Error in auto-indexer: {e}")
        
        # Wait before next run
        time.sleep(10)

if __name__ == "__main__":
    try:
        auto_index_loop()
    except KeyboardInterrupt:
        print("\n🛑 Auto-indexer stopped.")
