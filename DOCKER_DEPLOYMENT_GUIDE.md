# Stripe Dashboard - Docker Deployment Guide

Complete Docker setup for deploying the Stripe Dashboard application on Dell Linux servers with cross-platform compatibility.

## 🚀 Quick Start

### 1. Configure Environment Variables

```bash
# Copy and configure the Docker environment file
cp .env.docker .env.production
nano .env.production

# Essential configurations to update:
# - SECRET_KEY: Generate a strong secret key
# - STRIPE_ACCOUNT_*_KEY: Your Stripe API keys
# - REDIS_PASSWORD: Set a strong Redis password
```

### 2. Deploy to Production (Dell Linux Server)

```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Deploy to production
./scripts/deploy.sh production

# Or deploy for ARM-based systems (M1/M2 Macs)
./scripts/deploy.sh production linux/arm64
```

### 3. Deploy for Development (macOS)

```bash
# Start development environment with hot-reload
./scripts/deploy.sh development
```

## 📋 Architecture Overview

### Multi-Stage Docker Build

The `Dockerfile.multi-stage` provides:
- **Builder Stage**: Development dependencies and build tools
- **Production Stage**: Minimal runtime environment with security hardening
- **Cross-Platform Support**: Works on both Intel/AMD (Dell servers) and ARM (M1/M2 Macs)

### Production Services

1. **Stripe Dashboard App**: Main Flask application
2. **Nginx**: Reverse proxy with SSL termination and security headers
3. **Redis**: Caching and session management
4. **Database Backup**: Automated SQLite backup service
5. **Monitoring**: Node exporter for system metrics

## 🔧 Configuration Files

### Docker Compose Files

| File | Purpose | Environment |
|------|---------|-------------|
| `docker-compose.production.yml` | Full production deployment | Dell Linux Server |
| `docker-compose.dev.yml` | Development with hot-reload | macOS Development |

### Environment Configuration

| File | Purpose |
|------|---------|
| `.env.docker` | Production environment template |
| `.env.production` | Your production configuration |

### Infrastructure Configuration

| File | Purpose |
|------|---------|
| `nginx/nginx.conf` | Nginx reverse proxy configuration |
| `scripts/backup.sh` | Database backup automation |
| `scripts/deploy.sh` | Cross-platform deployment automation |

## 🏗️ Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Dell Linux Server                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    Nginx    │  │   Redis     │  │  Monitoring │         │
│  │  (Port 80)  │  │ (Caching)   │  │ (Metrics)   │         │
│  │ (Port 443)  │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Stripe Dashboard App                       │ │
│  │                 (Port 5000)                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│  │  │  Database   │  │  CSV Data   │  │   Backups   │     │ │
│  │  │  (SQLite)   │  │ (Uploads)   │  │ (Automated) │     │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Security Features

### Network Security
- HTTPS with SSL/TLS encryption
- Rate limiting on API endpoints
- Security headers (HSTS, CSP, etc.)
- Internal Docker network isolation

### Application Security
- Non-root container execution
- Read-only file systems where possible
- Environment variable secrets management
- Input validation and sanitization

### Infrastructure Security
- Automated security updates
- Resource limits and quotas
- Health checks and monitoring
- Backup encryption and retention

## 📊 Monitoring & Health Checks

### Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Comprehensive system health |
| `/health/simple` | Basic availability check |
| `/health/database` | Database connectivity |
| `/health/version` | Application version info |

### Monitoring Features

1. **Application Metrics**: Response times, error rates, throughput
2. **System Metrics**: CPU, memory, disk usage
3. **Database Metrics**: Connection pool, query performance
4. **Infrastructure Metrics**: Container health, network performance

## 💾 Data Management

### Persistent Volumes

| Volume | Purpose | Mount Point |
|--------|---------|-------------|
| `stripe_db_data` | SQLite database | `/var/lib/stripe_dashboard` |
| `stripe_csv_data` | CSV uploads | `/app/csv_data` |
| `stripe_uploads` | File uploads | `/app/uploads` |
| `stripe_logs` | Application logs | `/app/logs` |
| `stripe_backups` | Database backups | `/var/backups/stripe_dashboard` |

### Backup Strategy

- **Automated Daily Backups**: 2:00 AM daily via cron
- **Retention Policy**: 30 days (configurable)
- **Backup Types**: Database snapshots, CSV data archives
- **Compression**: Gzip compression for space efficiency
- **Verification**: Automated backup integrity checks

## 🚀 Deployment Commands

### Production Deployment

```bash
# Full production deployment on Dell server
./scripts/deploy.sh production

# View application logs
docker-compose -f docker-compose.production.yml logs -f stripe-dashboard

# View all service logs
docker-compose -f docker-compose.production.yml logs -f

# Check service status
docker-compose -f docker-compose.production.yml ps

# Stop services
docker-compose -f docker-compose.production.yml down

# Update application (rebuild and restart)
./scripts/deploy.sh production
```

### Development Environment

```bash
# Start development environment
./scripts/deploy.sh development

# Access development services
# - Main app: http://localhost:5000
# - Database admin: http://localhost:8080
# - Redis: localhost:6379

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

### Maintenance Commands

```bash
# Manual database backup
docker-compose -f docker-compose.production.yml run --rm db-backup

# View backup reports
docker-compose -f docker-compose.production.yml exec stripe-dashboard \
  cat /var/backups/stripe_dashboard/latest_backup_report.txt

