-- CCR Compliance Agent - Supabase Schema Update for Gemini
-- This script updates the database to support 768-dimensional embeddings from Google Gemini
-- (instead of 1536-dimensional embeddings from OpenAI)

-- INSTRUCTIONS:
-- 1. Go to your Supabase project: https://supabase.com/dashboard/project/wvmycgezydduqxfjpkky
-- 2. Click "SQL Editor" in the left sidebar
-- 3. Click "New Query"
-- 4. Copy and paste this entire script
-- 5. Click "Run" (or press F5)
-- 6. You should see "Success. No rows returned" or success message

-- =====================================================================
-- WARNING: This will delete all existing embeddings data!
-- If you have important data, back it up first.
-- =====================================================================

BEGIN;

-- Drop the old vector index (it's tied to 1536 dimensions)
DROP INDEX IF EXISTS ccr_sections_embedding_idx;

-- Alter the embedding column to support 768 dimensions (Gemini)
ALTER TABLE ccr_sections 
ALTER COLUMN embedding TYPE vector(768);

-- Recreate the vector similarity index for 768 dimensions
CREATE INDEX ccr_sections_embedding_idx 
ON ccr_sections 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Update the search function to work with 768-dim vectors
CREATE OR REPLACE FUNCTION search_ccr_sections(
  query_embedding vector(768),
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
LANGUAGE plpgsql
AS $$
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

-- Verification query - should return 0 rows but no errors
SELECT COUNT(*) as total_sections FROM ccr_sections WHERE embedding IS NOT NULL;
