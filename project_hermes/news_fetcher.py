"""Fetch news articles from RSS feeds and extract basic content."""

from dataclasses import dataclass
from typing import List
import feedparser
from newspaper import Article

@dataclass
class NewsArticle:
    title: str
    summary: str
    link: str
    content: str
    bullets: List[str] | None = None


def fetch_articles(feeds: List[str]) -> List[NewsArticle]:
    """Fetch articles from the given RSS feed URLs."""
    articles: List[NewsArticle] = []
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # limit per source for speed
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            content = ""
            if link:
                try:
                    art = Article(link)
                    art.download()
                    art.parse()
                    content = art.text
                except Exception:
                    content = summary
            articles.append(NewsArticle(title=title, summary=summary, link=link, content=content))
    if not articles:
        articles = [
            NewsArticle(title="Sample Tech News", summary="Sample", link="", content="Technology and AI are advancing rapidly."),
            NewsArticle(title="Sample Economy News", summary="Sample", link="", content="Global markets show mixed results amid policy changes."),
            NewsArticle(title="Sample Science News", summary="Sample", link="", content="Researchers discover new insights in health science.")
        ]
    return articles
