#!/bin/bash

# 🐳 MEFAPEX PostgreSQL Docker Startup Script
# ===========================================

set -e

echo "🚀 Starting MEFAPEX ChatBox with PostgreSQL"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker compose is available (new or old syntax)
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker.${NC}"
    exit 1
fi

# Use modern docker compose syntax
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    # Fallback to older docker-compose if available
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        echo -e "${RED}❌ Docker Compose is not available. Please install Docker Compose.${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}📋 Pre-flight Checks...${NC}"

# Create necessary directories
mkdir -p data logs models_cache content backup

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found, copying from .env.docker${NC}"
    cp .env.docker .env
    echo -e "${GREEN}✅ Created .env file${NC}"
fi

# Backup existing SQLite data if it exists
if [ -f "mefapex.db" ]; then
    echo -e "${YELLOW}📦 Backing up existing SQLite database...${NC}"
    cp mefapex.db backup/mefapex_$(date +%Y%m%d_%H%M%S).db
    echo -e "${GREEN}✅ SQLite database backed up${NC}"
fi

echo -e "${BLUE}🐳 Building Docker images...${NC}"
$DOCKER_COMPOSE_CMD build --no-cache

echo -e "${BLUE}🚀 Starting services...${NC}"
$DOCKER_COMPOSE_CMD up -d

echo -e "${GREEN}✅ Services started successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Service Status:${NC}"
$DOCKER_COMPOSE_CMD ps

echo ""
echo -e "${GREEN}🎉 MEFAPEX ChatBox is now running!${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo "🌐 Application: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo "🗄️ PostgreSQL: localhost:5432"
echo "🔍 Qdrant: http://localhost:6333"
echo "📦 Redis: localhost:6379"
echo ""
echo -e "${BLUE}📋 Useful Commands:${NC}"
echo "📊 View logs: $DOCKER_COMPOSE_CMD logs -f"
echo "🔧 Enter app container: $DOCKER_COMPOSE_CMD exec mefapex-app bash"
echo "🗄️ Access PostgreSQL: $DOCKER_COMPOSE_CMD exec postgres psql -U mefapex -d mefapex_chatbot"
echo "🛑 Stop services: $DOCKER_COMPOSE_CMD down"
echo "🗑️ Remove all data: $DOCKER_COMPOSE_CMD down -v"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "• This setup uses PostgreSQL exclusively"
echo "• SQLite support has been completely removed"
echo "• Change default passwords in .env for production"
echo "• Data is persisted in Docker volumes"
echo ""

# Wait a moment for services to start
sleep 5

# Check if services are healthy
echo -e "${BLUE}🏥 Health Check...${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Application is healthy and responding${NC}"
else
    echo -e "${YELLOW}⚠️  Application may still be starting up...${NC}"
    echo "   Check logs with: docker-compose logs -f mefapex-app"
fi

echo ""
echo -e "${GREEN}🚀 Deployment Complete!${NC}"
