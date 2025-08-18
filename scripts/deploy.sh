#!/bin/bash
# Stripe Dashboard Deployment Script for Dell Server
# Production deployment automation

set -euo pipefail

# Configuration
APP_NAME="stripe-dashboard"
APP_USER="www-data"
APP_GROUP="www-data"
APP_DIR="/opt/stripe-dashboard"
BACKUP_DIR="/var/backups/stripe-dashboard"
LOG_DIR="/var/log/stripe-dashboard"
DATA_DIR="/var/lib/stripe-dashboard"
SERVICE_NAME="stripe-dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Create application user
create_app_user() {
    log "Creating application user..."
    
    if ! id "$APP_USER" &>/dev/null; then
        useradd --system --home-dir "$APP_DIR" --shell /bin/bash "$APP_USER"
        log "User $APP_USER created"
    else
        info "User $APP_USER already exists"
    fi
}

# Create directories
create_directories() {
    log "Creating application directories..."
    
    # Create main directories
    mkdir -p "$APP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "/var/run/stripe-dashboard"
    
    # Set ownership
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
    chown -R "$APP_USER:$APP_GROUP" "$LOG_DIR"
    chown -R "$APP_USER:$APP_GROUP" "$DATA_DIR"
    chown -R "$APP_USER:$APP_GROUP" "$BACKUP_DIR"
    chown -R "$APP_USER:$APP_GROUP" "/var/run/stripe-dashboard"
    
    # Set permissions
    chmod 755 "$APP_DIR"
    chmod 755 "$LOG_DIR"
    chmod 750 "$DATA_DIR"
    chmod 750 "$BACKUP_DIR"
    chmod 755 "/var/run/stripe-dashboard"
    
    log "Directories created and configured"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package list
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        sqlite3 \
        logrotate \
        cron \
        supervisor \
        fail2ban \
        ufw
    
    # Install Gunicorn system-wide (using apt instead of pip)
    apt-get install -y python3-gunicorn || true
    
    log "System dependencies installed"
}

# Deploy application
deploy_application() {
    log "Deploying application..."
    
    # Stop service if running
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl stop "$SERVICE_NAME"
        warn "Stopped existing service"
    fi
    
    # Backup existing installation
    if [ -d "$APP_DIR/app" ]; then
        backup_name="backup-$(date +%Y%m%d-%H%M%S)"
        cp -r "$APP_DIR" "$BACKUP_DIR/$backup_name"
        log "Created backup: $backup_name"
    fi
    
    # Copy application files
    if [ -d "./app" ]; then
        cp -r ./app "$APP_DIR/"
        cp -r ./config "$APP_DIR/"
        cp wsgi.py "$APP_DIR/"
        cp gunicorn.conf.py "$APP_DIR/"
        cp requirements.txt "$APP_DIR/"
        
        # Copy environment template
        if [ -f ".env.production" ]; then
            cp .env.production "$APP_DIR/.env.template"
        fi
        
        log "Application files copied"
    else
        error "Application files not found in current directory"
        exit 1
    fi
    
    # Set ownership
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
    
    log "Application deployed"
}

# Setup Python environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    
    # Create virtual environment
    sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
    
    # Upgrade pip
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
    
    # Install requirements
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    
    # Install additional production packages
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install gunicorn psutil
    
    log "Python environment configured"
}

# Configure environment
configure_environment() {
    log "Configuring environment..."
    
    # Generate secret key if .env doesn't exist
    if [ ! -f "$APP_DIR/.env" ]; then
        if [ -f "$APP_DIR/.env.template" ]; then
            cp "$APP_DIR/.env.template" "$APP_DIR/.env"
        else
            cat > "$APP_DIR/.env" << EOF
# Production Environment Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=sqlite:///$DATA_DIR/production.db
HOST=0.0.0.0
PORT=5000
LOG_LEVEL=INFO
EOF
        fi
        
        # Set secure permissions
        chmod 600 "$APP_DIR/.env"
        chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
        
        warn "Environment file created. Please review and update $APP_DIR/.env"
    else
        info "Environment file already exists"
    fi
    
    log "Environment configured"
}

