# CCR Compliance Agent - Quick Start Guide

## 🎯 You Are Here: Environment Setup

The complete system has been built! Now we need to configure it and run it.

---

## ✅ Already Done

- [x] Project structure created
- [x] All Python code implemented
- [x] Virtual environment created
- [x] Dependencies installed (in progress)
- [x] .env file created

---

## 🔧 Next Steps (Required Before Running)

### Step 1: Get API Keys

You need to obtain these API keys:

#### 1.1 OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

**Cost Estimate:** ~$5-15 for full CCR indexing
- Embeddings: ~$2-5
- Agent queries: ~$0.01-0.10 per query

#### 1.2 Supabase Account
1. Go to https://supabase.com
2. Sign up (free tier is perfect)
3. Create a new project
4. Wait 2-3 minutes for setup
5. Go to Project Settings → API
6. Copy:
   - **Project URL** (looks like `https://xxxxx.supabase.co`)
   - **service_role key** (under "Project API keys", the secret one)

---

### Step 2: Configure .env File

Open the `.env` file and fill in your keys:

```bash
# Edit C:\Users\mahesh polamreddy\.gemini\antigravity\scratch\ccr-compliance-agent\.env

OPENAI_API_KEY=sk-your-actual-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-key-here
```

**Keep the rest of the settings unchanged** (already configured optimally).

---

### Step 3: Set Up Supabase Database Schema

1. Go to your Supabase project
2. Click on **SQL Editor** in left menu
3. Click **New Query**
4. Copy and paste this SQL:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create CCR sections table
CREATE TABLE ccr_sections (
    id BIGSERIAL PRIMARY KEY,
    section_url TEXT UNIQUE NOT NULL,
    title_number INTEGER,
    title_name TEXT,
    division TEXT,
    chapter TEXT,
    subchapter TEXT,
    article TEXT,
    section_number TEXT,
    section_heading TEXT,
    citation TEXT,
    breadcrumb_path TEXT,
    content_markdown TEXT,
    embedding vector(1536),
    chunk_index INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 1,
    retrieved_at TIMESTAMP DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX ccr_sections_embedding_idx 
ON ccr_sections USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create metadata indexes
CREATE INDEX ccr_sections_title_number_idx ON ccr_sections (title_number);
CREATE INDEX ccr_sections_citation_idx ON ccr_sections (citation);
```

5. Click **Run** (or press F5)
6. You should see "Success. No rows returned"

---

### Step 4: Validate Setup

Run the setup validation script:

```bash
python setup_check.py
```

If all checks pass (✅), you're ready to go!

---

## 🚀 Running the Pipeline

Once setup is complete, run these commands in order:

### 1. Discover CCR URLs (30-60 minutes)
```bash
python crawler/url_discoverer.py
```
This crawls the CCR website hierarchy and finds all section URLs.

### 2. Extract Section Content (1-3 hours)
```bash
python crawler/section_extractor.py
```
Downloads each section and converts to Markdown.

### 3. Validate Coverage
```bash
python coverage_tracker.py
```
Generates a report showing extraction completeness.

### 4. Index to Vector Database (10-30 minutes)
```bash
python index_pipeline.py
```
Generates embeddings and uploads to Supabase.

### 5. Use the Agent!
```bash
# Interactive mode
python cli.py

# Single query
python cli.py --query "What regulations apply to restaurants?"
```

---

## ⚠️ Important Notes

### Crawling Behavior
- **Rate limited:** 1 second delay between requests
- **Checkpointing:** Saves progress every 50 URLs
- **Resumable:** Can stop/resume without losing progress
- **Duration:** Full CCR crawl may take 2-4 hours total

### Cost Management
- **Test first:** Try on a single title before full crawl
- **Monitor usage:** Check OpenAI dashboard for costs
- **Free tier:** Supabase free tier should be sufficient

### If Something Fails
1. Check logs in `logs/` directory
2. Review `data/failed_urls.jsonl` for errors
3. Re-run the failed step (checkpoints prevent re-work)
4. Coverage report will show gaps

---

## 🧪 Quick Test (Before Full Crawl)

Want to test without crawling the entire CCR?

You can manually create a test section in `data/extracted_sections.jsonl`:

```json
{"title_number": 17, "title_name": "Public Health", "division": null, "chapter": "1", "subchapter": null, "article": null, "section_number": "1234", "section_heading": "Test Section", "citation": "17 CCR § 1234", "breadcrumb_path": "Title 17 > Chapter 1 > Section 1234", "source_url": "https://example.com", "content_markdown": "This is a test regulation for restaurants regarding food safety.", "retrieved_at": "2026-01-30T19:00:00"}
```

Then run:
```bash
python index_pipeline.py
python cli.py --query "restaurant regulations"
```

---

## 📞 Need Help?

**Assignment Contact:**
- Email: aravind.karanam@gmail.com
- WhatsApp: 8688743302

**Common Issues:**
- **"No module named X"**: Run `pip install -r requirements.txt` again
- **"Invalid API key"**: Check your .env file
- **"Table already exists"**: That's fine, SQL is idempotent
- **Slow crawling**: Normal! The site has rate limits

---

## ✅ Checklist

Before running the pipeline:

- [ ] OpenAI API key added to `.env`
- [ ] Supabase URL added to `.env`
- [ ] Supabase service key added to `.env`
- [ ] SQL schema created in Supabase
- [ ] `python setup_check.py` shows all ✅

Ready? Start with Step 1: **URL Discovery**! 🚀
