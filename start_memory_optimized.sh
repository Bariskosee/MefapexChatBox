#!/bin/bash

# 🚨 MEFAPEX Memory-Optimized Startup
# ===================================

echo "🚀 Starting MEFAPEX with memory optimizations..."

# Set memory-optimized environment variables
export MEMORY_THRESHOLD_MB=2048
export MODEL_CACHE_SIZE=25
export FORCE_GC_INTERVAL=15
export LRU_CACHE_SIZE=50
export AUTO_GC_ENABLED=true
export MODEL_LAZY_LOADING=true
export MODEL_AUTO_UNLOAD=true

# Memory monitoring
export MEMORY_MONITOR_INTERVAL=30
export MEMORY_ALERT_THRESHOLD=3072

# Check initial memory
echo "📊 Initial memory check..."
python3 emergency_memory_manager.py

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️ Virtual environment not found"
fi

# Start with memory monitoring
echo "🧠 Starting with memory leak fixes applied..."
python3 main.py

# Monitor memory during startup
python3 emergency_memory_manager.py
