"""Configuration for Project Hermes pilot backend."""

from pathlib import Path

# RSS feed URLs for news sources
NEWS_SOURCES = [
    "https://feeds.reuters.com/reuters/topNews",
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://apnews.com/rss"
]

# Keywords to exclude (noise)
EXCLUDE_KEYWORDS = [
    "shooting", "arrested", "celebrity", "gossip", "crime"
]

# Keywords to include for categorization
CATEGORY_KEYWORDS = {
    "Global Affairs": ["election", "war", "diplomacy", "government"],
    "Tech & AI": ["technology", "tech", "ai", "artificial intelligence", "software", "hardware"],
    "Science & Health": ["science", "research", "health", "medicine", "climate"],
    "Economy & Policy": ["economy", "market", "policy", "finance", "trade"],
    "Culture & Ideas": ["culture", "society", "education", "ideas"]
}

# OpenAI model name
OPENAI_MODEL = "gpt-4o-mini"

# Output directory for digests
DIGEST_DIR = Path(__file__).resolve().parent / "data" / "digests"
DIGEST_DIR.mkdir(parents=True, exist_ok=True)
