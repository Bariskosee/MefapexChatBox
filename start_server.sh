#!/bin/bash

# MEFAPEX Chatbot Server Startup Script
echo "🚀 Starting MEFAPEX Chatbot Server..."

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=mefapex
export POSTGRES_PASSWORD=mefapex
export POSTGRES_DB=mefapex_chatbot
export SECRET_KEY=mefapex-secret-key-change-in-production
export DEBUG=true
export ENVIRONMENT=development

# Server settings for Safari compatibility
export HOST=127.0.0.1
export PORT=8000
export ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000,http://0.0.0.0:8000,*"

# Redis settings
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please create it first:"
    echo "python -m venv .venv"
    echo "source .venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Check if PostgreSQL is running
echo "🗄️ Checking PostgreSQL connection..."
if docker exec mefapex-postgres pg_isready -U mefapex -d mefapex_chatbot >/dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready. Starting Docker containers..."
    docker compose up -d postgres redis qdrant
    sleep 5
    
    # Check again
    if docker exec mefapex-postgres pg_isready -U mefapex -d mefapex_chatbot >/dev/null 2>&1; then
        echo "✅ PostgreSQL is now ready"
    else
        echo "❌ Failed to start PostgreSQL. Please check Docker containers."
        echo "Run: docker compose logs postgres"
        exit 1
    fi
fi

# Start the server
echo "🚀 Starting MEFAPEX server..."
echo "Environment variables set:"
echo "  POSTGRES_HOST=$POSTGRES_HOST"
echo "  POSTGRES_PORT=$POSTGRES_PORT"
echo "  POSTGRES_USER=$POSTGRES_USER"
echo "  POSTGRES_DB=$POSTGRES_DB"
echo "  DEBUG=$DEBUG"
echo ""

python main.py
