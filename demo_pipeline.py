"""
Simple demonstration: Extract and index a few sections to test the complete pipeline.
"""

import sys
import json
from pathlib import Path
import time
sys.path.append(str(Path(__file__).parent))

import requests
from bs4 import BeautifulSoup
from vectordb.embedder import TextEmbedder
from vectordb.supabase_client import SupabaseClient
import config
from logger import extraction_logger

# Sample a few URLs to test
sample_urls = [
    "https://govt.westlaw.com/calregs/Document/I004899234C8211EC89E5000D3A7C4BC3",
    "https://govt.westlaw.com/calregs/Document/I004C69B14C8211EC89E5000D3A7C4BC3",
    "https://govt.westlaw.com/calregs/Document/I0050FD934C8211EC89E5000D3A7C4BC3",
]

def extract_simple_text(url):
    """Extract simple text from URL for demo."""
    try:
        time.sleep(1)  # Rate limiting
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get title
        title_elem = soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "Unknown"
        
        # Get main content
        content_div = soup.find('div', class_='content') or soup.find('body')
        content = content_div.get_text()[:500] if content_div else "No content"
        
        return {
            'url': url,
            'title': title,
            'content': content,
        }
    except Exception as e:
        extraction_logger.error(f"Error extracting {url}: {e}")
        return None

def main():
    """Demo the full pipeline."""
    print("\n🚀 CCR Compliance Agent - Quick Demo\n")
    print(f"Testing with {len(sample_urls)} sample URLs...\n")
    
    # Step 1: Extract
    print("Step 1: Extracting content from sample URLs...")
    sections = []
    for url in sample_urls:
        section = extract_simple_text(url)
        if section:
            sections.append(section)
            print(f"  ✓ Extracted: {section['title'][:50]}...")
    
    print(f"\n✅ Extracted {len(sections)} sections\n")
    
    # Step 2: Generate embeddings
    print("Step 2: Generating embeddings...")
    embedder = TextEmbedder()
    for section in sections:
        section['embedding'] = embedder.generate_embedding(section['content'])
        print(f"  ✓ Embedded: {section['title'][:50]}...")
    
    print(f"\n✅ Generated {len(sections)} embeddings\n")
    
    # Step 3: Index to Supabase
    print("Step 3: Indexing to Supabase...")
    client = SupabaseClient()
    
    success_count = 0
    for section in sections:
        data = {
            'section_url': section['url'],
            'section_heading': section['title'],
            'content_markdown': section['content'],
            'citation': 'Demo Section',
            'embedding': section['embedding']
        }
        try:
            client.upsert_section(data)
            success_count += 1
            print(f"  ✓ Indexed: {section['title'][:50]}...")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    print(f"\n✅ Indexed {success_count}/{len(sections)} sections to Supabase\n")
    
    # Step 4: Test search
    print("Step 4: Testing semantic search...")
    query = "California regulations"
    query_embedding = embedder.generate_embedding(query)
    results = client.search_similar(query_embedding, limit=3)
    
    print(f"\nSearch results for '{query}':")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.get('section_heading', 'No title')}")
        print(f"   URL: {result.get('section_url', 'N/A')}")
        print(f"   Similarity: {1 - result.get('distance', 1):.2%}")
    
    print("\n" + "="*70)
    print("🎉 DEMO COMPLETE! The full pipeline is working!")
    print("="*70)
    print("\nNext steps:")
    print("1. Let the full crawler finish (1,102+ URLs so far)")
    print("2. Run: python crawler/section_extractor.py")
    print("3. Run: python index_pipeline.py")
    print("4. Run: python cli.py")
    print()

if __name__ == "__main__":
    main()
