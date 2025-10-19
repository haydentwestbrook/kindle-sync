#!/bin/bash
# Enhanced deployment script with comprehensive logging for Raspberry Pi

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]${NC} $1" | tee -a deployment.log
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]${NC} $1" | tee -a deployment.log
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $1" | tee -a deployment.log
}

log_debug() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')] [DEBUG]${NC} $1" | tee -a deployment.log
}

log_step() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] [STEP]${NC} $1" | tee -a deployment.log
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS]${NC} $1" | tee -a deployment.log
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] <pi-ip-address>

Deploy Kindle Scribe Sync System to Raspberry Pi with comprehensive logging

Options:
    -u, --user USER         SSH username (default: pi)
    -k, --key KEYFILE       SSH private key file
    -p, --port PORT         SSH port (default: 22)
    -d, --directory DIR     Target directory on Pi (default: /home/pi/kindle-sync)
    --skip-docker           Skip Docker installation
    --skip-build            Skip Docker image build
    --skip-config           Skip configuration setup
    --verbose               Enable verbose logging
    -h, --help              Show this help message

Examples:
    $0 192.168.1.100
    $0 -u hayden -k ~/.ssh/id_rsa 192.168.0.12
    $0 --verbose 192.168.1.100

EOF
}

# Default values
PI_USER="pi"
PI_PORT="22"
PI_DIR="/home/pi/kindle-sync"
SSH_KEY=""
SKIP_DOCKER=false
SKIP_BUILD=false
SKIP_CONFIG=false
VERBOSE=false

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
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
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
    log_error "Raspberry Pi IP address is required"
    show_usage
    exit 1
fi

# Initialize log file
echo "=== Kindle Sync Deployment Log ===" > deployment.log
echo "Started at: $(date)" >> deployment.log
echo "Target: $PI_USER@$PI_IP:$PI_DIR" >> deployment.log
echo "=================================" >> deployment.log

# Build SSH command
SSH_CMD="ssh"
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="$SSH_CMD -i $SSH_KEY"
fi
SSH_CMD="$SSH_CMD -p $PI_PORT $PI_USER@$PI_IP"

# Function to execute command on Pi with logging
run_on_pi() {
    local cmd="$1"
    local description="$2"

    if [ -n "$description" ]; then
        log_step "Executing: $description"
    else
        log_step "Executing: $cmd"
    fi

    log_debug "SSH Command: $SSH_CMD \"$cmd\""

    if [ "$VERBOSE" = true ]; then
        log_debug "Command output:"
        if $SSH_CMD "$cmd" 2>&1 | tee -a deployment.log; then
            log_success "Command completed successfully"
        else
            log_error "Command failed with exit code $?"
            return 1
        fi
    else
        if $SSH_CMD "$cmd" >> deployment.log 2>&1; then
            log_success "Command completed successfully"
        else
            log_error "Command failed with exit code $?"
            return 1
        fi
    fi
}

# Function to copy files to Pi with logging
copy_to_pi() {
    local src="$1"
    local dst="$2"
    local description="$3"

    if [ -n "$description" ]; then
        log_step "Copying: $description"
    else
        log_step "Copying $src to Pi:$dst"
    fi

    local scp_cmd="scp -r"
    if [ -n "$SSH_KEY" ]; then
        scp_cmd="$scp_cmd -i $SSH_KEY"
    fi
    scp_cmd="$scp_cmd -P $PI_PORT $src $PI_USER@$PI_IP:$dst"

    log_debug "SCP Command: $scp_cmd"

    if eval $scp_cmd >> deployment.log 2>&1; then
        log_success "File copy completed successfully"
    else
        log_error "File copy failed"
        return 1
    fi
}

# Function to check if command exists on Pi
check_command_on_pi() {
    local cmd="$1"
    log_debug "Checking if $cmd exists on Pi"
    run_on_pi "command -v $cmd >/dev/null 2>&1" "Check for $cmd"
}

# Function to wait for network connectivity
wait_for_network() {
    log_step "Checking network connectivity to Pi"
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log_debug "Ping attempt $attempt/$max_attempts"
        if ping -c 1 -W 5 "$PI_IP" >/dev/null 2>&1; then
            log_success "Network connectivity confirmed"
            return 0
        else
            log_warn "Ping attempt $attempt failed, retrying in 5 seconds..."
            sleep 5
            ((attempt++))
        fi
    done

    log_error "Failed to establish network connectivity after $max_attempts attempts"
    return 1
}

# Function to check SSH connectivity
check_ssh_connectivity() {
    log_step "Testing SSH connection to Pi"
    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log_debug "SSH connection attempt $attempt/$max_attempts"
        if run_on_pi "echo 'SSH connection successful'" "Test SSH connection" >/dev/null 2>&1; then
            log_success "SSH connection established"
            return 0
        else
            log_warn "SSH attempt $attempt failed, retrying in 10 seconds..."
            sleep 10
            ((attempt++))
        fi
    done

    log_error "Failed to establish SSH connection after $max_attempts attempts"
    log_error "Please check:"
    log_error "  - IP address: $PI_IP"
    log_error "  - SSH port: $PI_PORT"
    log_error "  - Username: $PI_USER"
    log_error "  - SSH key: $SSH_KEY"
    return 1
}

