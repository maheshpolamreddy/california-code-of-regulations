-- CCR Compliance Agent - Supabase Schema for Sentence-Transformers Embeddings
-- This sets up the database for 384-dimensional embeddings (sentence-transformers/all-MiniLM-L6-v2)

BEGIN;

TRUNCATE TABLE ccr_sections;

DROP INDEX IF EXISTS ccr_sections_embedding_idx;
ALTER TABLE ccr_sections DROP COLUMN IF EXISTS embedding;
ALTER TABLE ccr_sections ADD COLUMN embedding vector(384);

-- Create ivfflat index (works fine with 384 dims)
CREATE INDEX ccr_sections_embedding_idx 
ON ccr_sections 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

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
