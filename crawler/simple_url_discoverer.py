"""
Simple URL Discovery (Windows-compatible version)
Uses requests library instead of Crawl4AI to avoid Windows subprocess issues.
"""

import time
import json
from pathlib import Path
from typing import Set
from datetime import datetime
from urllib.parse import urljoin, urlparse
import sys
sys.path.append(str(Path(__file__).parent.parent))

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from logger import crawler_logger
from models import DiscoveredURL

class SimpleURLDiscoverer:
    """
    Simple URL discoverer using requests library (Windows-compatible).
    """
    
    def __init__(self):
        self.discovered_urls: Set[str] = set()
        self.checkpoint_file = config.CHECKPOINT_DIR / "url_discovery_checkpoint.json"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
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
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized
    
    def is_section_url(self, url: str) -> bool:
        """Check if URL points to an actual section page."""
        return '/document/' in url.lower() and 'calregs' in url.lower()
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=16)
    )
    def fetch_page(self, url: str) -> str:
        """Fetch page HTML with retry logic."""
        time.sleep(config.REQUEST_DELAY_SECONDS)
        response = self.session.get(url, timeout=config.TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    
    def extract_links(self, html: str, base_url: str) -> Set[str]:
        """Extract all relevant CCR links from page."""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_url = urljoin(base_url, href)
            
            if 'calregs' in absolute_url and 'westlaw.com' in absolute_url:
                normalized = self.normalize_url(absolute_url)
                links.add(normalized)
                
        return links
    
    def discover_urls(self, start_url: str = None):
        """Main discovery method."""
        if start_url is None:
            start_url = config.CCR_BASE_URL
            
        to_visit = {start_url}
        visited = set()
        section_urls = set()
        
        print(f"\n🔍 Starting URL discovery from {start_url}")
        print(f"⚙️  Rate limit: {config.REQUEST_DELAY_SECONDS}s delay between requests\n")
        
        while to_visit:
            current_url = to_visit.pop()
            
            if current_url in visited:
                continue
                
            visited.add(current_url)
            print(f"✓ [{len(visited)} visited] {current_url[:80]}...")
            
            try:
                # Fetch page
                html = self.fetch_page(current_url)
                links = self.extract_links(html, current_url)
                
                crawler_logger.info(f"Found {len(links)} links on {current_url}")
                
                # Process links
                for link in links:
                    if link in visited:
                        continue
                        
                    if self.is_section_url(link):
                        section_urls.add(link)
                        self.discovered_urls.add(link)
                        print(f"  📄 Section found: {link[:70]}...")
                    else:
                        to_visit.add(link)
                
                # Save checkpoint every 20 pages
                if len(visited) % 20 == 0:
                    self.save_checkpoint()
                    self.save_discovered_urls()
                    print(f"\n💾 Checkpoint saved: {len(section_urls)} sections discovered\n")
                    
            except Exception as e:
                crawler_logger.error(f"Failed to crawl {current_url}: {e}")
                print(f"  ❌ Error: {e}")
        
        # Final save
        self.save_checkpoint()
        self.save_discovered_urls()
        
        print(f"\n✅ Discovery complete!")
        print(f"   Total sections found: {len(section_urls)}")
        print(f"   Saved to: {config.DISCOVERED_URLS_FILE}\n")
        
        return section_urls
    
    def save_discovered_urls(self):
        """Save discovered URLs to JSONL file."""
        try:
            with open(config.DISCOVERED_URLS_FILE, 'w', encoding='utf-8') as f:
                for url in sorted(self.discovered_urls):
                    discovered = DiscoveredURL(url=url)
                    f.write(discovered.model_dump_json() + '\n')
        except Exception as e:
            crawler_logger.error(f"Failed to save discovered URLs: {e}")

def main():
    """Main entry point."""
    discoverer = SimpleURLDiscoverer()
    discoverer.discover_urls()

if __name__ == "__main__":
    main()
