"""
Shared test fixtures and configuration for MEFAPEX ChatBox tests.
"""
import asyncio
import pytest
import httpx
from pathlib import Path
import sys
import os

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    async with httpx.AsyncClient() as client:
        yield client

@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "username": "test_user",
        "email": "test@example.com",
        "password": "test_password"
    }

@pytest.fixture
def test_message_data():
    """Sample message data for testing."""
    return {
        "content": "Hello, this is a test message",
        "role": "user"
    }

# Set test environment variables
@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    yield
    # Cleanup
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
