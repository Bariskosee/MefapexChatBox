# 🐘 PostgreSQL Setup Guide for MEFAPEX ChatBox

## Overview
This guide will help you migrate from SQLite to PostgreSQL and resolve login issues.

## ✅ What We've Accomplished

1. **PostgreSQL Dependencies**: Added `psycopg2-binary` and `asyncpg` to requirements.txt
2. **Database Manager**: Created `postgresql_manager.py` for PostgreSQL support
3. **Application**: Created `main_postgresql.py` with PostgreSQL integration
4. **Database Schema**: Set up proper PostgreSQL schema with users, sessions, and messages
5. **Environment**: Configured `.env` file for PostgreSQL settings
6. **Docker**: Updated `docker-compose.yml` to include PostgreSQL service

## 🚀 Quick Start

### 1. Install PostgreSQL (if not already installed)

```bash
# macOS with Homebrew
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
```

### 2. Set up Database

```bash
# Add PostgreSQL to PATH (macOS with Homebrew)
export PATH="/opt/homebrew/Cellar/postgresql@15/15.13/bin:$PATH"

# Create user and database
psql postgres -c "CREATE USER mefapex WITH PASSWORD 'mefapex';"
psql postgres -c "CREATE DATABASE mefapex_chatbot OWNER mefapex;"

# Initialize schema
cd /path/to/MefapexChatBox-main
PGPASSWORD=mefapex psql -h localhost -U mefapex -d mefapex_chatbot -f simple_schema.sql
```

### 3. Install Python Dependencies

```bash
cd /path/to/MefapexChatBox-main
./.venv/bin/pip install psycopg2-binary asyncpg bcrypt
```

### 4. Configure Environment

The `.env` file is already configured with PostgreSQL settings:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mefapex
POSTGRES_PASSWORD=mefapex
POSTGRES_DB=mefapex_chatbot
```

### 5. Test Login Functionality

```bash
# Test PostgreSQL connection and login
./.venv/bin/python test_postgresql_login.py

# Test user creation
./.venv/bin/python test_user_creation.py
```

### 6. Start the Application

```bash
# Using the PostgreSQL-enabled version
./.venv/bin/python main_postgresql.py
```

## 🔑 Login Credentials

### Demo User
- **Username**: `demo`
- **Password**: `1234`

### Test User (created by test script)
- **Username**: `testuser`
- **Password**: `testpass123`

## 🧪 Testing

### Command Line Testing

```bash
# Test login via HTTP
curl -X POST "http://localhost:8000/login" \
-H "Content-Type: application/json" \
-d '{"username": "demo", "password": "1234"}'

# Expected response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user_info": {
    "username": "demo",
    "user_id": "c2ca939a-302a-427b-becd-f7beefcafb22"
  }
}
```

### Web Interface Testing

1. Open browser to `http://localhost:8000`
2. Use login credentials:
   - Username: `demo`
   - Password: `1234`
3. You should be able to login and chat

## 🔧 Troubleshooting

### PostgreSQL Connection Issues

1. **Check if PostgreSQL is running**:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. **Check if database exists**:
   ```bash
   PGPASSWORD=mefapex psql -h localhost -U mefapex -l
   ```

3. **Recreate database if needed**:
   ```bash
   psql postgres -c "DROP DATABASE IF EXISTS mefapex_chatbot;"
   psql postgres -c "CREATE DATABASE mefapex_chatbot OWNER mefapex;"
   PGPASSWORD=mefapex psql -h localhost -U mefapex -d mefapex_chatbot -f simple_schema.sql
   ```

### Login Issues

1. **Check if demo user exists**:
   ```bash
   PGPASSWORD=mefapex psql -h localhost -U mefapex -d mefapex_chatbot -c "SELECT username, email FROM users;"
   ```

2. **Reset demo user password**:
   ```bash
   PGPASSWORD=mefapex psql -h localhost -U mefapex -d mefapex_chatbot -c "
   UPDATE users SET hashed_password = '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBMeO.j9OJrEy2' 
   WHERE username = 'demo';"
   ```

### Application Issues

1. **Check application logs**:
   ```bash
   ./.venv/bin/python main_postgresql.py
   ```

2. **Test database connection**:
   ```bash
   ./.venv/bin/python test_postgresql_login.py
   ```

## 🐳 Docker Setup (Alternative)

If you prefer using Docker:

```bash
# Start PostgreSQL with Docker
docker-compose up postgres -d

# Wait for PostgreSQL to start
sleep 10

# Initialize schema
docker-compose exec postgres psql -U mefapex -d mefapex_chatbot -f /docker-entrypoint-initdb.d/init.sql

# Start the application
docker-compose up mefapex-app
```

## 📋 Database Schema

The PostgreSQL setup includes:

- **users**: User accounts with bcrypt password hashing
- **chat_sessions**: User chat sessions
- **chat_messages**: Individual chat messages
- **Indexes**: Optimized for fast queries
- **UUID support**: Using PostgreSQL UUID extension

## 🔐 Security Features

- Bcrypt password hashing
- JWT token authentication
- Session management
- SQL injection protection via parameterized queries
- Connection pooling for performance

## 📊 Database Statistics

You can check database statistics via:

```bash
curl http://localhost:8000/db/status
```

## 🎯 Next Steps

1. **Production Deployment**: Update environment variables for production
2. **SSL/TLS**: Configure SSL for database connections in production
3. **Backup**: Set up regular database backups
4. **Monitoring**: Add database monitoring and alerting
5. **Performance**: Tune PostgreSQL settings for your workload

## 📞 Support

If you encounter any issues:

1. Check the troubleshooting section above
2. Run the test scripts to verify setup
3. Check application and database logs
4. Ensure all dependencies are installed

The PostgreSQL setup provides better performance, scalability, and reliability compared to SQLite, making it ideal for production use.
