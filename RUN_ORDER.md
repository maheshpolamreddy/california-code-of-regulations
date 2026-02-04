# CCR Compliance Agent – Run Order

Use these steps in order to go from zero to a working agent.

---

## 1. Install & configure

```bash
pip install -r requirements.txt
copy .env.example .env
# Edit .env: OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
```

In Supabase SQL Editor, run the full **supabase_schema.sql** (table + `search_ccr_sections` RPC).

---

## 2. Validate setup

```bash
python validate_setup.py
python validate_setup.py --crawl   # optional: 1-page test crawl
```

Fix any missing env or imports before continuing.

---

## 3. Discover URLs (Crawl4AI)

```bash
python crawler/url_discoverer.py
```

- **Output**: `data/discovered_urls.jsonl`
- **Checkpoints**: `checkpoints/url_discovery_checkpoint.json`
- Can resume after interrupt.

---

## 4. Extract sections (Crawl4AI)

```bash
python crawler/section_extractor.py
```

- **Output**: `data/extracted_sections.jsonl`, `data/failed_urls.jsonl`
- Skips URLs already in `extracted_sections.jsonl`.

---

## 5. (Optional) Retry failed URLs

```bash
python retry_failed_extractions.py
```

Then regenerate coverage:

```bash
python coverage_tracker.py
```

---

## 6. Coverage report

```bash
python coverage_tracker.py
```

- **Output**: `data/coverage_report.md`
- Review discovered vs extracted and fix gaps if needed.

---

## 7. Index into Supabase

```bash
python index_pipeline.py
```

- Needs: `.env` with OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY.
- Idempotent: safe to re-run.

---

## 8. Run the agent

```bash
python cli.py
# or
python cli.py --query "What CCR sections apply to restaurants in California?"
python cli.py --query "Movie theater safety requirements" --title 17
```

---

## One-shot: full pipeline (no index)

```bash
python run_pipeline.py
```

Runs: discover → extract → coverage. Add `--retry` to retry failed URLs; add `--index` to run the index step after (requires Supabase + OpenAI).

---

## Quick test (limit URLs)

To validate the pipeline without a full crawl:

```bash
# Discover up to 20 pages and up to 50 section URLs
python crawler/url_discoverer.py --max-pages 20 --max-section-urls 50

# Extract only the first 10 URLs
python crawler/section_extractor.py --limit 10

python coverage_tracker.py
```

Then run index + agent if you have Supabase/OpenAI set.

---

## Run tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover URL normalization, section-URL detection, and deduplication.

---

## Fallback (no Crawl4AI)

If Crawl4AI is not installed or fails:

```bash
python crawler/simple_url_discoverer.py
python crawler/simple_section_extractor.py
```

Note: simple extractor uses `requests` only; many Westlaw pages need JavaScript, so content may be empty. Prefer Crawl4AI for production.
