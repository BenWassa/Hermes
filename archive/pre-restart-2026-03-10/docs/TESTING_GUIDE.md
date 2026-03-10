# Hermes Testing Guide

## Overview

This guide explains how to implement and run tests for the Hermes project. The test suite covers all major components with unit tests, integration tests, and mock-based testing for external dependencies.

## Test Structure

```
tests/
├── conftest.py           # Test configuration and shared fixtures
├── test_config.py        # Configuration testing
├── test_fetcher.py       # RSS feed and article fetching tests
├── test_filter.py        # Content filtering and categorization tests
├── test_summarizer.py    # Summarization (OpenAI + fallback) tests
├── test_writer.py        # Output generation tests (MD/HTML/JSON)
├── test_main.py          # Pipeline integration tests
└── test_cli.py           # Command-line interface tests
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_fetcher.py

# Run specific test class
pytest tests/test_fetcher.py::TestFetchArticles

# Run specific test method
pytest tests/test_fetcher.py::TestFetchArticles::test_fetch_articles_basic
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=hermes

# Generate HTML coverage report
pytest --cov=hermes --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Test Categories

```bash
# Run only fast tests (exclude slow ones)
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run with specific markers
pytest -m "not slow and not integration"
```

## Test Implementation Patterns

### 1. Mock External Dependencies

```python
@patch('hermes.fetcher.feedparser.parse')
def test_fetch_articles_basic(self, mock_parse, mock_feed_data):
    """Test basic article fetching functionality."""
    mock_parse.return_value = mock_feed_data
    
    with patch('hermes.fetcher._fetch_article_content', return_value="Full content"):
        articles = fetch_articles(["https://example.com/feed"])
        
    assert len(articles) == 2
    mock_parse.assert_called_once()
```

### 2. Use Fixtures for Test Data

```python
@pytest.fixture
def sample_articles():
    """List of sample NewsArticle objects for testing."""
    return [
        NewsArticle(
            title="AI Breakthrough in Healthcare",
            summary="AI shows promise in medical diagnostics",
            link="https://example.com/ai-health",
            content="Artificial intelligence technology..."
        ),
        # More test articles...
    ]
```

### 3. Test Error Conditions

```python
def test_fetch_articles_with_failed_feed(self, mock_parse):
    """Test handling of failed RSS feed parsing."""
    mock_parse.side_effect = Exception("Feed parsing failed")
    
    articles = fetch_articles(["https://bad-feed.com"])
    
    # Should fall back to sample articles
    assert len(articles) > 0
```

### 4. Integration Testing

```python
def test_full_write_workflow(self, sample_articles, temp_output_dir):
    """Test complete workflow from articles to file."""
    # Set up articles with categories and bullets
    sample_articles[0].category = "⚙️ Tech & AI"
    sample_articles[0].bullets = ["• AI advancement", "• Technology impact"]
    
    with patch('hermes.writer.DIGEST_DIR', temp_output_dir):
        output_path = write_digest(sample_articles, "markdown")
        
    assert output_path.exists()
    content = output_path.read_text(encoding='utf-8')
    assert "⚙️ Tech & AI" in content
```

## Key Testing Concepts

### Mocking External APIs

- **RSS Feeds**: Mock `feedparser.parse()` to avoid network calls
- **OpenAI API**: Mock OpenAI client to avoid API charges
- **File System**: Use `tmp_path` fixture for temporary files
- **Article Content**: Mock `newspaper3k` to avoid web scraping

### Test Data Management

- **Fixtures**: Use pytest fixtures for reusable test data
- **Factories**: Create helper functions for generating test objects
- **Parameterization**: Test multiple scenarios with `@pytest.mark.parametrize`

### Assertion Strategies

```python
# Test return values
assert len(articles) == expected_count
assert article.title == "Expected Title"

# Test side effects
mock_function.assert_called_once()
mock_function.assert_called_with(expected_args)

# Test file outputs
assert output_path.exists()
assert "expected content" in file_content

