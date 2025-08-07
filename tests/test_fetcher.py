"""Tests for the fetcher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from hermes.fetcher import (
    fetch_articles, 
    NewsArticle, 
    _parse_feed_entry, 
    _fetch_article_content,
    _get_sample_articles
)


class TestNewsArticle:
    """Test the NewsArticle dataclass."""
    
    def test_newsarticle_creation(self):
        """Test creating a NewsArticle instance."""
        article = NewsArticle(
            title="Test Title",
            summary="Test Summary", 
            link="https://example.com",
            content="Test Content"
        )
        
        assert article.title == "Test Title"
        assert article.summary == "Test Summary"
        assert article.link == "https://example.com"
        assert article.content == "Test Content"
        assert article.category is None
        assert article.bullets is None


class TestFetchArticles:
    """Test the main fetch_articles function."""
    
    @patch('hermes.fetcher.feedparser.parse')
    def test_fetch_articles_basic(self, mock_parse, mock_feed_data):
        """Test basic article fetching functionality."""
        mock_parse.return_value = mock_feed_data
        
        with patch('hermes.fetcher._fetch_article_content', return_value="Full content"):
            articles = fetch_articles(["https://example.com/feed"])
            
        assert len(articles) == 2
        assert articles[0].title == "Tech Innovation News"
        assert articles[1].title == "Global Politics Update"
        mock_parse.assert_called_once()
    
    @patch('hermes.fetcher.feedparser.parse')
    def test_fetch_articles_with_empty_sources(self, mock_parse):
        """Test handling of empty news sources."""
        mock_parse.return_value = {'entries': []}
        
        # Should fall back to sample articles
        articles = fetch_articles([])
        
        # Should get sample articles as fallback
        assert len(articles) > 0
        assert any("AI Breakthrough" in article.title for article in articles)
    
    @patch('hermes.fetcher.feedparser.parse')
    def test_fetch_articles_with_failed_feed(self, mock_parse):
        """Test handling of failed RSS feed parsing."""
        mock_parse.side_effect = Exception("Feed parsing failed")
        
        articles = fetch_articles(["https://bad-feed.com"])
        
        # Should fall back to sample articles
        assert len(articles) > 0
        assert any("AI Breakthrough" in article.title for article in articles)
    
    def test_fetch_articles_default_sources(self):
        """Test using default news sources."""
        with patch('hermes.fetcher.feedparser.parse') as mock_parse:
            mock_parse.return_value = {'entries': []}
            
            articles = fetch_articles()  # No sources provided
            
            # Should use default NEWS_SOURCES
            assert mock_parse.call_count >= 1


class TestParseFeedEntry:
    """Test the _parse_feed_entry function."""
    
    def test_parse_feed_entry_valid(self):
        """Test parsing a valid RSS feed entry."""
        entry = {
            'title': 'Test Article Title',
            'summary': 'Test article summary',
            'link': 'https://example.com/article'
        }
        
        with patch('hermes.fetcher._fetch_article_content', return_value="Full content"):
            article = _parse_feed_entry(entry)
        
        assert article is not None
        assert article.title == "Test Article Title"
        assert article.summary == "Test article summary"
        assert article.link == "https://example.com/article"
        assert article.content == "Full content"
    
    def test_parse_feed_entry_missing_title(self):
        """Test parsing entry with missing title."""
        entry = {
            'summary': 'Test summary',
            'link': 'https://example.com'
        }
        
        article = _parse_feed_entry(entry)
        assert article is None
    
    def test_parse_feed_entry_with_exception(self):
        """Test parsing entry that raises an exception."""
        entry = None  # Will cause an exception
        
        article = _parse_feed_entry(entry)
        assert article is None


class TestFetchArticleContent:
    """Test the _fetch_article_content function."""
    
    @patch('hermes.fetcher.Article')
    def test_fetch_article_content_success(self, mock_article_class):
        """Test successful article content fetching."""
        mock_article = Mock()
        mock_article.text = "Article full text content"
        mock_article_class.return_value = mock_article
        
        content = _fetch_article_content("https://example.com/article")
        
        assert content == "Article full text content"
        mock_article.download.assert_called_once()
        mock_article.parse.assert_called_once()
    
    @patch('hermes.fetcher.Article')
    def test_fetch_article_content_failure(self, mock_article_class):
        """Test failed article content fetching."""
        mock_article_class.side_effect = Exception("Download failed")
        
        content = _fetch_article_content("https://example.com/article")
        
        assert content is None
    
    def test_fetch_article_content_empty_url(self):
        """Test handling of empty URL."""
        content = _fetch_article_content("")
        assert content is None
        
        content = _fetch_article_content(None)
        assert content is None


class TestGetSampleArticles:
    """Test the _get_sample_articles function."""
    
    def test_get_sample_articles(self):
        """Test getting sample articles."""
        articles = _get_sample_articles()
        
        assert len(articles) == 3
        assert all(isinstance(article, NewsArticle) for article in articles)
        assert any("AI Breakthrough" in article.title for article in articles)
        assert any("Climate Summit" in article.title for article in articles)
        assert any("Economic Markets" in article.title for article in articles)
    
    def test_sample_articles_structure(self):
        """Test that sample articles have proper structure."""
        articles = _get_sample_articles()
        
        for article in articles:
            assert article.title
            assert article.summary
            assert article.link
            assert article.content
            assert len(article.content) > len(article.summary)
