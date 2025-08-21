# Stripe Dashboard Docker Management
# Cross-platform deployment automation

.PHONY: help build deploy-prod deploy-dev stop logs clean backup health

# Default target
help:
	@echo "Stripe Dashboard Docker Management"
	@echo "=================================="
	@echo ""
	@echo "Available commands:"
	@echo "  help          Show this help message"
	@echo "  build         Build Docker images"
	@echo "  deploy-prod   Deploy to production (Dell Linux server)"
	@echo "  deploy-dev    Deploy development environment"
	@echo "  stop          Stop all services"
	@echo "  logs          View application logs"
	@echo "  logs-all      View all service logs"
	@echo "  health        Check application health"
	@echo "  backup        Run database backup"
	@echo "  clean         Clean up Docker resources"
	@echo "  status        Show service status"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy-prod    # Deploy to production"
	@echo "  make deploy-dev     # Start development environment"
	@echo "  make logs           # View application logs"
	@echo "  make health         # Check system health"

# Build Docker images
build:
	@echo "Building Docker images..."
	docker buildx build --platform linux/amd64 -f Dockerfile.multi-stage --target production -t stripe-dashboard:latest .

# Production deployment
deploy-prod:
	@echo "Deploying to production..."
	./scripts/deploy.sh production

# Development deployment
deploy-dev:
	@echo "Starting development environment..."
	./scripts/deploy.sh development

# Stop all services
stop:
	@echo "Stopping production services..."
	-docker-compose -f docker-compose.production.yml down
	@echo "Stopping development services..."
	-docker-compose -f docker-compose.dev.yml down

# View application logs
logs:
	@echo "Viewing application logs..."
	docker-compose -f docker-compose.production.yml logs -f stripe-dashboard

# View all service logs
logs-all:
	@echo "Viewing all service logs..."
	docker-compose -f docker-compose.production.yml logs -f

# Check application health
health:
	@echo "Checking application health..."
	@curl -s http://localhost/health | jq . || echo "Health check failed - is the service running?"

# Run database backup
backup:
	@echo "Running database backup..."
	docker-compose -f docker-compose.production.yml run --rm db-backup

# Show service status
status:
	@echo "Production services status:"
	@docker-compose -f docker-compose.production.yml ps
	@echo ""
	@echo "Development services status:"
	@docker-compose -f docker-compose.dev.yml ps

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	@echo "Removing stopped containers..."
	-docker container prune -f
	@echo "Removing unused images..."
	-docker image prune -f
	@echo "Removing unused volumes..."
	-docker volume prune -f
	@echo "Removing unused networks..."
	-docker network prune -f
	@echo "Cleanup completed"

# Development specific commands
dev-logs:
	@echo "Viewing development logs..."
	docker-compose -f docker-compose.dev.yml logs -f

dev-shell:
	@echo "Opening development shell..."
	docker-compose -f docker-compose.dev.yml exec stripe-dashboard-dev bash

# Production specific commands
prod-shell:
	@echo "Opening production shell..."
	docker-compose -f docker-compose.production.yml exec stripe-dashboard bash

prod-db:
	@echo "Opening production database shell..."
	docker-compose -f docker-compose.production.yml exec stripe-dashboard \
		sqlite3 /var/lib/stripe_dashboard/production.db

# Backup and restore commands
backup-list:
	@echo "Available backups:"
	@docker-compose -f docker-compose.production.yml exec stripe-dashboard \
		ls -la /var/backups/stripe_dashboard/database/

backup-report:
	@echo "Latest backup report:"
	@docker-compose -f docker-compose.production.yml exec stripe-dashboard \
		cat /var/backups/stripe_dashboard/latest_backup_report.txt

# Security and maintenance
update:
	@echo "Updating application..."
	git pull origin main
	make build
	make deploy-prod
	make health

security-scan:
	@echo "Running security scan..."
	docker run --rm -v $(PWD):/app \
		aquasec/trivy fs --security-checks vuln /app

# Platform-specific builds
build-amd64:
	@echo "Building for AMD64 (Dell servers)..."
	docker buildx build --platform linux/amd64 -f Dockerfile.multi-stage --target production -t stripe-dashboard:amd64 .

build-arm64:
	@echo "Building for ARM64 (M1/M2 Macs)..."
	docker buildx build --platform linux/arm64 -f Dockerfile.multi-stage --target production -t stripe-dashboard:arm64 .

# Multi-platform build
build-multiplatform:
	@echo "Building for multiple platforms..."
	docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.multi-stage --target production -t stripe-dashboard:latest .

# Configuration validation
validate-config:
	@echo "Validating Docker Compose configuration..."
	docker-compose -f docker-compose.production.yml config
	docker-compose -f docker-compose.dev.yml config

# Environment setup
setup-env:
	@echo "Setting up environment files..."
	@if [ ! -f .env.docker ]; then \
		echo "Creating .env.docker from template..."; \
		cp .env.docker.example .env.docker 2>/dev/null || echo "Please create .env.docker manually"; \
	fi
	@echo "Please edit .env.docker with your production values"

# SSL certificate setup
setup-ssl:
	@echo "Setting up SSL certificates..."
	@mkdir -p ssl
	@if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then \
		echo "Creating self-signed SSL certificates..."; \
		openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem \
			-days 365 -nodes -subj "/C=HK/ST=Hong Kong/L=Hong Kong/O=Stripe Dashboard/CN=localhost"; \
		echo "SSL certificates created in ssl/ directory"; \
	else \
		echo "SSL certificates already exist"; \
	fi

# Complete setup for new deployment
setup: setup-env setup-ssl
	@echo "Environment setup completed"
	@echo "Next steps:"
	@echo "1. Edit .env.docker with your configuration"
	@echo "2. Run 'make deploy-prod' for production"
	@echo "3. Run 'make deploy-dev' for development"

# Performance monitoring
monitor:
	@echo "System performance monitoring..."
	@echo "Docker stats:"
	docker stats --no-stream
	@echo ""
	@echo "Service health:"
	@make health

# Troubleshooting
troubleshoot:
	@echo "Troubleshooting information..."
	@echo "================================"
	@echo "Service status:"
	@make status
	@echo ""
	@echo "Recent logs (last 50 lines):"
	@docker-compose -f docker-compose.production.yml logs --tail=50
	@echo ""
	@echo "System resources:"
	@docker system df
	@echo ""
	@echo "Health check:"
	@make health