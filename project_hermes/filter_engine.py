"""Filter news articles based on simple keyword rules."""
from typing import List
import re

from .news_fetcher import NewsArticle
from .config import EXCLUDE_KEYWORDS, CATEGORY_KEYWORDS


def filter_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Filter out articles containing excluded keywords."""
    filtered = []
    for article in articles:
        text = f"{article.title} {article.summary}"
        if any(re.search(r"\b" + kw + r"\b", text, re.IGNORECASE) for kw in EXCLUDE_KEYWORDS):
            continue
        filtered.append(article)
    return filtered


def categorize_article(article: NewsArticle) -> str:
    """Assign a category based on keyword presence."""
    text = f"{article.title} {article.summary} {article.content}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            return category
    return "Misc"
