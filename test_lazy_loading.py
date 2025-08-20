#!/usr/bin/env python3
"""
🧪 Lazy Loading Test Script
Test the new lazy loading optimization
"""
import sys
import os
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_lazy_loading():
    """Test lazy loading functionality"""
    print("🧪 Testing Lazy Loading Optimization...")
    
    try:
        # Import model manager
        from model_manager import model_manager
        
        print("✅ Model manager imported successfully")
        
        # Check initial state (models should NOT be loaded)
        print(f"📊 Initial state:")
        print(f"   Turkish model loaded: {model_manager._turkish_sentence_model is not None}")
        print(f"   English model loaded: {model_manager._english_sentence_model is not None}")
        print(f"   Text generator loaded: {model_manager._text_generator_model is not None}")
        
        # Get lazy loading statistics
        if hasattr(model_manager, 'get_lazy_loading_statistics'):
            stats = model_manager.get_lazy_loading_statistics()
            print(f"📈 Lazy loading stats: {stats['current_state']['models_loaded']}")
        
        # Test configuration
        model_manager.set_auto_cleanup(
            enabled=True,
            cleanup_interval=60,  # 1 minute for testing
            max_idle_time=120     # 2 minutes for testing
        )
        print("⚙️ Auto-cleanup configured")
        
        # Test embedding generation (should trigger lazy loading)
        print("🔄 Testing embedding generation (triggers lazy loading)...")
        start_time = time.time()
        
        embedding = model_manager.generate_embedding("Merhaba dünya")
        
        load_time = time.time() - start_time
        print(f"✅ Embedding generated in {load_time:.2f} seconds")
        print(f"   Embedding length: {len(embedding) if embedding else 0}")
        
        # Check state after loading
        print(f"📊 State after loading:")
        print(f"   Turkish model loaded: {model_manager._turkish_sentence_model is not None}")
        print(f"   English model loaded: {model_manager._english_sentence_model is not None}")
        
        # Test model info
        if hasattr(model_manager, 'get_model_info'):
            model_info = model_manager.get_model_info()
            print(f"💾 Memory usage: {model_info.get('memory_info', {}).get('memory_mb', 'N/A')} MB")
            
            cache_info = model_info.get('cache_info', {})
            print(f"🔄 Cache hits: {cache_info.get('embedding_cache_hits', 0)}")
            print(f"   Cache misses: {cache_info.get('embedding_cache_misses', 0)}")
        
        # Test second embedding (should be faster - cached)
        print("🔄 Testing second embedding (should use cache)...")
        start_time = time.time()
        
        embedding2 = model_manager.generate_embedding("Merhaba dünya")  # Same text
        
        cached_time = time.time() - start_time
        print(f"✅ Cached embedding generated in {cached_time:.2f} seconds")
        
        # Test different text
        embedding3 = model_manager.generate_embedding("Hello world")
        print(f"✅ English embedding generated")
        
        # Final statistics
        if hasattr(model_manager, 'get_lazy_loading_statistics'):
            final_stats = model_manager.get_lazy_loading_statistics()
            print(f"📈 Final lazy loading stats:")
            for model_type, loaded in final_stats['current_state']['models_loaded'].items():
                print(f"   {model_type}: {'✅ loaded' if loaded else '❌ not loaded'}")
        
        print("🎉 Lazy loading test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_lazy_loading()
    sys.exit(0 if success else 1)
