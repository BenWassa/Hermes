"""Fetch news articles from RSS feeds and extract content."""

import logging
from dataclasses import dataclass
from typing import List, Optional

import feedparser
from newspaper import Article

from .config import NEWS_SOURCES, MAX_ARTICLES_PER_SOURCE

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """Represents a news article with metadata and content."""
    title: str
    summary: str
    link: str
    content: str
    category: Optional[str] = None
    bullets: Optional[List[str]] = None


def fetch_articles(sources: Optional[List[str]] = None) -> List[NewsArticle]:
    """
    Fetch articles from RSS feed URLs.
    
    Args:
        sources: List of RSS feed URLs. Defaults to NEWS_SOURCES.
        
    Returns:
        List of NewsArticle objects.
    """
    if sources is None:
        sources = NEWS_SOURCES
        
    articles: List[NewsArticle] = []
    
    for url in sources:
        try:
            logger.info(f"Fetching from: {url}")
            feed = feedparser.parse(url)
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {url}")
                continue
                
            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                article = _parse_feed_entry(entry)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            logger.error(f"Error fetching from {url}: {e}")
            continue
    
    # Fallback sample data if no articles fetched
    if not articles:
        logger.warning("No articles fetched, using sample data")
        articles = _get_sample_articles()
    
    logger.info(f"Fetched {len(articles)} articles total")
    return articles


def _parse_feed_entry(entry) -> Optional[NewsArticle]:
    """Parse a single RSS feed entry into a NewsArticle."""
    try:
        title = entry.get("title", "").strip()
        summary = entry.get("summary", "").strip()
        link = entry.get("link", "").strip()
        
        if not title:
            return None
            
        # Fetch full article content
        content = _fetch_article_content(link) or summary
        
        return NewsArticle(
            title=title,
            summary=summary,
            link=link,
            content=content
        )
        
    except Exception as e:
        logger.error(f"Error parsing entry: {e}")
        return None


def _fetch_article_content(url: str) -> Optional[str]:
    """Fetch full article content from URL."""
    if not url:
        return None
        
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
        
    except Exception as e:
        logger.debug(f"Could not fetch article content from {url}: {e}")
        return None


def _get_sample_articles() -> List[NewsArticle]:
    """Return sample articles for testing/fallback."""
    return [
        NewsArticle(
            title="AI Breakthrough in Medical Diagnostics",
            summary="New AI system shows promise in early disease detection",
            link="https://example.com/ai-medical",
            content="Researchers have developed an AI system that can detect early-stage diseases with unprecedented accuracy. The technology uses advanced machine learning algorithms to analyze medical imaging data."
        ),
        NewsArticle(
            title="Global Climate Summit Reaches Key Agreement",
            summary="Nations commit to new emissions targets",
            link="https://example.com/climate-summit",
            content="World leaders at the climate summit have agreed to ambitious new emissions reduction targets. The agreement includes binding commitments for major economies."
        ),
        NewsArticle(
            title="Economic Markets Show Mixed Signals",
            summary="Investors react to policy changes",
            link="https://example.com/markets",
            content="Financial markets displayed volatility this week as investors processed new policy announcements. Tech stocks led gains while energy sectors declined."
        )
    ]
