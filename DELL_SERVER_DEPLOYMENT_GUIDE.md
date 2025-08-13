# Dell Server Deployment Guide - Stripe Dashboard

## Overview

This guide provides complete instructions for deploying the Stripe Dashboard application on a Dell server for production use with both intranet and internet access.

## Prerequisites

- Dell server with Ubuntu 20.04 LTS or newer
- Root access to the server
- Network connectivity (intranet and internet)
- At least 4GB RAM and 20GB storage
- Git installed on the server

## Quick Start

For immediate deployment, follow these steps:

```bash
# 1. Clone or copy the application to the server
git clone <repository-url> /tmp/stripe-dashboard
cd /tmp/stripe-dashboard

# 2. Install production dependencies
sudo ./scripts/install-production-deps.sh

# 3. Deploy the application
sudo ./scripts/deploy.sh

# 4. Configure environment (edit as needed)
sudo nano /opt/stripe-dashboard/.env

# 5. Restart services
sudo systemctl restart stripe-dashboard
sudo systemctl restart nginx
```

The application will be available at `http://server-ip`

## Detailed Deployment Steps

### Step 1: System Preparation

1. **Update the system:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Git (if not already installed):**
   ```bash
   sudo apt install git -y
   ```

3. **Clone the repository:**
   ```bash
   git clone <repository-url> /tmp/stripe-dashboard
   cd /tmp/stripe-dashboard
   ```

### Step 2: Install Dependencies

Run the production dependencies installer:

```bash
sudo ./scripts/install-production-deps.sh
```

This script will:
- Install Python 3, pip, and development tools
- Install Nginx web server
- Configure security tools (fail2ban, UFW firewall)
- Set up monitoring and maintenance scripts
- Configure system optimizations
- Enable automatic security updates

### Step 3: Deploy Application

Run the main deployment script:

```bash
sudo ./scripts/deploy.sh
```

This script will:
- Create application user and directories
- Deploy application files to `/opt/stripe-dashboard`
- Set up Python virtual environment
- Configure systemd service
- Set up Nginx reverse proxy
- Initialize the database
- Configure logging and log rotation
- Set up automated backups
- Start all services

### Step 4: Configure Environment

Edit the environment configuration:

```bash
sudo nano /opt/stripe-dashboard/.env
```

Key settings to configure:

```bash
# Generate a strong secret key
SECRET_KEY=your_generated_secret_key_here

# Database path (default is fine for single server)
DATABASE_URL=sqlite:///var/lib/stripe-dashboard/production.db

# Company information
COMPANY_NAME=Your Company Name

# Network settings (defaults are usually fine)
HOST=0.0.0.0
PORT=5000
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 5: Restart Services

After configuration changes:

```bash
sudo systemctl restart stripe-dashboard
sudo systemctl restart nginx
```

## Network Configuration

### Firewall Settings

The deployment automatically configures UFW firewall with:

- **Port 22** (SSH) - Open
- **Port 80** (HTTP) - Open  
- **Port 443** (HTTPS) - Open
- **Port 5000** - Only accessible from private networks (192.168.x.x, 10.x.x.x, 172.16-31.x.x)

### Intranet Access

The application is accessible on the local network at:
- `http://server-ip` (HTTP)
- `http://server-hostname` (if DNS is configured)

### Internet Access

For internet connectivity (for updates and external services):
- Outbound connections are allowed
- Inbound connections are restricted by firewall rules
- Consider setting up HTTPS with SSL certificates for internet exposure

### Network Interface Binding

The application binds to `0.0.0.0:5000` internally and is proxied through Nginx on port 80.

## File Structure

After deployment, the following structure is created:

```
/opt/stripe-dashboard/          # Application root
├── app/                        # Flask application
├── config/                     # Configuration files
├── venv/                       # Python virtual environment
├── wsgi.py                     # WSGI entry point
├── gunicorn.conf.py           # Gunicorn configuration
├── .env                       # Environment variables
└── requirements.txt           # Python dependencies

/var/log/stripe-dashboard/      # Application logs
├── stripe_dashboard.log       # Main application log
├── stripe_dashboard_errors.log # Error log
├── stripe_dashboard_access.log # Access log
├── access.log                 # Gunicorn access log
└── error.log                  # Gunicorn error log

/var/lib/stripe-dashboard/      # Application data
└── production.db              # SQLite database

/var/backups/stripe-dashboard/  # Automated backups
└── backup-YYYYMMDD-HHMMSS/    # Daily backup directories

/etc/systemd/system/           # System service
└── stripe-dashboard.service   # Systemd service file

/etc/nginx/sites-available/    # Nginx configuration
└── stripe-dashboard           # Nginx site configuration
```

