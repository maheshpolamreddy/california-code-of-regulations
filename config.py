"""
Configuration management for CCR Compliance Agent.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env optional; use os.environ

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Crawling Configuration
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))  # Avoid hammering site
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "45"))
CHECKPOINT_EVERY_N_URLS = int(os.getenv("CHECKPOINT_EVERY_N_URLS", "50"))  # Persistent checkpoints

# Base URL for CCR
CCR_BASE_URL = "https://govt.westlaw.com/calregs"

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
CHECKPOINT_DIR = BASE_DIR / os.getenv("CHECKPOINT_DIR", "checkpoints")
LOGS_DIR = BASE_DIR / os.getenv("LOGS_DIR", "logs")

# Create directories if they don't exist
# On Vercel (read-only), these might fail, so we ignore errors
# The app handles missing local files gracefully via Exception handling in modules
for directory in [DATA_DIR, CHECKPOINT_DIR, LOGS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
    except OSError:
        pass  # Ignore on read-only filesystems

# File paths
DISCOVERED_URLS_FILE = DATA_DIR / "discovered_urls.jsonl"
EXTRACTED_SECTIONS_FILE = DATA_DIR / "extracted_sections.jsonl"
FAILED_URLS_FILE = DATA_DIR / "failed_urls.jsonl"
COVERAGE_REPORT_FILE = DATA_DIR / "coverage_report.md"

# Embedding Configuration
# Use Gemini if API key is available, otherwise fall back to OpenAI
EMBEDDING_MODEL = "models/gemini-embedding-001" if GEMINI_API_KEY else "text-embedding-3-small"
EMBEDDING_DIMENSION = 768 if GEMINI_API_KEY else 1536
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens

# Agent Configuration
# Use Gemini if API key is available, otherwise fall back to OpenAI
AGENT_MODEL = "gemini-2.0-flash" if GEMINI_API_KEY else "gpt-4o-mini"
AGENT_TEMPERATURE = 0.1
MAX_RETRIEVAL_RESULTS = 10

# Supabase Table Name
SUPABASE_TABLE_NAME = "ccr_sections"

# Gemini API Retry Configuration
GEMINI_RETRY_ATTEMPTS = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "5"))
GEMINI_RETRY_MIN_WAIT = int(os.getenv("GEMINI_RETRY_MIN_WAIT", "2"))
GEMINI_RETRY_MAX_WAIT = int(os.getenv("GEMINI_RETRY_MAX_WAIT", "60"))
