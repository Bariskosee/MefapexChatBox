#!/bin/bash

# 🚀 MefapexChatBox Docker Management Script
# Usage: ./docker-manager.sh [command] [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.docker"
ENVIRONMENT="development"

# Function to display usage
show_usage() {
    echo -e "${BLUE}🐳 MefapexChatBox Docker Manager${NC}"
    echo ""
    echo "Usage: $0 [command] [environment]"
    echo ""
    echo "Commands:"
    echo "  start     - Start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  build     - Build and start services"
    echo "  logs      - Show service logs"
    echo "  status    - Show service status"
    echo "  clean     - Clean up and rebuild"
    echo "  shell     - Access application shell"
    echo ""
    echo "Environments:"
    echo "  dev       - Development (default)"
    echo "  prod      - Production with monitoring"
    echo ""
    echo "Examples:"
    echo "  $0 start dev     # Start development environment"
    echo "  $0 start prod    # Start production environment"
    echo "  $0 logs          # Show all logs"
    echo "  $0 clean         # Clean rebuild"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi
}

# Function to set environment
set_environment() {
    if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
        ENVIRONMENT="production"
        export COMPOSE_PROFILES="production"
        echo -e "${YELLOW}🏭 Production environment selected${NC}"
    else
        ENVIRONMENT="development"
        export COMPOSE_PROFILES=""
        echo -e "${GREEN}🛠️ Development environment selected${NC}"
    fi
}

# Function to start services
start_services() {
    echo -e "${GREEN}🚀 Starting MefapexChatBox services...${NC}"
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
    
    echo -e "${GREEN}✅ Services started successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Service URLs:${NC}"
    echo "🚀 Main App: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo "🏥 Health: http://localhost:8000/health"
    echo "🗄️ Qdrant: http://localhost:6333"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "📊 Monitoring: http://localhost:9090"
        echo "🌍 Nginx: http://localhost:80"
    fi
}

# Function to stop services
stop_services() {
    echo -e "${YELLOW}🛑 Stopping MefapexChatBox services...${NC}"
    docker-compose -f $COMPOSE_FILE down
    echo -e "${GREEN}✅ Services stopped successfully!${NC}"
}

# Function to restart services
restart_services() {
    echo -e "${YELLOW}🔄 Restarting MefapexChatBox services...${NC}"
    docker-compose -f $COMPOSE_FILE restart
    echo -e "${GREEN}✅ Services restarted successfully!${NC}"
}

# Function to build and start
build_services() {
    echo -e "${BLUE}🏗️ Building and starting services...${NC}"
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up --build -d
    echo -e "${GREEN}✅ Build completed and services started!${NC}"
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}📋 Showing service logs...${NC}"
    docker-compose -f $COMPOSE_FILE logs -f --tail=100
}

# Function to show status
show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    docker-compose -f $COMPOSE_FILE ps
    echo ""
    echo -e "${BLUE}🐳 Docker Stats:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Function to clean up and rebuild
clean_rebuild() {
    echo -e "${YELLOW}🧹 Cleaning up and rebuilding...${NC}"
    docker-compose -f $COMPOSE_FILE down -v
    docker system prune -f
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up --build -d
    echo -e "${GREEN}✅ Clean rebuild completed!${NC}"
}

# Function to access shell
access_shell() {
    echo -e "${BLUE}🖥️ Accessing application shell...${NC}"
    docker exec -it mefapex-chatbox bash
}

# Main script logic
check_docker

# Parse arguments
COMMAND=${1:-"start"}
ENV_ARG=${2:-"dev"}

set_environment $ENV_ARG

case $COMMAND in
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "build")
        build_services
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "clean")
        clean_rebuild
        ;;
    "shell")
        access_shell
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac
