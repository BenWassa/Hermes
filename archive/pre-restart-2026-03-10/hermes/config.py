"""Configuration for Project Hermes."""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# RSS feed URLs for news sources
NEWS_SOURCES = [
    "https://feeds.reuters.com/reuters/topNews",
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://apnews.com/rss"
]

# Keywords to exclude (noise filtering)
EXCLUDE_KEYWORDS = [
    "shooting", "arrested", "celebrity", "gossip", "crime", "stabbing",
    "viral", "social media", "instagram", "twitter", "tiktok"
]

# Keywords for categorization
CATEGORY_KEYWORDS = {
    "🌍 Global Affairs": [
        "election", "war", "diplomacy", "government", "politics", 
        "international", "treaty", "sanctions", "conflict"
    ],
    "⚙️ Tech & AI": [
        "technology", "tech", "ai", "artificial intelligence", "software", 
        "hardware", "computing", "digital", "innovation", "startup"
    ],
    "🧬 Science & Health": [
        "science", "research", "health", "medicine", "climate", "environment",
        "study", "discovery", "breakthrough", "medical"
    ],
    "📊 Economy & Policy": [
        "economy", "market", "policy", "finance", "trade", "business",
        "economic", "financial", "investment", "regulatory"
    ],
    "📚 Culture & Ideas": [
        "culture", "society", "education", "ideas", "philosophy",
        "social", "academic", "intellectual"
    ]
}

# OpenAI configuration
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Output directories
DATA_DIR = PROJECT_ROOT / "data"
DIGEST_DIR = DATA_DIR / "digests"
LOGS_DIR = DATA_DIR / "logs"

# Create directories if they don't exist
for directory in [DATA_DIR, DIGEST_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Maximum articles per source and total
MAX_ARTICLES_PER_SOURCE = 5
MAX_TOTAL_ARTICLES = 15