# Database shell access
docker-compose -f docker-compose.production.yml exec stripe-dashboard \
  sqlite3 /var/lib/stripe_dashboard/production.db

# Application shell access
docker-compose -f docker-compose.production.yml exec stripe-dashboard bash

# View system resources
docker-compose -f docker-compose.production.yml exec stripe-dashboard \
  python -c "
from app.health import health_bp
from flask import Flask
app = Flask(__name__)
app.register_blueprint(health_bp)
with app.test_client() as client:
    response = client.get('/health')
    print(response.get_json())
"
```

## 🔧 Customization

### Environment Variables

Key environment variables in `.env.docker`:

```bash
# Security
SECRET_KEY=your_production_secret_key_here
REDIS_PASSWORD=your_redis_password_here

# Application
FLASK_ENV=production
DATABASE_URL=sqlite:///var/lib/stripe_dashboard/production.db

# Stripe API
STRIPE_ACCOUNT_1_KEY=sk_live_your_stripe_key_1
STRIPE_ACCOUNT_2_KEY=sk_live_your_stripe_key_2
STRIPE_ACCOUNT_3_KEY=sk_live_your_stripe_key_3

# Performance
SQLALCHEMY_POOL_SIZE=10
CACHE_TYPE=redis

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true

# Backup
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
```

### Resource Limits

Adjust resource limits in `docker-compose.production.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Adjust based on Dell server specs
      memory: 1G       # Adjust based on available RAM
    reservations:
      cpus: '0.5'
      memory: 256M
```

### SSL Certificates

For production deployment with custom SSL certificates:

```bash
# Place your SSL certificates in the ssl/ directory
mkdir -p ssl
cp your_certificate.pem ssl/cert.pem
cp your_private_key.pem ssl/key.pem

# Or use Let's Encrypt (recommended)
# Update nginx/nginx.conf with your domain
# Configure Let's Encrypt certificates
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check if ports are in use
   sudo netstat -tlnp | grep :80
   sudo netstat -tlnp | grep :443
   
   # Stop conflicting services
   sudo systemctl stop apache2  # If Apache is running
   sudo systemctl stop nginx    # If system Nginx is running
   ```

2. **Permission Issues**
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER /var/lib/docker/volumes/stripe_dashboard_*
   sudo chown -R $USER:$USER /var/log/stripe_dashboard
   sudo chown -R $USER:$USER /var/backups/stripe_dashboard
   ```

3. **Database Issues**
   ```bash
   # Check database file
   ls -la /var/lib/docker/volumes/stripe_dashboard_db/
   
   # Restore from backup
   docker-compose -f docker-compose.production.yml exec stripe-dashboard \
     cp /var/backups/stripe_dashboard/database/latest_backup.db.gz \
        /tmp/restore.db.gz
   ```

4. **Memory Issues**
   ```bash
   # Check container memory usage
   docker stats
   
   # Increase memory limits in docker-compose.production.yml
   ```

### Health Check Debugging

```bash
# Check comprehensive health status
curl -s http://localhost/health | jq .

# Check simple health status
curl -s http://localhost/health/simple

# Check database health
curl -s http://localhost/health/database

# Check application version
curl -s http://localhost/health/version
```

### Log Analysis

```bash
# Application logs
docker-compose -f docker-compose.production.yml logs stripe-dashboard

# Nginx logs
docker-compose -f docker-compose.production.yml logs nginx

# System logs
journalctl -u docker

# Real-time monitoring
docker-compose -f docker-compose.production.yml logs -f --tail=100
```

## 📈 Performance Optimization

### For Dell Server Hardware

1. **CPU Optimization**
   - Set appropriate CPU limits based on server cores
   - Use CPU affinity for better performance
   - Monitor CPU usage with health checks

2. **Memory Optimization**
   - Configure SQLAlchemy connection pooling
   - Set appropriate memory limits
   - Use Redis for caching

3. **Disk I/O Optimization**
   - Use SSD storage for database
   - Regular database VACUUM operations
   - Compress log files and backups

4. **Network Optimization**
   - Configure Nginx worker processes
   - Enable gzip compression
   - Use HTTP/2 for better performance

### Scaling Considerations

For high-traffic scenarios:

1. **Horizontal Scaling**: Deploy multiple app containers behind load balancer
2. **Database Scaling**: Consider PostgreSQL for better concurrent access
3. **Caching**: Implement Redis cluster for distributed caching
4. **CDN**: Use CDN for static assets

## 🔄 Updates and Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review application logs and performance metrics
2. **Monthly**: Update Docker images and security patches
3. **Quarterly**: Review backup integrity and disaster recovery procedures
4. **Annually**: Security audit and penetration testing

### Update Procedure

```bash
# Pull latest code
git pull origin main

# Rebuild and deploy
./scripts/deploy.sh production

# Verify deployment
curl -s http://localhost/health | jq .status
```

## 📞 Support

### Getting Help

1. **Health Check Endpoints**: Monitor system status
2. **Log Analysis**: Check application and system logs
3. **Performance Metrics**: Use monitoring dashboards
4. **Documentation**: Refer to this guide and inline comments

### Emergency Procedures

1. **Service Outage**: Restart services using deployment script
2. **Data Corruption**: Restore from automated backups
3. **Security Incident**: Stop services and review logs
4. **Performance Issues**: Check resource usage and scale accordingly

---

This deployment guide provides comprehensive instructions for deploying the Stripe Dashboard application in a production environment optimized for Dell Linux servers while maintaining cross-platform compatibility with macOS development environments.