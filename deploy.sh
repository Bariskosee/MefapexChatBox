#!/bin/bash

# 🚀 MEFAPEX Production Deployment Script
# Author: MEFAPEX AI Assistant
# Description: Production-ready deployment with security and monitoring

set -e  # Exit on any error

echo "🚀 Starting MEFAPEX Production Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="mefapex-chatbot"
APP_USER="mefapex"
APP_DIR="/opt/mefapex"
LOG_DIR="/var/log/mefapex"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
NGINX_CONFIG="/etc/nginx/sites-available/${APP_NAME}"
DOMAIN="yourdomain.com"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Update system
    apt update && apt upgrade -y
    
    # Install required packages
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        supervisor \
        postgresql \
        postgresql-contrib \
        redis-server \
        htop \
        ufw \
        fail2ban \
        certbot \
        python3-certbot-nginx
        
    log_success "System dependencies installed"
}

create_user() {
    log_info "Creating application user..."
    
    if ! id "$APP_USER" &>/dev/null; then
        useradd --system --home-dir "$APP_DIR" --shell /bin/bash "$APP_USER"
        log_success "User $APP_USER created"
    else
        log_warning "User $APP_USER already exists"
    fi
}

setup_directories() {
    log_info "Setting up directories..."
    
    # Create directories
    mkdir -p "$APP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "/etc/mefapex"
    
    # Set permissions
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$LOG_DIR"
    
    log_success "Directories created and permissions set"
}

setup_database() {
    log_info "Setting up PostgreSQL database..."
    
    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql -c "CREATE DATABASE mefapex_db;" || log_warning "Database might already exist"
    sudo -u postgres psql -c "CREATE USER mefapex_user WITH PASSWORD 'secure_password_change_this';" || log_warning "User might already exist"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mefapex_db TO mefapex_user;" || log_warning "Privileges might already be granted"
    
    log_success "Database setup completed"
}

setup_application() {
    log_info "Setting up application..."
    
    # Copy application files
    cp -r . "$APP_DIR/"
    
    # Create virtual environment
    sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
    
    # Install Python dependencies
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    
    # Create production .env file
    if [ ! -f "$APP_DIR/.env" ]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        
        # Generate secure secret key
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s/your-super-secure-secret-key-change-this-in-production-at-least-32-chars-long/$SECRET_KEY/g" "$APP_DIR/.env"
        sed -i "s/ENVIRONMENT=production/ENVIRONMENT=production/g" "$APP_DIR/.env"
        sed -i "s/DEBUG=False/DEBUG=False/g" "$APP_DIR/.env"
        sed -i "s|DATABASE_URL=sqlite:///./mefapex.db|DATABASE_URL=postgresql://mefapex_user:secure_password_change_this@localhost:5432/mefapex_db|g" "$APP_DIR/.env"
        
        log_warning "Please review and update $APP_DIR/.env with your production settings"
    fi
    
    # Set permissions
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chmod 600 "$APP_DIR/.env"  # Secure environment file
    
    log_success "Application setup completed"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=MEFAPEX Chatbot API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR $LOG_DIR /tmp

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$APP_NAME"
    
    log_success "Systemd service created"
}

setup_nginx() {
    log_info "Setting up Nginx..."
    
    cat > "$NGINX_CONFIG" << EOF
# MEFAPEX Chatbot Nginx Configuration
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Static files
    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
    
    # API endpoints
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Health check endpoint (bypass rate limiting)
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
    
    # Security - block common attack patterns
    location ~* \\.(php|asp|aspx|jsp)\$ {
        return 444;
    }
    
    location ~ /\\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

    # Enable site
    ln -sf "$NGINX_CONFIG" "/etc/nginx/sites-enabled/"
    rm -f "/etc/nginx/sites-enabled/default"
    
    # Test configuration
    nginx -t
    
    log_success "Nginx configuration created"
}

