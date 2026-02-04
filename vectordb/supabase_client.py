"""
Supabase Client Module
Handles connection to Supabase database and vector operations using pgvector.
"""

from typing import List, Dict, Optional
from supabase import create_client, Client
import config
from logger import vectordb_logger

class SupabaseVectorDB:
    """
    Manages Supabase database operations with pgvector extension.
    Provides vector similarity search and metadata filtering.
    """
    
    def __init__(self):
        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
        
        self.client: Client = create_client(
            config.SUPABASE_URL,
            config.SUPABASE_SERVICE_KEY
        )
        self.table_name = config.SUPABASE_TABLE_NAME
        vectordb_logger.info("Connected to Supabase")
    
    def setup_schema(self):
        """
        Create the ccr_sections table with pgvector extension.
        This should be run once during initial setup.
        
        NOTE: Run this SQL directly in Supabase SQL Editor:
        
        -- Enable pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;
        
        -- Create table
        CREATE TABLE IF NOT EXISTS ccr_sections (
            id BIGSERIAL PRIMARY KEY,
            section_url TEXT UNIQUE NOT NULL,
            title_number INTEGER,
            title_name TEXT,
            division TEXT,
            chapter TEXT,
            subchapter TEXT,
            article TEXT,
            section_number TEXT,
            section_heading TEXT,
            citation TEXT,
            breadcrumb_path TEXT,
            content_markdown TEXT,
            embedding vector(1536),
            chunk_index INTEGER DEFAULT 0,
            total_chunks INTEGER DEFAULT 1,
            retrieved_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Create indexes for vector similarity search
        CREATE INDEX IF NOT EXISTS ccr_sections_embedding_idx 
        ON ccr_sections USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        
        -- Create indexes for metadata filtering
        CREATE INDEX IF NOT EXISTS ccr_sections_title_number_idx ON ccr_sections (title_number);
        CREATE INDEX IF NOT EXISTS ccr_sections_section_number_idx ON ccr_sections (section_number);
        CREATE INDEX IF NOT EXISTS ccr_sections_citation_idx ON ccr_sections (citation);
        """
        vectordb_logger.info("Schema setup instructions logged. Please run SQL in Supabase dashboard.")
        print("\n" + "="*70)
        print("SUPABASE SCHEMA SETUP")
        print("="*70)
        print("Please run the following SQL in your Supabase SQL Editor:")
        print(self.setup_schema.__doc__)
        print("="*70 + "\n")
    
    def upsert_section(self, section_data: Dict) -> bool:
        """
        Insert or update a CCR section with embedding.
        Uses section_url as unique identifier for idempotent upserts.
        
        Args:
            section_data: Dict containing section fields including embedding
            
        Returns:
            True if successful
        """
        try:
            result = self.client.table(self.table_name).upsert(
                section_data,
                on_conflict='section_url'
            ).execute()
            
            vectordb_logger.debug(f"Upserted section: {section_data.get('citation', 'unknown')}")
            return True
            
        except Exception as e:
            vectordb_logger.error(f"Failed to upsert section: {e}")
            return False
    
    def upsert_batch(self, sections_data: List[Dict]) -> int:
        """
        Batch upsert multiple sections.
        More efficient than individual upserts.
        
        Args:
            sections_data: List of section dicts
            
        Returns:
            Number of sections successfully upserted
        """
        try:
            result = self.client.table(self.table_name).upsert(
                sections_data,
                on_conflict='section_url'
            ).execute()
            
            count = len(sections_data)
            vectordb_logger.info(f"Batch upserted {count} sections")
            return count
            
        except Exception as e:
            vectordb_logger.error(f"Failed to batch upsert: {e}")
            return 0
    
    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        title_number: Optional[int] = None,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar sections using vector similarity.
        Uses Supabase RPC (search_ccr_sections) when available; falls back to Python-side search.
        
        Args:
            query_embedding: Query vector (1536 dims)
            limit: Maximum number of results
            title_number: Optional filter by title number
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of matching sections with similarity scores
        """
        try:
            # Prefer native pgvector RPC (run supabase_schema.sql to create search_ccr_sections)
            result = self.client.rpc(
                "search_ccr_sections",
                {
                    "query_embedding": query_embedding,
                    "match_count": limit,
                    "match_threshold": min_similarity,
                    "filter_title_number": title_number,
                },
            ).execute()
            if result.data is not None:
                rows = [dict(row) for row in result.data]
                # Filter by min_similarity
                filtered = [r for r in rows if r.get("similarity", 0) >= min_similarity]
                vectordb_logger.info(f"RPC search: {len(filtered)} similar sections")
                return filtered
        except Exception as rpc_err:
            vectordb_logger.debug(f"RPC search not available, using Python fallback: {rpc_err}")

        # Fallback: fetch candidates and rank in Python
        try:
            query = self.client.table(self.table_name).select("*")
            if title_number is not None:
                query = query.eq("title_number", title_number)
            result = query.limit(1000).execute()
            import numpy as np
            query_vec = np.array(query_embedding)
            results_with_scores = []
            for row in result.data or []:
                if row.get("embedding"):
                    row_vec = np.array(row["embedding"])
                    similarity = float(
                        np.dot(query_vec, row_vec)
                        / (np.linalg.norm(query_vec) * np.linalg.norm(row_vec))
                    )
                    if similarity >= min_similarity:
                        row["similarity"] = similarity
                        results_with_scores.append(row)
            results_with_scores.sort(key=lambda x: x["similarity"], reverse=True)
            top_results = results_with_scores[:limit]
            vectordb_logger.info(f"Python search: {len(top_results)} similar sections")
            return top_results
        except Exception as e:
            vectordb_logger.error(f"Search failed: {e}")
            return []
    
    def get_section_by_citation(self, citation: str) -> Optional[Dict]:
        """Get a specific section by its citation."""
        try:
            result = self.client.table(self.table_name).select('*').eq(
                'citation', citation
            ).limit(1).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            vectordb_logger.error(f"Failed to get section by citation: {e}")
            return None
    
    def count_sections(self) -> int:
        """Get total number of indexed sections."""
        try:
            result = self.client.table(self.table_name).select(
                'id', count='exact'
            ).limit(1).execute()
            return result.count or 0
        except Exception as e:
            vectordb_logger.error(f"Failed to count sections: {e}")
            return 0
