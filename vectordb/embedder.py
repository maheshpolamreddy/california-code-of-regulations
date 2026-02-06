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
        # Check EMBEDDING_MODEL to determine which client to use
        if "sentence-transformers" in config.EMBEDDING_MODEL.lower():
            # LAZY LOADING: Don't load model at init to save memory on startup
            # Extract model name from config (e.g., "sentence-transformers/all-MiniLM-L6-v2" -> "all-MiniLM-L6-v2")
            self.model_name = config.EMBEDDING_MODEL.split("/")[-1] if "/" in config.EMBEDDING_MODEL else config.EMBEDDING_MODEL
            self.client_type = "sentence-transformers"
            self.client = None  # Will be loaded on first use
            vectordb_logger.info(f"Configured Sentence-Transformers for embeddings: {self.model_name} (lazy loading)")
        elif "gemini" in config.EMBEDDING_MODEL.lower():
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.client_type = "gemini"
            self.client = genai
            self.model_name = None
            vectordb_logger.info("Using Google Gemini for embeddings")
        else:
            # Use OpenAI
            from openai import OpenAI
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.client_type = "openai"
            self.model_name = None
            vectordb_logger.info("Using OpenAI for embeddings")
        
        # Use simple splitting for sentence-transformers (doesn't need strict token counting)
        self.model = config.EMBEDDING_MODEL
        self.max_tokens = config.CHUNK_SIZE
        self.overlap_tokens = config.CHUNK_OVERLAP
    
    def _ensure_model_loaded(self):
        """Lazy-load sentence-transformers model on first use (saves startup memory)"""
        if self.client_type == "sentence-transformers" and self.client is None:
            from sentence_transformers import SentenceTransformer
            vectordb_logger.info(f"Loading Sentence-Transformers model: {self.model_name}...")
            self.client = SentenceTransformer(self.model_name)
            vectordb_logger.info("✅ Model loaded successfully!")
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text. For sentence-transformers, use word count approximation."""
        if self.client_type == "sentence-transformers":
            # Approximate: 1 token ≈ 0.75 words
            return int(len(text.split()) * 1.33)
        else:
            # Use tiktoken for OpenAI/Gemini
            import tiktoken
            encoding = tiktoken.encoding_for_model("text-embedding-3-small")
            return len(encoding.encode(text))
    
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
        if self.client_type == "sentence-transformers":
            # Simple word-based chunking for sentence-transformers
            words = text.split()
            if len(words) <= self.max_tokens:
                return [{
                    'text': text,
                    'metadata': metadata or {},
                    'chunk_index': 0,
                    'total_chunks': 1
                }]
            
            chunks = []
            start = 0
            chunk_index = 0
            
            while start < len(words):
                end = start + self.max_tokens
                chunk_words = words[start:end]
                chunk_text = ' '.join(chunk_words)
                
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata['chunk_index'] = chunk_index
                chunk_metadata['is_chunked'] = True
                
                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_metadata,
                    'chunk_index': chunk_index,
                    'total_chunks': 0
                })
                
                start += self.max_tokens - self.overlap_tokens
                chunk_index += 1
            
            for chunk in chunks:
                chunk['total_chunks'] = len(chunks)
                chunk['metadata']['total_chunks'] = len(chunks)
            
            vectordb_logger.info(f"Split text into {len(chunks)} chunks")
            return chunks
        else:
            # Token-based chunking for OpenAI/Gemini
            import tiktoken
            encoding = tiktoken.encoding_for_model("text-embedding-3-small")
            tokens = encoding.encode(text)
            chunks = []
            
            if len(tokens) <= self.max_tokens:
                return [{
                    'text': text,
                    'metadata': metadata or {},
                    'chunk_index': 0,
                    'total_chunks': 1
                }]
            
            start = 0
            chunk_index = 0
            
            while start < len(tokens):
                end = start + self.max_tokens
                chunk_tokens = tokens[start:end]
                chunk_text = encoding.decode(chunk_tokens)
                
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata['chunk_index'] = chunk_index
                chunk_metadata['is_chunked'] = True
                
                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_metadata,
                    'chunk_index': chunk_index,
                    'total_chunks': 0
                })
                
                start += self.max_tokens - self.overlap_tokens
                chunk_index += 1
            
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
            Embedding vector (384 dims for sentence-transformers, 768 for Gemini, 1536 for OpenAI)
        """
        try:
            if self.client_type == "sentence-transformers":
                # Lazy-load model on first use
                self._ensure_model_loaded()
                # Use sentence-transformers (local, no API)
                embedding = self.client.encode(text, convert_to_numpy=True).tolist()
            elif self.client_type == "gemini":
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
