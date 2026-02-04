# CCR Compliance Agent

🌐 **Live Demo:** [https://california-code-of-regulations.onrender.com](https://california-code-of-regulations.onrender.com)

A complete system for crawling the California Code of Regulations (CCR), indexing it into a vector database, and providing AI-powered compliance advice to facility operators.

## 🎯 Project Overview

This project is an internship assignment demonstrating:
- Web crawling with Crawl4AI
- Vector database integration (Supabase + pgvector)
- RAG (Retrieval-Augmented Generation) with OpenAI
- Coverage validation and completeness tracking
- Production-ready error handling and logging

### System Components

1. **Web Crawler** - Discovers and extracts CCR sections from govt.westlaw.com
2. **Data Pipeline** - Converts HTML to Markdown with hierarchical metadata  
3. **Coverage Tracker** - Validates 100% extraction completeness
4. **Vector Database** - Semantic search with Supabase + pgvector
5. **AI Agent** - GPT-4 powered compliance advisor with citations

### 👨‍💻 Author

**Mahesh Polamreddy**
- 📧 Email: polamreddymahesh623@gmail.com
- 📱 Mobile: +91 7013441009

## 📸 Screenshots

### Futuristic Holographic Dashboard
![Dashboard View](screenshots/dashboard.png)
*Main interface with particle background, glassmorphism effects, and real-time stats*

### Query Interface
![Query Example](screenshots/query-example.png)
*Voice-enabled query input with example pills and 3D tilt effects*

### AI-Powered Results
![Results Display](screenshots/results.png)
*Typewriter-animated answers with clickable citations and source links*

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key
- Supabase account (free tier)
- Internet connection

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ccr-compliance-agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy example env file
   copy .env.example .env
   
   # Edit .env and add your API keys:
   # - OPENAI_API_KEY
   # - SUPABASE_URL
   # - SUPABASE_SERVICE_KEY
   ```

5. **Validate setup (optional)**
   ```bash
   python validate_setup.py          # Check env and imports
   python validate_setup.py --crawl   # Also run 1-page test crawl
   ```

6. **Set up Supabase database**
   
   Go to your Supabase project SQL Editor and run the full `supabase_schema.sql` (includes table + `search_ccr_sections` RPC for native vector search):
   
   ```sql
   -- Enable pgvector extension
   CREATE EXTENSION IF NOT EXISTS vector;
   
   -- Create table
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
   
   -- Create indexes
   CREATE INDEX ccr_sections_embedding_idx 
   ON ccr_sections USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);
   
   CREATE INDEX ccr_sections_title_number_idx ON ccr_sections (title_number);
   CREATE INDEX ccr_sections_citation_idx ON ccr_sections (citation);
   ```
   
   The schema file also defines an RPC `search_ccr_sections(query_embedding, match_limit, filter_title_number)` for native pgvector similarity search; the agent uses it when available and falls back to Python-side search otherwise.

---

## 📊 Usage

### Run full pipeline (discover → extract → coverage)

See **[RUN_ORDER.md](RUN_ORDER.md)** for the full step-by-step run order.

```bash
python run_pipeline.py
```

Optional: retry failed URLs and then run indexing:

```bash
python run_pipeline.py --retry --index
```

Single stages: `--discover`, `--extract`, `--coverage`, or `--index`.

### Step 1: Discover URLs

Crawl the CCR website hierarchy to discover all section URLs.

```bash
python crawler/url_discoverer.py
```

**Output:** `data/discovered_urls.jsonl`

**Features (per assignment):**
- Controlled concurrency (`MAX_CONCURRENT_REQUESTS`, default 3)
- URL normalization and deduplication
- Persistent checkpoints every N URLs (`CHECKPOINT_EVERY_N_URLS`, default 50); resume after crashes
- Clear separation: URL discovery (this step) vs section content extraction (Step 2)
- Breadth-first crawl of CCR hierarchy (Title → Division → Chapter → Section links)

### Step 2: Extract Sections

Extract content and metadata from discovered URLs.

```bash
python crawler/section_extractor.py
```

**Output:** `data/extracted_sections.jsonl`

**Features (per assignment):**
- HTML to Markdown conversion (clean Markdown output)
- Hierarchical metadata extraction (Title → Division → Chapter → Article → Section)
- Citation generation (e.g., "17 CCR § 1234")
- Retry logic with exponential backoff (`tenacity`; `MAX_RETRIES` from config)
- Failed URL tracking (saved to `failed_urls.jsonl` for coverage report)

### Step 2b (optional): Retry Failed URLs

Re-attempt extraction for URLs that failed in Step 2.

```bash
python retry_failed_extractions.py
```

**Output:** Recovered sections appended to `data/extracted_sections.jsonl`; remaining failures in `data/failed_urls.jsonl`. Then run Step 3 to refresh the coverage report.

### Step 3: Validate Coverage

Generate completeness report comparing discovered vs extracted sections.

```bash
python coverage_tracker.py
```

**Output:** `data/coverage_report.md`

**Metrics:**
- Total discovered vs extracted
- Coverage percentage
- Failed extractions by error type
- Missing/unprocessed URLs
- Recommendations for gaps

### Step 4: Index into Vector Database

Generate embeddings and upload to Supabase.

```bash
python index_pipeline.py
```

**Features:**
- OpenAI text-embedding-3-small (1536 dimensions)
- Automatic chunking for long sections
- Batch processing for efficiency
- Idempotent upserts (safe re-runs)

### Step 5: Use the Compliance Agent

Query the agent for regulatory advice.

**Interactive mode:**
```bash
python cli.py
```

**Single query mode:**
```bash
python cli.py --query "What CCR sections apply to restaurants in California?"

