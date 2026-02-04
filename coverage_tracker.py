"""
Coverage Tracker Module
Validates completeness of CCR extraction by comparing discovered vs extracted URLs.
Generates detailed coverage reports.
"""

import json
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime, timezone
import sys
sys.path.append(str(Path(__file__).parent))

import config
from logger import setup_logger

coverage_logger = setup_logger('coverage', 'coverage.log')

class CoverageTracker:
    """
    Tracks and validates extraction coverage.
    Compares discovered URLs against successfully extracted sections.
    """
    
    def __init__(self):
        self.discovered_urls: Set[str] = set()
        self.extracted_urls: Set[str] = set()
        self.failed_urls: Dict[str, dict] = {}
        
    def load_discovered_urls(self):
        """Load all discovered URLs."""
        if not config.DISCOVERED_URLS_FILE.exists():
            coverage_logger.error(f"Discovered URLs file not found: {config.DISCOVERED_URLS_FILE}")
            return
            
        with open(config.DISCOVERED_URLS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    self.discovered_urls.add(data['url'])
        
        coverage_logger.info(f"Loaded {len(self.discovered_urls)} discovered URLs")
    
    def load_extracted_urls(self):
        """Load all successfully extracted URLs."""
        if not config.EXTRACTED_SECTIONS_FILE.exists():
            coverage_logger.warning(f"Extracted sections file not found: {config.EXTRACTED_SECTIONS_FILE}")
            return
            
        with open(config.EXTRACTED_SECTIONS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    url = data.get('source_url') or data.get('section_url')
                    if url:
                        # Normalize: strip #chunk0 etc. for dedup
                        if '#chunk' in url:
                            url = url.split('#chunk')[0]
                        self.extracted_urls.add(url)
        
        coverage_logger.info(f"Loaded {len(self.extracted_urls)} extracted URLs")
    
    def load_failed_urls(self):
        """Load failed URL information."""
        if not config.FAILED_URLS_FILE.exists():
            coverage_logger.info("No failed URLs file found")
            return
            
        with open(config.FAILED_URLS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    self.failed_urls[data['url']] = {
                        'error_type': data.get('error_type'),
                        'error_message': data.get('error_message'),
                        'retry_count': data.get('retry_count', 0)
                    }
        
        coverage_logger.info(f"Loaded {len(self.failed_urls)} failed URLs")
    
    def calculate_coverage(self) -> Dict[str, any]:
        """
        Calculate coverage statistics.
        Returns detailed metrics about extraction completeness.
        """
        missing_urls = self.discovered_urls - self.extracted_urls
        
        total_discovered = len(self.discovered_urls)
        total_extracted = len(self.extracted_urls)
        total_failed = len(self.failed_urls)
        total_missing = len(missing_urls)
        
        coverage_percentage = (total_extracted / total_discovered * 100) if total_discovered > 0 else 0
        
        return {
            'total_discovered': total_discovered,
            'total_extracted': total_extracted,
            'total_failed': total_failed,
            'total_missing': total_missing,
            'coverage_percentage': coverage_percentage,
            'missing_urls': list(missing_urls)
        }
    
    def generate_report(self) -> str:
        """
        Generate comprehensive coverage report in Markdown format.
        """
        self.load_discovered_urls()
        self.load_extracted_urls()
        self.load_failed_urls()
        
        stats = self.calculate_coverage()
        total_d = max(stats['total_discovered'], 1)
        
        report = f"""# CCR Compliance Agent - Coverage Report

**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Summary Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Total Discovered URLs | {stats['total_discovered']} | 100.0% |
| Successfully Extracted | {stats['total_extracted']} | {stats['coverage_percentage']:.2f}% |
| Failed Extractions | {stats['total_failed']} | {stats['total_failed']/total_d*100:.2f}% |
| Missing/Unprocessed | {stats['total_missing']} | {stats['total_missing']/total_d*100:.2f}% |

## Coverage Status

"""
        if stats['coverage_percentage'] >= 95:
            report += "✅ **EXCELLENT**: Coverage is >95% - deployment ready\n\n"
        elif stats['coverage_percentage'] >= 90:
            report += "⚠️ **GOOD**: Coverage is >90% - minor gaps acceptable\n\n"
        elif stats['coverage_percentage'] >= 80:
            report += "⚠️ **ACCEPTABLE**: Coverage is >80% - investigate missing sections\n\n"
        else:
            report += "❌ **INSUFFICIENT**: Coverage is <80% - significant gaps exist\n\n"
        
        # Failed URLs breakdown
        if self.failed_urls:
            report += "## Failed Extractions\n\n"
            
            # Group by error type
            error_types = {}
            for url, info in self.failed_urls.items():
                error_type = info['error_type']
                if error_type not in error_types:
                    error_types[error_type] = []
                error_types[error_type].append((url, info['error_message']))
            
            for error_type, urls_list in error_types.items():
                report += f"### {error_type} ({len(urls_list)} URLs)\n\n"
                for url, msg in urls_list[:10]:  # Show first 10
                    report += f"- [{url}]({url})\n  - Error: `{msg}`\n"
                if len(urls_list) > 10:
                    report += f"- _(and {len(urls_list) - 10} more)_\n"
                report += "\n"
        
        # Missing URLs
        if stats['missing_urls']:
            report += "## Missing/Unprocessed URLs\n\n"
            report += f"Total: {len(stats['missing_urls'])} URLs\n\n"
            for url in stats['missing_urls'][:20]:  # Show first 20
                report += f"- [{url}]({url})\n"
            if len(stats['missing_urls']) > 20:
                report += f"- _(and {len(stats['missing_urls']) - 20} more)_\n"
            report += "\n"
        
        # Recommendations
        report += "## Recommendations\n\n"
        
        if stats['total_failed'] > 0:
            report += "1. **Retry failed URLs** with adjusted parameters (longer timeout, different parser)\n"
        
        if stats['total_missing'] > 0:
            report += "2. **Process missing URLs** by re-running the extraction pipeline\n"
        
        if stats['coverage_percentage'] < 100:
            report += "3. **Manual review** recommended for any URLs that consistently fail\n"
        else:
            report += "✅ **No action needed** - Full coverage achieved!\n"
        
        report += "\n## Notes\n\n"
        report += "- This report tracks discovered section URLs vs successfully extracted sections\n"
        report += "- Coverage percentage indicates extraction completeness\n"
        report += "- Failed URLs may be retried with exponential backoff\n"
        report += "- Some failures may be due to invalid/removed sections on the source website\n"
        
        return report
    
    def save_report(self):
        """Generate and save coverage report."""
        report = self.generate_report()
        
        with open(config.COVERAGE_REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        
        coverage_logger.info(f"Coverage report saved to {config.COVERAGE_REPORT_FILE}")
        print(f"\nCoverage Report saved to: {config.COVERAGE_REPORT_FILE}")
        
        # Also print summary to console
        stats = self.calculate_coverage()
        print(f"\n{'='*60}")
        print(f"COVERAGE SUMMARY")
        print(f"{'='*60}")
        print(f"Discovered URLs:     {stats['total_discovered']}")
        print(f"Extracted:           {stats['total_extracted']} ({stats['coverage_percentage']:.2f}%)")
        print(f"Failed:              {stats['total_failed']}")
        print(f"Missing:             {stats['total_missing']}")
        print(f"{'='*60}\n")

def main():
    """Main entry point for coverage tracking."""
    tracker = CoverageTracker()
    tracker.save_report()

if __name__ == "__main__":
    main()
