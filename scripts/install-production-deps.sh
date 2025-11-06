#!/bin/bash
# Install Production Dependencies for Stripe Dashboard
# Dell Server Setup

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

log "Installing production dependencies for Stripe Dashboard..."

# Update system
log "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Python and essential packages
log "Installing Python and essential packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    curl \
    wget \
    sqlite3 \
    libsqlite3-dev

# Install web server components
log "Installing web server components..."
apt-get install -y \
    nginx \
    supervisor \
    gunicorn

# Install monitoring and logging tools
log "Installing monitoring and logging tools..."
apt-get install -y \
    logrotate \
    rsyslog \
    htop \
    iotop \
    netstat-nat \
    fail2ban

# Install security tools
log "Installing security tools..."
apt-get install -y \
    ufw \
    unattended-upgrades \
    apt-listchanges

# Configure automatic security updates
log "Configuring automatic security updates..."
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/20auto-upgrades
echo 'Unattended-Upgrade::Remove-Unused-Dependencies "true";' >> /etc/apt/apt.conf.d/20auto-upgrades

# Install additional Python packages system-wide
log "Installing additional Python packages..."
pip3 install --upgrade pip
pip3 install gunicorn psutil

# Create system directories
log "Creating system directories..."
mkdir -p /var/log/stripe-dashboard
mkdir -p /var/lib/stripe-dashboard
mkdir -p /var/backups/stripe-dashboard
mkdir -p /etc/stripe-dashboard

# Set up log rotation for system logs
log "Setting up system log rotation..."
cat > /etc/logrotate.d/stripe-dashboard-system << 'EOF'
/var/log/stripe-dashboard/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
EOF

# Configure fail2ban for basic protection
log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
EOF

systemctl enable fail2ban
systemctl start fail2ban

# Configure basic firewall
log "Setting up basic firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https

# Enable firewall (will be configured further during deployment)
echo "y" | ufw enable

# Set up system monitoring
log "Setting up system monitoring..."
cat > /usr/local/bin/system-health-check << 'EOF'
#!/bin/bash
# Basic system health check

echo "=== System Health Check ===$(date)==="
echo "Disk Usage:"
df -h

echo -e "\nMemory Usage:"
free -h

echo -e "\nCPU Load:"
uptime

echo -e "\nTop Processes:"
ps aux --sort=-%cpu | head -10

echo -e "\nNetwork Connections:"
netstat -tulpn | grep :80
netstat -tulpn | grep :5000

echo -e "\nSystem Services:"
systemctl status nginx
systemctl status stripe-dashboard 2>/dev/null || echo "Stripe Dashboard not yet installed"
EOF

chmod +x /usr/local/bin/system-health-check

# Add health check to crontab (run every hour)
echo "0 * * * * /usr/local/bin/system-health-check >> /var/log/system-health.log 2>&1" | crontab -

# Configure system limits
log "Configuring system limits..."
cat >> /etc/security/limits.conf << 'EOF'
# Stripe Dashboard limits
www-data soft nofile 65536
www-data hard nofile 65536
www-data soft nproc 4096
www-data hard nproc 4096
EOF

# Configure kernel parameters
log "Configuring kernel parameters..."
cat >> /etc/sysctl.conf << 'EOF'
# Network optimizations for web server
net.core.somaxconn = 65536
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65536
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 120
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3
EOF

sysctl -p

# Install and configure NTP for time synchronization
log "Setting up time synchronization..."
apt-get install -y ntp
systemctl enable ntp
systemctl start ntp

# Create maintenance scripts
log "Creating maintenance scripts..."

# Cleanup script
cat > /usr/local/bin/cleanup-stripe-dashboard << 'EOF'
#!/bin/bash
# Cleanup script for Stripe Dashboard

echo "Starting cleanup process..."

# Clean old log files
find /var/log/stripe-dashboard -name "*.log.*" -mtime +30 -delete
echo "Cleaned old log files"

# Clean old backups
find /var/backups/stripe-dashboard -name "stripe-dashboard-*" -type d -mtime +30 -exec rm -rf {} \;
echo "Cleaned old backups"

# Clean temporary files
find /tmp -name "*stripe*" -mtime +1 -delete 2>/dev/null || true
echo "Cleaned temporary files"

# Clean package cache
apt-get autoremove -y
apt-get autoclean
echo "Cleaned package cache"

echo "Cleanup completed"
EOF

chmod +x /usr/local/bin/cleanup-stripe-dashboard

# Schedule cleanup weekly
echo "0 3 * * 0 /usr/local/bin/cleanup-stripe-dashboard >> /var/log/cleanup.log 2>&1" | crontab -

# Create startup check script
cat > /usr/local/bin/startup-check-stripe-dashboard << 'EOF'
#!/bin/bash
# Startup check script

echo "Performing startup checks..."

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "WARNING: Disk usage is at ${DISK_USAGE}%"
fi

# Check memory
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -gt 90 ]; then
    echo "WARNING: Memory usage is at ${MEMORY_USAGE}%"
fi

# Check critical services
for service in nginx fail2ban; do
    if ! systemctl is-active --quiet $service; then
        echo "WARNING: $service is not running"
        systemctl start $service
    fi
done

echo "Startup checks completed"
EOF

chmod +x /usr/local/bin/startup-check-stripe-dashboard

# Add startup check to crontab (run at boot)
echo "@reboot /usr/local/bin/startup-check-stripe-dashboard >> /var/log/startup-check.log 2>&1" | crontab -

# Clean up
log "Cleaning up..."
apt-get autoremove -y
apt-get autoclean

log "Production dependencies installation completed!"
log "System is ready for Stripe Dashboard deployment"

# Display summary
echo ""
echo "=== Installation Summary ==="
echo "✅ Python 3 and development tools installed"
echo "✅ Nginx web server installed"
echo "✅ Security tools (fail2ban, ufw) configured"
echo "✅ Monitoring and maintenance scripts created"
echo "✅ System optimization applied"
echo "✅ Automatic security updates enabled"
echo ""
echo "Next steps:"
echo "1. Run the main deployment script: sudo ./scripts/deploy.sh"
echo "2. Configure environment variables in /opt/stripe-dashboard/.env"
echo "3. Test the application"
echo ""
echo "Monitoring commands:"
echo "- System health: /usr/local/bin/system-health-check"
echo "- Cleanup: /usr/local/bin/cleanup-stripe-dashboard"
echo "- Startup check: /usr/local/bin/startup-check-stripe-dashboard"