"""Tests for the config module."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch
from hermes.config import (
    PROJECT_ROOT,
    NEWS_SOURCES,
    EXCLUDE_KEYWORDS,
    CATEGORY_KEYWORDS,
    OPENAI_MODEL,
    OPENAI_API_KEY
)


class TestProjectConfiguration:
    """Test basic project configuration."""
    
    def test_project_root_exists(self):
        """Test that PROJECT_ROOT points to a valid directory."""
        assert isinstance(PROJECT_ROOT, Path)
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()
    
    def test_project_root_structure(self):
        """Test that PROJECT_ROOT contains expected files."""
        # Should contain the hermes package
        hermes_package = PROJECT_ROOT / "hermes"
        assert hermes_package.exists()
        assert hermes_package.is_dir()
        
        # Should contain pyproject.toml
        pyproject = PROJECT_ROOT / "pyproject.toml"
        assert pyproject.exists()


class TestNewsSourcesConfiguration:
    """Test news sources configuration."""
    
    def test_news_sources_is_list(self):
        """Test that NEWS_SOURCES is a list."""
        assert isinstance(NEWS_SOURCES, list)
        assert len(NEWS_SOURCES) > 0
    
    def test_news_sources_are_urls(self):
        """Test that all news sources are valid URLs."""
        for source in NEWS_SOURCES:
            assert isinstance(source, str)
            assert source.startswith(('http://', 'https://'))
            assert len(source) > 10  # Reasonable URL length
    
    def test_news_sources_include_major_outlets(self):
        """Test that major news outlets are included."""
        sources_text = " ".join(NEWS_SOURCES).lower()
        
        # Should include some major outlets
        expected_outlets = ['reuters', 'bbc', 'ap']
        found_outlets = [outlet for outlet in expected_outlets if outlet in sources_text]
        
        assert len(found_outlets) > 0, "Should include at least one major news outlet"


class TestFilterConfiguration:
    """Test filtering configuration."""
    
    def test_exclude_keywords_is_list(self):
        """Test that EXCLUDE_KEYWORDS is a list."""
        assert isinstance(EXCLUDE_KEYWORDS, list)
        assert len(EXCLUDE_KEYWORDS) > 0
    
    def test_exclude_keywords_are_strings(self):
        """Test that all exclude keywords are strings."""
        for keyword in EXCLUDE_KEYWORDS:
            assert isinstance(keyword, str)
            assert len(keyword) > 0
    
    def test_exclude_keywords_include_noise_terms(self):
        """Test that exclude keywords include expected noise terms."""
        keywords_lower = [kw.lower() for kw in EXCLUDE_KEYWORDS]
        
        expected_noise = ['celebrity', 'gossip', 'crime', 'viral']
        found_noise = [term for term in expected_noise if term in keywords_lower]
        
        assert len(found_noise) > 0, "Should exclude some noise terms"
    
    def test_exclude_keywords_no_duplicates(self):
        """Test that exclude keywords don't have duplicates."""
        lowercase_keywords = [kw.lower() for kw in EXCLUDE_KEYWORDS]
        assert len(lowercase_keywords) == len(set(lowercase_keywords))


class TestCategoryConfiguration:
    """Test category configuration."""
    
    def test_category_keywords_is_dict(self):
        """Test that CATEGORY_KEYWORDS is a dictionary."""
        assert isinstance(CATEGORY_KEYWORDS, dict)
        assert len(CATEGORY_KEYWORDS) > 0
    
    def test_category_keywords_structure(self):
        """Test the structure of CATEGORY_KEYWORDS."""
        for category, keywords in CATEGORY_KEYWORDS.items():
            assert isinstance(category, str)
            assert len(category) > 0
            assert isinstance(keywords, list)
            assert len(keywords) > 0
            
            for keyword in keywords:
                assert isinstance(keyword, str)
                assert len(keyword) > 0
    
    def test_expected_categories_exist(self):
        """Test that expected categories are defined."""
        expected_categories = [
            "Global Affairs", "Tech & AI", "Science & Health", 
            "Economy & Policy", "Culture & Ideas"
        ]
        
        category_text = " ".join(CATEGORY_KEYWORDS.keys()).lower()
        
        for expected in expected_categories:
            assert any(word in category_text for word in expected.lower().split()), \
                f"Category containing '{expected}' should exist"
    
    def test_category_keywords_comprehensive(self):
        """Test that categories have comprehensive keyword coverage."""
        # Each category should have reasonable number of keywords
        for category, keywords in CATEGORY_KEYWORDS.items():
            assert len(keywords) >= 3, f"Category '{category}' should have at least 3 keywords"
    
    def test_category_keywords_no_overlap(self):
        """Test that category keywords don't significantly overlap."""
        all_keywords = []
        for keywords in CATEGORY_KEYWORDS.values():
            all_keywords.extend([kw.lower() for kw in keywords])
        
        # Some overlap is expected, but not too much
        unique_keywords = set(all_keywords)
        overlap_ratio = (len(all_keywords) - len(unique_keywords)) / len(all_keywords)
        
        assert overlap_ratio < 0.3, "Category keywords should not overlap too much"


