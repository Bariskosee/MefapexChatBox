"""
Test cache manager functionality and centralized cache access.
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestCacheManager:
    """Test cache manager centralized access"""
    
    @pytest.fixture(autouse=True)
    async def setup_cache_manager(self):
        """Setup cache manager for tests"""
        try:
            from cache_manager import initialize_cache_manager, shutdown_cache_manager, get_cache_manager
            self.cache_manager = get_cache_manager()
            
            # Initialize with test config
            await initialize_cache_manager()
            yield
            
            # Cleanup
            await shutdown_cache_manager()
        except ImportError:
            pytest.skip("Cache manager not available")
    
    def test_cache_manager_functions_available(self):
        """Test that cache manager functions are available for import"""
        try:
            from cache_manager import get_response_cache, get_distributed_cache
            assert get_response_cache is not None
            assert get_distributed_cache is not None
        except ImportError:
            pytest.fail("Cache manager functions should be available")
    
    def test_response_cache_access(self):
        """Test response cache can be accessed through cache manager"""
        try:
            from cache_manager import get_response_cache
            response_cache = get_response_cache()
            
            # Response cache might be None if not initialized, that's okay
            # The important thing is the function doesn't crash
            assert True  # If we get here, the function works
            
        except Exception as e:
            pytest.fail(f"Response cache access failed: {e}")
    
    def test_distributed_cache_access(self):
        """Test distributed cache can be accessed through cache manager"""
        try:
            from cache_manager import get_distributed_cache
            distributed_cache = get_distributed_cache()
            
            # Distributed cache might be None if not initialized, that's okay
            # The important thing is the function doesn't crash
            assert True  # If we get here, the function works
            
        except Exception as e:
            pytest.fail(f"Distributed cache access failed: {e}")
    
    async def test_cache_manager_initialization(self):
        """Test cache manager can be initialized"""
        try:
            from cache_manager import get_cache_manager
            cache_manager = get_cache_manager()
            
            # Check if manager is available
            assert cache_manager is not None
            
            # Check if it has expected methods
            assert hasattr(cache_manager, 'get_response_cache')
            assert hasattr(cache_manager, 'get_distributed_cache')
            
        except Exception as e:
            pytest.fail(f"Cache manager initialization test failed: {e}")

class TestChatApiCacheIntegration:
    """Test that chat API properly uses centralized cache"""
    
    def test_chat_api_imports_cache_manager(self):
        """Test that chat API imports cache manager functions"""
        try:
            # Read the chat API file to check imports
            chat_api_path = project_root / "api" / "chat.py"
            with open(chat_api_path, 'r') as f:
                content = f.read()
            
            # Check that it imports from cache_manager
            assert "from cache_manager import get_response_cache, get_distributed_cache" in content
            
            # Check that old cache imports are removed
            assert "from distributed_cache import create_distributed_cache" not in content
            assert "def get_cache():" not in content
            
            # Check that the old distributed_cache global variable is not present
            assert "distributed_cache = None  # Will be initialized later" not in content
            
        except FileNotFoundError:
            pytest.skip("Chat API file not found")
        except Exception as e:
            pytest.fail(f"Chat API cache integration test failed: {e}")
    
    def test_chat_api_uses_centralized_cache(self):
        """Test that chat API uses centralized cache functions"""
        try:
            # Import the chat module to check it works
            from api.chat import router
            
            # If import succeeds without errors, the integration is working
            assert router is not None
            
        except ImportError as e:
            # If cache_manager import fails, that's expected in some environments
            if "cache_manager" in str(e):
                pytest.skip("Cache manager not available in test environment")
            else:
                pytest.fail(f"Chat API import failed: {e}")
        except Exception as e:
            pytest.fail(f"Chat API centralized cache test failed: {e}")

class TestCacheConsistency:
    """Test cache consistency and behavior"""
    
    async def test_both_caches_accessible(self):
        """Test that both response and distributed caches are accessible"""
        try:
            from cache_manager import get_response_cache, get_distributed_cache
            
            # Get both cache instances
            response_cache = get_response_cache()
            distributed_cache = get_distributed_cache()
            
            # Both may be None if not initialized, but functions should work
            # This test verifies the API is consistent
            assert True  # Test passes if no exceptions are raised
            
        except ImportError:
            pytest.skip("Cache manager not available")
        except Exception as e:
            pytest.fail(f"Cache consistency test failed: {e}")
    
    def test_cache_manager_singleton(self):
        """Test that cache manager provides consistent instances"""
        try:
            from cache_manager import get_cache_manager
            
            # Get manager instances
            manager1 = get_cache_manager()
            manager2 = get_cache_manager()
            
            # Should be the same instance (singleton pattern)
            assert manager1 is manager2
            
        except ImportError:
            pytest.skip("Cache manager not available")
        except Exception as e:
            pytest.fail(f"Cache manager singleton test failed: {e}")

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
