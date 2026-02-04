"""
Section Extraction Module
Extracts content and metadata from discovered CCR section URLs.
Implements retry logic and checkpointing.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent))

from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tenacity import retry, stop_after_attempt, wait_exponential
import config
from logger import extraction_logger
from models import CCRSection, FailedURL

class SectionExtractor:
    """
    Extracts CCR section content and metadata from individual pages.
    Implements robust error handling and retry logic.
    """
    
    def __init__(self):
        self.extracted_count = 0
        self.failed_urls = []
        self.checkpoint_file = config.CHECKPOINT_DIR / "extraction_checkpoint.json"
        self.extracted_urls = self.load_extracted_urls()
        
    def load_extracted_urls(self) -> set:
        """Load already extracted URLs to avoid re-processing."""
        extracted = set()
        if config.EXTRACTED_SECTIONS_FILE.exists():
            try:
                with open(config.EXTRACTED_SECTIONS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            section = json.loads(line)
                            extracted.add(section.get('source_url'))
                extraction_logger.info(f"Loaded {len(extracted)} already extracted URLs")
            except Exception as e:
                extraction_logger.error(f"Failed to load extracted URLs: {e}")
        return extracted
    
    def extract_title_number(self, text: str) -> Optional[int]:
        """Extract title number from breadcrumb or heading."""
        match = re.search(r'Title\s+(\d+)', text, re.IGNORECASE)
        return int(match.group(1)) if match else None
    
    def extract_section_number(self, text: str) -> Optional[str]:
        """Extract section number (e.g., '1234' from '§ 1234' or from URL)."""
        if not text:
            return None
        # Try various patterns
        patterns = [
            r'§\s*(\d+(?:\.\d+)?)',  # § 1234 or § 1234.5
            r'Section\s+(\d+(?:\.\d+)?)',
            r'sec\.\s*(\d+(?:\.\d+)?)',
            r'\b(\d{3,}(?:\.\d+)?)\b',  # 3+ digit number (CCR section numbers, avoid 2-digit)
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_section_number_from_url(self, url: str) -> Optional[str]:
        """Extract section number from Westlaw document URL if present (e.g. document id hints)."""
        # Westlaw uses Document/... URLs; section numbers often in content, not URL
        # Fallback: look for numeric patterns in path
        match = re.search(r'[/\-](\d{4,}(?:\.\d+)?)[/?]', url)
        return match.group(1) if match else None
    
    def parse_breadcrumb(self, soup: BeautifulSoup) -> Dict[str, any]:
        """
        Parse breadcrumb navigation to extract hierarchical metadata.
        Returns dict with title, division, chapter, etc.
        """
        metadata = {
            'title_number': None,
            'title_name': None,
            'division': None,
            'chapter': None,
            'subchapter': None,
            'article': None,
            'breadcrumb_path': ''
        }
        
        # Look for breadcrumb elements
        breadcrumb = soup.find('nav', class_=re.compile('breadcrumb|navigation', re.I))
        if not breadcrumb:
            breadcrumb = soup.find('div', class_=re.compile('breadcrumb', re.I))
        
        if breadcrumb:
            breadcrumb_text = breadcrumb.get_text(separator=' > ', strip=True)
            metadata['breadcrumb_path'] = breadcrumb_text
            
            # Extract title
            title_num = self.extract_title_number(breadcrumb_text)
            if title_num:
                metadata['title_number'] = title_num
                
            # Extract other hierarchy levels
            parts = breadcrumb_text.split('>')
            for part in parts:
                part = part.strip()
                if 'title' in part.lower():
                    metadata['title_name'] = part
                elif 'division' in part.lower():
                    metadata['division'] = part
                elif 'chapter' in part.lower():
                    metadata['chapter'] = part
                elif 'article' in part.lower():
                    metadata['article'] = part
                elif 'subchapter' in part.lower():
                    metadata['subchapter'] = part
        
        return metadata
    
    def extract_section_content(self, soup: BeautifulSoup) -> tuple[str, str, str]:
        """
        Extract section heading and content.
        Returns (section_number, section_heading, content_markdown)
        """
        section_number = None
        section_heading = "Unknown"
        content_html = ""
        
        # Find section heading (usually in h1, h2, or specific class)
        heading_tag = soup.find(['h1', 'h2'], class_=re.compile('section|heading|title', re.I))
        if not heading_tag:
            heading_tag = soup.find(['h1', 'h2'])
            
        if heading_tag:
            heading_text = heading_tag.get_text(strip=True)
            section_heading = heading_text
            section_number = self.extract_section_number(heading_text)
        
        # Find main content (usually in specific container)
        content_div = soup.find('div', class_=re.compile('content|body|section-content', re.I))
        if not content_div:
            # Fallback: get main tag or article
            content_div = soup.find(['main', 'article'])
        if not content_div:
            # Last resort: get body
            content_div = soup.find('body')
        
        if content_div:
            # Remove script, style, nav elements
            for tag in content_div.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            content_html = str(content_div)
        
        # Convert HTML to Markdown
        content_markdown = md(content_html, heading_style="ATX").strip()
        
        return section_number, section_heading, content_markdown
    
    def build_citation(self, title_number: Optional[int], section_number: Optional[str]) -> str:
        """Build standard CCR citation (e.g., '17 CCR § 1234')."""
        if title_number and section_number:
            return f"{title_number} CCR § {section_number}"
        elif section_number:
            return f"CCR § {section_number}"
        else:
            return "CCR (unknown section)"
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True
    )
    async def extract_section(self, url: str, crawler: AsyncWebCrawler) -> Optional[CCRSection]:
        """
        Extract a single CCR section from URL.
        Implements exponential backoff retry logic.
        """
        try:
            await asyncio.sleep(config.REQUEST_DELAY_SECONDS)
            
            result = await crawler.arun(url=url, timeout=config.TIMEOUT_SECONDS)
            
            if not result.success:
                raise Exception(f"Crawl failed: {result.error_message}")
            
            soup = BeautifulSoup(result.html, 'lxml')
            
            # Parse breadcrumb for hierarchy
            metadata = self.parse_breadcrumb(soup)
            
            # Extract section content
            section_number, section_heading, content_markdown = self.extract_section_content(soup)
            
            # If we couldn't extract section number from heading, try from URL or breadcrumb
            if not section_number:
                section_number = self.extract_section_number_from_url(url)
            if not section_number:
                section_number = self.extract_section_number(metadata['breadcrumb_path'])
            if not section_number:
                section_number = "unknown"
            
            # Build citation
            citation = self.build_citation(metadata['title_number'], section_number)
            
            # Create CCRSection object
            section = CCRSection(
                title_number=metadata['title_number'],
                title_name=metadata['title_name'],
                division=metadata['division'],
                chapter=metadata['chapter'],
                subchapter=metadata['subchapter'],
                article=metadata['article'],
                section_number=section_number,
                section_heading=section_heading,
                citation=citation,
                breadcrumb_path=metadata['breadcrumb_path'],
                source_url=url,
                content_markdown=content_markdown,
                retrieved_at=datetime.utcnow()
            )
            
            return section
            
        except Exception as e:
            extraction_logger.error(f"Failed to extract {url}: {e}")
            raise
    
    async def process_discovered_urls(self, limit: int = None):
        """
        Process all discovered URLs and extract sections concurrently.
        Main extraction pipeline.

        Args:
            limit: If set, process only the first N URLs (for quick test).
        """
        # Load discovered URLs
        if not config.DISCOVERED_URLS_FILE.exists():
            extraction_logger.error(f"No discovered URLs file found at {config.DISCOVERED_URLS_FILE}")
            print("❌ Please run url_discoverer.py first to discover URLs")
            return

        urls_to_process = []
        with open(config.DISCOVERED_URLS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    url = data["url"]
                    if url not in self.extracted_urls:
                        urls_to_process.append(url)
                        if limit and len(urls_to_process) >= limit:
                            break

        total = len(urls_to_process)
        extraction_logger.info(f"Processing {total} URLs" + (f" (limit={limit})" if limit else ""))
        print(f"📊 Total URLs to extract: {total}" + (f" (limit {limit})" if limit else ""))
        
        # Concurrency limit
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)
        
        async def process_url(url: str, crawler: AsyncWebCrawler, idx: int):
            async with semaphore:
                try:
                    # Small random delay to prevent thundering herd
                    await asyncio.sleep(config.REQUEST_DELAY_SECONDS)
                    
                    section = await self.extract_section(url, crawler)
                    
                    if section:
                        # Save to JSONL (append mode is atomic-ish for small writes, but lock is safer if needed)
                        # For simplicity in this script, we'll write directly. 
                        # In high concurrency, a file lock is better, but JSONL append is usually fine.
                        with open(config.EXTRACTED_SECTIONS_FILE, 'a', encoding='utf-8') as f:
                            f.write(section.model_dump_json() + '\n')
                        
                        self.extracted_count += 1
                        extraction_logger.info(f"✓ Extracted: {section.citation}")
                        
                        # Print progress occasionally
                        if self.extracted_count % 10 == 0:
                            print(f"Progress: {self.extracted_count}/{total} ({(self.extracted_count/total)*100:.1f}%) - Extracted: {self.extracted_count}, Failed: {len(self.failed_urls)}")

                except Exception as e:
                    extraction_logger.error(f"✗ Failed {url}: {e}")
                    failed = FailedURL(
                        url=url,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                    self.failed_urls.append(failed)
                    # Also write failed to file incrementally to avoid loss
                    with open(config.FAILED_URLS_FILE, 'a', encoding='utf-8') as f:
                        f.write(failed.model_dump_json() + '\n')

        # Use a single crawler instance
        async with AsyncWebCrawler(verbose=False) as crawler:
            tasks = []
            for idx, url in enumerate(urls_to_process, 1):
                tasks.append(process_url(url, crawler, idx))
            
            # Run all tasks
            print(f"🚀 Starting concurrent extraction with {config.MAX_CONCURRENT_REQUESTS} workers...")
            await asyncio.gather(*tasks)
        
        print(f"\n✅ Extraction complete!")
        print(f"   Extracted: {self.extracted_count}")
        print(f"   Failed: {len(self.failed_urls)}")
        print(f"   Data saved to: {config.EXTRACTED_SECTIONS_FILE}")

async def main(limit: int = None):
    """Main entry point for section extraction."""
    extractor = SectionExtractor()
    await extractor.process_discovered_urls(limit=limit)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract CCR sections from discovered URLs")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Process only first N URLs (quick test)")
    args = parser.parse_args()

    if __import__("platform").system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(limit=args.limit))