# Setup systemd service
setup_systemd() {
    log "Setting up systemd service..."
    
    # Copy service file
    if [ -f "./systemd/stripe-dashboard.service" ]; then
        cp "./systemd/stripe-dashboard.service" "/etc/systemd/system/"
        
        # Reload systemd
        systemctl daemon-reload
        systemctl enable "$SERVICE_NAME"
        
        log "Systemd service configured"
    else
        warn "Systemd service file not found, creating basic service"
        
        cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Stripe Dashboard Web Application
After=network.target

[Service]
Type=exec
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py wsgi:application
Restart=always
RestartSec=5
EnvironmentFile=$APP_DIR/.env

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable "$SERVICE_NAME"
        log "Basic systemd service created"
    fi
}

# Configure nginx
configure_nginx() {
    log "Configuring Nginx..."
    
    # First, add rate limiting to the http block in main nginx.conf
    if ! grep -q "limit_req_zone.*zone=app" /etc/nginx/nginx.conf; then
        sed -i '/http {/a\\tlimit_req_zone $binary_remote_addr zone=app:10m rate=10r/m;' /etc/nginx/nginx.conf
    fi
    
    # Create nginx configuration
    cat > "/etc/nginx/sites-available/$APP_NAME" << EOF
server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        limit_req zone=app burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static {
        alias $APP_DIR/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
    
    # Enable site
    ln -sf "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/"
    
    # Remove default site
    rm -f "/etc/nginx/sites-enabled/default"
    
    # Test configuration
    nginx -t
    
    # Restart nginx
    systemctl restart nginx
    systemctl enable nginx
    
    log "Nginx configured"
}

# Setup logging
setup_logging() {
    log "Setting up log rotation..."
    
    # Create logrotate configuration
    cat > "/etc/logrotate.d/$APP_NAME" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_GROUP
    postrotate
        systemctl reload $SERVICE_NAME
    endscript
}
EOF
    
    log "Log rotation configured"
}

# Setup firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Reset UFW
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow http
    ufw allow https
    
    # Allow specific network access (adjust as needed)
    ufw allow from 192.168.0.0/16 to any port 5000
    
    # Enable firewall
    ufw --force enable
    
    log "Firewall configured"
}

# Initialize database
initialize_database() {
    log "Initializing database..."
    
    cd "$APP_DIR"
    
    # Run database initialization
    sudo -u "$APP_USER" FLASK_APP=wsgi.py "$APP_DIR/venv/bin/python" -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created')
"
    
    log "Database initialized"
}

# Create backup script
create_backup_script() {
    log "Creating backup script..."
    
    cat > "/usr/local/bin/backup-stripe-dashboard" << 'EOF'
#!/bin/bash
# Automated backup script for Stripe Dashboard

BACKUP_DIR="/var/backups/stripe-dashboard"
APP_DIR="/opt/stripe-dashboard"
DATA_DIR="/var/lib/stripe-dashboard"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="stripe-dashboard-$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup application
tar -czf "$BACKUP_DIR/$BACKUP_NAME/application.tar.gz" -C /opt stripe-dashboard

# Backup database
cp "$DATA_DIR/production.db" "$BACKUP_DIR/$BACKUP_NAME/database.db" 2>/dev/null || true

# Backup logs
tar -czf "$BACKUP_DIR/$BACKUP_NAME/logs.tar.gz" -C /var/log stripe-dashboard

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "stripe-dashboard-*" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_NAME"
EOF
    
    chmod +x "/usr/local/bin/backup-stripe-dashboard"
    
    # Add to crontab
    echo "0 2 * * * /usr/local/bin/backup-stripe-dashboard" | crontab -
    
    log "Backup script created and scheduled"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start and enable services
    systemctl start "$SERVICE_NAME"
    systemctl start nginx
    
    # Check status
    sleep 5
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "Stripe Dashboard service started successfully"
    else
        error "Failed to start Stripe Dashboard service"
        systemctl status "$SERVICE_NAME"
        exit 1
    fi
    
    if systemctl is-active --quiet nginx; then
        log "Nginx started successfully"
    else
        error "Failed to start Nginx"
        systemctl status nginx
        exit 1
    fi
}

# Main deployment function
main() {
    log "Starting Stripe Dashboard deployment..."
    
    check_root
    create_app_user
    create_directories
    install_dependencies
    deploy_application
    setup_python_env
    configure_environment
    setup_systemd
    configure_nginx
    setup_logging
    setup_firewall
    initialize_database
    create_backup_script
    start_services
    
    log "Deployment completed successfully!"
    info "Application is now available at: http://$(hostname -I | awk '{print $1}')"
    info "Logs are available in: $LOG_DIR"
    info "Configuration: $APP_DIR/.env"
    warn "Please review and update the environment configuration in $APP_DIR/.env"
}

# Run main function
main "$@"