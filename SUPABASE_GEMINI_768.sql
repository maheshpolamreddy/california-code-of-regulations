-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Delete existing 384-dim table and index (incompatible with 768-dim)
drop table if exists ccr_sections cascade;

-- Create a table to store your documents
create table ccr_sections (
  id bigserial primary key,
  url text not null,
  section_no text,
  title text,
  content text,
  metadata jsonb,
  embedding vector(768) -- Gemini embeddings are 768-dimensional
);

-- Create a search function
create or replace function match_ccr_sections (
  query_embedding vector(768),
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

-- Create an HNSW index for faster queries
create index on ccr_sections using hnsw (embedding vector_cosine_ops);