class TestOpenAIConfiguration:
    """Test OpenAI configuration."""
    
    def test_openai_model_is_string(self):
        """Test that OPENAI_MODEL is a string."""
        assert isinstance(OPENAI_MODEL, str)
        assert len(OPENAI_MODEL) > 0
    
    def test_openai_model_is_valid(self):
        """Test that OPENAI_MODEL is a reasonable model name."""
        # Should be a GPT model
        assert "gpt" in OPENAI_MODEL.lower()
        assert len(OPENAI_MODEL) > 5
    
    def test_openai_api_key_from_environment(self):
        """Test that OPENAI_API_KEY is read from environment."""
        # Test with environment variable set
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'}):
            from hermes import config
            # Reload the config module to get new environment value
            import importlib
            importlib.reload(config)
            
            assert config.OPENAI_API_KEY == 'test-api-key'
    
    def test_openai_api_key_can_be_none(self):
        """Test that OPENAI_API_KEY can be None when not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY from environment
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            
            from hermes import config
            import importlib
            importlib.reload(config)
            
            # Should be None when not set
            assert config.OPENAI_API_KEY is None


class TestDirectoryConfiguration:
    """Test directory configuration."""
    
    def test_output_directories_configuration(self):
        """Test that output directories are properly configured."""
        # These should be defined in config
        from hermes.config import DIGEST_DIR, LOGS_DIR
        
        assert isinstance(DIGEST_DIR, Path)
        assert isinstance(LOGS_DIR, Path)
        
        # Should be relative to project structure
        assert DIGEST_DIR.is_absolute()
        assert LOGS_DIR.is_absolute()


class TestConfigurationConsistency:
    """Test configuration consistency and relationships."""
    
    def test_exclude_and_category_keywords_consistency(self):
        """Test that exclude keywords don't conflict with category keywords."""
        exclude_lower = [kw.lower() for kw in EXCLUDE_KEYWORDS]
        
        all_category_keywords = []
        for keywords in CATEGORY_KEYWORDS.values():
            all_category_keywords.extend([kw.lower() for kw in keywords])
        
        # Should not have significant overlap
        conflicts = set(exclude_lower) & set(all_category_keywords)
        
        # Some minor conflicts might be acceptable, but not many
        assert len(conflicts) < 3, f"Too many conflicts between exclude and category keywords: {conflicts}"
    
    def test_configuration_types_are_immutable(self):
        """Test that configuration objects are appropriate types."""
        # Lists and dicts should be mutable for practical use
        assert isinstance(NEWS_SOURCES, list)
        assert isinstance(EXCLUDE_KEYWORDS, list)
        assert isinstance(CATEGORY_KEYWORDS, dict)
        
        # Strings should be immutable
        assert isinstance(OPENAI_MODEL, str)
    
    def test_configuration_completeness(self):
        """Test that all required configuration is present."""
        required_configs = [
            'PROJECT_ROOT', 'NEWS_SOURCES', 'EXCLUDE_KEYWORDS',
            'CATEGORY_KEYWORDS', 'OPENAI_MODEL'
        ]
        
        import hermes.config as config
        
        for required in required_configs:
            assert hasattr(config, required), f"Missing required configuration: {required}"
            assert getattr(config, required) is not None, f"Configuration {required} should not be None"


class TestConfigurationValues:
    """Test specific configuration values."""
    
    def test_reasonable_source_count(self):
        """Test that we have a reasonable number of news sources."""
        assert 2 <= len(NEWS_SOURCES) <= 20, "Should have reasonable number of news sources"
    
    def test_reasonable_exclude_keyword_count(self):
        """Test that we have reasonable number of exclude keywords."""
        assert 5 <= len(EXCLUDE_KEYWORDS) <= 50, "Should have reasonable number of exclude keywords"
    
    def test_reasonable_category_count(self):
        """Test that we have reasonable number of categories."""
        assert 3 <= len(CATEGORY_KEYWORDS) <= 10, "Should have reasonable number of categories"
