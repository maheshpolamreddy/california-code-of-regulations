from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("Testing OpenAI embeddings...")
try:
    resp = client.embeddings.create(
        input="test",
        model="text-embedding-3-small"
    )
    print("SUCCESS!")
except Exception as e:
    print(f"FAILED: {e}")
