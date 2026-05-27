from agent.compliance_advisor import ComplianceAdvisor
from vectordb.pinecone_client import PineconeVectorDB
import json

# Initialize
advisor = ComplianceAdvisor()
db = PineconeVectorDB()

query = "What are the requirements for ADA bathrooms?"
# buffer output to file
with open("final_results.txt", "w", encoding="utf-8") as f:
    f.write(f"🔍 Query: {query}\n")
    f.write("-" * 50 + "\n")

    # 1. Retrieve sections (to show citations)
    f.write("📥 Retrieving matched sections...\n")
    results = advisor.retriever.retrieve(query, top_k=5)

    f.write(f"\n✅ Found {len(results)} relevant citations:\n")
    for i, section in enumerate(results):
        # Handle nested metadata from new schema
        citation = section.get('citation') or section.get('metadata', {}).get('citation', 'Unknown')
        url = section.get('url') or section.get('section_url') or section.get('metadata', {}).get('url', 'Unknown')
        
        f.write(f"   {i+1}. {citation}\n")
        f.write(f"      Source: {url}\n")
        f.write(f"      Score: {section.get('similarity', 0):.4f}\n")

    # 2. Get Answer
    f.write("\n🤖 Generating Answer...\n")
    response = advisor.answer_query(query)
    f.write("\n📝 Final Answer:\n")
    f.write("-" * 50 + "\n")
    f.write(response['answer'] + "\n")
    f.write("-" * 50 + "\n")

print("Done. Check final_results.txt")
