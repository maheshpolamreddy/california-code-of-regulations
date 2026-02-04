"""
Embedder Module
Generates text embeddings using OpenAI for CCR sections.
Handles chunking of long sections.
"""

from typing import List, Dict
import tiktoken
from openai import OpenAI
import config
from logger import vectordb_logger

class TextEmbedder:
    """
    Generates embeddings for CCR section content.
    Handles chunking for long texts that exceed token limits.
    """
    
    def __init__(self):
        # Prefer Gemini if available, fallback to OpenAI
        if config.GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.client_type = "gemini"
            self.client = genai
            vectordb_logger.info("Using Google Gemini for embeddings")
        elif config.OPENAI_API_KEY:
            from openai import OpenAI
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.client_type = "openai"
            vectordb_logger.info("Using OpenAI for embeddings")
        else:
            raise ValueError("Neither GEMINI_API_KEY nor OPENAI_API_KEY found in environment")
        
        self.encoding = tiktoken.encoding_for_model("text-embedding-3-small")
        self.model = config.EMBEDDING_MODEL
        self.max_tokens = config.CHUNK_SIZE
        self.overlap_tokens = config.CHUNK_OVERLAP
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[Dict[str, any]]:
        """
        Split long text into chunks with overlap.
        Each chunk preserves metadata.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of dicts with 'text' and 'metadata' keys
        """
        tokens = self.encoding.encode(text)
        chunks = []
        
        if len(tokens) <= self.max_tokens:
            # No chunking needed
            return [{
                'text': text,
                'metadata': metadata or {},
                'chunk_index': 0,
                'total_chunks': 1
            }]
        
        # Split into overlapping chunks
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            end = start + self.max_tokens
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata['chunk_index'] = chunk_index
            chunk_metadata['is_chunked'] = True
            
            chunks.append({
                'text': chunk_text,
                'metadata': chunk_metadata,
                'chunk_index': chunk_index,
                'total_chunks': 0  # Will update after loop
            })
            
            start += self.max_tokens - self.overlap_tokens
            chunk_index += 1
        
        # Update total_chunks for all chunks
        for chunk in chunks:
            chunk['total_chunks'] = len(chunks)
            chunk['metadata']['total_chunks'] = len(chunks)
        
        vectordb_logger.info(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def embed_text(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            task_type: Type of embedding task - "retrieval_document" for indexing, "retrieval_query" for search
            
        Returns:
            Embedding vector (768 dimensions for Gemini, 1536 for OpenAI)
        """
        try:
            if self.client_type == "gemini":
                # Use Gemini embedding with task type
                result = self.client.embed_content(
                    model=self.model,
                    content=text,
                    task_type=task_type  # "retrieval_document" or "retrieval_query"
                )
                embedding = result['embedding']
            else:
                # Use OpenAI embedding (no task type needed)
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                embedding = response.data[0].embedding
            
            vectordb_logger.debug(f"Generated embedding (dim={len(embedding)})")
            return embedding
        except Exception as e:
            vectordb_logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch.
        More efficient than calling embed_text multiple times.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            if self.client_type == "gemini":
                # Gemini embeds one at a time (no batch API yet)
                embeddings = []
                for text in texts:
                    result = self.client.embed_content(
                        model=self.model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
            else:
                # Use OpenAI batch embedding
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                embeddings = [item.embedding for item in response.data]
            
            vectordb_logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings
        except Exception as e:
            vectordb_logger.error(f"Failed to generate batch embeddings: {e}")
            raise
