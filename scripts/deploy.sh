#!/bin/bash

# Kindle Sync Deployment Script
# This script automates the deployment of the Kindle Sync application

set -euo pipefail

# Configuration
APP_NAME="kindle-sync"
DOCKER_IMAGE="kindle-sync:latest"
CONTAINER_NAME="kindle-sync-app"
CONFIG_FILE="config.yaml"
BACKUP_DIR="backups"
LOG_DIR="logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if config file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file $CONFIG_FILE not found."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "data"
    
    log_success "Directories created"
}

# Backup existing data
backup_data() {
    log_info "Creating backup of existing data..."
    
    BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_PATH="$BACKUP_DIR/backup_$BACKUP_TIMESTAMP"
    
    mkdir -p "$BACKUP_PATH"
    
    # Backup database if it exists
    if [[ -f "data/kindle_sync.db" ]]; then
        cp "data/kindle_sync.db" "$BACKUP_PATH/"
        log_info "Database backed up"
    fi
    
    # Backup logs
    if [[ -d "$LOG_DIR" ]]; then
        cp -r "$LOG_DIR" "$BACKUP_PATH/"
        log_info "Logs backed up"
    fi
    
    # Backup configuration
    cp "$CONFIG_FILE" "$BACKUP_PATH/"
    log_info "Configuration backed up"
    
    log_success "Backup created at $BACKUP_PATH"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    docker build -t "$DOCKER_IMAGE" .
    
    if [[ $? -eq 0 ]]; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

# Stop existing container
stop_container() {
    log_info "Stopping existing container..."
    
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        docker stop "$CONTAINER_NAME"
        log_info "Container stopped"
    fi
    
    if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
        docker rm "$CONTAINER_NAME"
        log_info "Container removed"
    fi
}

# Deploy new container
deploy_container() {
    log_info "Deploying new container..."
    
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p 8080:8080 \
        -v "$(pwd)/$CONFIG_FILE:/app/config.yaml:ro" \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/$LOG_DIR:/app/logs" \
        -e TZ=UTC \
        "$DOCKER_IMAGE"
    
    if [[ $? -eq 0 ]]; then
        log_success "Container deployed successfully"
    else
        log_error "Failed to deploy container"
        exit 1
    fi
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Wait for container to start
    sleep 10
    
    # Check if container is running
    if ! docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_error "Container is not running"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
    
    # Check health endpoint
    for i in {1..30}; do
        if curl -f http://localhost:8080/health &> /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        log_info "Waiting for service to be ready... ($i/30)"
        sleep 2
    done
    
    log_error "Health check failed"
    docker logs "$CONTAINER_NAME"
    exit 1
}

# Cleanup old images
cleanup_images() {
    log_info "Cleaning up old Docker images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions of the app image (keep last 3)
    docker images "$APP_NAME" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | \
        tail -n +4 | \
        awk '{print $1}' | \
        xargs -r docker rmi
    
    log_success "Cleanup completed"
}

# Show deployment status
show_status() {
    log_info "Deployment Status:"
    echo "=================="
    
    # Container status
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_success "Container: Running"
        echo "Container ID: $(docker ps -q -f name="$CONTAINER_NAME")"
        echo "Image: $(docker inspect --format='{{.Config.Image}}' "$CONTAINER_NAME")"
        echo "Status: $(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME")"
        echo "Started: $(docker inspect --format='{{.State.StartedAt}}' "$CONTAINER_NAME")"
    else
        log_error "Container: Not running"
    fi
    
    # Service endpoints
    echo ""
    echo "Service Endpoints:"
    echo "- Health Check: http://localhost:8080/health"
    echo "- Metrics: http://localhost:8080/metrics"
    echo "- Status: http://localhost:8080/status"
    
    # Logs location
    echo ""
    echo "Logs:"
    echo "- Container logs: docker logs $CONTAINER_NAME"
    echo "- Application logs: $LOG_DIR/"
}

# Main deployment function
deploy() {
    log_info "Starting deployment of $APP_NAME..."
    
    check_root
    check_prerequisites
    create_directories
    backup_data
    build_image
    stop_container
    deploy_container
    health_check
    cleanup_images
    show_status
    
    log_success "Deployment completed successfully!"
}

# Rollback function
rollback() {
    log_info "Starting rollback..."
    
    # Stop current container
    stop_container
    
    # Find latest backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/backup_* 2>/dev/null | head -n1)
    
    if [[ -z "$LATEST_BACKUP" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    log_info "Rolling back to backup: $LATEST_BACKUP"
    
    # Restore data
    if [[ -f "$LATEST_BACKUP/kindle_sync.db" ]]; then
        cp "$LATEST_BACKUP/kindle_sync.db" "data/"
    fi
    
    if [[ -d "$LATEST_BACKUP/logs" ]]; then
        cp -r "$LATEST_BACKUP/logs"/* "$LOG_DIR/"
    fi
    
    if [[ -f "$LATEST_BACKUP/$CONFIG_FILE" ]]; then
        cp "$LATEST_BACKUP/$CONFIG_FILE" ./
    fi
    
    # Deploy previous version
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p 8080:8080 \
        -v "$(pwd)/$CONFIG_FILE:/app/config.yaml:ro" \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/$LOG_DIR:/app/logs" \
        -e TZ=UTC \
        "$DOCKER_IMAGE"
    
    log_success "Rollback completed"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  deploy     Deploy the application (default)"
    echo "  rollback   Rollback to previous version"
    echo "  status     Show deployment status"
    echo "  logs       Show application logs"
    echo "  stop       Stop the application"
    echo "  start      Start the application"
    echo "  restart    Restart the application"
    echo "  -h, --help Show this help message"
    echo ""
}

# Handle command line arguments
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    rollback)
        rollback
        ;;
    status)
        show_status
        ;;
    logs)
        docker logs -f "$CONTAINER_NAME"
        ;;
    stop)
        stop_container
        log_success "Application stopped"
        ;;
    start)
        if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
            docker start "$CONTAINER_NAME"
            log_success "Application started"
        else
            log_error "Container not found. Run deploy first."
            exit 1
        fi
        ;;
    restart)
        stop_container
        sleep 2
        if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
            docker start "$CONTAINER_NAME"
            log_success "Application restarted"
        else
            log_error "Container not found. Run deploy first."
            exit 1
        fi
        ;;
    -h|--help)
        usage
        ;;
    *)
        log_error "Unknown option: $1"
        usage
        exit 1
        ;;
esac
