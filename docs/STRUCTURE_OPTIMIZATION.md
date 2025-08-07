# Hermes Project Structure Optimization

## Current Issues Identified

1. **Code Duplication**: Both `hermes/` and `scripts/` directories contain similar functionality
2. **Missing Test Structure**: No proper test organization
3. **Legacy Files**: Inconsistent organization with some legacy elements

## Recommended Actions

### 1. Remove Duplicate `scripts/` Directory
The `scripts/` directory appears to be legacy code that duplicates functionality in the main `hermes/` package. 

**Action**: Remove the entire `scripts/` directory as the main package in `hermes/` is more complete and properly structured.

### 2. Optimize Project Structure
The recommended structure follows Python best practices:

```
hermes/
├── hermes/                 # Main package (✅ already good)
│   ├── __init__.py
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Configuration
│   ├── fetcher.py         # RSS feed parsing
│   ├── filter.py          # Content filtering
│   ├── main.py            # Pipeline orchestration
│   ├── summarizer.py      # AI summarization
│   └── writer.py          # Output generation
├── tests/                 # ✅ Created
│   ├── __init__.py
│   ├── conftest.py        # Test configuration
│   ├── test_fetcher.py    # Unit tests for each module
│   ├── test_filter.py
│   ├── test_summarizer.py
│   └── test_writer.py
├── docs/                  # ✅ Created for documentation
├── data/                  # ✅ Already exists
│   └── digests/           # Generated outputs
├── pyproject.toml         # ✅ Modern Python packaging
├── requirements.txt       # ✅ Dependencies
├── .gitignore            # ✅ Proper exclusions
└── README.md             # ✅ Cleaned up
```

### 3. Clean Up Root Directory
- Remove `__init__.py` from root (not needed for packages)
- Keep `pilot setup instructions.md` for historical reference or move to `docs/`

### 4. Update Dependencies Management
The project has both `pyproject.toml` and `requirements.txt`. Modern Python projects should primarily use `pyproject.toml`:

- Keep `pyproject.toml` as the primary dependency source
- `requirements.txt` can be maintained for backwards compatibility

## Benefits of This Structure

1. **Clear Separation**: Code, tests, docs, and data are properly separated
2. **Standard Compliance**: Follows Python packaging standards
3. **Maintainability**: Easy to understand and contribute to
4. **Scalability**: Structure supports future growth
5. **Tool Integration**: Works well with IDEs, linters, and CI/CD

## Next Steps

1. Remove `scripts/` directory
2. Create comprehensive test suite
3. Add documentation in `docs/`
4. Consider moving pilot instructions to `docs/`
5. Set up CI/CD pipeline using the standardized structure
