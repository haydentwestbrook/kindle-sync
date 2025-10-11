#!/bin/bash
# Configuration-based deployment script for Raspberry Pi

set -e

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

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
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

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] <pi-ip-address>

Deploy Kindle Scribe Sync System to Raspberry Pi using config.yaml

Options:
    --config FILE        Use specific config file (default: config.yaml)
    --dry-run            Show what would be deployed without actually deploying
    --help               Show this help message

Examples:
    $0 192.168.1.100
    $0 --config my-config.yaml 192.168.1.100
    $0 --dry-run 192.168.1.100

EOF
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
CONFIG_FILE="$PROJECT_DIR/config.yaml"
DRY_RUN=false
PI_IP=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            PI_IP="$1"
            shift
            ;;
    esac
done

# Check if IP address is provided
if [ -z "$PI_IP" ]; then
    print_error "Raspberry Pi IP address is required"
    show_usage
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    print_status "Run './scripts/setup-env.sh --create-config' to create it"
    exit 1
fi

# Function to get config value
get_config() {
    local key="$1"
    local default="$2"
    
    if command -v yq >/dev/null 2>&1; then
        yq eval "$key" "$CONFIG_FILE" 2>/dev/null || echo "$default"
    else
        print_warning "yq not found, using default value for $key"
        echo "$default"
    fi
}

# Load configuration
print_header "Loading Configuration"
print_status "Using config file: $CONFIG_FILE"

PI_USER=$(get_config '.deployment.pi.user' 'pi')
PI_PORT=$(get_config '.deployment.pi.port' '22')
PI_SSH_KEY=$(get_config '.deployment.pi.ssh_key' '')
PI_DIRECTORY=$(get_config '.deployment.pi.directory' '/home/pi/kindle-sync')
SKIP_DOCKER=$(get_config '.deployment.options.skip_docker' 'false')
SKIP_BUILD=$(get_config '.deployment.options.skip_build' 'false')
SKIP_CONFIG=$(get_config '.deployment.options.skip_config' 'false')

print_status "Pi User: $PI_USER"
print_status "SSH Port: $PI_PORT"
print_status "SSH Key: ${PI_SSH_KEY:-'None (using password)'}"
print_status "Target Directory: $PI_DIRECTORY"
print_status "Skip Docker: $SKIP_DOCKER"
print_status "Skip Build: $SKIP_BUILD"
print_status "Skip Config: $SKIP_CONFIG"

# Build SSH command
SSH_CMD="ssh"
if [ -n "$PI_SSH_KEY" ]; then
    SSH_CMD="$SSH_CMD -i $PI_SSH_KEY"
fi
SSH_CMD="$SSH_CMD -p $PI_PORT $PI_USER@$PI_IP"

# Function to execute command on Pi
run_on_pi() {
    local cmd="$1"
    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would execute on Pi: $cmd"
    else
        print_status "Executing on Pi: $cmd"
        $SSH_CMD "$cmd"
    fi
}

# Function to copy files to Pi
copy_to_pi() {
    local src="$1"
    local dst="$2"
    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would copy $src to Pi:$dst"
    else
        print_status "Copying $src to Pi:$dst"
        
        local scp_cmd="scp -r"
        if [ -n "$PI_SSH_KEY" ]; then
            scp_cmd="$scp_cmd -i $PI_SSH_KEY"
        fi
        scp_cmd="$scp_cmd -P $PI_PORT $src $PI_USER@$PI_IP:$dst"
        
        eval $scp_cmd
    fi
}

# Function to check if command exists on Pi
check_command_on_pi() {
    local cmd="$1"
    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would check if $cmd exists on Pi"
        return 0
    else
        run_on_pi "command -v $cmd >/dev/null 2>&1"
    fi
}

