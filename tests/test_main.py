"""Tests for the main pipeline module."""

import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from hermes.main import (
    setup_logging,
    run_pipeline
)
from hermes.fetcher import NewsArticle


class TestSetupLogging:
    """Test the setup_logging function."""
    
    @patch('hermes.main.logging.basicConfig')
    def test_setup_logging_basic(self, mock_basic_config, temp_output_dir):
        """Test basic logging setup."""
        with patch('hermes.main.LOGS_DIR', temp_output_dir):
            setup_logging()
            
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        
        assert call_args['level'] == logging.INFO
        assert 'format' in call_args
        assert 'handlers' in call_args
        assert len(call_args['handlers']) == 2  # File and console handlers
    
    def test_setup_logging_creates_log_dir(self, temp_output_dir):
        """Test that logging setup creates log directory."""
        log_dir = temp_output_dir / "logs"
        
        with patch('hermes.main.LOGS_DIR', log_dir):
            setup_logging()
            
        # Directory should be created by the logging setup
        assert log_dir.exists()


class TestRunPipeline:
    """Test the main run_pipeline function."""
    
    @patch('hermes.main.write_digest')
    @patch('hermes.main.summarize_articles')
    @patch('hermes.main.categorize_articles')
    @patch('hermes.main.filter_articles')
    @patch('hermes.main.fetch_articles')
    def test_run_pipeline_success(self, mock_fetch, mock_filter, mock_categorize, 
                                 mock_summarize, mock_write, sample_articles):
        """Test successful pipeline execution."""
        # Setup mocks
        mock_fetch.return_value = sample_articles
        mock_filter.return_value = sample_articles[:2]  # Filter some out
        mock_categorize.return_value = sample_articles[:2]
        mock_summarize.return_value = sample_articles[:2]
        mock_write.return_value = Path("/fake/path/digest.md")
        
        result_path = run_pipeline("markdown")
        
        # Verify all steps were called
        mock_fetch.assert_called_once()
        mock_filter.assert_called_once_with(sample_articles)
        mock_categorize.assert_called_once_with(sample_articles[:2])
        mock_summarize.assert_called_once_with(sample_articles[:2])
        mock_write.assert_called_once_with(sample_articles[:2], "markdown")
        
        assert result_path == Path("/fake/path/digest.md")
    
    @patch('hermes.main.fetch_articles')
    def test_run_pipeline_no_articles(self, mock_fetch):
        """Test pipeline when no articles are fetched."""
        mock_fetch.return_value = []
        
        result = run_pipeline("markdown")
        
        assert result is None
        mock_fetch.assert_called_once()
    
    @patch('hermes.main.write_digest')
    @patch('hermes.main.summarize_articles')
    @patch('hermes.main.categorize_articles')
    @patch('hermes.main.filter_articles')
    @patch('hermes.main.fetch_articles')
    def test_run_pipeline_different_formats(self, mock_fetch, mock_filter, 
                                          mock_categorize, mock_summarize, mock_write):
        """Test pipeline with different output formats."""
        sample_article = NewsArticle(
            title="Test",
            summary="Test",
            link="https://example.com",
            content="Test content"
        )
        
        mock_fetch.return_value = [sample_article]
        mock_filter.return_value = [sample_article]
        mock_categorize.return_value = [sample_article]
        mock_summarize.return_value = [sample_article]
        mock_write.return_value = Path("/fake/path/digest.html")
        
        # Test HTML format
        result = run_pipeline("html")
        
        mock_write.assert_called_with([sample_article], "html")
        assert result == Path("/fake/path/digest.html")
    
    @patch('hermes.main.fetch_articles')
    def test_run_pipeline_fetch_exception(self, mock_fetch):
        """Test pipeline when fetching raises an exception."""
        mock_fetch.side_effect = Exception("Fetch failed")
        
        with pytest.raises(Exception, match="Fetch failed"):
            run_pipeline("markdown")
    
    @patch('hermes.main.write_digest')
    @patch('hermes.main.summarize_articles')
    @patch('hermes.main.categorize_articles')
    @patch('hermes.main.filter_articles')
    @patch('hermes.main.fetch_articles')
    def test_run_pipeline_filter_all_articles(self, mock_fetch, mock_filter, 
                                            mock_categorize, mock_summarize, mock_write,
                                            sample_articles):
        """Test pipeline when filter removes all articles."""
        mock_fetch.return_value = sample_articles
        mock_filter.return_value = []  # All articles filtered out
        
        result = run_pipeline("markdown")
        
        assert result is None
        mock_fetch.assert_called_once()
        mock_filter.assert_called_once()
        # Subsequent steps should not be called
        mock_categorize.assert_not_called()
        mock_summarize.assert_not_called()
        mock_write.assert_not_called()


