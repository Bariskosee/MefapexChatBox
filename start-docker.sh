#!/bin/bash

# 🚀 MefapexChatBox Docker Startup Script
# One command to rule them all!

set -e

echo "🚀 Starting MefapexChatBox with Docker Compose..."

# 🎨 Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 📋 Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 🔍 Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# 🔍 Check if Docker Compose is available
check_docker_compose() {
    if docker compose version > /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
        print_success "Docker Compose v2 is available"
    elif command -v docker-compose > /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
        print_success "Docker Compose v1 is available"
    else
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
}

# 📁 Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p data models_cache logs nginx/ssl
    chmod 755 data models_cache logs
    print_success "Directories created"
}

# 🔧 Setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    if [[ ! -f .env ]]; then
        if [[ -f .env.docker ]]; then
            cp .env.docker .env
            print_success "Environment file created from .env.docker"
        else
            print_warning "No .env file found. Using default environment variables."
        fi
    else
        print_success "Environment file already exists"
    fi
}

# 🧹 Clean up function
cleanup() {
    print_status "Cleaning up old containers and images..."
    $DOCKER_COMPOSE_CMD down --remove-orphans
    docker system prune -f
    print_success "Cleanup completed"
}

# 🚀 Start services
start_services() {
    print_status "Starting all services..."
    
    # Build and start services
    $DOCKER_COMPOSE_CMD up --build -d
    
    print_success "All services started!"
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_service_health
}

# 🏥 Check service health
check_service_health() {
    print_status "Checking service health..."
    
    local services=("mefapex-app" "qdrant" "redis")
    local all_healthy=true
    
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
            print_success "$service is running"
        else
            print_error "$service is not running"
            all_healthy=false
        fi
    done
    
    if $all_healthy; then
        print_success "All core services are healthy!"
        show_access_info
    else
        print_error "Some services are not healthy. Check logs with: $DOCKER_COMPOSE_CMD logs"
        exit 1
    fi
}

# 📊 Show access information
show_access_info() {
    echo ""
    echo "🎉 MefapexChatBox is ready!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Application: http://localhost:8000"
    echo "📊 Health Check: http://localhost:8000/health"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo "🗄️ Qdrant: http://localhost:6333"
    echo "🗂️ Redis: localhost:6379"
    echo "📈 Monitoring: http://localhost:9090 (if enabled)"
    echo "🌍 Nginx: http://localhost:80 (if enabled)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: $DOCKER_COMPOSE_CMD logs -f"
    echo "   Stop services: $DOCKER_COMPOSE_CMD down"
    echo "   Restart: $DOCKER_COMPOSE_CMD restart"
    echo "   Update: $DOCKER_COMPOSE_CMD pull && $DOCKER_COMPOSE_CMD up -d"
    echo ""
}

# 🔄 Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  start     Start all services (default)"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  logs      Show logs"
    echo "  status    Show service status"
    echo "  clean     Clean up and restart"
    echo "  help      Show this help message"
    echo ""
}

# 📊 Show status
show_status() {
    print_status "Service Status:"
    $DOCKER_COMPOSE_CMD ps
}

# 📋 Show logs
show_logs() {
    $DOCKER_COMPOSE_CMD logs -f
}

# 🛑 Stop services
stop_services() {
    print_status "Stopping all services..."
    $DOCKER_COMPOSE_CMD down
    print_success "All services stopped"
}

# 🔄 Restart services
restart_services() {
    print_status "Restarting all services..."
    $DOCKER_COMPOSE_CMD restart
    print_success "All services restarted"
}

# 🎯 Main function
main() {
    local action="${1:-start}"
    
    case "$action" in
        "start")
            check_docker
            check_docker_compose
            create_directories
            setup_environment
            start_services
            ;;
        "stop")
            check_docker_compose
            stop_services
            ;;
        "restart")
            check_docker_compose
            restart_services
            ;;
        "logs")
            check_docker_compose
            show_logs
            ;;
        "status")
            check_docker_compose
            show_status
            ;;
        "clean")
            check_docker
            check_docker_compose
            cleanup
            create_directories
            setup_environment
            start_services
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown action: $action"
            show_usage
            exit 1
            ;;
    esac
}

# 🚀 Run main function
main "$@"
