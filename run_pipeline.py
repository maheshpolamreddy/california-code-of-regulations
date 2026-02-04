"""
Run Full CCR Pipeline
Runs: URL discovery → Section extraction → Coverage report.
Optionally runs indexing (requires Supabase and OPENAI_API_KEY).

Usage:
  python run_pipeline.py              # discover → extract → coverage
  python run_pipeline.py --index     # also run index_pipeline.py
  python run_pipeline.py --discover  # only URL discovery
  python run_pipeline.py --extract   # only extraction (requires discovered_urls.jsonl)
  python run_pipeline.py --coverage  # only coverage report
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import config


def run_discover():
    """Run URL discovery (crawler/url_discoverer.py)."""
    from crawler.url_discoverer import URLDiscoverer

    async def _run():
        discoverer = URLDiscoverer()
        await discoverer.discover_all_urls()
        print(f"Saved to {config.DISCOVERED_URLS_FILE}")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_run())


def run_extract():
    """Run section extraction (crawler/section_extractor.py)."""
    from crawler.section_extractor import SectionExtractor

    async def _run():
        extractor = SectionExtractor()
        await extractor.process_discovered_urls()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_run())


def run_coverage():
    """Run coverage report (coverage_tracker.py)."""
    from coverage_tracker import CoverageTracker

    tracker = CoverageTracker()
    tracker.save_report()


def run_index():
    """Run indexing pipeline (index_pipeline.py)."""
    from index_pipeline import IndexPipeline

    pipeline = IndexPipeline()
    pipeline.run()


def main():
    parser = argparse.ArgumentParser(description="Run CCR pipeline stages")
    parser.add_argument("--discover", action="store_true", help="Only run URL discovery")
    parser.add_argument("--extract", action="store_true", help="Only run section extraction")
    parser.add_argument("--coverage", action="store_true", help="Only run coverage report")
    parser.add_argument("--index", action="store_true", help="Also run index pipeline (after extract)")
    parser.add_argument("--retry", action="store_true", help="After extract, retry failed URLs once")
    args = parser.parse_args()

    only_one = sum([args.discover, args.extract, args.coverage]) == 1

    if only_one:
        if args.discover:
            run_discover()
        elif args.extract:
            run_extract()
        else:
            run_coverage()
        return

    # Full pipeline: discover → extract → [retry] → coverage [→ index]
    print("=" * 60)
    print("CCR Pipeline: Discover → Extract → Coverage")
    print("=" * 60)

    print("\n[1/3] URL discovery...")
    run_discover()

    print("\n[2/3] Section extraction...")
    run_extract()

    if args.retry and config.FAILED_URLS_FILE.exists():
        print("\n[2b] Retrying failed URLs...")
        import retry_failed_extractions
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(retry_failed_extractions.main())

    print("\n[3/3] Coverage report...")
    run_coverage()

    if args.index:
        print("\n[4/4] Indexing (Supabase)...")
        run_index()

    print("\nPipeline complete. See data/coverage_report.md for coverage.")


if __name__ == "__main__":
    main()
