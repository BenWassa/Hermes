"""Summarize articles using OpenAI API with a simple fallback."""
from typing import List
import os
import textwrap

try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    openai = None

from .config import OPENAI_MODEL


def summarize_article(text: str) -> List[str]:
    """Summarize text into bullet points. Uses OpenAI if available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and openai is not None:
        openai.api_key = api_key
        try:
            resp = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": f"Summarize into 3 concise bullet points:\n{text}"}]
            )
            content = resp.choices[0].message["content"]
            bullets = [line.strip("- ") for line in content.splitlines() if line.strip()]
            return bullets[:5]
        except Exception:
            pass
    # Fallback: naive bullet points using first sentences
    sentences = [s.strip() for s in textwrap.wrap(text, 200)[:3]]
    return [s for s in sentences if s]
