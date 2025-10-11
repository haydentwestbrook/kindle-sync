#!/bin/bash
# Automated deployment script for Raspberry Pi

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

Deploy Kindle Scribe Sync System to Raspberry Pi

Options:
    -u, --user USER         SSH username (default: pi)
    -k, --key KEYFILE       SSH private key file
    -p, --port PORT         SSH port (default: 22)
    -d, --directory DIR     Target directory on Pi (default: /home/pi/kindle-sync)
    --config FILE           Use config.yaml for deployment settings
    --skip-docker           Skip Docker installation
    --skip-build            Skip Docker image build
    --skip-config           Skip configuration setup
    -h, --help              Show this help message

Examples:
    $0 192.168.1.100
    $0 -u pi -k ~/.ssh/id_rsa 192.168.1.100
    $0 --config config.yaml 192.168.1.100
    $0 --skip-docker 192.168.1.100

EOF
}

# Default values
PI_USER="pi"
PI_PORT="22"
PI_DIR="/home/pi/kindle-sync"
SSH_KEY=""
CONFIG_FILE=""
SKIP_DOCKER=false
SKIP_BUILD=false
SKIP_CONFIG=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--user)
            PI_USER="$2"
            shift 2
            ;;
        -k|--key)
            SSH_KEY="$2"
            shift 2
            ;;
        -p|--port)
            PI_PORT="$2"
            shift 2
            ;;
        -d|--directory)
            PI_DIR="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-config)
            SKIP_CONFIG=true
            shift
            ;;
        -h|--help)
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

# Function to get config value
get_config() {
    local key="$1"
    local default="$2"
    
    if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ] && command -v yq >/dev/null 2>&1; then
        yq eval "$key" "$CONFIG_FILE" 2>/dev/null || echo "$default"
    else
        echo "$default"
    fi
}

# Load configuration from file if specified
if [ -n "$CONFIG_FILE" ]; then
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    print_status "Loading configuration from: $CONFIG_FILE"
    
    # Override command line arguments with config file values
    PI_USER=$(get_config '.deployment.pi.user' "$PI_USER")
    PI_PORT=$(get_config '.deployment.pi.port' "$PI_PORT")
    PI_DIR=$(get_config '.deployment.pi.directory' "$PI_DIR")
    SSH_KEY=$(get_config '.deployment.pi.ssh_key' "$SSH_KEY")
    SKIP_DOCKER=$(get_config '.deployment.options.skip_docker' "$SKIP_DOCKER")
    SKIP_BUILD=$(get_config '.deployment.options.skip_build' "$SKIP_BUILD")
    SKIP_CONFIG=$(get_config '.deployment.options.skip_config' "$SKIP_CONFIG")
    
    print_status "Configuration loaded:"
    print_status "  User: $PI_USER"
    print_status "  Port: $PI_PORT"
    print_status "  Directory: $PI_DIR"
    print_status "  SSH Key: ${SSH_KEY:-'None'}"
    print_status "  Skip Docker: $SKIP_DOCKER"
    print_status "  Skip Build: $SKIP_BUILD"
    print_status "  Skip Config: $SKIP_CONFIG"
fi

# Build SSH command
SSH_CMD="ssh"
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="$SSH_CMD -i $SSH_KEY"
fi
SSH_CMD="$SSH_CMD -p $PI_PORT $PI_USER@$PI_IP"

# Function to execute command on Pi
run_on_pi() {
    local cmd="$1"
    print_status "Executing on Pi: $cmd"
    $SSH_CMD "$cmd"
}

# Function to copy files to Pi
copy_to_pi() {
    local src="$1"
    local dst="$2"
    print_status "Copying $src to Pi:$dst"
    
    local scp_cmd="scp -r"
    if [ -n "$SSH_KEY" ]; then
        scp_cmd="$scp_cmd -i $SSH_KEY"
    fi
    scp_cmd="$scp_cmd -P $PI_PORT $src $PI_USER@$PI_IP:$dst"
    
    eval $scp_cmd
}

