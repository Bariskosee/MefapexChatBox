#!/bin/bash
# 🚨 Ultra Memory Optimized MEFAPEX Startup
# =========================================
# Target: < 1 MB/minute memory leak

echo "🚨 Starting MEFAPEX with ULTRA memory optimization..."

# Set ultra-aggressive environment variables
export MEMORY_THRESHOLD_MB=1024
export MODEL_CACHE_SIZE=5
export LRU_CACHE_SIZE=5
export EMERGENCY_MODE=true
export DISABLE_TEXT_GENERATION=true
export DISABLE_LARGE_MODELS=true
export FORCE_CPU_ONLY=true
export GC_FREQUENCY=5
export AUTO_UNLOAD_TIMEOUT=120
export MAX_TEXT_LENGTH=100
export MAX_BATCH_SIZE=1

# Memory check
echo "📊 Pre-startup memory check..."
INITIAL_MEM=$(python3 -c "import psutil; print(f'{psutil.Process().memory_info().rss/1024/1024:.1f}')")
echo "✅ Initial memory: ${INITIAL_MEM}MB"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Start with ultra monitoring
echo "🚨 Starting with ultra-aggressive memory monitoring..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ultra_memory_monitor import start_ultra_monitoring
    start_ultra_monitoring()
    print('✅ Ultra memory monitor started')
except Exception as e:
    print(f'⚠️ Ultra monitor failed: {e}')
" &

# Start the server
echo "🧠 Starting MEFAPEX with emergency model manager..."
python3 main.py

# Cleanup on exit
echo "🧹 Cleanup on exit..."
python3 -c "
try:
    from ultra_memory_monitor import stop_ultra_monitoring
    stop_ultra_monitoring()
    print('✅ Ultra monitor stopped')
except:
    pass
"