# Test exceptions
with pytest.raises(ValueError, match="error message"):
    function_that_should_fail()
```

## Common Test Scenarios

### 1. Fetcher Module Tests

- Valid RSS feed parsing
- Invalid/empty feeds
- Network failures
- Content extraction
- Fallback sample data

### 2. Filter Module Tests

- Keyword-based filtering
- Category assignment
- Edge cases (empty content, special characters)
- Configuration-driven behavior

### 3. Summarizer Module Tests

- OpenAI API success/failure
- Fallback summarization
- Different content lengths
- Error handling

### 4. Writer Module Tests

- Multiple output formats (MD, HTML, JSON)
- File creation and structure
- Content accuracy
- Directory handling

### 5. Integration Tests

- End-to-end pipeline
- Configuration integration
- Error propagation
- Performance under load

## Best Practices

### 1. Test Independence

```python
# Good: Each test is independent
def test_filter_articles_basic(self, sample_articles):
    filtered = filter_articles(sample_articles.copy())  # Use copy
    # Test logic...

# Bad: Tests that depend on previous test state
def test_sequence_step_1(self):
    self.shared_state = "something"

def test_sequence_step_2(self):
    assert self.shared_state == "something"  # Fragile!
```

### 2. Clear Test Names

```python
# Good: Descriptive test names
def test_fetch_articles_with_empty_sources(self):
def test_categorize_articles_with_no_matching_keywords(self):
def test_write_digest_creates_output_directory(self):

# Bad: Vague test names
def test_fetch(self):
def test_categorize(self):
def test_write(self):
```

### 3. Arrange-Act-Assert Pattern

```python
def test_filter_articles_removes_excluded_content(self):
    # Arrange
    articles = [create_article_with_excluded_keyword()]
    
    # Act
    filtered = filter_articles(articles)
    
    # Assert
    assert len(filtered) == 0
```

### 4. Mock at the Right Level

```python
# Good: Mock external dependencies
@patch('hermes.fetcher.feedparser.parse')
def test_fetch_articles(self, mock_parse):
    # Test internal logic without network calls

# Bad: Over-mocking internal functions
@patch('hermes.fetcher._parse_feed_entry')  # Too internal
def test_fetch_articles(self, mock_parse_entry):
    # Defeats the purpose of testing
```

## Continuous Integration

The project includes GitHub Actions workflow (`.github/workflows/ci.yml`) that:

- Runs tests on Python 3.9, 3.10, 3.11
- Checks code formatting with Black
- Performs linting with flake8
- Runs type checking with mypy
- Generates coverage reports
- Uploads coverage to Codecov

## Troubleshooting Tests

### Common Issues

1. **Import Errors**: Ensure the package is installed in editable mode (`pip install -e .`)
2. **Missing Dependencies**: Install test dependencies (`pip install -e ".[dev]"`)
3. **Path Issues**: Use absolute paths and proper fixtures
4. **Mock Failures**: Verify mock patch targets are correct
5. **Coverage Issues**: Check that all code paths are tested

### Debugging Tests

```bash
# Run with detailed output
pytest -v -s

# Stop on first failure
pytest -x

# Run specific failing test
pytest tests/test_module.py::TestClass::test_method -v

# Print statements (use -s flag)
pytest -s tests/test_module.py
```

## Adding New Tests

When adding new functionality:

1. **Write tests first** (TDD approach)
2. **Cover happy path and edge cases**
3. **Mock external dependencies**
4. **Update fixtures if needed**
5. **Maintain high coverage** (target: >80%)

### Example New Test

```python
def test_new_feature_success(self, sample_data):
    """Test new feature with valid input."""
    # Arrange
    input_data = sample_data
    
    # Act
    result = new_feature(input_data)
    
    # Assert
    assert result.success is True
    assert result.data == expected_output

def test_new_feature_handles_errors(self):
    """Test new feature error handling."""
    with pytest.raises(ValueError, match="Invalid input"):
        new_feature(invalid_input)
```

This comprehensive test suite ensures the Hermes project is reliable, maintainable, and ready for production use.
