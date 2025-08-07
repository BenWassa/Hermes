"""Tests for the summarizer module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from hermes.summarizer import (
    summarize_articles,
    _summarize_text,
    _openai_summary,
    _fallback_summary,
    _can_use_openai
)
from hermes.fetcher import NewsArticle


class TestSummarizeArticles:
    """Test the main summarize_articles function."""
    
    def test_summarize_articles_basic(self, sample_articles):
        """Test basic article summarization."""
        with patch('hermes.summarizer._summarize_text') as mock_summarize:
            mock_summarize.return_value = ["• Key point 1", "• Key point 2"]
            
            summarized = summarize_articles(sample_articles.copy())
            
            assert len(summarized) == len(sample_articles)
            for article in summarized:
                assert article.bullets is not None
                assert len(article.bullets) == 2
    
    def test_summarize_articles_with_error(self, sample_articles):
        """Test summarization when an error occurs."""
        with patch('hermes.summarizer._summarize_text') as mock_summarize:
            mock_summarize.side_effect = Exception("Summarization failed")
            
            with patch('hermes.summarizer._fallback_summary') as mock_fallback:
                mock_fallback.return_value = ["• Fallback summary"]
                
                summarized = summarize_articles(sample_articles.copy())
                
                for article in summarized:
                    assert article.bullets == ["• Fallback summary"]
    
    def test_summarize_articles_empty_list(self):
        """Test summarization of empty article list."""
        summarized = summarize_articles([])
        assert summarized == []


class TestSummarizeText:
    """Test the _summarize_text function."""
    
    @patch('hermes.summarizer._can_use_openai')
    @patch('hermes.summarizer._openai_summary')
    def test_summarize_text_with_openai(self, mock_openai_summary, mock_can_use_openai):
        """Test text summarization using OpenAI."""
        mock_can_use_openai.return_value = True
        mock_openai_summary.return_value = ["• OpenAI point 1", "• OpenAI point 2"]
        
        result = _summarize_text("Test content for summarization")
        
        assert result == ["• OpenAI point 1", "• OpenAI point 2"]
        mock_openai_summary.assert_called_once_with("Test content for summarization")
    
    @patch('hermes.summarizer._can_use_openai')
    @patch('hermes.summarizer._fallback_summary')
    def test_summarize_text_without_openai(self, mock_fallback_summary, mock_can_use_openai):
        """Test text summarization using fallback method."""
        mock_can_use_openai.return_value = False
        mock_fallback_summary.return_value = ["• Fallback point 1", "• Fallback point 2"]
        
        result = _summarize_text("Test content for summarization")
        
        assert result == ["• Fallback point 1", "• Fallback point 2"]
        mock_fallback_summary.assert_called_once_with("Test content for summarization")


class TestOpenAISummary:
    """Test the _openai_summary function."""
    
    @patch('hermes.summarizer.openai')
    @patch('hermes.summarizer.HAS_OPENAI', True)
    def test_openai_summary_success(self, mock_openai, mock_openai_response):
        """Test successful OpenAI summarization."""
        mock_openai.chat.completions.create.return_value = mock_openai_response
        
        result = _openai_summary("Test article content about technology")
        
        expected = ["Key point 1", "Key point 2", "Key point 3"]
        assert result == expected
        
        # Verify OpenAI was called with correct parameters
        mock_openai.chat.completions.create.assert_called_once()
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4o-mini'
        assert 'messages' in call_args[1]
    
    @patch('hermes.summarizer.openai')
    @patch('hermes.summarizer.HAS_OPENAI', True)
    def test_openai_summary_failure(self, mock_openai):
        """Test OpenAI summarization failure."""
        mock_openai.chat.completions.create.side_effect = Exception("API Error")
        
        with patch('hermes.summarizer._fallback_summary') as mock_fallback:
            mock_fallback.return_value = ["• Fallback summary"]
            
            result = _openai_summary("Test content")
            
            assert result == ["• Fallback summary"]
            mock_fallback.assert_called_once_with("Test content")
    
    @patch('hermes.summarizer.HAS_OPENAI', False)
    def test_openai_summary_no_openai_available(self):
        """Test OpenAI summarization when OpenAI is not available."""
        with patch('hermes.summarizer._fallback_summary') as mock_fallback:
            mock_fallback.return_value = ["• Fallback summary"]
            
            result = _openai_summary("Test content")
            
            assert result == ["• Fallback summary"]


class TestFallbackSummary:
    """Test the _fallback_summary function."""
    
    def test_fallback_summary_basic(self):
        """Test basic fallback summarization."""
        content = "This is a test article. It contains multiple sentences. Each sentence provides important information. The article discusses technology and innovation."
        
        result = _fallback_summary(content)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(bullet.startswith("•") for bullet in result)
    
    def test_fallback_summary_short_content(self):
        """Test fallback summarization with short content."""
        content = "Short content."
        
        result = _fallback_summary(content)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0].startswith("•")
    
    def test_fallback_summary_empty_content(self):
        """Test fallback summarization with empty content."""
        result = _fallback_summary("")
        
        assert result == ["• No content available for summary"]
    
    def test_fallback_summary_long_content(self):
        """Test fallback summarization with long content."""
        content = " ".join([f"This is sentence {i} about important topic." for i in range(20)])
        
        result = _fallback_summary(content)
        
        assert isinstance(result, list)
        assert len(result) <= 5  # Should limit to reasonable number of bullets


class TestCanUseOpenAI:
    """Test the _can_use_openai function."""
    
    @patch('hermes.summarizer.HAS_OPENAI', True)
    @patch('hermes.summarizer.OPENAI_API_KEY', 'test-api-key')
    def test_can_use_openai_available(self):
        """Test when OpenAI is available and API key is set."""
        assert _can_use_openai() is True
    
    @patch('hermes.summarizer.HAS_OPENAI', False)
    def test_can_use_openai_not_installed(self):
        """Test when OpenAI library is not installed."""
        assert _can_use_openai() is False
    
    @patch('hermes.summarizer.HAS_OPENAI', True)
    @patch('hermes.summarizer.OPENAI_API_KEY', None)
    def test_can_use_openai_no_api_key(self):
        """Test when OpenAI is available but no API key is set."""
        assert _can_use_openai() is False
    
    @patch('hermes.summarizer.HAS_OPENAI', True)
    @patch('hermes.summarizer.OPENAI_API_KEY', '')
    def test_can_use_openai_empty_api_key(self):
        """Test when OpenAI is available but API key is empty."""
        assert _can_use_openai() is False


class TestIntegration:
    """Integration tests for summarizer module."""
    
    def test_end_to_end_summarization(self, sample_article):
        """Test end-to-end summarization process."""
        articles = [sample_article]
        
        # Test without OpenAI (fallback mode)
        with patch('hermes.summarizer._can_use_openai', return_value=False):
            summarized = summarize_articles(articles)
            
            assert len(summarized) == 1
            assert summarized[0].bullets is not None
            assert len(summarized[0].bullets) > 0
            assert all(bullet.startswith("•") for bullet in summarized[0].bullets)
    
    def test_summarization_with_missing_content(self):
        """Test summarization when article has no content."""
        article = NewsArticle(
            title="Test Article",
            summary="Test summary",
            link="https://example.com",
            content=""  # Empty content
        )
        
        summarized = summarize_articles([article])
        
        assert len(summarized) == 1
        assert summarized[0].bullets is not None
