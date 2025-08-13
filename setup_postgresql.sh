#!/bin/bash

# 🐘 PostgreSQL Setup Script for MEFAPEX ChatBox
# ==============================================
# This script sets up PostgreSQL for the MEFAPEX application

set -e  # Exit on any error

echo "🐘 Setting up PostgreSQL for MEFAPEX ChatBox"
echo "============================================="

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed!"
    echo "📋 Installation instructions:"
    echo ""
    echo "🍺 On macOS with Homebrew:"
    echo "   brew install postgresql"
    echo "   brew services start postgresql"
    echo ""
    echo "🐧 On Ubuntu/Debian:"
    echo "   sudo apt update"
    echo "   sudo apt install postgresql postgresql-contrib"
    echo "   sudo systemctl start postgresql"
    echo ""
    echo "🎩 On CentOS/RHEL:"
    echo "   sudo yum install postgresql-server postgresql-contrib"
    echo "   sudo postgresql-setup initdb"
    echo "   sudo systemctl start postgresql"
    echo ""
    exit 1
fi

echo "✅ PostgreSQL is installed"

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running!"
    echo "📋 Start PostgreSQL:"
    echo ""
    echo "🍺 On macOS with Homebrew:"
    echo "   brew services start postgresql"
    echo ""
    echo "🐧 On Ubuntu/Debian:"
    echo "   sudo systemctl start postgresql"
    echo ""
    exit 1
fi

echo "✅ PostgreSQL is running"

# Database configuration
DB_NAME="mefapex_chatbot"
DB_USER="mefapex"
DB_PASSWORD="mefapex"

echo "🔧 Creating database and user..."

# Create user and database
psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "ℹ️  User $DB_USER already exists"
psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "ℹ️  Database $DB_NAME already exists"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "✅ Database setup completed"

# Initialize database schema
echo "🏗️  Initializing database schema..."
export PGPASSWORD=$DB_PASSWORD
psql -h localhost -U $DB_USER -d $DB_NAME -f database/init.sql

echo "✅ Database schema initialized"

# Test connection
echo "🔍 Testing database connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        database='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD'
    )
    print('✅ Database connection successful!')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

echo ""
echo "🎉 PostgreSQL setup completed successfully!"
echo ""
echo "📋 Connection details:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo "   Password: $DB_PASSWORD"
echo ""
echo "🔧 Next steps:"
echo "1. Install Python dependencies: pip install -r requirements.txt"
echo "2. Run the application: python main_postgresql.py"
echo ""
