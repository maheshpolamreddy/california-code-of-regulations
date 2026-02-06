-- Revert Supabase Schema to 384 dimensions for FastEmbed
-- Run this in your Supabase SQL Editor to fix the schema

-- Delete existing 768-dim table and index
drop table if exists ccr_sections cascade;

-- Create table with 384-dimensional vectors
create table ccr_sections (
  id bigserial primary key,
  url text not null,
  section_no text,
  title text,
  content text,
  metadata jsonb,
  embedding vector(384) -- FastEmbed / Sentence-Transformers uses 384 dims
);

-- Re-create search function for 384 dims
create or replace function match_ccr_sections (
  query_embedding vector(384),
  match_threshold float,
  match_count int
) returns table (
  id bigint,
  url text,
  section_no text,
  title text,
  content text,
  metadata jsonb,
  similarity float
) language sql stable as $$
  select
    ccr_sections.id,
    ccr_sections.url,
    ccr_sections.section_no,
    ccr_sections.title,
    ccr_sections.content,
    ccr_sections.metadata,
    1 - (ccr_sections.embedding <=> query_embedding) as similarity
  from ccr_sections
  where 1 - (ccr_sections.embedding <=> query_embedding) > match_threshold
  order by ccr_sections.embedding <=> query_embedding
  limit match_count;
$$;

-- Create HNSW index for fast search
create index on ccr_sections using hnsw (embedding vector_cosine_ops);