python cli.py --query "Movie theater safety requirements" --title 17
```

**Agent Features:**
- Semantic search with RAG
- Facility type detection (restaurant, theater, farm, etc.)
- Specific CCR citations with source URLs
- Explanation of why each section applies
- Follow-up question suggestions
- Legal disclaimer ("not legal advice")

---

## 📁 Project Structure

```
ccr-compliance-agent/
│
├── crawler/
│   ├── __init__.py
│   ├── url_discoverer.py      # URL discovery crawler
│   └── section_extractor.py   # Content extractor
│
├── vectordb/
│   ├── __init__.py
│   ├── embedder.py             # OpenAI embedding generator
│   └── supabase_client.py     # Supabase vector DB client
│
├── agent/
│   ├── __init__.py
│   ├── retriever.py            # RAG retrieval logic
│   └── compliance_advisor.py  # LLM-powered advisor
│
├── data/                       # Output data (created automatically)
│   ├── discovered_urls.jsonl
│   ├── extracted_sections.jsonl
│   ├── failed_urls.jsonl
│   └── coverage_report.md
│
├── checkpoints/                # Crawler checkpoints
├── logs/                       # Application logs
│
├── config.py                   # Configuration management
├── logger.py                   # Logging setup
├── models.py                   # Pydantic data models
├── coverage_tracker.py         # Coverage validation
├── index_pipeline.py           # Indexing pipeline
├── run_pipeline.py              # Run full pipeline (discover → extract → coverage)
├── retry_failed_extractions.py # Retry failed URLs from failed_urls.jsonl
├── validate_setup.py            # Validate env, imports, optional test crawl
├── cli.py                      # Command-line interface
│
├── requirements.txt
├── RUN_ORDER.md                  # Step-by-step run order
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔍 Design Decisions

### 1. Coverage-First Design (Assignment Requirement)

**Decision:** Prioritize completeness over speed. Design crawling to extract *every* CCR section, not "most pages."

**Rationale:**
- Assignment states: "Reliably extracting every single CCR section" is the core difficulty
- We instrument coverage (discovered vs extracted), track failures, and report what was missed
- A partially correct but well-instrumented system is preferred over a silent, incomplete one

### 2. Two-Phase Crawling

**Decision:** Separate URL discovery from content extraction

**Rationale:**
- Ensures complete coverage (discover ALL URLs first)
- Allows restart from extraction phase without re-crawling
- Easier to track missing sections (discovered - extracted = gaps)
- Clear separation between URL discovery and section content extraction (per assignment)

### 3. Supabase + pgvector

**Decision:** Use PostgreSQL with pgvector instead of specialized vector DB

**Rationale:**
- Store structured data + vectors in same database
- Flexible SQL queries for metadata filtering
- 500MB free tier sufficient for CCR data
- Mature PostgreSQL ecosystem

### 4. Checkpointing Strategy

**Decision:** Save progress every 50 URLs during crawling

**Rationale:**
- Resume after crashes without re-downloading
- Minimize data loss from network failures
- Balance between I/O overhead and safety
- Configurable via `CHECKPOINT_EVERY_N_URLS` (default 50)

### 5. Chunking Long Sections

**Decision:** Split sections >512 tokens with 50-token overlap

**Rationale:**
- Maintain context across chunk boundaries
- Fit within embedding model limits
- Preserve searchability of long regulations

### 6. Citation-Based RAG

**Decision:** Enforce citation requirements in system prompt

