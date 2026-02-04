"""
Validate Setup - CCR Compliance Agent
Checks environment, imports, and optionally runs a 1-page test crawl.
Run before full pipeline: python validate_setup.py
With test crawl: python validate_setup.py --crawl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def check_env():
    """Check required and optional env vars."""
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # .env not loaded; still check os.environ
    required = {
        "OPENAI_API_KEY": "Agent and embeddings (required for index + agent)",
        "SUPABASE_URL": "Vector DB (required for index + agent)",
        "SUPABASE_SERVICE_KEY": "Vector DB (required for index + agent)",
    }
    optional = {
        "MAX_CONCURRENT_REQUESTS": "Crawling (default 3)",
        "REQUEST_DELAY_SECONDS": "Crawling (default 1.5)",
        "CHECKPOINT_EVERY_N_URLS": "Crawling (default 50)",
    }
    ok = True
    print("Environment:")
    for name, desc in required.items():
        val = os.getenv(name)
        if val and val != "your_openai_api_key_here" and "your_supabase" not in (val or ""):
            print(f"  [OK] {name} set")
        else:
            print(f"  [--] {name} missing or placeholder ({desc})")
            ok = False
    for name, desc in optional.items():
        val = os.getenv(name)
        print(f"  [.]  {name} = {val or '(default)'} ({desc})")
    return ok


def check_imports():
    """Check critical imports."""
    print("\nImports:")
    deps = [
        ("crawl4ai", "AsyncWebCrawler"),
        ("bs4", "BeautifulSoup"),
        ("markdownify", "markdownify"),
        ("tenacity", "retry"),
        ("pydantic", "BaseModel"),
        ("openai", "OpenAI"),
        ("supabase", "create_client"),
    ]
    ok = True
    for module, attr in deps:
        try:
            m = __import__(module)
            getattr(m, attr)
            print(f"  [OK] {module}.{attr}")
        except Exception as e:
            print(f"  [FAIL] {module}.{attr}: {e}")
            ok = False
    return ok


def check_config():
    """Check config and paths."""
    import config
    print("\nConfig & paths:")
    print(f"  CCR_BASE_URL = {config.CCR_BASE_URL}")
    print(f"  DATA_DIR = {config.DATA_DIR} (exists: {config.DATA_DIR.exists()})")
    print(f"  CHECKPOINT_DIR = {config.CHECKPOINT_DIR} (exists: {config.CHECKPOINT_DIR.exists()})")
    print(f"  CHECKPOINT_EVERY_N_URLS = {getattr(config, 'CHECKPOINT_EVERY_N_URLS', 'N/A')}")
    return True


def test_crawl():
    """Run a single-page test crawl (CCR homepage)."""
    import asyncio
    import config
    from crawl4ai import AsyncWebCrawler
    from crawler.url_discoverer import URLDiscoverer

    async def _run():
        discoverer = URLDiscoverer()
        url = config.CCR_BASE_URL
        print(f"\nTest crawl: {url}")
        async with AsyncWebCrawler(verbose=False) as crawler:
            links = await discoverer.crawl_page(url, crawler)
        print(f"  Links found: {len(links)}")
        section_count = sum(1 for l in links if discoverer.is_section_url(l))
        print(f"  Section URLs (in this page): {section_count}")
        return len(links) >= 1

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_run())


def main():
    parser = argparse.ArgumentParser(description="Validate CCR Compliance Agent setup")
    parser.add_argument("--crawl", action="store_true", help="Run 1-page test crawl")
    args = parser.parse_args()

    print("=" * 60)
    print("CCR Compliance Agent - Setup Validation")
    print("=" * 60)

    env_ok = check_env()
    imp_ok = check_imports()
    check_config()

    if args.crawl:
        crawl_ok = test_crawl()
    else:
        crawl_ok = True
        print("\n(Use --crawl to run a 1-page test crawl)")

    print("\n" + "=" * 60)
    if not imp_ok:
        print("Fix imports: pip install -r requirements.txt")
        sys.exit(1)
    if args.crawl and not crawl_ok:
        print("Test crawl failed. Check network and Crawl4AI setup.")
        sys.exit(1)
    if not env_ok:
        print("Set OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY in .env for index + agent.")
    print("Validation OK. Crawl: python run_pipeline.py  |  Agent: python cli.py (after index)")
    print("=" * 60)


if __name__ == "__main__":
    main()
