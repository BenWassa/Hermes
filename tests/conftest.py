"""Test configuration and fixtures."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from hermes.fetcher import NewsArticle


@pytest.fixture
def sample_article():
    """Sample NewsArticle for testing."""
    return NewsArticle(
        title="Test Article About AI Technology",
        summary="A test article summary about artificial intelligence.",
        link="https://example.com/article",
        content="This is a longer content about artificial intelligence and technology innovations. The article discusses breakthrough research in machine learning."
    )


@pytest.fixture
def sample_articles():
    """List of sample NewsArticle objects for testing."""
    return [
        NewsArticle(
            title="AI Breakthrough in Healthcare",
            summary="AI shows promise in medical diagnostics",
            link="https://example.com/ai-health",
            content="Artificial intelligence technology has shown remarkable progress in healthcare diagnostics and treatment planning."
        ),
        NewsArticle(
            title="Climate Change Policy Updates",
            summary="New environmental regulations announced",
            link="https://example.com/climate-policy", 
            content="Government announces new climate change policies including carbon emission targets and environmental regulations."
        ),
        NewsArticle(
            title="Celebrity Gossip Drama",
            summary="Social media buzz about celebrity",
            link="https://example.com/gossip",
            content="Latest celebrity drama on social media platforms including Instagram and Twitter reactions."
        ),
        NewsArticle(
            title="Economic Market Analysis",
            summary="Stock market trends and predictions",
            link="https://example.com/economy",
            content="Financial markets show mixed signals as investors analyze economic policy changes and market trends."
        )
    ]


@pytest.fixture
def mock_feed_data():
    """Mock RSS feed data for testing."""
    return {
        'entries': [
            {
                'title': 'Tech Innovation News',
                'summary': 'Latest in technology innovation',
                'link': 'https://example.com/tech'
            },
            {
                'title': 'Global Politics Update',
                'summary': 'International diplomatic developments',
                'link': 'https://example.com/politics'
            }
        ]
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test outputs."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing."""
    return Mock(
        choices=[
            Mock(
                message=Mock(
                    content="• Key point 1\n• Key point 2\n• Key point 3"
                )
            )
        ]
    )