## Service Management

### Systemd Commands

```bash
# Check service status
sudo systemctl status stripe-dashboard

# Start/stop/restart service
sudo systemctl start stripe-dashboard
sudo systemctl stop stripe-dashboard
sudo systemctl restart stripe-dashboard

# View logs
sudo journalctl -u stripe-dashboard -f

# Enable/disable service on boot
sudo systemctl enable stripe-dashboard
sudo systemctl disable stripe-dashboard
```

### Nginx Commands

```bash
# Check Nginx status
sudo systemctl status nginx

# Test Nginx configuration
sudo nginx -t

# Reload Nginx configuration
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx
```

## Monitoring and Maintenance

### Log Files

Monitor application logs:

```bash
# Application logs
sudo tail -f /var/log/stripe-dashboard/stripe_dashboard.log

# Error logs
sudo tail -f /var/log/stripe-dashboard/stripe_dashboard_errors.log

# Access logs
sudo tail -f /var/log/stripe-dashboard/access.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Health Checks

System health check:
```bash
sudo /usr/local/bin/system-health-check
```

Application health check:
```bash
curl http://localhost/health
```

### Automated Maintenance

The deployment sets up automated maintenance:

- **Daily backups** at 2:00 AM
- **Log rotation** daily, keeping 30 days
- **System cleanup** weekly on Sundays
- **Health checks** every hour

### Manual Backup

Create immediate backup:
```bash
sudo /usr/local/bin/backup-stripe-dashboard
```

### Manual Cleanup

Clean old files:
```bash
sudo /usr/local/bin/cleanup-stripe-dashboard
```

## Security Features

### Implemented Security

- **Firewall (UFW)** - Restricts network access
- **Fail2ban** - Prevents brute force attacks
- **Security headers** - Prevents common web attacks
- **Rate limiting** - Prevents abuse
- **Process isolation** - Runs as dedicated user
- **File permissions** - Restrictive file access
- **Automatic updates** - Security patches applied automatically

### Security Headers

The application automatically adds these security headers:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy: <restrictive policy>`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Rate Limiting

Built-in rate limiting:
- 100 requests per minute per IP address
- Burst capacity of 20 requests
- Automatic blocking of excessive requests

## Troubleshooting

### Common Issues

1. **Service won't start:**
   ```bash
   sudo journalctl -u stripe-dashboard -n 50
   sudo systemctl status stripe-dashboard
   ```

2. **Database errors:**
   ```bash
   # Check database permissions
   ls -la /var/lib/stripe-dashboard/
   
   # Recreate database
   sudo -u www-data /opt/stripe-dashboard/venv/bin/python /opt/stripe-dashboard/wsgi.py
   ```

3. **Permission errors:**
   ```bash
   # Fix file ownership
   sudo chown -R www-data:www-data /opt/stripe-dashboard
   sudo chown -R www-data:www-data /var/lib/stripe-dashboard
   sudo chown -R www-data:www-data /var/log/stripe-dashboard
   ```

4. **Network access issues:**
   ```bash
   # Check firewall status
   sudo ufw status
   
   # Check if application is listening
   sudo netstat -tulpn | grep :5000
   sudo netstat -tulpn | grep :80
   ```

5. **High memory usage:**
   ```bash
   # Restart application
   sudo systemctl restart stripe-dashboard
   
   # Check memory usage
   free -h
   ps aux --sort=-%mem | head -10
   ```

### Log Analysis

Common log locations for troubleshooting:

```bash
# Application startup issues
sudo journalctl -u stripe-dashboard --since "1 hour ago"

# Database connection issues
sudo grep -i "database" /var/log/stripe-dashboard/*.log

# Permission issues
sudo grep -i "permission\|denied" /var/log/stripe-dashboard/*.log

# Network issues
sudo grep -i "connection\|timeout" /var/log/stripe-dashboard/*.log
```

## Performance Tuning

### Gunicorn Workers