# Function to get system info from Pi
get_system_info() {
    log_step "Gathering system information from Pi"

    log_info "System Information:"
    run_on_pi "uname -a" "Get system info" || true
    run_on_pi "cat /etc/os-release" "Get OS info" || true
    run_on_pi "free -h" "Get memory info" || true
    run_on_pi "df -h" "Get disk info" || true
    run_on_pi "python3 --version" "Get Python version" || true
}

# Main deployment function
deploy_to_pi() {
    log_info "Starting Kindle Scribe Sync deployment to Raspberry Pi"
    log_info "Target: $PI_USER@$PI_IP:$PI_DIR"
    log_info "Verbose mode: $VERBOSE"

    # Wait for network connectivity
    if ! wait_for_network; then
        exit 1
    fi

    # Check SSH connectivity
    if ! check_ssh_connectivity; then
        exit 1
    fi

    # Get system information
    get_system_info

    # Update system
    log_step "Updating Raspberry Pi system packages"
    run_on_pi "sudo apt update" "Update package lists"
    run_on_pi "sudo apt upgrade -y" "Upgrade packages"

    # Install Git if not present
    if ! check_command_on_pi "git"; then
        log_step "Installing Git"
        run_on_pi "sudo apt install git -y" "Install Git"
    else
        log_success "Git is already installed"
    fi

    # Clone or update repository
    log_step "Setting up repository"
    if run_on_pi "[ -d '$PI_DIR' ]" "Check if repository exists" >/dev/null 2>&1; then
        log_info "Repository exists, updating..."
        run_on_pi "cd $PI_DIR && git pull" "Update repository"
    else
        log_info "Cloning repository..."
        run_on_pi "git clone https://github.com/haydentwestbrook/kindle-sync.git $PI_DIR" "Clone repository"
    fi

    # Set up Python environment
    log_step "Setting up Python virtual environment"
    run_on_pi "cd $PI_DIR && python3 -m venv venv" "Create virtual environment"
    run_on_pi "cd $PI_DIR && source venv/bin/activate && pip install --upgrade pip" "Upgrade pip"

    log_step "Installing Python dependencies"
    run_on_pi "cd $PI_DIR && source venv/bin/activate && pip install -r requirements.txt" "Install Python packages"

    # Install system dependencies
    log_step "Installing system dependencies"
    run_on_pi "sudo apt install -y tesseract-ocr tesseract-ocr-eng poppler-utils" "Install OCR and PDF tools"

    # Set up configuration if not skipping
    if [ "$SKIP_CONFIG" = false ]; then
        log_step "Setting up configuration"

        # Create config if it doesn't exist
        if ! run_on_pi "[ -f '$PI_DIR/config.yaml' ]" "Check if config exists" >/dev/null 2>&1; then
            log_info "Creating configuration file..."
            run_on_pi "cd $PI_DIR && cp config.yaml.example config.yaml" "Create config from example"
        fi

        # Create directories
        log_info "Creating necessary directories..."
        run_on_pi "mkdir -p $PI_DIR/logs $PI_DIR/backups $PI_DIR/temp" "Create application directories"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault" "Create Obsidian vault directory"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault/'Kindle Sync'" "Create sync folder"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault/Templates" "Create templates folder"
        run_on_pi "mkdir -p /home/$PI_USER/obsidian-vault/Backups" "Create backups folder"

        # Set permissions
        run_on_pi "sudo chown -R $PI_USER:$PI_USER $PI_DIR" "Set ownership of app directory"
        run_on_pi "sudo chown -R $PI_USER:$PI_USER /home/$PI_USER/obsidian-vault" "Set ownership of vault directory"
    fi

    # Make scripts executable
    log_step "Setting up scripts"
    run_on_pi "cd $PI_DIR && chmod +x scripts/*.sh" "Make scripts executable"
    run_on_pi "cd $PI_DIR && chmod +x simple_sync.py" "Make sync script executable"

    # Test the deployment
    log_step "Testing deployment"
    run_on_pi "cd $PI_DIR && source venv/bin/activate && python -c 'import pytesseract; print(\"Tesseract available\")'" "Test Tesseract"
    run_on_pi "cd $PI_DIR && source venv/bin/activate && python -c 'import pdf2image; print(\"PDF2Image available\")'" "Test PDF2Image"
    run_on_pi "cd $PI_DIR && source venv/bin/activate && python -c 'import reportlab; print(\"ReportLab available\")'" "Test ReportLab"

    log_success "Deployment completed successfully!"
    log_info "Next steps:"
    log_info "1. SSH into your Pi: ssh $PI_USER@$PI_IP"
    log_info "2. Edit configuration: nano $PI_DIR/config.yaml"
    log_info "3. Start the service: cd $PI_DIR && source venv/bin/activate && python simple_sync.py"
    log_info "4. View logs: tail -f $PI_DIR/kindle_sync.log"
    log_info ""
    log_info "For detailed instructions, see: docs/RASPBERRY_PI_DEPLOYMENT.md"
    log_info "Deployment log saved to: deployment.log"
}

# Run deployment
deploy_to_pi