# Function to check if command exists on Pi
check_command_on_pi() {
    local cmd="$1"
    run_on_pi "command -v $cmd >/dev/null 2>&1"
}

# Main deployment function
deploy_to_pi() {
    print_header "Deploying Kindle Scribe Sync to Raspberry Pi"
    print_status "Target: $PI_USER@$PI_IP:$PI_DIR"
    
    # Test SSH connection
    print_status "Testing SSH connection..."
    if ! run_on_pi "echo 'SSH connection successful'" >/dev/null 2>&1; then
        print_error "Cannot connect to Raspberry Pi. Please check:"
        print_error "  - IP address: $PI_IP"
        print_error "  - SSH port: $PI_PORT"
        print_error "  - Username: $PI_USER"
        print_error "  - SSH key: $SSH_KEY"
        exit 1
    fi
    print_status "SSH connection successful"
    
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
    if run_on_pi "[ -d '$PI_DIR' ]"; then
        print_status "Repository exists, updating..."
        run_on_pi "cd $PI_DIR && git pull"
    else
        print_status "Cloning repository..."
        run_on_pi "git clone https://github.com/haydentwestbrook/kindle-sync.git $PI_DIR"
    fi
    
    # Install Docker if not skipping
    if [ "$SKIP_DOCKER" = false ]; then
        print_header "Installing Docker"
        if ! check_command_on_pi "docker"; then
            print_status "Installing Docker..."
            run_on_pi "cd $PI_DIR && chmod +x scripts/docker-setup.sh && ./scripts/docker-setup.sh"
        else
            print_status "Docker already installed"
        fi
    fi
    
    # Build Docker image if not skipping
    if [ "$SKIP_BUILD" = false ]; then
        print_header "Building Docker Image"
        run_on_pi "cd $PI_DIR && docker-compose build"
    fi
    
    # Set up configuration if not skipping
    if [ "$SKIP_CONFIG" = false ]; then
        print_header "Setting up Configuration"
        
        # Create config if it doesn't exist
        if ! run_on_pi "[ -f '$PI_DIR/config.yaml' ]"; then
            print_status "Creating configuration file..."
            run_on_pi "cd $PI_DIR && cp config.yaml.example config.yaml"
        fi
        
        # Create .env if it doesn't exist
        if ! run_on_pi "[ -f '$PI_DIR/.env' ]"; then
            print_status "Creating environment file..."
            run_on_pi "cd $PI_DIR && cat > .env << 'EOF'
# Docker environment variables
TZ=America/New_York
OBSIDIAN_VAULT_PATH=/home/$PI_USER/obsidian-vault
KINDLE_EMAIL=your-kindle@kindle.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EOF"
        fi
        
        # Create directories
        print_status "Creating necessary directories..."
        run_on_pi "mkdir -p $PI_DIR/logs $PI_DIR/backups $PI_DIR/temp"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault/'Kindle Sync'"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault/Templates"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault/Backups"
        
        # Set permissions
        run_on_pi "sudo chown -R $PI_USER:$PI_USER $PI_DIR"
        run_on_pi "sudo chown -R $PI_USER:$PI_USER /home/$PI_USER/obsidian-vault"
    fi
    
    # Make scripts executable
    print_status "Setting up scripts..."
    run_on_pi "cd $PI_DIR && chmod +x scripts/*.sh"
    
    print_header "Deployment Complete!"
    print_status "Next steps:"
    print_status "1. SSH into your Pi: ssh $PI_USER@$PI_IP"
    print_status "2. Edit configuration: nano $PI_DIR/config.yaml"
    print_status "3. Edit environment: nano $PI_DIR/.env"
    print_status "4. Start the service: cd $PI_DIR && ./scripts/docker-commands.sh start"
    print_status "5. View logs: ./scripts/docker-commands.sh logs"
    print_status ""
    print_status "For detailed instructions, see: docs/RASPBERRY_PI_DEPLOYMENT.md"
}

# Run deployment
deploy_to_pi
