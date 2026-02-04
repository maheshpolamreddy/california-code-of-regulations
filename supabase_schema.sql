-- CCR Compliance Agent - Supabase Database Schema
-- Run this SQL in your Supabase SQL Editor

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create CCR sections table with hierarchical metadata and vector embeddings
CREATE TABLE IF NOT EXISTS ccr_sections (
    id BIGSERIAL PRIMARY KEY,
    section_url TEXT UNIQUE NOT NULL,
    
    -- Hierarchical metadata
    title_number INTEGER,
    title_name TEXT,
    division TEXT,
    chapter TEXT,
    subchapter TEXT,
    article TEXT,
    
    -- Section identifiers
    section_number TEXT,
    section_heading TEXT,
    citation TEXT,
    breadcrumb_path TEXT,
    
    -- Content
    content_markdown TEXT,
    
    -- Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)
    embedding vector(1536),
    
    -- Chunking metadata
    chunk_index INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 1,
    
    -- Timestamp
    retrieved_at TIMESTAMP DEFAULT NOW()
);

-- Create vector similarity search index using ivfflat
-- This enables fast cosine similarity searches
CREATE INDEX IF NOT EXISTS ccr_sections_embedding_idx 
ON ccr_sections USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create B-tree indexes for metadata filtering
CREATE INDEX IF NOT EXISTS ccr_sections_title_number_idx 
ON ccr_sections (title_number);

CREATE INDEX IF NOT EXISTS ccr_sections_citation_idx 
ON ccr_sections (citation);

CREATE INDEX IF NOT EXISTS ccr_sections_section_number_idx 
ON ccr_sections (section_number);

-- RPC: Vector similarity search with optional metadata filter (title_number)
-- Call from app: supabase.rpc('search_ccr_sections', { query_embedding: [...], match_limit: 10, filter_title_number: null })
CREATE OR REPLACE FUNCTION search_ccr_sections(
    query_embedding vector(1536),
    match_limit int DEFAULT 10,
    filter_title_number int DEFAULT NULL
)
RETURNS TABLE (
    id bigint,
    section_url text,
    title_number int,
    title_name text,
    division text,
    chapter text,
    subchapter text,
    article text,
    section_number text,
    section_heading text,
    citation text,
    breadcrumb_path text,
    content_markdown text,
    chunk_index int,
    total_chunks int,
    retrieved_at timestamptz,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.section_url,
        c.title_number,
        c.title_name,
        c.division,
        c.chapter,
        c.subchapter,
        c.article,
        c.section_number,
        c.section_heading,
        c.citation,
        c.breadcrumb_path,
        c.content_markdown,
        c.chunk_index,
        c.total_chunks,
        c.retrieved_at,
        (1 - (c.embedding <=> query_embedding))::float AS similarity
    FROM ccr_sections c
    WHERE c.embedding IS NOT NULL
      AND (filter_title_number IS NULL OR c.title_number = filter_title_number)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_limit;
END;
$$;

-- Verify table was created
SELECT 'Schema created successfully!' AS status;
