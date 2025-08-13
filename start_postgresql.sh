#!/bin/bash

# 🚀 MEFAPEX PostgreSQL Startup Script
# ===================================

set -e

echo "🚀 Starting MEFAPEX ChatBox with PostgreSQL"
echo "=========================================="

# Change to script directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "📋 Please run: python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check if PostgreSQL is running
export PATH="/opt/homebrew/Cellar/postgresql@15/15.13/bin:$PATH"
if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "❌ PostgreSQL is not running!"
    echo "📋 Please start PostgreSQL:"
    echo "   macOS: brew services start postgresql@15"
    echo "   Linux: sudo systemctl start postgresql"
    exit 1
fi

echo "✅ PostgreSQL is running"

# Check if database exists
if ! PGPASSWORD=mefapex psql -h localhost -U mefapex -d mefapex_chatbot -c '\q' >/dev/null 2>&1; then
    echo "❌ Database 'mefapex_chatbot' not accessible!"
    echo "📋 Please run setup:"
    echo "   ./setup_postgresql.sh"
    exit 1
fi

echo "✅ Database is accessible"

# Test login functionality
echo "🧪 Testing login functionality..."
if ./.venv/bin/python test_postgresql_login.py >/dev/null 2>&1; then
    echo "✅ Login test passed"
else
    echo "❌ Login test failed!"
    echo "📋 Please check database setup"
    exit 1
fi

# Start the application
echo "🚀 Starting MEFAPEX application..."
echo "📱 Open your browser to: http://localhost:8000"
echo "🔑 Demo login: username=demo, password=1234"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start with proper error handling
exec ./.venv/bin/python main_postgresql.py
