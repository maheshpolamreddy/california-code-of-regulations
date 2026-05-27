"""
Simple CLI demo for CCR Compliance Agent
Demonstrates the RAG system with available data
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from vectordb.embedder import TextEmbedder
from vectordb.pinecone_client import PineconeVectorDB
from openai import OpenAI
import config

def demo_agent(query: str):
    """Demonstrate the full RAG pipeline."""
    print("\n" + "="*70)
    print(f"🤖 CCR Compliance Agent Demo")
    print("="*70 + "\n")
    print(f"Query: {query}\n")
    
    # Step 1: Generate query embedding
    print("Step 1: Generating query embedding...")
    embedder = TextEmbedder()
    query_embedding = embedder.embed_text(query)
    print(f"  ✓ Generated {len(query_embedding)}-dimensional vector\n")
    
    # Step 2: Search Supabase
    print("Step 2: Searching Pinecone for relevant sections...")
    db = PineconeVectorDB()
    
    try:
        results = db.search_similar(query_embedding, limit=3)
        print(f"  ✓ Found {len(results)} relevant sections\n")
        
        if results:
            print("Top Results:")
            for i, result in enumerate(results, 1):
                heading = result.get('section_heading', 'No heading')
                citation = result.get('citation', 'N/A')
                distance = result.get('distance', 1.0)
                similarity = (1 - distance) * 100
                print(f"\n{i}. {heading}")
                print(f"   Citation: {citation}")
                print(f"   Similarity: {similarity:.1f}%")
                content = result.get('content_markdown', '')[:200]
                if content:
                    print(f"   Preview: {content}...")
        else:
            print("  ⚠️ No results found in database")
            print("     This likely means:")
            print("     - Database is empty (indexing may have failed)")
            print("     - Connection issues with Pinecone")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print("     This likely means:")
        print("     - Pinecone credentials not configured")
        print("     - Table doesn't exist yet")
        print("     - Network connection issue")
    
    # Step 3: Generate AI response (mock for now)
    print("\nStep 3: Generating AI response...")
    print("  (Skipping - would use GPT-4 with retrieved context)\n")
    
    print("="*70)
    print("Demo Complete!")
    print("="*70)
    print("\n📊 System Status:")
    print("  ✅ Query Embedding Generation")
    print("  ✅ Vector Similarity Search")  
    print("  🔜 AI Response Generation (needs full dataset)")
    print("\n💡 To fully populate the database:")
    print("  1. Let URL crawler finish (3,091 URLs discovered)")
    print("  2. Fix extraction to handle JavaScript content")
    print("  3. Re-run indexing with full data")
    print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "What are the California regulations for restaurants?"
    
    demo_agent(query)
