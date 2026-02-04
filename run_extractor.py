"""
Run Section Extractor with Windows Compatibility
Handles async event loop policy for Windows systems
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from crawler.section_extractor import SectionExtractor

async def main():
    """Main entry point for section extraction"""
    print("\n" + "="*70)
    print("CCR SECTION EXTRACTOR - WINDOWS COMPATIBLE")
    print("="*70 + "\n")
    
    extractor = SectionExtractor()
    await extractor.process_discovered_urls()
    
    print("\n" + "="*70)
    print("EXTRACTION COMPLETE!")
    print("="*70)
    print("\nNext step: Run index_pipeline.py to index sections into Supabase\n")

if __name__ == "__main__":
    # Set Windows-compatible event loop policy
    if sys.platform == "win32":
        # Use ProactorEventLoop for Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExtraction cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise
