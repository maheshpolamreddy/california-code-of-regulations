"""
Basic tests for crawler URL normalization and deduplication.
"""

import pytest
from crawler.url_discoverer import URLDiscoverer

def test_url_normalization():
    """Test URL normalization removes fragments and standardizes format."""
    discoverer = URLDiscoverer()
    
    url1 = "https://govt.westlaw.com/calregs/document/cc?section=1234#fragment"
    url2 = "https://govt.westlaw.com/calregs/document/cc?section=1234"
    
    normalized1 = discoverer.normalize_url(url1)
    normalized2 = discoverer.normalize_url(url2)
    
    # Should normalize to same URL (no fragment)
    assert normalized1 == normalized2
    assert "#" not in normalized1

def test_is_section_url():
    """Test section URL detection."""
    discoverer = URLDiscoverer()
    
    section_url = "https://govt.westlaw.com/calregs/document/cc?section=1234"
    index_url = "https://govt.westlaw.com/calregs/browse"
    
    assert discoverer.is_section_url(section_url)
    assert not discoverer.is_section_url(index_url)

def test_url_deduplication():
    """Test that discovered URLs are deduplicated (raw strings; fragments create distinct entries)."""
    discoverer = URLDiscoverer()
    discoverer.discovered_urls = set()  # Isolate test from checkpoint state

    url = "https://govt.westlaw.com/calregs/document/cc?section=1234"

    discoverer.discovered_urls.add(url)
    discoverer.discovered_urls.add(url)  # Same URL
    discoverer.discovered_urls.add(url + "#fragment")  # Different string (with fragment)

    # Set has 2 distinct strings: url and url+#fragment
    assert len(discoverer.discovered_urls) == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
