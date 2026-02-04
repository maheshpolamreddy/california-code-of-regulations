"""
Retry Failed Extractions
Re-attempts extraction for URLs that failed in the first run.
Run after section_extractor.py; reads data/failed_urls.jsonl and retries each URL.
Successful extractions are appended to data/extracted_sections.jsonl;
remaining failures are written back to data/failed_urls.jsonl.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from crawler.section_extractor import SectionExtractor
from crawl4ai import AsyncWebCrawler
from logger import extraction_logger
from models import FailedURL


async def main():
    if not config.FAILED_URLS_FILE.exists():
        print(f"No failed URLs file at {config.FAILED_URLS_FILE}. Run section_extractor.py first.")
        return

    # Load failed URLs
    failed_entries = []
    with open(config.FAILED_URLS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                failed_entries.append(json.loads(line))

    urls_to_retry = [e["url"] for e in failed_entries]
    if not urls_to_retry:
        print("No failed URLs to retry.")
        return

    extractor = SectionExtractor()
    still_failed = []

    print(f"Retrying {len(urls_to_retry)} failed URLs...")
    extraction_logger.info(f"Retry run: {len(urls_to_retry)} URLs")

    async with AsyncWebCrawler(verbose=False) as crawler:
        for idx, url in enumerate(urls_to_retry, 1):
            try:
                print(f"[{idx}/{len(urls_to_retry)}] Retrying: {url[:80]}...")
                section = await extractor.extract_section(url, crawler)
                if section:
                    with open(config.EXTRACTED_SECTIONS_FILE, "a", encoding="utf-8") as f:
                        f.write(section.model_dump_json() + "\n")
                    extractor.extracted_urls.add(url)
                    extraction_logger.info(f"Retry OK: {section.citation}")
            except Exception as e:
                extraction_logger.error(f"Retry failed {url}: {e}")
                still_failed.append(
                    FailedURL(
                        url=url,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        retry_count=1,
                    )
                )

    # Write back remaining failures
    with open(config.FAILED_URLS_FILE, "w", encoding="utf-8") as f:
        for failed in still_failed:
            f.write(failed.model_dump_json() + "\n")

    recovered = len(urls_to_retry) - len(still_failed)
    print(f"\nRetry complete: {recovered} recovered, {len(still_failed)} still failed")
    print(f"Run coverage_tracker.py to refresh the coverage report.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
