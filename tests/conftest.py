"""Test configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_article():
    """Sample article for testing."""
    return {
        "title": "Test Article",
        "summary": "A test article summary.",
        "url": "https://example.com/article",
        "source": "Test Source",
        "published": "2025-08-07T09:00:00Z"
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test outputs."""
    return tmp_path / "test_output"
