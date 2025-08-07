#!/bin/bash

# MEFAPEX AI Assistant - Optimized Production Startup Script
# This script starts the application with performance optimizations

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="MEFAPEX AI Assistant"
MAIN_FILE="main.py"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-4}"
ENV_FILE=".env.production"

echo -e "${BLUE}🚀 Starting ${APP_NAME} in Production Mode${NC}"
echo -e "${BLUE}============================================${NC}"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  Environment file $ENV_FILE not found. Using default settings.${NC}"
else
    echo -e "${GREEN}✅ Loading environment from $ENV_FILE${NC}"
    export $(cat $ENV_FILE | grep -v '^#' | xargs)
fi

# Check if main application file exists
if [ ! -f "$MAIN_FILE" ]; then
    echo -e "${RED}❌ Main application file $MAIN_FILE not found!${NC}"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}🐍 Python version: $python_version${NC}"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  No virtual environment detected. Consider using venv or conda.${NC}"
else
    echo -e "${GREEN}🎯 Virtual environment: $VIRTUAL_ENV${NC}"
fi

# Install/check dependencies
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if [ -f "requirements_optimized.txt" ]; then
    pip install -q -r requirements_optimized.txt
    echo -e "${GREEN}✅ Dependencies checked/installed${NC}"
elif [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo -e "${GREEN}✅ Dependencies checked/installed from requirements.txt${NC}"
else
    echo -e "${YELLOW}⚠️  No requirements file found. Make sure dependencies are installed.${NC}"
fi

# Check if Qdrant is running (optional but recommended)
if command -v curl >/dev/null 2>&1; then
    qdrant_host="${QDRANT_HOST:-localhost}"
    qdrant_port="${QDRANT_PORT:-6333}"
    
    if curl -s "http://$qdrant_host:$qdrant_port/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Qdrant vector database is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Qdrant not detected at $qdrant_host:$qdrant_port${NC}"
        echo -e "${YELLOW}   The application will work but vector search may be limited${NC}"
    fi
fi

# Create necessary directories
mkdir -p logs
mkdir -p data
echo -e "${GREEN}✅ Created necessary directories${NC}"

# Display configuration
echo -e "${BLUE}🔧 Configuration:${NC}"
echo -e "   Host: $HOST"
echo -e "   Port: $PORT"
echo -e "   Workers: $WORKERS"
echo -e "   Environment: ${FASTAPI_ENV:-development}"

# Function to start with Uvicorn (development/single worker)
start_uvicorn() {
    echo -e "${GREEN}🚀 Starting with Uvicorn (single worker)...${NC}"
    uvicorn main:app \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        --log-level "${LOG_LEVEL:-info}" \
        --access-log \
        --loop uvloop \
        --http httptools
}

# Function to start with Gunicorn (production/multiple workers)
start_gunicorn() {
    echo -e "${GREEN}🚀 Starting with Gunicorn (production mode)...${NC}"
    
    # Gunicorn configuration
    gunicorn main:app \
        --worker-class uvicorn.workers.UvicornWorker \
        --workers "$WORKERS" \
        --bind "$HOST:$PORT" \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --preload \
        --log-level "${LOG_LEVEL:-info}" \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --capture-output \
        --enable-stdio-inheritance
}

# Determine which server to use
if [ "$WORKERS" -eq 1 ] || [ "${FASTAPI_ENV:-development}" = "development" ]; then
    start_uvicorn
else
    # Check if Gunicorn is available
    if command -v gunicorn >/dev/null 2>&1; then
        start_gunicorn
    else
        echo -e "${YELLOW}⚠️  Gunicorn not found. Installing...${NC}"
        pip install gunicorn
        start_gunicorn
    fi
fi
