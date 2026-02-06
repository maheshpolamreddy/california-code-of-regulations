-- Update Supabase Schema for Sentence-Transformers (384 dimensions)
-- Run this in your Supabase SQL Editor

BEGIN;

-- Drop old index and column
DROP INDEX IF EXISTS ccr_sections_embedding_idx;
ALTER TABLE ccr_sections DROP COLUMN IF EXISTS embedding;

-- Add new embedding column with 384 dimensions (sentence-transformers)
ALTER TABLE ccr_sections ADD COLUMN embedding vector(384);

-- Create ivfflat index for 384 dimensions
CREATE INDEX ccr_sections_embedding_idx 
ON ccr_sections 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Update search function for 384 dimensions
CREATE OR REPLACE FUNCTION search_ccr_sections(
  query_embedding vector(384),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
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
  similarity float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    ccr_sections.id,
    ccr_sections.section_url,
    ccr_sections.title_number,
    ccr_sections.title_name,
    ccr_sections.division,
    ccr_sections.chapter,
    ccr_sections.subchapter,
    ccr_sections.article,
    ccr_sections.section_number,
    ccr_sections.section_heading,
    ccr_sections.citation,
    ccr_sections.breadcrumb_path,
    ccr_sections.content_markdown,
    1 - (ccr_sections.embedding <=> query_embedding) as similarity
  FROM ccr_sections
  WHERE 
    (filter_title_number IS NULL OR ccr_sections.title_number = filter_title_number)
    AND 1 - (ccr_sections.embedding <=> query_embedding) > match_threshold
  ORDER BY ccr_sections.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMIT;
