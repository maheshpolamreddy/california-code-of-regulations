"""
URL Discovery Module
Discovers all CCR section URLs by navigating the hierarchy.
Implements checkpointing for resumable crawls.
"""

import asyncio
import json
from pathlib import Path
from typing import Set, List, Dict
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
import sys
sys.path.append(str(Path(__file__).parent.parent))

from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
import config
from logger import crawler_logger
from models import DiscoveredURL

class URLDiscoverer:
    """
    Discovers all CCR section URLs by crawling the hierarchical structure.
    Two-phase approach:
    1. Navigate Title → Division → Chapter structure
    2. Collect all section page URLs
    """
    
    def __init__(self):
        self.discovered_urls: Set[str] = set()
        self.checkpoint_file = config.CHECKPOINT_DIR / "url_discovery_checkpoint.json"
        self.load_checkpoint()
        
    def load_checkpoint(self):
        """Load previously discovered URLs from checkpoint."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.discovered_urls = set(data.get('discovered_urls', []))
                crawler_logger.info(f"Loaded {len(self.discovered_urls)} URLs from checkpoint")
            except Exception as e:
                crawler_logger.error(f"Failed to load checkpoint: {e}")
                
    def save_checkpoint(self):
        """Save current progress to checkpoint file."""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'discovered_urls': list(self.discovered_urls),
                    'last_updated': datetime.utcnow().isoformat()
                }, f, indent=2)
            crawler_logger.info(f"Checkpoint saved: {len(self.discovered_urls)} URLs")
        except Exception as e:
            crawler_logger.error(f"Failed to save checkpoint: {e}")
            
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication.
        Removes fragments and sorts query parameters.
        """
        parsed = urlparse(url)
        # Remove fragment
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized
    
    def is_section_url(self, url: str) -> bool:
        """
        Check if URL points to an actual CCR section/document page (content to extract).
        Westlaw uses: /calregs/Document/... for section content; Browse/... for TOC/navigation.
        """
        u = url.lower()
        # Document pages (section content)
        if '/calregs/document/' in u and 'viewtype=fulltext' in u:
            return True
        if '/calregs/document/' in u:
            return True
        # Some section links may use different path patterns
        if '/calregs/' in u and ('document' in u or 'section' in u) and 'browse' not in u:
            return True
        return False

    def is_toc_or_browse_url(self, url: str) -> bool:
        """True if URL is a table-of-contents / browse page (to crawl for links), not section content."""
        u = url.lower()
        if '/calregs/document/' in u:
            return False  # Section content page
        return '/calregs/browse/' in u or ('calregs' in u and 'guid=' in u)
    
    async def extract_links_from_page(self, html: str, base_url: str) -> List[str]:
        """
        Extract all relevant links from a page.
        Filters for CCR-related links only.
        """
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Only include calregs links
            if 'calregs' in absolute_url and 'westlaw.com' in absolute_url:
                normalized = self.normalize_url(absolute_url)
                links.append(normalized)
                
        return links
    
    async def crawl_page(self, url: str, crawler: AsyncWebCrawler) -> List[str]:
        """
        Crawl a single page and extract links.
        Implements rate limiting and error handling.
        """
        try:
            await asyncio.sleep(config.REQUEST_DELAY_SECONDS)
            
            result = await crawler.arun(
                url=url,
                timeout=config.TIMEOUT_SECONDS
            )
            
            if result.success:
                links = await self.extract_links_from_page(result.html, url)
                crawler_logger.info(f"Found {len(links)} links on {url}")
                return links
            else:
                crawler_logger.warning(f"Failed to crawl {url}: {result.error_message}")
                return []
                
        except Exception as e:
            crawler_logger.error(f"Error crawling {url}: {e}")
            return []
    
    async def discover_all_urls(
        self,
        start_url: str = None,
        max_pages: int = None,
        max_section_urls: int = None,
    ) -> Set[str]:
        """
        Main discovery method. Performs breadth-first crawl of CCR hierarchy.

        Args:
            start_url: Starting URL (defaults to CCR base)
            max_pages: Stop after visiting this many pages (for quick test).
            max_section_urls: Stop after discovering this many section URLs (for quick test).

        Returns:
            Set of all discovered section URLs
        """
        if start_url is None:
            start_url = config.CCR_BASE_URL

        to_visit = {start_url}
        visited = set()
        section_urls = set()

        crawler_logger.info(f"Starting URL discovery from {start_url}")
        if max_pages or max_section_urls:
            crawler_logger.info(f"Limits: max_pages={max_pages}, max_section_urls={max_section_urls}")

        checkpoint_every = getattr(config, "CHECKPOINT_EVERY_N_URLS", 50)
        async with AsyncWebCrawler(verbose=False) as crawler:
            while to_visit:
                if max_pages and len(visited) >= max_pages:
                    crawler_logger.info(f"Stopping: reached max_pages={max_pages}")
                    break
                if max_section_urls and len(self.discovered_urls) >= max_section_urls:
                    crawler_logger.info(f"Stopping: reached max_section_urls={max_section_urls}")
                    break

                current_url = to_visit.pop()

                if current_url in visited:
                    continue

                visited.add(current_url)
                crawler_logger.info(f"Visiting ({len(visited)} visited, {len(self.discovered_urls)} sections): {current_url[:80]}...")

                links = await self.crawl_page(current_url, crawler)

                for link in links:
                    if link in visited:
                        continue
                    normalized = self.normalize_url(link)
                    if self.is_section_url(normalized):
                        section_urls.add(normalized)
                        self.discovered_urls.add(normalized)
                    elif self.is_toc_or_browse_url(normalized) or (config.CCR_BASE_URL.lower() in normalized and "calregs" in normalized):
                        to_visit.add(normalized)

                if len(visited) % checkpoint_every == 0:
                    self.save_checkpoint()
                    self.save_discovered_urls()

        self.save_checkpoint()
        self.save_discovered_urls()

        crawler_logger.info(f"Discovery complete: {len(section_urls)} section URLs found")
        return section_urls
    
    def save_discovered_urls(self):
        """Save discovered URLs to JSONL file."""
        try:
            with open(config.DISCOVERED_URLS_FILE, 'w', encoding='utf-8') as f:
                for url in sorted(self.discovered_urls):
                    discovered = DiscoveredURL(url=url)
                    f.write(discovered.model_dump_json() + '\n')
            crawler_logger.info(f"Saved {len(self.discovered_urls)} URLs to {config.DISCOVERED_URLS_FILE}")
        except Exception as e:
            crawler_logger.error(f"Failed to save discovered URLs: {e}")

async def main(max_pages: int = None, max_section_urls: int = None):
    """Main entry point for URL discovery."""
    discoverer = URLDiscoverer()
    urls = await discoverer.discover_all_urls(
        max_pages=max_pages,
        max_section_urls=max_section_urls,
    )
    print(f"✅ Discovery complete: {len(urls)} section URLs found")
    print(f"📁 Saved to: {config.DISCOVERED_URLS_FILE}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Discover CCR section URLs")
    parser.add_argument("--max-pages", type=int, default=None, help="Stop after visiting N pages (quick test)")
    parser.add_argument("--max-section-urls", type=int, default=None, help="Stop after discovering N section URLs (quick test)")
    args = parser.parse_args()

    if __import__("platform").system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(max_pages=args.max_pages, max_section_urls=args.max_section_urls))
