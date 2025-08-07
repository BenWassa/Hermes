"""Tests for the filter module."""

import pytest
from hermes.filter import (
    filter_articles, 
    categorize_articles
)
from hermes.fetcher import NewsArticle

# Import private functions for testing
from hermes.filter import _should_exclude_article, _determine_category


class TestFilterArticles:
    """Test the filter_articles function."""
    
    def test_filter_articles_basic(self, sample_articles):
        """Test basic article filtering."""
        filtered = filter_articles(sample_articles)
        
        # Should filter out the celebrity gossip article
        assert len(filtered) == 3  # One article should be filtered out
        
        # Check that gossip article was removed
        titles = [article.title for article in filtered]
        assert "Celebrity Gossip Drama" not in titles
    
    def test_filter_articles_no_exclusions(self):
        """Test filtering when no articles should be excluded."""
        articles = [
            NewsArticle(
                title="Clean Technology News",
                summary="Innovation in clean tech",
                link="https://example.com/clean-tech",
                content="Clean technology innovations are transforming energy sector."
            ),
            NewsArticle(
                title="Economic Policy Analysis", 
                summary="Government economic policies",
                link="https://example.com/policy",
                content="New economic policies focus on sustainable growth and innovation."
            )
        ]
        
        filtered = filter_articles(articles)
        assert len(filtered) == 2  # No articles should be filtered
    
    def test_filter_articles_all_excluded(self):
        """Test filtering when all articles should be excluded."""
        articles = [
            NewsArticle(
                title="Celebrity Shooting Incident",
                summary="Celebrity involved in shooting",
                link="https://example.com/shooting",
                content="A celebrity was involved in a shooting incident."
            ),
            NewsArticle(
                title="Viral TikTok Crime Story",
                summary="Crime goes viral on social media",
                link="https://example.com/viral-crime",
                content="A crime story went viral on TikTok and Instagram."
            )
        ]
        
        filtered = filter_articles(articles)
        assert len(filtered) == 0  # All articles should be filtered out


class TestCategorizeArticles:
    """Test the categorize_articles function."""
    
    def test_categorize_articles(self, sample_articles):
        """Test article categorization."""
        categorized = categorize_articles(sample_articles.copy())
        
        # Check that categories were assigned
        categories = [article.category for article in categorized]
        assert "⚙️ Tech & AI" in categories  # AI article
        assert "🧬 Science & Health" in categories  # Climate article  
        assert "📊 Economy & Policy" in categories  # Economic article
    
    def test_categorize_tech_article(self):
        """Test categorization of technology articles."""
        article = NewsArticle(
            title="AI Innovation Breakthrough",
            summary="Artificial intelligence advances",
            link="https://example.com/ai",
            content="New artificial intelligence technology breakthrough in computing."
        )
        
        categorized = categorize_articles([article])
        assert categorized[0].category == "⚙️ Tech & AI"
    
    def test_categorize_science_article(self):
        """Test categorization of science articles."""
        article = NewsArticle(
            title="Climate Research Discovery",
            summary="New climate science research",
            link="https://example.com/climate",
            content="Scientists discover new climate patterns through environmental research."
        )
        
        categorized = categorize_articles([article])
        assert categorized[0].category == "🧬 Science & Health"
    
    def test_categorize_uncategorized_article(self):
        """Test categorization of articles that don't match any category."""
        article = NewsArticle(
            title="Random News Item",
            summary="Something unrelated",
            link="https://example.com/random",
            content="This content doesn't match any specific category keywords."
        )
        
        categorized = categorize_articles([article])
        assert categorized[0].category == "📚 Culture & Ideas"  # Default category


class TestShouldExcludeArticle:
    """Test the _should_exclude_article function."""
    
    def test_should_exclude_article_with_keywords(self):
        """Test exclusion of articles with excluded keywords."""
        article = NewsArticle(
            title="Celebrity Shooting Drama",
            summary="Celebrity involved in shooting",
            link="https://example.com/shooting",
            content="A celebrity was involved in a shooting incident."
        )
        
        assert _should_exclude_article(article) is True
    
    def test_should_exclude_article_clean_content(self):
        """Test that clean articles are not excluded."""
        article = NewsArticle(
            title="Technology Innovation",
            summary="New tech breakthrough",
            link="https://example.com/tech",
            content="Scientists develop new technology for sustainable energy."
        )
        
        assert _should_exclude_article(article) is False
    
    def test_should_exclude_article_social_media_keywords(self):
        """Test exclusion of social media-related articles."""
        article = NewsArticle(
            title="Viral Instagram Post",
            summary="Post goes viral on social media",
            link="https://example.com/viral",
            content="A post went viral on Instagram and Twitter platforms."
        )
        
        assert _should_exclude_article(article) is True


class TestDetermineCategory:
    """Test the _determine_category function."""
    
    def test_determine_category_politics(self):
        """Test categorization of political articles."""
        article = NewsArticle(
            title="Election Results",
            summary="Government election update",
            link="https://example.com/election",
            content="International election results show political shifts in government."
        )
        
        category = _determine_category(article)
        assert category == "🌍 Global Affairs"
    
    def test_determine_category_technology(self):
        """Test categorization of technology articles."""
        article = NewsArticle(
            title="AI Breakthrough",
            summary="Artificial intelligence advance",
            link="https://example.com/ai",
            content="New artificial intelligence technology shows promise in computing."
        )
        
        category = _determine_category(article)
        assert category == "⚙️ Tech & AI"
    
    def test_determine_category_multiple_matches(self):
        """Test categorization when multiple categories match."""
        article = NewsArticle(
            title="AI in Healthcare Research",
            summary="Technology meets science",
            link="https://example.com/ai-health",
            content="Artificial intelligence technology advances medical research and health outcomes."
        )
        
        category = _determine_category(article)
        # Should return the first matching category
        assert category in ["⚙️ Tech & AI", "🧬 Science & Health"]
    
    def test_determine_category_no_match(self):
        """Test default categorization when no keywords match."""
        article = NewsArticle(
            title="General News Item",
            summary="Miscellaneous content",
            link="https://example.com/misc",
            content="This is general content that doesn't match specific categories."
        )
        
        category = _determine_category(article)
        assert category == "📚 Culture & Ideas"
