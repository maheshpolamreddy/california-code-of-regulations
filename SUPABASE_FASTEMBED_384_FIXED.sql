-- FIXED Schema for FastEmbed (384 dimensions)
-- Matches exactly with supabase_client.py expectation

-- 1. Enable pgvector extension
create extension if not exists vector;

-- 2. Delete existing table (to fix schema mismatch)
drop table if exists ccr_sections cascade;

-- 3. Create table with CORRECT column names
create table ccr_sections (
  id bigserial primary key,
  section_url text unique not null,  -- Match Python: 'section_url'
  title_number integer,
  title_name text,
  division text,
  chapter text,
  subchapter text,
  article text,
  section_number text,               -- Match Python: 'section_number'
  section_heading text,
  citation text,
  breadcrumb_path text,
  content_markdown text,
  embedding vector(384),             -- FastEmbed Dimension
  chunk_index integer default 0,
  total_chunks integer default 1,
  retrieved_at timestamp default now()
);

-- 4. Create indexes for performance
create index on ccr_sections using hnsw (embedding vector_cosine_ops);
create index on ccr_sections (citation);
create index on ccr_sections (title_number);

-- 5. Create Search Function (RPC)
create or replace function match_ccr_sections (
  query_embedding vector(384),
  match_threshold float,
  match_count int
) returns table (
  id bigint,
  section_url text,
  section_number text,
  title_number integer,
  title_name text,
  citation text,
  content_markdown text,
  similarity float
) language sql stable as $$
  select
    ccr_sections.id,
    ccr_sections.section_url,
    ccr_sections.section_number,
    ccr_sections.title_number,
    ccr_sections.title_name,
    ccr_sections.citation,
    ccr_sections.content_markdown,
    1 - (ccr_sections.embedding <=> query_embedding) as similarity
  from ccr_sections
  where 1 - (ccr_sections.embedding <=> query_embedding) > match_threshold
  order by ccr_sections.embedding <=> query_embedding
  limit match_count;
$$;
