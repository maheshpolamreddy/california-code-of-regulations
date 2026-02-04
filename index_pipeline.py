"""
Index Pipeline
Orchestrates the embedding and indexing of CCR sections into Supabase.
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
import sys
sys.path.append(str(Path(__file__).parent))

import config
from logger import vectordb_logger
from vectordb.embedder import TextEmbedder
from vectordb.supabase_client import SupabaseVectorDB
from models import CCRSection

class IndexPipeline:
    """
    Manages the full indexing pipeline:
    1. Load extracted sections
    2. Generate embeddings (with chunking)
    3. Upload to Supabase with metadata
    """
    
    def __init__(self):
        self.embedder = TextEmbedder()
        self.vectordb = SupabaseVectorDB()
        self.batch_size = 10  # Process in batches for efficiency
        
    def load_extracted_sections(self) -> List[CCRSection]:
        """Load all extracted CCR sections from JSONL file."""
        if not config.EXTRACTED_SECTIONS_FILE.exists():
            raise FileNotFoundError(
                f"Extracted sections file not found: {config.EXTRACTED_SECTIONS_FILE}\n"
                "Please run section_extractor.py first"
            )
        
        sections = []
        with open(config.EXTRACTED_SECTIONS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if 'source_url' not in data and 'section_url' in data:
                        data = {**data, 'source_url': data['section_url']}
                    section = CCRSection(**data)
                    sections.append(section)
        
        vectordb_logger.info(f"Loaded {len(sections)} extracted sections")
        return sections
    
    def prepare_section_for_embedding(self, section: CCRSection) -> str:
        """
        Prepare section text for embedding.
        Combines metadata and content into a searchable representation.
        """
        # Create rich text representation
        text_parts = [
            f"Citation: {section.citation}",
            f"Title: {section.title_name or 'Unknown'}",
            f"Section: {section.section_heading}",
        ]
        
        if section.breadcrumb_path:
            text_parts.append(f"Hierarchy: {section.breadcrumb_path}")
        
        # Add main content
        text_parts.append(f"\nContent:\n{section.content_markdown}")
        
        return "\n".join(text_parts)
    
    def section_to_db_record(
        self,
        section: CCRSection,
        embedding: List[float],
        chunk_index: int = 0,
        total_chunks: int = 1
    ) -> Dict:
        """
        Convert CCRSection to database record format.
        """
        return {
            'section_url': section.source_url,
            'title_number': section.title_number,
            'title_name': section.title_name,
            'division': section.division,
            'chapter': section.chapter,
            'subchapter': section.subchapter,
            'article': section.article,
            'section_number': section.section_number,
            'section_heading': section.section_heading,
            'citation': section.citation,
            'breadcrumb_path': section.breadcrumb_path,
            'content_markdown': section.content_markdown,
            'embedding': embedding,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'retrieved_at': section.retrieved_at.isoformat()
        }
    
    def index_sections(self, sections: List[CCRSection]):
        """
        Index all sections into Supabase.
        Handles chunking, embedding, and batch uploads.
        """
        total_sections = len(sections)
        indexed_count = 0
        failed_count = 0
        
        print(f"\nIndexing {total_sections} CCR sections into Supabase...")
        print(f"Batch size: {self.batch_size}\n")
        
        for i in tqdm(range(0, total_sections, self.batch_size), desc="Indexing batches"):
            batch = sections[i:i + self.batch_size]
            batch_records = []
            
            for section in batch:
                try:
                    # Prepare text for embedding
                    text = self.prepare_section_for_embedding(section)
                    
                    # Check if chunking is needed
                    token_count = self.embedder.count_tokens(text)
                    
                    if token_count > config.CHUNK_SIZE:
                        # Need to chunk
                        chunks = self.embedder.chunk_text(text, metadata={'section_url': section.source_url})
                        
                        # Embed all chunks
                        chunk_texts = [chunk['text'] for chunk in chunks]
                        embeddings = self.embedder.embed_batch(chunk_texts)
                        
                        # Create DB record for each chunk
                        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                            record = self.section_to_db_record(
                                section,
                                embedding,
                                chunk_index=idx,
                                total_chunks=len(chunks)
                            )
                            # Modify URL to make it unique per chunk
                            record['section_url'] = f"{section.source_url}#chunk{idx}"
                            batch_records.append(record)
                    else:
                        # No chunking needed
                        embedding = self.embedder.embed_text(text)
                        record = self.section_to_db_record(section, embedding)
                        batch_records.append(record)
                    
                except Exception as e:
                    vectordb_logger.error(f"Failed to process section {section.citation}: {e}")
                    failed_count += 1
            
            # Batch upsert to Supabase
            if batch_records:
                success_count = self.vectordb.upsert_batch(batch_records)
                indexed_count += success_count
                
                if success_count < len(batch_records):
                    failed_count += len(batch_records) - success_count
        
        print(f"\nIndexing complete!")
        print(f"   Successfully indexed: {indexed_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total in database: {self.vectordb.count_sections()}\n")
        
        vectordb_logger.info(f"Indexing complete: {indexed_count} indexed, {failed_count} failed")
    
    def run(self):
        """Main pipeline execution."""
        print("\n" + "="*70)
        print("CCR COMPLIANCE AGENT - INDEXING PIPELINE")
        print("="*70 + "\n")
        
        # Load sections
        print("Loading extracted sections...")
        sections = self.load_extracted_sections()
        print(f"   Loaded: {len(sections)} sections\n")
        
        # Index sections
        self.index_sections(sections)

def main():
    """Main entry point for indexing pipeline."""
    try:
        pipeline = IndexPipeline()
        pipeline.run()
    except Exception as e:
        print(f"\nError: {e}")
        vectordb_logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()
