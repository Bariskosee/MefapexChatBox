# MEFAPEX ChatBox Test Suite

This directory contains all tests for the MEFAPEX ChatBox application.

## Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared test fixtures and configuration
├── test_conversation_history.py # Conversation history tests
├── test_db_compatibility.py    # Database compatibility tests
├── test_history_api.py         # History API tests
├── test_postgresql_login.py    # PostgreSQL login tests
├── test_unified_database.py    # Unified database tests
└── test_user_creation.py       # User creation tests
```

## Running Tests

### Using pytest directly:
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_user_creation.py

# Run with verbose output
pytest tests/ -v

# Run tests with specific markers
pytest tests/ -m unit
pytest tests/ -m integration
```

### Using the test runner script:
```bash
# Run all tests
python run_tests.py

# Run unit tests only
python run_tests.py --unit

# Run integration tests only
python run_tests.py --integration

# Run with coverage report
python run_tests.py --coverage

# Run specific test file
python run_tests.py --file test_user_creation.py
```

## Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, require external dependencies)
- `@pytest.mark.database` - Tests that require database access
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow-running tests

## Configuration

- `pytest.ini` - Pytest configuration in the project root
- `conftest.py` - Shared test fixtures and setup
- Test environment variables are automatically set for testing

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Use Fixtures**: Leverage pytest fixtures for common test data and setup
3. **Mark Tests**: Use appropriate pytest markers to categorize tests
4. **Async Testing**: Use `pytest-asyncio` for testing async functions
5. **Mock External Dependencies**: Use mocking for external services and APIs

## Adding New Tests

1. Create test files with the `test_` prefix
2. Name test functions with the `test_` prefix
3. Use appropriate pytest markers
4. Add docstrings to explain what the test does
5. Use fixtures from `conftest.py` when possible

Example:
```python
import pytest

@pytest.mark.unit
async def test_example_function(test_user_data):
    """Test that example function works correctly."""
    # Your test code here
    assert True
```
