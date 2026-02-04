"""
Pydantic models for canonical CCR data structure.
Defines the schema for California Code of Regulations sections.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

class CCRSection(BaseModel):
    """
    Canonical structure for a CCR section.
    Handles the hierarchical organization: Title → Division → Chapter → Article → Section
    """
    model_config = ConfigDict()

    # Hierarchical Metadata
    title_number: Optional[int] = Field(None, description="CCR Title number (e.g., 17)")
    title_name: Optional[str] = Field(None, description="CCR Title name (e.g., 'Public Health')")
    division: Optional[str] = Field(None, description="Division number/name (may not exist)")
    chapter: Optional[str] = Field(None, description="Chapter number/name")
    subchapter: Optional[str] = Field(None, description="Subchapter (if present)")
    article: Optional[str] = Field(None, description="Article number/name (if present)")

    # Section Identifiers
    section_number: str = Field(..., description="Section number (e.g., '1234')")
    section_heading: str = Field(..., description="Section heading/title")

    # Citation and Navigation
    citation: str = Field(..., description="Full citation (e.g., '17 CCR § 1234')")
    breadcrumb_path: str = Field(..., description="Human-readable hierarchy path")
    source_url: str = Field(..., description="Original URL on govt.westlaw.com")

    # Content
    content_markdown: str = Field(..., description="Section content in Markdown format")

    # Metadata
    retrieved_at: datetime = Field(default_factory=_utc_now, description="Timestamp of retrieval")

class DiscoveredURL(BaseModel):
    """
    Represents a discovered CCR section URL during crawling.
    Used for tracking discovery vs extraction progress.
    """
    url: str
    title_number: Optional[int] = None
    discovered_at: datetime = Field(default_factory=_utc_now)

class FailedURL(BaseModel):
    """
    Tracks URLs that failed during extraction with error details.
    """
    url: str
    error_type: str
    error_message: str
    retry_count: int = 0
    failed_at: datetime = Field(default_factory=_utc_now)
