-- Fix Missing Unique Constraint on 'url' column
-- This is required for the re-indexing script to work (upsert).

ALTER TABLE ccr_sections ADD CONSTRAINT ccr_sections_url_key UNIQUE (url);
