# CCR Compliance Agent – Design & Assignment Alignment

This document explains how the system meets the internship assignment constraints, design choices, assumptions, and trade-offs.

---

## Assignment Constraints Checklist

| Requirement | Implementation |
|-------------|----------------|
| **Crawl CCR from govt.westlaw.com/calregs** | `crawler/url_discoverer.py` starts at `config.CCR_BASE_URL`; `section_extractor.py` fetches section pages. |
| **Use Crawl4AI** | `AsyncWebCrawler` from `crawl4ai` used for both URL discovery and section extraction. |
| **Controlled concurrency** | `MAX_CONCURRENT_REQUESTS` (default 3), `REQUEST_DELAY_SECONDS` (default 1.5). |
| **Retry with exponential backoff** | `tenacity` on `extract_section()`: `stop_after_attempt(MAX_RETRIES)`, `wait_exponential(min=1, max=16)`. |
| **URL normalization and deduplication** | `normalize_url()` strips fragments; all URLs normalized before adding to `discovered_urls` / `to_visit`. |
| **Persistent checkpoints (resume after crashes)** | `CHECKPOINT_DIR/url_discovery_checkpoint.json` and `CHECKPOINT_EVERY_N_URLS` (default 50). Extraction resumes by skipping URLs already in `extracted_sections.jsonl`. |
| **Clear separation: URL discovery vs section extraction** | Phase 1: `url_discoverer.py` → `discovered_urls.jsonl`. Phase 2: `section_extractor.py` reads that file, outputs `extracted_sections.jsonl`. |
| **Canonical data structure** | `models.CCRSection`: title_number, title_name, division, chapter, subchapter, article, section_number, section_heading, citation, breadcrumb_path, source_url, content_markdown, retrieved_at. Missing levels allowed (optional fields). |
| **Vector DB: semantic search, metadata filtering, idempotent upserts** | Supabase + pgvector: `search_similar()` with optional `title_number`; upsert on `section_url`. |
| **Agent: RAG, citations, explain applicability, follow-up questions, disclaimer** | `ComplianceAdvisor`: retrieval via `CCRRetriever`; system prompt enforces citations, “why it applies,” follow-up questions, and “not legal advice” disclaimer. |

---

## Key Technical Decisions

### 1. Westlaw URL semantics

- **Browse/TOC pages**: `.../Browse/...?guid=...` — we crawl these to discover links.
- **Section (document) pages**: `.../Document/...` (often with `viewType=FullText`) — we treat these as section content and extract once; we do not re-crawl them for further discovery.
- **Section detection**: `is_section_url()` returns true for URLs containing `/calregs/document/`. All other calregs links from the site are treated as potential TOC/browse and queued for discovery.

### 2. Coverage-first behavior

- Discovery aims to find *every* section URL by following all TOC/browse links; section URLs are collected and written to `discovered_urls.jsonl`.
- Extraction is resumable: already-extracted URLs (from `extracted_sections.jsonl`) are skipped.
- Failures are recorded in `failed_urls.jsonl`; `coverage_tracker.py` produces a coverage report (discovered vs extracted, failed, missing).

### 3. Supabase + pgvector

- **Choice**: Single Postgres DB for metadata and vectors; no separate vector service.
- **Rationale**: Free tier, SQL + metadata filters, and `section_url` as unique key for idempotent upserts. Embeddings are 1536-d (OpenAI text-embedding-3-small).

### 4. Agent behavior

- **RAG only**: Answers are based on retrieved CCR sections; the system prompt forbids inventing regulations.
- **Citations**: Every applicable section must be cited (e.g. “17 CCR § 1234”); CLI shows source URL from DB (`section_url` holds the source page URL).
- **Follow-ups**: Prompt instructs the model to ask 1–2 clarifying questions when information is insufficient.
- **Disclaimer**: Explicit “not legal advice” wording is required in every response and is appended if missing.

---

## Assumptions & Limitations

1. **Site structure**: Parsing assumes govt.westlaw.com’s current HTML (breadcrumbs, headings, content containers). Selectors may need updates if the site changes.
2. **Section URLs**: We rely on the site exposing section content via `/calregs/document/...`. If some sections are only reachable by other patterns, discovery logic may need to be extended.
3. **Rate limits**: Conservative defaults (3 concurrent, 1.5s delay) to reduce block risk; can be tuned via env.
4. **Vector search**: Current implementation fetches candidates and ranks in Python when a native pgvector RPC is not used; for very large corpora, a Supabase RPC using `<=>` would be better.
5. **Title 24 / Title 6**: Assignment mentions Title 24 (Building Standards) and Title 6 as external or different sites; discovery is scoped to the main calregs domain. Any separate domains would need extra discovery steps.

---

## What Was Improved (Summary)

- **Crawler**: Fixed `extract_section_number` typo; added `extract_section_number_from_url`; refined `is_section_url` / `is_toc_or_browse_url` for Westlaw; configurable checkpoint interval; coverage-safe report (no division by zero).
- **Agent**: Citations use `source_url` with fallback to `section_url`; stronger system prompt (follow-up questions + disclaimer).
- **Config**: `CHECKPOINT_EVERY_N_URLS`, slightly lower default concurrency and longer delay/timeout for stability.
- **Docs**: README updated with coverage-first design and Crawl4AI alignment; DESIGN.md added for constraints and trade-offs.

---

## How to Run Each Stage

See **RUN_ORDER.md** for the full sequence.

1. **Full pipeline**: `python run_pipeline.py` (discover → extract → coverage). Use `--retry` to retry failed URLs, `--index` to run indexing after.
2. **Discover URLs**: `python crawler/url_discoverer.py` → `data/discovered_urls.jsonl`, checkpoints in `checkpoints/`.
3. **Extract sections**: `python crawler/section_extractor.py` → `data/extracted_sections.jsonl`, `data/failed_urls.jsonl`.
4. **Retry failed**: `python retry_failed_extractions.py` (reads `failed_urls.jsonl`, appends successes to `extracted_sections.jsonl`, rewrites `failed_urls.jsonl`).
5. **Coverage report**: `python coverage_tracker.py` → `data/coverage_report.md`.
6. **Index**: `python index_pipeline.py` (requires Supabase schema applied).
7. **Agent**: `python cli.py` or `python cli.py --query "..."` (optional `--title N`).

---

*This project is built for the CCR Compliance Agent internship assignment. For questions: aravind.karanam@gmail.com / 8688743302.*
