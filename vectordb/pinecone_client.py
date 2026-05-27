"""
Pinecone Client Module
Handles connection to Pinecone database and vector operations.
"""

from typing import List, Dict, Optional
import json
from pinecone import Pinecone, ServerlessSpec
import config
from logger import vectordb_logger

class PineconeVectorDB:
    """
    Manages Pinecone database operations.
    Provides vector similarity search and metadata filtering.
    """
    
    def __init__(self):
        if not config.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY must be set in environment")
        
        self.client = Pinecone(api_key=config.PINECONE_API_KEY)
        self.index_name = config.PINECONE_INDEX_NAME
        
        # Check if index exists, and initialize connection
        # (This will fail fast if offline/unreachable)
        try:
            existing_indexes = [idx.name for idx in self.client.list_indexes()]
            if self.index_name not in existing_indexes:
                vectordb_logger.warning(f"Pinecone index '{self.index_name}' does not exist. Call setup_schema() to create it.")
        except Exception as e:
            vectordb_logger.debug(f"Pinecone ping failed during init: {e}")
            # Raise exception so connection fallback logic handles it
            raise ConnectionError(f"Failed to connect to Pinecone: {e}")
            
        self.index = self.client.Index(self.index_name)
        vectordb_logger.info(f"Connected to Pinecone index: {self.index_name}")

    def setup_schema(self):
        """Create the Pinecone index if it doesn't exist."""
        try:
            existing_indexes = [idx.name for idx in self.client.list_indexes()]
            if self.index_name not in existing_indexes:
                vectordb_logger.info(f"Creating Pinecone index '{self.index_name}'...")
                self.client.create_index(
                    name=self.index_name,
                    dimension=config.EMBEDDING_DIMENSION,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                vectordb_logger.info(f"Pinecone index '{self.index_name}' created successfully")
            else:
                vectordb_logger.info(f"Pinecone index '{self.index_name}' already exists")
        except Exception as e:
            vectordb_logger.error(f"Failed to setup Pinecone schema/index: {e}")
            raise

    def _clean_metadata(self, metadata: dict) -> dict:
        cleaned = {}
        for k, v in metadata.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                cleaned[k] = v
            elif isinstance(v, list):
                cleaned[k] = [str(item) for item in v if item is not None]
            else:
                cleaned[k] = json.dumps(v)
        return cleaned

    def _prepare_pinecone_vector(self, section_data: Dict) -> Dict:
        """
        Prepare record for Pinecone upsert by flattening columns and cleaning metadata.
        """
        # The unique ID is the URL
        vector_id = section_data.get('url') or section_data.get('section_url')
        if not vector_id:
            raise ValueError("Record must have 'url' or 'section_url' for Pinecone ID")

        # Embedding values
        values = section_data.get('embedding')
        if not values:
            raise ValueError("Record must have 'embedding'")

        # Flatten metadata and columns
        raw_meta = {}
        # 1. Add all nested metadata fields if present
        if 'metadata' in section_data and isinstance(section_data['metadata'], dict):
            raw_meta.update(section_data['metadata'])
        # 2. Add top-level fields
        for field in ['url', 'section_no', 'title', 'content', 'section_url', 'section_number', 'section_heading', 'citation', 'breadcrumb_path', 'content_markdown']:
            if field in section_data and section_data[field] is not None:
                raw_meta[field] = section_data[field]

        # Make sure title is mapped to section_heading, etc.
        if 'title' in raw_meta and 'section_heading' not in raw_meta:
            raw_meta['section_heading'] = raw_meta['title']
        if 'section_heading' in raw_meta and 'title' not in raw_meta:
            raw_meta['title'] = raw_meta['section_heading']
        if 'content' in raw_meta and 'content_markdown' not in raw_meta:
            raw_meta['content_markdown'] = raw_meta['content']
        if 'content_markdown' in raw_meta and 'content' not in raw_meta:
            raw_meta['content'] = raw_meta['content_markdown']
        if 'url' in raw_meta and 'section_url' not in raw_meta:
            raw_meta['section_url'] = raw_meta['url']
        if 'section_url' in raw_meta and 'url' not in raw_meta:
            raw_meta['url'] = raw_meta['section_url']

        return {
            "id": vector_id,
            "values": values,
            "metadata": self._clean_metadata(raw_meta)
        }

    def upsert_section(self, section_data: Dict) -> bool:
        """Insert or update a CCR section with embedding."""
        try:
            vector = self._prepare_pinecone_vector(section_data)
            self.index.upsert(vectors=[vector])
            vectordb_logger.debug(f"Upserted section to Pinecone: {section_data.get('citation', 'unknown')}")
            return True
        except Exception as e:
            vectordb_logger.error(f"Failed to upsert section to Pinecone: {e}")
            return False

    def upsert_batch(self, sections_data: List[Dict]) -> int:
        """Batch upsert multiple sections."""
        try:
            vectors = []
            for item in sections_data:
                try:
                    vectors.append(self._prepare_pinecone_vector(item))
                except Exception as ex:
                    vectordb_logger.error(f"Skipping malformed section: {ex}")
            
            # Pinecone recommends upserting in batches of ~100
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                chunk = vectors[i:i + batch_size]
                self.index.upsert(vectors=chunk)
                
            count = len(vectors)
            vectordb_logger.info(f"Batch upserted {count} sections to Pinecone")
            return count
        except Exception as e:
            vectordb_logger.error(f"Failed to batch upsert to Pinecone: {e}")
            with open("LATEST_ERROR.txt", "w") as f:
                f.write(str(e))
            return 0

    def _map_match_to_record(self, match) -> Dict:
        """Helper to convert Pinecone match to the format expected by retrieval code."""
        meta = match.get('metadata', {})
        # Reconstruct the expected row layout
        record = {
            'id': match.get('id'),
            'similarity': match.get('score', 0.0),
            'url': meta.get('url'),
            'section_url': meta.get('section_url') or meta.get('url'),
            'section_no': meta.get('section_no') or meta.get('section_number'),
            'title': meta.get('title') or meta.get('section_heading'),
            'section_heading': meta.get('section_heading') or meta.get('title'),
            'content': meta.get('content') or meta.get('content_markdown'),
            'content_markdown': meta.get('content_markdown') or meta.get('content'),
            'citation': meta.get('citation'),
            'title_number': int(meta.get('title_number')) if meta.get('title_number') is not None else None,
            'breadcrumb_path': meta.get('breadcrumb_path'),
            'metadata': meta
        }
        return record

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        title_number: Optional[int] = None,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """Search for similar sections using vector similarity."""
        try:
            # Build filters
            pinecone_filter = {}
            if title_number is not None:
                pinecone_filter["title_number"] = {"$eq": title_number}
                
            response = self.index.query(
                vector=query_embedding,
                top_k=limit,
                filter=pinecone_filter if pinecone_filter else None,
                include_metadata=True
            )
            
            results = []
            for match in response.get('matches', []):
                score = match.get('score', 0.0)
                # Map score if needed or use as similarity
                if score >= min_similarity:
                    results.append(self._map_match_to_record(match))
                    
            vectordb_logger.info(f"Pinecone search: {len(results)} similar sections")
            return results
        except Exception as e:
            vectordb_logger.error(f"Pinecone Search failed: {e}")
            return []

    def get_section_by_citation(self, citation: str) -> Optional[Dict]:
        """Get a specific section by its citation."""
        try:
            zero_vector = [0.0] * config.EMBEDDING_DIMENSION
            response = self.index.query(
                vector=zero_vector,
                filter={"citation": {"$eq": citation}},
                top_k=1,
                include_metadata=True
            )
            matches = response.get('matches', [])
            if matches:
                return self._map_match_to_record(matches[0])
            return None
        except Exception as e:
            vectordb_logger.error(f"Failed to get section by citation: {e}")
            return None

    def count_sections(self) -> int:
        """Get total number of indexed sections."""
        try:
            stats = self.index.describe_index_stats()
            # total_vector_count holds the total number of vectors in index
            return stats.get('total_vector_count', 0)
        except Exception as e:
            vectordb_logger.error(f"Failed to count sections: {e}")
            return 0