class TestMainIntegration:
    """Integration tests for the main module."""
    
    @patch('hermes.main.write_digest')
    @patch('hermes.main.openai')  # Mock OpenAI to avoid API calls
    def test_pipeline_integration_without_openai(self, mock_openai, mock_write, temp_output_dir):
        """Test pipeline integration using fallback summarization."""
        mock_write.return_value = temp_output_dir / "test-digest.md"
        
        # Mock OpenAI as unavailable
        with patch('hermes.summarizer.HAS_OPENAI', False):
            with patch('hermes.main.fetch_articles') as mock_fetch:
                # Provide sample articles
                sample_articles = [
                    NewsArticle(
                        title="Tech Innovation",
                        summary="New technology breakthrough",
                        link="https://example.com/tech",
                        content="Technology content about innovation and artificial intelligence"
                    ),
                    NewsArticle(
                        title="Climate Science",
                        summary="Climate research findings",
                        link="https://example.com/climate",
                        content="Climate science research shows environmental changes"
                    )
                ]
                mock_fetch.return_value = sample_articles
                
                result = run_pipeline("markdown")
                
                assert result == temp_output_dir / "test-digest.md"
    
    def test_pipeline_logging(self, caplog):
        """Test that pipeline generates appropriate log messages."""
        with patch('hermes.main.fetch_articles') as mock_fetch:
            mock_fetch.return_value = []
            
            with caplog.at_level(logging.INFO):
                run_pipeline("markdown")
            
            # Check for expected log messages
            log_messages = [record.message for record in caplog.records]
            assert any("Starting Hermes news digest pipeline" in msg for msg in log_messages)
            assert any("No articles fetched" in msg for msg in log_messages)


class TestErrorHandling:
    """Test error handling in the main module."""
    
    @patch('hermes.main.write_digest')
    @patch('hermes.main.summarize_articles')
    @patch('hermes.main.categorize_articles')
    @patch('hermes.main.filter_articles')
    @patch('hermes.main.fetch_articles')
    def test_pipeline_handles_summarization_errors(self, mock_fetch, mock_filter, 
                                                  mock_categorize, mock_summarize, mock_write):
        """Test pipeline handles summarization errors gracefully."""
        sample_article = NewsArticle(
            title="Test",
            summary="Test", 
            link="https://example.com",
            content="Test"
        )
        
        mock_fetch.return_value = [sample_article]
        mock_filter.return_value = [sample_article]
        mock_categorize.return_value = [sample_article]
        mock_summarize.side_effect = Exception("Summarization failed")
        
        # Pipeline should still attempt to continue and write
        with pytest.raises(Exception, match="Summarization failed"):
            run_pipeline("markdown")
    
    @patch('hermes.main.summarize_articles')
    @patch('hermes.main.categorize_articles')
    @patch('hermes.main.filter_articles')
    @patch('hermes.main.fetch_articles')
    def test_pipeline_handles_write_errors(self, mock_fetch, mock_filter, 
                                         mock_categorize, mock_summarize):
        """Test pipeline handles write errors."""
        sample_article = NewsArticle(
            title="Test",
            summary="Test",
            link="https://example.com", 
            content="Test"
        )
        
        mock_fetch.return_value = [sample_article]
        mock_filter.return_value = [sample_article]
        mock_categorize.return_value = [sample_article]
        mock_summarize.return_value = [sample_article]
        
        with patch('hermes.main.write_digest') as mock_write:
            mock_write.side_effect = Exception("Write failed")
            
            with pytest.raises(Exception, match="Write failed"):
                run_pipeline("markdown")


class TestConfigurationIntegration:
    """Test integration with configuration settings."""
    
    @patch('hermes.main.write_digest')
    @patch('hermes.main.fetch_articles')
    def test_pipeline_respects_max_articles_config(self, mock_fetch, mock_write, temp_output_dir):
        """Test that pipeline respects MAX_TOTAL_ARTICLES configuration."""
        # Create more articles than the limit
        many_articles = [
            NewsArticle(
                title=f"Article {i}",
                summary=f"Summary {i}",
                link=f"https://example.com/{i}",
                content=f"Content {i}"
            ) for i in range(20)  # More than typical limit
        ]
        
        mock_fetch.return_value = many_articles
        mock_write.return_value = temp_output_dir / "digest.md"
        
        with patch('hermes.main.MAX_TOTAL_ARTICLES', 10):
            result = run_pipeline("markdown")
            
            # Check that write_digest was called with limited articles
            call_args = mock_write.call_args[0][0]  # First argument (articles)
            assert len(call_args) <= 10
