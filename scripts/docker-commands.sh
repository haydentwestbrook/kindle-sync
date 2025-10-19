#!/bin/bash
# Docker management commands for Kindle Scribe Sync System

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Function to start the container
start_container() {
    print_header "Starting Kindle Sync Container"
    docker-compose up -d
    print_status "Container started successfully"
    print_status "View logs with: docker-compose logs -f"
}

# Function to stop the container
stop_container() {
    print_header "Stopping Kindle Sync Container"
    docker-compose down
    print_status "Container stopped successfully"
}

# Function to restart the container
restart_container() {
    print_header "Restarting Kindle Sync Container"
    docker-compose restart
    print_status "Container restarted successfully"
}

# Function to view logs
view_logs() {
    print_header "Viewing Container Logs"
    docker-compose logs -f
}

# Function to view container status
view_status() {
    print_header "Container Status"
    docker-compose ps
    echo ""
    print_header "Container Health"
    docker-compose exec kindle-sync python -c "
import sys
sys.path.append('/app')
from src.sync_processor import SyncProcessor
from src.config import Config
try:
    config = Config('/app/config.yaml')
    processor = SyncProcessor(config)
    stats = processor.get_statistics()
    print('Processing Statistics:')
    for key, value in stats.items():
        print(f'  {key}: {value}')
except Exception as e:
    print(f'Error getting statistics: {e}')
"
}

# Function to rebuild the container
rebuild_container() {
    print_header "Rebuilding Container"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    print_status "Container rebuilt and started successfully"
}

# Function to update the container
update_container() {
    print_header "Updating Container"
    git pull
    docker-compose down
    docker-compose build
    docker-compose up -d
    print_status "Container updated successfully"
}

# Function to clean up
cleanup() {
    print_header "Cleaning Up"
    docker-compose down
    docker system prune -f
    print_status "Cleanup completed"
}

# Function to backup data
backup_data() {
    print_header "Backing Up Data"
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # Backup logs
    if [ -d "logs" ]; then
        cp -r logs "$BACKUP_DIR/"
        print_status "Logs backed up to $BACKUP_DIR"
    fi

    # Backup configuration
    if [ -f "config.yaml" ]; then
        cp config.yaml "$BACKUP_DIR/"
        print_status "Configuration backed up to $BACKUP_DIR"
    fi

    print_status "Backup completed: $BACKUP_DIR"
}

# Function to restore data
restore_data() {
    print_header "Available Backups"
    if [ -d "backups" ]; then
        ls -la backups/
        echo ""
        read -p "Enter backup directory name: " backup_name
        if [ -d "backups/$backup_name" ]; then
            print_status "Restoring from backup: $backup_name"
            cp -r "backups/$backup_name"/* ./
            print_status "Restore completed"
        else
            print_error "Backup directory not found: $backup_name"
        fi
    else
        print_error "No backups directory found"
    fi
}

# Function to show help
show_help() {
    echo "Kindle Scribe Sync Docker Management Commands"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       Start the container"
    echo "  stop        Stop the container"
    echo "  restart     Restart the container"
    echo "  logs        View container logs"
    echo "  status      View container status and statistics"
    echo "  rebuild     Rebuild the container from scratch"
    echo "  update      Update and restart the container"
    echo "  cleanup     Clean up Docker resources"
    echo "  backup      Backup data and configuration"
    echo "  restore     Restore from backup"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start    # Start the container"
    echo "  $0 logs     # View logs in real-time"
    echo "  $0 status   # Check container health and statistics"
}

# Main script logic
case "$1" in
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    logs)
        view_logs
        ;;
    status)
        view_status
        ;;
    rebuild)
        rebuild_container
        ;;
    update)
        update_container
        ;;
    cleanup)
        cleanup
        ;;
    backup)
        backup_data
        ;;
    restore)
        restore_data
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
