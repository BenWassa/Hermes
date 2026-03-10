"""Summarize articles using OpenAI API or fallback methods."""

import logging
import os
import textwrap
from typing import List, Optional

from .config import OPENAI_MODEL, OPENAI_API_KEY
from .fetcher import NewsArticle

logger = logging.getLogger(__name__)

# Optional OpenAI import
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    openai = None
    HAS_OPENAI = False


def summarize_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """
    Summarize articles into bullet points.
    
    Args:
        articles: List of NewsArticle objects to summarize.
        
    Returns:
        List of NewsArticle objects with bullets added.
    """
    for article in articles:
        try:
            article.bullets = _summarize_text(article.content or article.summary)
            logger.debug(f"Summarized: {article.title}")
        except Exception as e:
            logger.error(f"Error summarizing {article.title}: {e}")
            article.bullets = _fallback_summary(article.content or article.summary)
    
    return articles


def _summarize_text(text: str) -> List[str]:
    """Summarize text using OpenAI or fallback method."""
    if _can_use_openai():
        return _openai_summary(text)
    else:
        return _fallback_summary(text)


def _can_use_openai() -> bool:
    """Check if OpenAI API is available and configured."""
    return HAS_OPENAI and OPENAI_API_KEY is not None and OPENAI_API_KEY.strip() != ""


def _openai_summary(text: str) -> List[str]:
    """Generate summary using OpenAI API."""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""Summarize the following news article into 3-4 concise bullet points. 
        Focus on the most important facts and developments. Each bullet should be one clear sentence.
        
        Article: {text[:1500]}"""  # Limit text length for API
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        bullets = [
            "• " + line.strip().lstrip('•-* ').strip() 
            for line in content.split('\n') 
            if line.strip() and not line.strip().startswith('Summary')
        ]
        
        return bullets[:4]  # Limit to 4 bullets
        
    except Exception as e:
        logger.warning(f"OpenAI API error: {e}")
        return _fallback_summary(text)


def _fallback_summary(text: str) -> List[str]:
    """Generate fallback summary without external APIs."""
    if not text:
        return ["• No content available for summary"]
    
    # Split into sentences and take the most important ones
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    
    # Take first few sentences, wrapped to reasonable length
    summary_sentences = []
    for sentence in sentences[:3]:
        if len(sentence) > 150:
            # Wrap long sentences
            wrapped = textwrap.fill(sentence, width=120)
            summary_sentences.append("• " + wrapped.split('\n')[0] + '...')
        else:
            summary_sentences.append("• " + sentence)
    
    return summary_sentences if summary_sentences else ["• Content available but could not generate summary"]