**Rationale:**
- Prevent hallucination of fake regulations
- Provide verifiable source URLs
- Meet assignment requirement for accuracy

---

## ⚠️ Known Limitations

### 1. Website Structure Dependency

**Issue:** Parser relies on HTML structure of govt.westlaw.com

**Mitigation:**
- Flexible CSS selectors with fallbacks
- Error logging for parse failures
- Manual review process for failed URLs

### 2. Rate Limiting

**Issue:** Aggressive crawling may trigger blocks

**Current Settings:**
- 1 second delay between requests
- Max 5 concurrent requests

**Adjustment:** Increase `REQUEST_DELAY_SECONDS` if needed

### 3. Embedding Costs

**Issue:** OpenAI embeddings cost money ($0.00002/1K tokens)

**Estimate:** ~$5-15 for full CCR corpus

**Alternative:** Consider local embeddings (sentence-transformers) for cost savings

### 4. Vector Search Performance

**Issue:** Python-based cosine similarity (not ideal at scale)

**Better Approach:** Use Supabase RPC with native pgvector operations

**SQL Example:**
```sql
SELECT *, embedding <=> $1::vector AS distance
FROM ccr_sections
ORDER BY distance
LIMIT 10;
```

### 5. Completeness Challenges

**Potential Gaps:**
- Dynamic JavaScript content (Crawl4AI may miss some)
- Rate-limited pages
- Malformed HTML

**Validation:** Always review `coverage_report.md` before deployment

---

## 🧪 Testing

### Unit tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover URL normalization, section-URL detection, and deduplication.

### Quick test (limit URLs)

Validate the pipeline without a full crawl:

```bash
python crawler/url_discoverer.py --max-pages 20 --max-section-urls 50
python crawler/section_extractor.py --limit 10
python coverage_tracker.py
```

See [RUN_ORDER.md](RUN_ORDER.md) for the full quick-test section.

### Manual testing

```bash
# Full crawler (no limit)
python crawler/url_discoverer.py

# Full extraction (no limit)
python crawler/section_extractor.py

# Verify coverage
python coverage_tracker.py

# Test agent
python cli.py --query "restaurant health code requirements"
```

### Expected Outputs

1. **Coverage Report:** Should show >90% extraction rate
2. **Agent Responses:** Must include CCR citations with §  symbols
3. **Source URLs:** Should link to govt.westlaw.com
4. **Disclaimer:** Every response must say "not legal advice"

---

## 🚧 Future Improvements

### High Priority

1. **Optimize vector search** - Use Supabase RPC instead of Python similarity
2. **Add retry for failed URLs** - Automated re-attempt with different parameters
3. **Implement incremental indexing** - Only update changed sections
4. **Add metadata filters** - Filter by county, effective date, etc.

### Medium Priority

5. **Multi-turn conversations** - Better conversation history management
6. **Export to PDF** - Generate compliance reports
7. **API endpoint** - REST API for programmatic access
8. **Caching** - Cache frequent queries

### Low Priority

9. **Local embeddings** - Reduce OpenAI costs  
10. **UI frontend** - Web interface instead of CLI
11. **Multi-state support** - Extend to other state regulations
12. **Email alerts** - Notify on regulation changes

---

## 📝 Deliverables Checklist

- [x] **Code**
  - [x] Crawling scripts with checkpointing
  - [x] Indexing pipeline with vector DB
  - [x] Agent implementation (CLI)
  
- [x] **Data**
  - [x] Discovered section URLs (JSONL)
  - [x] Extracted CCR sections (JSONL)
  - [x] Coverage/completeness report (Markdown)
  
- [x] **Documentation**
  - [x] README with setup instructions
  - [x] Design decisions explained
  - [x] Known limitations documented
  - [x] Future improvements outlined

---

## 🤝 Support & Contact

**Project Developer:**
- **Mahesh Polamreddy**
- 📧 Email: polamreddymahesh623@gmail.com
- 📱 Mobile: +91 7013441009

**Assignment Coordinator:**
- Email: aravind.karanam@gmail.com
- WhatsApp: 8688743302

---

## 📜 License

This project was created as part of an internship assignment.

---

## 🙏 Acknowledgments

- **Crawl4AI** - Excellent web crawling framework
- **Supabase** - Generous free tier for PostgreSQL + pgvector
- **OpenAI** - GPT-4 and text-embedding-3-small models
- **Assignment Designer** - For a challenging and educational project

---

**⚖️ Disclaimer:** This tool provides informational guidance based on CCR sections. It is NOT legal advice. Always consult qualified legal counsel for compliance matters.