# Main deployment function
deploy_to_pi() {
    print_header "Deploying Kindle Scribe Sync to Raspberry Pi"
    print_status "Target: $PI_USER@$PI_IP:$PI_DIRECTORY"
    
    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN MODE - No actual changes will be made"
    fi
    
    # Test SSH connection
    print_status "Testing SSH connection..."
    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would test SSH connection"
    else
        if ! run_on_pi "echo 'SSH connection successful'" >/dev/null 2>&1; then
            print_error "Cannot connect to Raspberry Pi. Please check:"
            print_error "  - IP address: $PI_IP"
            print_error "  - SSH port: $PI_PORT"
            print_error "  - Username: $PI_USER"
            print_error "  - SSH key: $PI_SSH_KEY"
            exit 1
        fi
        print_success "SSH connection successful"
    fi
    
    # Update system
    print_header "Updating Raspberry Pi System"
    run_on_pi "sudo apt update && sudo apt upgrade -y"
    
    # Install Git if not present
    if ! check_command_on_pi "git"; then
        print_status "Installing Git..."
        run_on_pi "sudo apt install git -y"
    fi
    
    # Clone or update repository
    print_header "Setting up Repository"
    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would check if repository exists and update/clone"
    else
        if run_on_pi "[ -d '$PI_DIRECTORY' ]"; then
            print_status "Repository exists, updating..."
            run_on_pi "cd $PI_DIRECTORY && git pull"
        else
            print_status "Cloning repository..."
            run_on_pi "git clone https://github.com/haydentwestbrook/kindle-sync.git $PI_DIRECTORY"
        fi
    fi
    
    # Install Docker if not skipping
    if [ "$SKIP_DOCKER" = false ]; then
        print_header "Installing Docker"
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would check if Docker is installed and install if needed"
        else
            if ! check_command_on_pi "docker"; then
                print_status "Installing Docker..."
                run_on_pi "cd $PI_DIRECTORY && chmod +x scripts/docker-setup.sh && ./scripts/docker-setup.sh"
            else
                print_status "Docker already installed"
            fi
        fi
    fi
    
    # Build Docker image if not skipping
    if [ "$SKIP_BUILD" = false ]; then
        print_header "Building Docker Image"
        run_on_pi "cd $PI_DIRECTORY && docker-compose build"
    fi
    
    # Set up configuration if not skipping
    if [ "$SKIP_CONFIG" = false ]; then
        print_header "Setting up Configuration"
        
        # Copy config file to Pi
        copy_to_pi "$CONFIG_FILE" "$PI_DIRECTORY/config.yaml"
        
        # Create .env if it doesn't exist
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would create .env file on Pi"
        else
            if ! run_on_pi "[ -f '$PI_DIRECTORY/.env' ]"; then
                print_status "Creating environment file..."
                run_on_pi "cd $PI_DIRECTORY && ./scripts/setup-env.sh --setup-env"
            fi
        fi
        
        # Create directories
        print_status "Creating necessary directories..."
        run_on_pi "mkdir -p $PI_DIRECTORY/logs $PI_DIRECTORY/backups $PI_DIRECTORY/temp"
        
        # Get Obsidian path from config
        OBSIDIAN_PATH=$(get_config '.obsidian.vault_path' '/home/pi/obsidian-vault')
        run_on_pi "mkdir -p $OBSIDIAN_PATH"
        run_on_pi "mkdir -p $OBSIDIAN_PATH/'Kindle Sync'"
        run_on_pi "mkdir -p $OBSIDIAN_PATH/Templates"
        run_on_pi "mkdir -p $OBSIDIAN_PATH/Backups"
        
        # Set permissions
        run_on_pi "sudo chown -R $PI_USER:$PI_USER $PI_DIRECTORY"
        run_on_pi "sudo chown -R $PI_USER:$PI_USER $OBSIDIAN_PATH"
    fi
    
    # Make scripts executable
    print_status "Setting up scripts..."
    run_on_pi "cd $PI_DIRECTORY && chmod +x scripts/*.sh"
    
    print_header "Deployment Complete!"
    print_status "Next steps:"
    print_status "1. SSH into your Pi: ssh $PI_USER@$PI_IP"
    print_status "2. Edit configuration: nano $PI_DIRECTORY/config.yaml"
    print_status "3. Start the service: cd $PI_DIRECTORY && ./scripts/docker-commands.sh start"
    print_status "4. View logs: ./scripts/docker-commands.sh logs"
    print_status ""
    print_status "For detailed instructions, see: docs/RASPBERRY_PI_DEPLOYMENT.md"
}

# Run deployment
deploy_to_pi