Adjust worker count in `/opt/stripe-dashboard/gunicorn.conf.py`:

```python
# Default: CPU cores * 2 + 1
workers = 4  # Adjust based on server resources
```

### Database Optimization

For better performance with larger datasets:

1. **Consider PostgreSQL:**
   ```bash
   # Install PostgreSQL
   sudo apt install postgresql postgresql-contrib
   
   # Update DATABASE_URL in .env
   DATABASE_URL=postgresql://username:password@localhost/stripe_dashboard
   ```

2. **Database maintenance:**
   ```bash
   # SQLite optimization (if using SQLite)
   sudo -u www-data sqlite3 /var/lib/stripe-dashboard/production.db "VACUUM;"
   sudo -u www-data sqlite3 /var/lib/stripe-dashboard/production.db "ANALYZE;"
   ```

### System Resources

Monitor and adjust system resources:

```bash
# Monitor resource usage
htop
iotop

# Adjust system limits if needed
sudo nano /etc/security/limits.conf
```

## Updates and Maintenance

### Application Updates

To update the application:

1. **Backup current installation:**
   ```bash
   sudo /usr/local/bin/backup-stripe-dashboard
   ```

2. **Update code:**
   ```bash
   cd /tmp
   git clone <repository-url> stripe-dashboard-new
   cd stripe-dashboard-new
   sudo ./scripts/deploy.sh
   ```

3. **Test application:**
   ```bash
   curl http://localhost/health
   ```

### System Updates

The system is configured for automatic security updates. For manual updates:

```bash
sudo apt update && sudo apt upgrade -y
sudo systemctl restart stripe-dashboard
```

## SSL/HTTPS Configuration (Optional)

To enable HTTPS for internet access:

1. **Install Certbot:**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. **Obtain SSL certificate:**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

3. **Auto-renewal:**
   ```bash
   sudo systemctl enable certbot.timer
   ```

## Backup and Recovery

### Backup Strategy

Automated backups include:
- Application code and configuration
- Database files
- Log files

### Recovery Process

To restore from backup:

1. **Stop services:**
   ```bash
   sudo systemctl stop stripe-dashboard nginx
   ```

2. **Restore files:**
   ```bash
   cd /var/backups/stripe-dashboard/backup-YYYYMMDD-HHMMSS
   sudo tar -xzf application.tar.gz -C /opt/
   sudo cp database.db /var/lib/stripe-dashboard/production.db
   ```

3. **Fix permissions:**
   ```bash
   sudo chown -R www-data:www-data /opt/stripe-dashboard
   sudo chown -R www-data:www-data /var/lib/stripe-dashboard
   ```

4. **Start services:**
   ```bash
   sudo systemctl start stripe-dashboard nginx
   ```

## Support and Maintenance

### Regular Maintenance Tasks

- **Weekly:** Review logs for errors or security issues
- **Monthly:** Check disk space and clean old files
- **Quarterly:** Review and update security configurations
- **Annually:** Update SSL certificates (if using HTTPS)

### Monitoring Checklist

- [ ] Application is responding (http://server-ip/health)
- [ ] Services are running (systemctl status)
- [ ] Disk space is sufficient (df -h)
- [ ] Memory usage is reasonable (free -h)
- [ ] Logs are clean of errors
- [ ] Backups are being created
- [ ] Security updates are applied

### Contact Information

For technical support:
- Check application logs first
- Review this deployment guide
- Consult the application documentation
- Contact system administrator

---

## Quick Reference

### Essential Commands

```bash
# Service management
sudo systemctl status stripe-dashboard
sudo systemctl restart stripe-dashboard

# View logs
sudo tail -f /var/log/stripe-dashboard/stripe_dashboard.log

# Health check
curl http://localhost/health

# Backup
sudo /usr/local/bin/backup-stripe-dashboard

# System health
sudo /usr/local/bin/system-health-check
```

### File Locations

- **Application:** `/opt/stripe-dashboard/`
- **Logs:** `/var/log/stripe-dashboard/`
- **Database:** `/var/lib/stripe-dashboard/production.db`
- **Configuration:** `/opt/stripe-dashboard/.env`
- **Backups:** `/var/backups/stripe-dashboard/`

This deployment guide ensures a secure, monitored, and maintainable installation of the Stripe Dashboard on your Dell server.