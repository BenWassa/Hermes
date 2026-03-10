"""Filter and categorize news articles."""

import logging
import re
from typing import List

from .config import EXCLUDE_KEYWORDS, CATEGORY_KEYWORDS
from .fetcher import NewsArticle

logger = logging.getLogger(__name__)


def filter_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """
    Filter out articles containing excluded keywords.
    
    Args:
        articles: List of NewsArticle objects to filter.
        
    Returns:
        Filtered list of NewsArticle objects.
    """
    filtered = []
    excluded_count = 0
    
    for article in articles:
        if _should_exclude_article(article):
            excluded_count += 1
            logger.debug(f"Excluded article: {article.title}")
            continue
        filtered.append(article)
    
    logger.info(f"Filtered {excluded_count} articles, {len(filtered)} remaining")
    return filtered


def categorize_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """
    Assign categories to articles based on keyword matching.
    
    Args:
        articles: List of NewsArticle objects to categorize.
        
    Returns:
        List of NewsArticle objects with categories assigned.
    """
    for article in articles:
        article.category = _determine_category(article)
    
    return articles


def _should_exclude_article(article: NewsArticle) -> bool:
    """Check if article should be excluded based on keywords."""
    text = f"{article.title} {article.summary}".lower()
    
    for keyword in EXCLUDE_KEYWORDS:
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, text):
            return True
    
    return False


def _determine_category(article: NewsArticle) -> str:
    """Determine the category for an article based on keywords."""
    text = f"{article.title} {article.summary} {article.content}".lower()
    
    # Score each category
    category_scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1
        category_scores[category] = score
    
    # Return category with highest score, or default
    if category_scores and max(category_scores.values()) > 0:
        return max(category_scores.items(), key=lambda x: x[1])[0]
    
    return "📰 Other"
