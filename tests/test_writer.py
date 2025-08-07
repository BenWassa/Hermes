"""Tests for the writer module."""

import pytest
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from unittest.mock import patch, mock_open
from hermes.writer import (
    write_digest,
    _group_by_category,
    _write_markdown_digest,
    _write_html_digest,
    _write_json_digest
)
from hermes.fetcher import NewsArticle


class TestWriteDigest:
    """Test the main write_digest function."""
    
    def test_write_digest_markdown(self, sample_articles, temp_output_dir):
        """Test writing digest in markdown format."""
        # Categorize articles first
        sample_articles[0].category = "⚙️ Tech & AI"
        sample_articles[1].category = "🧬 Science & Health"
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = write_digest(sample_articles, "markdown")
            
        assert output_path.exists()
        assert output_path.suffix == ".md"
        
        content = output_path.read_text(encoding='utf-8')
        assert "# 🗞️ Hermes Daily Digest" in content
        assert "⚙️ Tech & AI" in content
        assert "🧬 Science & Health" in content
    
    def test_write_digest_html(self, sample_articles, temp_output_dir):
        """Test writing digest in HTML format."""
        sample_articles[0].category = "⚙️ Tech & AI"
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = write_digest(sample_articles, "html")
            
        assert output_path.exists()
        assert output_path.suffix == ".html"
        
        content = output_path.read_text(encoding='utf-8')
        assert "<html>" in content
        assert "<title>" in content
        assert "⚙️ Tech & AI" in content
    
    def test_write_digest_json(self, sample_articles, temp_output_dir):
        """Test writing digest in JSON format."""
        sample_articles[0].category = "⚙️ Tech & AI"
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = write_digest(sample_articles, "json")
            
        assert output_path.exists()
        assert output_path.suffix == ".json"
        
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        assert "digest_date" in data
        assert "categories" in data
        assert "⚙️ Tech & AI" in data["categories"]
    
    def test_write_digest_invalid_format(self, sample_articles):
        """Test writing digest with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            write_digest(sample_articles, "invalid_format")
    
    def test_write_digest_empty_articles(self, temp_output_dir):
        """Test writing digest with empty article list."""
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = write_digest([], "markdown")
            
        assert output_path.exists()
        content = output_path.read_text(encoding='utf-8')
        assert "No articles" in content or len(content.strip()) == 0


class TestGroupByCategory:
    """Test the _group_by_category function."""
    
    def test_group_by_category_basic(self, sample_articles):
        """Test basic article grouping by category."""
        # Assign categories
        sample_articles[0].category = "⚙️ Tech & AI"
        sample_articles[1].category = "🧬 Science & Health"
        sample_articles[2].category = "⚙️ Tech & AI"  # Same as first
        sample_articles[3].category = "📊 Economy & Policy"
        
        grouped = _group_by_category(sample_articles)
        
        assert len(grouped) == 3
        assert len(grouped["⚙️ Tech & AI"]) == 2
        assert len(grouped["🧬 Science & Health"]) == 1
        assert len(grouped["📊 Economy & Policy"]) == 1
    
    def test_group_by_category_no_category(self):
        """Test grouping articles without assigned categories."""
        articles = [
            NewsArticle(
                title="Test Article 1",
                summary="Summary 1",
                link="https://example.com/1",
                content="Content 1"
            ),
            NewsArticle(
                title="Test Article 2", 
                summary="Summary 2",
                link="https://example.com/2",
                content="Content 2"
            )
        ]
        
        grouped = _group_by_category(articles)
        
        assert len(grouped) == 1
        assert "📰 Other" in grouped
        assert len(grouped["📰 Other"]) == 2
    
    def test_group_by_category_mixed(self):
        """Test grouping mix of categorized and uncategorized articles."""
        articles = [
            NewsArticle(
                title="Tech Article",
                summary="Tech summary",
                link="https://example.com/tech",
                content="Tech content",
                category="⚙️ Tech & AI"
            ),
            NewsArticle(
                title="Uncategorized Article",
                summary="No category",
                link="https://example.com/none",
                content="No category content"
            )
        ]
        
        grouped = _group_by_category(articles)
        
        assert len(grouped) == 2
        assert "⚙️ Tech & AI" in grouped
        assert "📰 Other" in grouped


class TestWriteMarkdownDigest:
    """Test the _write_markdown_digest function."""
    
    def test_write_markdown_digest_basic(self, temp_output_dir):
        """Test writing basic markdown digest."""
        categorized = {
            "⚙️ Tech & AI": [
                NewsArticle(
                    title="AI Breakthrough",
                    summary="AI summary",
                    link="https://example.com/ai",
                    content="AI content",
                    bullets=["• Key point 1", "• Key point 2"]
                )
            ]
        }
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = _write_markdown_digest(categorized, "2025-08-07")
            
        assert output_path.exists()
        content = output_path.read_text(encoding='utf-8')
        
        assert "# 🗞️ Hermes Daily Digest — 2025-08-07" in content
        assert "## ⚙️ Tech & AI" in content
        assert "### AI Breakthrough" in content
        assert "• Key point 1" in content
        assert "[Read more →](https://example.com/ai)" in content
    
    def test_write_markdown_digest_no_bullets(self, temp_output_dir):
        """Test writing markdown digest for articles without bullets."""
        categorized = {
            "⚙️ Tech & AI": [
                NewsArticle(
                    title="Tech News",
                    summary="Tech summary",
                    link="https://example.com/tech",
                    content="Tech content"
                    # No bullets
                )
            ]
        }
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = _write_markdown_digest(categorized, "2025-08-07")
            
        content = output_path.read_text(encoding='utf-8')
        assert "Tech summary" in content  # Should fall back to summary


class TestWriteHtmlDigest:
    """Test the _write_html_digest function."""
    
    def test_write_html_digest_basic(self, temp_output_dir):
        """Test writing basic HTML digest."""
        categorized = {
            "⚙️ Tech & AI": [
                NewsArticle(
                    title="AI News",
                    summary="AI summary", 
                    link="https://example.com/ai",
                    content="AI content",
                    bullets=["• Tech point 1", "• Tech point 2"]
                )
            ]
        }
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = _write_html_digest(categorized, "2025-08-07")
            
        assert output_path.exists()
        content = output_path.read_text(encoding='utf-8')
        
        assert "<!DOCTYPE html>" in content
        assert "<title>Hermes Daily Digest — 2025-08-07</title>" in content
        assert "<h2>⚙️ Tech & AI</h2>" in content
        assert "<h3>AI News</h3>" in content
        assert "<li>Tech point 1</li>" in content
    
    def test_write_html_digest_structure(self, temp_output_dir):
        """Test HTML digest has proper structure."""
        categorized = {
            "⚙️ Tech & AI": [
                NewsArticle(
                    title="Test Article",
                    summary="Test summary",
                    link="https://example.com/test",
                    content="Test content"
                )
            ]
        }
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = _write_html_digest(categorized, "2025-08-07")
            
        content = output_path.read_text(encoding='utf-8')
        
        # Check HTML structure
        assert content.count("<html>") == 1
        assert content.count("</html>") == 1
        assert content.count("<head>") == 1
        assert content.count("</head>") == 1
        assert content.count("<body>") == 1
        assert content.count("</body>") == 1


class TestWriteJsonDigest:
    """Test the _write_json_digest function."""
    
    def test_write_json_digest_basic(self, temp_output_dir):
        """Test writing basic JSON digest."""
        categorized = {
            "⚙️ Tech & AI": [
                NewsArticle(
                    title="Tech Article",
                    summary="Tech summary",
                    link="https://example.com/tech",
                    content="Tech content",
                    bullets=["• Point 1", "• Point 2"]
                )
            ]
        }
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = _write_json_digest(categorized, "2025-08-07")
            
        assert output_path.exists()
        
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["digest_date"] == "2025-08-07"
        assert "categories" in data
        assert "⚙️ Tech & AI" in data["categories"]
        assert len(data["categories"]["⚙️ Tech & AI"]) == 1
        
        article_data = data["categories"]["⚙️ Tech & AI"][0]
        assert article_data["title"] == "Tech Article"
        assert article_data["summary"] == "Tech summary"
        assert article_data["link"] == "https://example.com/tech"
        assert article_data["bullets"] == ["• Point 1", "• Point 2"]
    
    def test_write_json_digest_valid_json(self, temp_output_dir):
        """Test that written JSON is valid and parseable."""
        categorized = {
            "📊 Economy & Policy": [
                NewsArticle(
                    title="Economic News",
                    summary="Economic summary",
                    link="https://example.com/econ",
                    content="Economic content"
                )
            ]
        }
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            output_path = _write_json_digest(categorized, "2025-08-07")
        
        # Should be able to parse without errors
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        assert isinstance(data, dict)
        assert "digest_date" in data
        assert "categories" in data


class TestFileHandling:
    """Test file handling and error scenarios."""
    
    def test_digest_directory_creation(self, temp_output_dir):
        """Test that digest directory is created if it doesn't exist."""
        non_existent_dir = temp_output_dir / "new_digest_dir"
        
        categorized = {
            "⚙️ Tech & AI": [
                NewsArticle(
                    title="Test",
                    summary="Test",
                    link="https://example.com",
                    content="Test"
                )
            ]
        }
        
        with patch('hermes.writer.DIGEST_DIR', non_existent_dir):
            output_path = _write_markdown_digest(categorized, "2025-08-07")
            
        assert non_existent_dir.exists()
        assert output_path.exists()
    
    def test_filename_generation(self, temp_output_dir):
        """Test that filenames are generated correctly."""
        categorized = {}
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            md_path = _write_markdown_digest(categorized, "2025-08-07")
            html_path = _write_html_digest(categorized, "2025-08-07")
            json_path = _write_json_digest(categorized, "2025-08-07")
        
        assert md_path.name == "2025-08-07.md"
        assert html_path.name == "2025-08-07.html"
        assert json_path.name == "2025-08-07.json"


class TestIntegration:
    """Integration tests for writer module."""
    
    def test_full_write_workflow(self, sample_articles, temp_output_dir):
        """Test complete workflow from articles to file."""
        # Set up articles with categories and bullets
        sample_articles[0].category = "⚙️ Tech & AI"
        sample_articles[0].bullets = ["• AI advancement", "• Technology impact"]
        
        sample_articles[1].category = "🧬 Science & Health"
        sample_articles[1].bullets = ["• Climate research", "• Environmental policy"]
        
        with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
            # Test all formats
            md_path = write_digest(sample_articles, "markdown")
            html_path = write_digest(sample_articles, "html")
            json_path = write_digest(sample_articles, "json")
        
        # All files should exist
        assert md_path.exists()
        assert html_path.exists()
        assert json_path.exists()
        
        # All should contain expected content
        md_content = md_path.read_text(encoding='utf-8')
        html_content = html_path.read_text(encoding='utf-8')
        
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Check cross-format consistency
        assert "Tech & AI" in md_content
        assert "Tech & AI" in html_content
        assert "⚙️ Tech & AI" in json_data["categories"]
