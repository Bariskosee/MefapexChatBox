#!/bin/bash
#
# Distributed WebSocket Deployment Script for MEFAPEX ChatBox
# This script starts the application with distributed WebSocket support
#

set -e

# Configuration
REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
WORKERS=${WORKERS:-4}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-"info"}
WORKER_CLASS=${WORKER_CLASS:-"uvicorn.workers.UvicornWorker"}

# Distributed WebSocket configuration
export DISTRIBUTED_WEBSOCKET_ENABLED=true
export WEBSOCKET_SESSION_TTL=3600
export WORKER_ID="${WORKER_ID:-worker-$$-$(date +%s)}"
export NODE_ID="${NODE_ID:-node-$(hostname)-$$}"

echo "🚀 Starting MEFAPEX ChatBox with Distributed WebSocket Support"
echo "=============================================================="
echo "Configuration:"
echo "  - Workers: $WORKERS"
echo "  - Host: $HOST"
echo "  - Port: $PORT"
echo "  - Redis URL: $REDIS_URL"
echo "  - Worker ID: $WORKER_ID"
echo "  - Node ID: $NODE_ID"
echo "  - Log Level: $LOG_LEVEL"
echo "=============================================================="

# Check if Redis is available
echo "🔍 Checking Redis connectivity..."
if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
        echo "✅ Redis is accessible"
    else
        echo "⚠️ Warning: Redis is not accessible. Will use in-memory session store."
        echo "   For distributed deployment, ensure Redis is running and accessible."
    fi
else
    echo "⚠️ Warning: redis-cli not found. Cannot verify Redis connectivity."
fi

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ] && [ -f ".venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
fi

# Install dependencies if needed
if [ ! -f ".dependencies_installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    touch .dependencies_installed
fi

# Choose deployment method based on available tools
if command -v gunicorn >/dev/null 2>&1; then
    echo "🦄 Starting with Gunicorn + Uvicorn workers..."
    
    # Create Gunicorn configuration if it doesn't exist
    if [ ! -f "gunicorn.conf.py" ]; then
        cat > gunicorn.conf.py << 'EOF'
# Gunicorn configuration for distributed WebSocket deployment
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"
workers = int(os.getenv('WORKERS', 4))
worker_class = "uvicorn.workers.UvicornWorker"

# Worker configuration
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5

# Process naming
proc_name = "mefapex-chatbox"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Graceful shutdown
graceful_timeout = 30

# Worker recycling
max_requests = 1000
max_requests_jitter = 100

# Memory efficiency
preload_app = True
worker_tmp_dir = "/dev/shm"

def post_fork(server, worker):
    """Set unique worker ID for each worker process"""
    import os
    os.environ['WORKER_ID'] = f"gunicorn-worker-{worker.pid}"
EOF
    fi
    
    exec gunicorn main:app -c gunicorn.conf.py
    
elif command -v uvicorn >/dev/null 2>&1; then
    echo "🦄 Starting with Uvicorn..."
    
    if [ "$WORKERS" -gt 1 ]; then
        echo "🔄 Multi-worker mode with $WORKERS workers"
        exec uvicorn main:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --worker-class "$WORKER_CLASS" \
            --log-level "$LOG_LEVEL"
    else
        echo "🔄 Single-worker mode"
        exec uvicorn main:app \
            --host "$HOST" \
            --port "$PORT" \
            --log-level "$LOG_LEVEL" \
            --reload
    fi
    
else
    echo "❌ Error: Neither Gunicorn nor Uvicorn is available"
    echo "Please install one of them:"
    echo "  pip install gunicorn"
    echo "  pip install uvicorn[standard]"
    exit 1
fi
