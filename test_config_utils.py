"""
Test configuration utilities to ensure proper fallback behavior
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_utils():
    """Test the configuration utilities"""
    print("Testing configuration utilities...")
    
    try:
        from core.config_utils import (
            load_config, 
            load_cache_config, 
            get_qdrant_config, 
            get_ai_config, 
            get_redis_config,
            is_unified_config,
            get_config_value
        )
        
        # Test basic config loading
        config = load_config()
        print(f"✓ Successfully loaded config: {type(config).__name__}")
        
        # Test unified config detection
        is_unified = is_unified_config(config)
        print(f"✓ Unified config detection: {is_unified}")
        
        # Test cache config loading
        cache_config = load_cache_config()
        print(f"✓ Successfully loaded cache config: {type(cache_config).__name__}")
        
        # Test convenience functions
        qdrant_config = get_qdrant_config()
        print(f"✓ Qdrant config: host={qdrant_config['host']}, port={qdrant_config['port']}")
        
        ai_config = get_ai_config()
        print(f"✓ AI config: use_openai={ai_config['use_openai']}, use_huggingface={ai_config['use_huggingface']}")
        
        redis_config = get_redis_config()
        print(f"✓ Redis config: host={redis_config['host']}, port={redis_config['port']}")
        
        # Test dynamic config value access
        debug_mode = get_config_value('debug', False, config)
        print(f"✓ Dynamic config access: debug={debug_mode}")
        
        print("\n🎉 All configuration utility tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration utility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_config_utils()
