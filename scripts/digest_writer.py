"""Write summarized articles to a Markdown digest."""
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .config import DIGEST_DIR
from .news_fetcher import NewsArticle


def write_digest(articles: Dict[str, List[NewsArticle]]) -> Path:
    """Write articles grouped by category to a Markdown file."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    filepath = DIGEST_DIR / f"{today}.md"
    lines = [f"# \U0001F5DE\ufe0f Project Hermes Digest — {today}\n"]
    for category, items in articles.items():
        lines.append(f"## {category}\n")
        for art in items:
            lines.append(f"**{art.title}**")
            for bullet in (art.bullets or []):
                lines.append(f"- {bullet}")
            if art.link:
                lines.append(f"[Read more →]({art.link})\n")
        lines.append("")
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath
