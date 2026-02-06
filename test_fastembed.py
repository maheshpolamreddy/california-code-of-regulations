from fastembed import TextEmbedding
import os

print("Testing FastEmbed...")
try:
    embedding_model = TextEmbedding("BAAI/bge-small-en-v1.5")
    embeddings = list(embedding_model.embed(["Hello World"]))
    print(f"SUCCESS! Shape: {len(embeddings[0])}")
except Exception as e:
    print(f"FAILED: {e}")