setup_ssl() {
    log_info "Setting up SSL certificate..."
    
    # Generate SSL certificate using Let's Encrypt
    certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN"
    
    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    log_success "SSL certificate configured"
}

setup_firewall() {
    log_info "Setting up firewall..."
    
    # Reset UFW
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 'Nginx Full'
    
    # Allow PostgreSQL from localhost only
    ufw allow from 127.0.0.1 to any port 5432
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured"
}

setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # Create monitoring script
    cat > "/usr/local/bin/mefapex-monitor.sh" << 'EOF'
#!/bin/bash

# MEFAPEX Monitoring Script
LOG_FILE="/var/log/mefapex/monitor.log"
APP_NAME="mefapex-chatbot"

# Check if service is running
if ! systemctl is-active --quiet "$APP_NAME"; then
    echo "$(date): Service $APP_NAME is not running, attempting restart" >> "$LOG_FILE"
    systemctl restart "$APP_NAME"
fi

# Check memory usage
MEMORY_USAGE=$(ps -p $(pgrep -f uvicorn) -o %mem --no-headers 2>/dev/null | awk '{print $1}' | head -1)
if [ ! -z "$MEMORY_USAGE" ] && (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "$(date): High memory usage: $MEMORY_USAGE%" >> "$LOG_FILE"
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): Low disk space: $DISK_USAGE% used" >> "$LOG_FILE"
fi

# Health check
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HEALTH_STATUS" != "200" ]; then
    echo "$(date): Health check failed with status: $HEALTH_STATUS" >> "$LOG_FILE"
fi
EOF

    chmod +x "/usr/local/bin/mefapex-monitor.sh"
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/mefapex-monitor.sh") | crontab -
    
    log_success "Monitoring setup completed"
}

setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/mefapex" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    copytruncate
    su $APP_USER $APP_USER
}
EOF

    log_success "Log rotation configured"
}

deploy() {
    log_info "Starting deployment process..."
    
    check_root
    install_dependencies
    create_user
    setup_directories
    setup_database
    setup_application
    create_systemd_service
    setup_nginx
    setup_firewall
    setup_monitoring
    setup_log_rotation
    
    # Start services
    systemctl restart "$APP_NAME"
    systemctl restart nginx
    
    # Wait for services to start
    sleep 5
    
    # Check service status
    if systemctl is-active --quiet "$APP_NAME"; then
        log_success "Application service is running"
    else
        log_error "Application service failed to start"
        systemctl status "$APP_NAME"
        exit 1
    fi
    
    if systemctl is-active --quiet nginx; then
        log_success "Nginx service is running"
    else
        log_error "Nginx service failed to start"
        systemctl status nginx
        exit 1
    fi
    
    log_success "Deployment completed successfully!"
    echo
    echo "🎉 MEFAPEX Chatbot is now running in production!"
    echo "📡 Application URL: http://$DOMAIN"
    echo "📊 Health Check: http://$DOMAIN/health"
    echo "📋 Logs: journalctl -u $APP_NAME -f"
    echo "🔧 Config: $APP_DIR/.env"
    echo
    echo "⚠️  Next steps:"
    echo "1. Update $APP_DIR/.env with your production settings"
    echo "2. Review firewall rules: ufw status"
    echo "3. Setup SSL: run setup_ssl function if domain is ready"
    echo "4. Configure monitoring alerts"
    echo "5. Setup backup procedures"
}

# Command line interface
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    ssl)
        setup_ssl
        ;;
    monitor)
        setup_monitoring
        ;;
    restart)
        systemctl restart "$APP_NAME"
        systemctl restart nginx
        log_success "Services restarted"
        ;;
    status)
        systemctl status "$APP_NAME"
        systemctl status nginx
        ;;
    logs)
        journalctl -u "$APP_NAME" -f
        ;;
    *)
        echo "Usage: $0 {deploy|ssl|monitor|restart|status|logs}"
        exit 1
        ;;
esac
