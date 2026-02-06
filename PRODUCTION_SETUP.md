# Production Deployment Setup - Quality Configuration

## ✅ What I've Configured

### Hybrid Embedding Strategy
- **Local Development**: sentence-transformers (FREE, 384 dims)
- **Production Deployment**: OpenAI (QUALITY, 1536 dims)

### Changes Made
1. ✅ `config.py` - Environment-aware embedding selection
2. ✅ `render.yaml` - Added RENDER=true environment variable
3. ✅ `supabase_schema_production.sql` - Schema for 1536-dim OpenAI embeddings

---

## 📋 Next Steps to Complete

### Step 1: Update Supabase Schema (5 minutes)

1. Go to your Supabase dashboard
2. Open SQL Editor
3. Run this script:

```sql
BEGIN;
TRUNCATE TABLE ccr_sections;
DROP INDEX IF EXISTS ccr_sections_embedding_idx;
ALTER TABLE ccr_sections DROP COLUMN IF EXISTS embedding;
ALTER TABLE ccr_sections ADD COLUMN embedding vector(1536);

CREATE INDEX ccr_sections_embedding_idx 
ON ccr_sections 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE OR REPLACE FUNCTION search_ccr_sections(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
  filter_title_number int DEFAULT NULL
)
RETURNS TABLE (
  id bigint, section_url text, title_number int, title_name text, 
  division text, chapter text, subchapter text, article text, 
  section_number text, section_heading text, citation text, 
  breadcrumb_path text, content_markdown text, similarity float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT ccr_sections.id, ccr_sections.section_url, ccr_sections.title_number,
    ccr_sections.title_name, ccr_sections.division, ccr_sections.chapter,
    ccr_sections.subchapter, ccr_sections.article, ccr_sections.section_number,
    ccr_sections.section_heading, ccr_sections.citation, ccr_sections.breadcrumb_path,
    ccr_sections.content_markdown, 1 - (ccr_sections.embedding <=> query_embedding) as similarity
  FROM ccr_sections
  WHERE (filter_title_number IS NULL OR ccr_sections.title_number = filter_title_number)
    AND 1 - (ccr_sections.embedding <=> query_embedding) > match_threshold
  ORDER BY ccr_sections.embedding <=> query_embedding LIMIT match_count;
END; $$;
COMMIT;
```

### Step 2: Add OpenAI Credits (~10 minutes)

1. Go to https://platform.openai.com/account/billing
2. Add payment method
3. Add $10-15 credits (covers ~6,500 sections)
4. Wait 2-3 minutes for activation

### Step 3: Re-index with OpenAI (1-2 hours)

```bash
# Your config will automatically use OpenAI locally now since RENDER env var is not set
# You need to temporarily force OpenAI mode:

# Option A: Set environment variable
set RENDER=true  # Windows
export RENDER=true  # Mac/Linux

# Option B: Comment out the local mode in config.py temporarily

# Then run:
python index_pipeline.py
```

This will generate **high-quality 1536-dimensional OpenAI embeddings** for all 6,530 sections.

### Step 4: Verify Deployment (5 minutes)

After indexing completes:
1. Check https://ccr-compliance-agent.onrender.com
2. Deployment will auto-update (already pushed to GitHub)
3. Test with queries like "restaurant regulations"

---

## 💰 Cost Breakdown

**One-Time Costs:**
- OpenAI indexing: ~$5-10 (text-embedding-3-small, ~6,500 sections)

**Monthly Costs:**
- OpenAI queries: ~$0.50-2/month (low usage)
- Render hosting: $0 (free tier works now!)
- Supabase: $0 (free tier)

**Total First Month: ~$10**  
**Total Ongoing: ~$1-2/month**

---

## 🎯 Why This is Best for Quality

✅ **Professional deployment** - OpenAI embeddings are industry-standard  
✅ **Reliable** - No memory issues on Render free tier  
✅ **Fast queries** - OpenAI client is lightweight  
✅ **Better results** - 1536 dimensions > 384 dimensions  
✅ **Internship-ready** - Shows you can use professional tools  

Your local development stays FREE with sentence-transformers!

---

## ⏭️ Ready to Proceed?

Type "done" after you:
1. ✅ Run the SQL in Supabase
2. ✅ Add OpenAI credits

Then I'll help you re-index with OpenAI for production quality! 🚀
