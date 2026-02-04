"""
Windows-compatible section extractor
Extracts content from discovered URLs
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
sys.path.append(str(Path(__file__).parent.parent))

import requests  
from bs4 import BeautifulSoup
from markdownify import markdownify as md

import config
from logger import extraction_logger
from models import CCRSection

class SimpleSectionExtractor:
    """Extract CCR sections using requests library (Windows-compatible)."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.extracted_count = 0
        self.failed_count = 0
        
    def extract_section(self, url: str) -> dict:
        """Extract section data from URL."""
        try:
            time.sleep(config.REQUEST_DELAY_SECONDS)
            response = self.session.get(url, timeout=config.TIMEOUT_SECONDS)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title/heading
            h1 = soup.find('h1')
            heading = h1.get_text().strip() if h1 else "Unknown Section"
            
            # Extract section number from heading (e.g., "Section 1234" -> "1234")
            section_number = heading.split()[-1] if heading else "Unknown"
            
            # Extract main content
            content_div = soup.find('div', class_='content') or soup.find('main') or soup.find('body')
            content_html = str(content_div) if content_div else "<p>No content found</p>"
            content_markdown = md(content_html)
            
            # Build citation
            citation = f"CCR § {section_number}"
            
            section_data = {
                'section_url': url,
                'section_number': section_number,
                'section_heading': heading,
                'citation': citation,
                'content_markdown': content_markdown[:2000],  # Limit for demo
                'breadcrumb_path': heading,
                'retrieved_at': datetime.utcnow().isoformat()
            }
            
            extraction_logger.info(f"Extracted: {heading}")
            return section_data
            
        except Exception as e:
            extraction_logger.error(f"Failed to extract {url}: {e}")
            return None
    
    def process_urls(self, max_sections=None):
        """Process discovered URLs."""
        limit_text = f"{max_sections} sections" if max_sections else "ALL sections"
        print(f"\n🔍 Starting Section Extraction (Processing {limit_text})\n")
        
        # Load discovered URLs
        with open(config.DISCOVERED_URLS_FILE, 'r', encoding='utf-8') as f:
            urls = [json.loads(line)['url'] for line in f]
        
        print(f"Found {len(urls)} discovered URLs")
        extract_text = f"first {max_sections}" if max_sections else "all"
        print(f"Extracting {extract_text} sections...\n")
        
        extracted_sections = []
        
        for i, url in enumerate(urls[:max_sections], 1):
            print(f"[{i}/{max_sections}] Extracting: {url[:70]}...")
            
            section_data = self.extract_section(url)
            if section_data:
                extracted_sections.append(section_data)
                self.extracted_count += 1
                print(f"  ✓ {section_data['section_heading'][:60]}")
            else:
                self.failed_count += 1
                print(f"  ❌ Failed")
        
        # Save extracted sections
        print(f"\n💾 Saving extracted sections...")
        with open(config.EXTRACTED_SECTIONS_FILE, 'w', encoding='utf-8') as f:
            for section in extracted_sections:
                f.write(json.dumps(section) + '\n')
        
        print(f"\n{'='*70}")
        print(f"✅ Extraction Complete!")
        print(f"   Successful: {self.extracted_count}")
        print(f"   Failed: {self.failed_count}")
        print(f"   Saved to: {config.EXTRACTED_SECTIONS_FILE}")
        print(f"{'='*70}\n")
        
        return extracted_sections

def main():
    """Main entry point."""
    extractor = SimpleSectionExtractor()
    extractor.process_urls()  # Extract ALL sections (no limit)
    
    print("Next steps:")
    print("1. Run: python index_pipeline.py (to index to Supabase)")
    print("2. Run: python cli.py (to test the AI agent)\n")

if __name__ == "__main__":
    main()
