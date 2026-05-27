"""
Simple indexing pipeline - indexes extracted sections to Pinecone
"""

import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from vectordb.embedder import TextEmbedder
from vectordb.pinecone_client import PineconeVectorDB
import config
from logger import vectordb_logger

def main():
    """Index extracted sections to Pinecone."""
    print("\n🚀 Starting Indexing Pipeline\n")
    
    # Load extracted sections
    print("Loading extracted sections...")
    sections = []
    with open(config.EXTRACTED_SECTIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            sections.append(json.loads(line))
    
    print(f"✓ Loaded {len(sections)} sections\n")
    
    # Initialize embedder and client
    print("Initializing embedder and Pinecone client...")
    embedder = TextEmbedder()
    client = PineconeVectorDB()
    print("✓ Ready\n")
    
    # Process each section
    print(f"Processing {len(sections)} sections...\n")
    success_count = 0
    
    for i, section in enumerate(sections, 1):
        try:
            print(f"[{i}/{len(sections)}] {section['section_heading'][:50]}...")
            
            # Generate embedding
            embedding = embedder.embed_text(section['content_markdown'])
            print(f"  ✓ Generated embedding ({len(embedding)} dimensions)")
            
            # Prepare data for Pinecone
            data = {
                'section_url': section['section_url'],
                'section_number': section.get('section_number'),
                'section_heading': section['section_heading'],
                'citation': section.get('citation'),
                'content_markdown': section['content_markdown'],
                'breadcrumb_path': section.get('breadcrumb_path'),
                'embedding': embedding
            }
            
            # Upsert to Pinecone
            client.upsert_section(data)
            print(f"  ✓ Indexed to Pinecone")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            vectordb_logger.error(f"Failed to index section: {e}")
    
    print(f"\n{'='*70}")
    print(f"✅ Indexing Complete!")
    print(f"   Successfully indexed: {success_count}/{len(sections)}")
    print(f"{'='*70}\n")
    
    print("Next steps:")
    print("1. Run: python cli.py (to test the AI agent)")
    print("2. Or try: python cli.py --query 'regulations for restaurants'\n")

if __name__ == "__main__":
    main()
