import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Testing text-embedding-004...")
try:
    result = genai.embed_content(
        model="models/text-embedding-004",
        content="Hello world",
        task_type="retrieval_document"
    )
    print("SUCCESS!")
    print(f"Dimension: {len(result['embedding'])}")
except Exception as e:
    print(f"FAILED: {e}")
