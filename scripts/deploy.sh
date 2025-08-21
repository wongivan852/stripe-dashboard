#!/bin/bash
# Deployment Script for Stripe Dashboard on Dell Linux Server
# Cross-platform deployment automation

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_MODE="${1:-production}"
BUILD_PLATFORM="${2:-linux/amd64}"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking deployment prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if .env.docker exists
    if [ ! -f "$PROJECT_DIR/.env.docker" ]; then
        warning ".env.docker not found. Please configure it with your production values"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Function to prepare directories
prepare_directories() {
    log "Preparing directories for deployment..."
    
    # Create necessary directories on host system
    sudo mkdir -p /var/lib/docker/volumes/stripe_dashboard_db
    sudo mkdir -p /var/lib/docker/volumes/stripe_dashboard_csv
    sudo mkdir -p /var/lib/docker/volumes/stripe_dashboard_uploads
    sudo mkdir -p /var/log/stripe_dashboard
    sudo mkdir -p /var/backups/stripe_dashboard
    
    # Set proper permissions
    sudo chown -R $USER:$USER /var/lib/docker/volumes/stripe_dashboard_*
    sudo chown -R $USER:$USER /var/log/stripe_dashboard
    sudo chown -R $USER:$USER /var/backups/stripe_dashboard
    
    success "Directories prepared"
}

# Function to build and deploy
deploy_application() {
    log "Deploying Stripe Dashboard in $DEPLOYMENT_MODE mode..."
    
    cd "$PROJECT_DIR"
    
    case $DEPLOYMENT_MODE in
        "production")
            log "Building production containers..."
            
            # Build multi-platform image
            docker buildx build --platform "$BUILD_PLATFORM" \
                -f Dockerfile.multi-stage \
                --target production \
                -t stripe-dashboard:latest .
            
            # Deploy with production compose
            docker-compose -f docker-compose.production.yml --env-file .env.docker up -d
            ;;
            
        "development")
            log "Starting development environment..."
            
            docker-compose -f docker-compose.dev.yml up -d
            ;;
            
        *)
            error "Unknown deployment mode: $DEPLOYMENT_MODE"
            error "Available modes: production, development"
            exit 1
            ;;
    esac
    
    success "Deployment completed for $DEPLOYMENT_MODE mode"
}

# Function to run health checks
run_health_checks() {
    log "Running health checks..."
    
    # Wait for services to start
    sleep 30
    
    # Check if main application is responding
    for i in {1..12}; do
        if curl -f http://localhost/health &> /dev/null; then
            success "Application health check passed"
            break
        else
            if [ $i -eq 12 ]; then
                warning "Application health check timeout - check logs manually"
                break
            fi
            log "Waiting for application to start... (attempt $i/12)"
            sleep 10
        fi
    done
    
    success "Health checks completed"
}

# Function to display deployment information
show_deployment_info() {
    log "Deployment Information"
    echo "========================================"
    echo "Mode: $DEPLOYMENT_MODE"
    echo "Platform: $BUILD_PLATFORM"
    echo "Project Directory: $PROJECT_DIR"
    echo ""
    echo "Access URLs:"
    echo "- Application: https://localhost (or your server IP)"
    echo "- Health Check: http://localhost/health"
    
    if [ "$DEPLOYMENT_MODE" = "development" ]; then
        echo "- Database Admin: http://localhost:8080"
        echo "- Development Server: http://localhost:5000"
    fi
    
    echo ""
    echo "Useful Commands:"
    echo "- View logs: docker-compose -f docker-compose.$DEPLOYMENT_MODE.yml logs -f"
    echo "- Stop services: docker-compose -f docker-compose.$DEPLOYMENT_MODE.yml down"
    echo "- Update application: $0 $DEPLOYMENT_MODE"
    echo "========================================"
}

# Main deployment function
main() {
    log "Starting Stripe Dashboard deployment..."
    log "Mode: $DEPLOYMENT_MODE | Platform: $BUILD_PLATFORM"
    
    check_prerequisites
    
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        prepare_directories
    fi
    
    deploy_application
    
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        run_health_checks
    fi
    
    show_deployment_info
    
    success "Stripe Dashboard deployment completed successfully!"
}

# Script usage information
usage() {
    echo "Usage: $0 [MODE] [PLATFORM]"
    echo ""
    echo "MODE (optional, default: production):"
    echo "  production  - Full production deployment with Nginx, SSL, monitoring"
    echo "  development - Development environment with hot-reload"
    echo ""
    echo "PLATFORM (optional, default: linux/amd64):"
    echo "  linux/amd64 - Intel/AMD 64-bit (Dell servers)"
    echo "  linux/arm64 - ARM 64-bit (M1/M2 Macs, ARM servers)"
    echo ""
    echo "Examples:"
    echo "  $0                          # Production deployment on linux/amd64"
    echo "  $0 development              # Development environment"
    echo "  $0 production linux/arm64   # Production on ARM platform"
    echo ""
}

# Handle command line arguments
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi

# Run main function
main "$@"