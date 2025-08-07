"""Run the Project Hermes pilot pipeline."""
from collections import defaultdict

from .config import NEWS_SOURCES
from .news_fetcher import fetch_articles, NewsArticle
from .filter_engine import filter_articles, categorize_article
from .summarizer import summarize_article
from .digest_writer import write_digest


def run() -> None:
    articles = fetch_articles(NEWS_SOURCES)
    articles = filter_articles(articles)

    categorized = defaultdict(list)
    for art in articles[:10]:  # limit total articles for pilot
        art.bullets = summarize_article(art.content or art.summary)
        category = categorize_article(art)
        categorized[category].append(art)

    if not categorized:
        print("No articles to write.")
        return
    path = write_digest(categorized)
    print(f"Digest written to {path}")


if __name__ == "__main__":
    run()
