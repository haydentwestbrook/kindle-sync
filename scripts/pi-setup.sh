#!/bin/bash
# Raspberry Pi setup script - run this ON the Raspberry Pi

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
Usage: $0 [OPTIONS]

Set up Kindle Scribe Sync System on Raspberry Pi

Options:
    --skip-docker           Skip Docker installation
    --skip-build            Skip Docker image build
    --skip-config           Skip configuration setup
    --obsidian-path PATH    Path to Obsidian vault (default: /home/pi/obsidian-vault)
    --kindle-email EMAIL    Kindle email address
    --smtp-username USER    SMTP username
    --smtp-password PASS    SMTP password
    -h, --help              Show this help message

Examples:
    $0
    $0 --kindle-email my-kindle@kindle.com --smtp-username myemail@gmail.com
    $0 --skip-docker --obsidian-path /home/pi/Documents/Obsidian

EOF
}

# Default values
SKIP_DOCKER=false
SKIP_BUILD=false
SKIP_CONFIG=false
OBSIDIAN_PATH="/home/pi/obsidian-vault"
KINDLE_EMAIL=""
SMTP_USERNAME=""
SMTP_PASSWORD=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        --obsidian-path)
            OBSIDIAN_PATH="$2"
            shift 2
            ;;
        --kindle-email)
            KINDLE_EMAIL="$2"
            shift 2
            ;;
        --smtp-username)
            SMTP_USERNAME="$2"
            shift 2
            ;;
        --smtp-password)
            SMTP_PASSWORD="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Get current directory (should be the project root)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

print_header "Raspberry Pi Setup for Kindle Scribe Sync"
print_status "Project directory: $PROJECT_DIR"
print_status "Obsidian path: $OBSIDIAN_PATH"

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_warning "This script is designed for Raspberry Pi. Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_status "Setup cancelled"
        exit 0
    fi
fi

# Update system
print_header "Updating System"
print_status "Updating package lists..."
sudo apt update

print_status "Upgrading packages..."
sudo apt upgrade -y

# Install required packages
print_header "Installing Required Packages"
print_status "Installing system dependencies..."
sudo apt install -y \
    git \
    curl \
    wget \
    unzip \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    python3-pip \
    python3-venv

# Install Docker if not skipping
if [ "$SKIP_DOCKER" = false ]; then
    print_header "Installing Docker"
    
    if ! command -v docker &> /dev/null; then
        print_status "Installing Docker..."
        
        # Install Docker
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh
        
        # Add user to docker group
        sudo usermod -aG docker $USER
        
        print_status "Docker installed successfully"
        print_warning "Please log out and log back in for Docker group changes to take effect"
    else
        print_status "Docker already installed"
    fi
    
    # Install Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_status "Installing Docker Compose..."
        
        # Get latest version
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        
        # Download and install
        sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
        print_status "Docker Compose installed successfully"
    else
        print_status "Docker Compose already installed"
    fi
fi

# Create directories
print_header "Creating Directories"
print_status "Creating project directories..."
mkdir -p logs backups temp data/obsidian

print_status "Creating Obsidian vault structure..."
mkdir -p "$OBSIDIAN_PATH"
mkdir -p "$OBSIDIAN_PATH/Kindle Sync"
mkdir -p "$OBSIDIAN_PATH/Templates"
mkdir -p "$OBSIDIAN_PATH/Backups"

# Set permissions
print_status "Setting permissions..."
sudo chown -R $USER:$USER "$PROJECT_DIR"
sudo chown -R $USER:$USER "$OBSIDIAN_PATH"

# Set up configuration if not skipping
if [ "$SKIP_CONFIG" = false ]; then
    print_header "Setting up Configuration"
    
    # Create config.yaml if it doesn't exist
    if [ ! -f "config.yaml" ]; then
        print_status "Creating configuration file..."
        cp config.yaml.example config.yaml
        
        # Update Obsidian path in config
        sed -i "s|/tmp/test_obsidian|$OBSIDIAN_PATH|g" config.yaml
        
        # Update Kindle email if provided
        if [ -n "$KINDLE_EMAIL" ]; then
            sed -i "s|test@kindle.com|$KINDLE_EMAIL|g" config.yaml
        fi
        
        # Update SMTP settings if provided
        if [ -n "$SMTP_USERNAME" ]; then
            sed -i "s|test@gmail.com|$SMTP_USERNAME|g" config.yaml
        fi
        
        print_status "Configuration file created: config.yaml"
    else
        print_status "Configuration file already exists"
    fi
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating environment file..."
        cat > .env << EOF
# Docker environment variables
TZ=$(timedatectl show --property=Timezone --value)
OBSIDIAN_VAULT_PATH=$OBSIDIAN_PATH
KINDLE_EMAIL=${KINDLE_EMAIL:-your-kindle@kindle.com}
SMTP_USERNAME=${SMTP_USERNAME:-your-email@gmail.com}
SMTP_PASSWORD=${SMTP_PASSWORD:-your-app-password}
EOF
        print_status "Environment file created: .env"
    else
        print_status "Environment file already exists"
    fi
    
    # Update docker-compose.yml with correct paths
    print_status "Updating Docker Compose configuration..."
    sed -i "s|/path/to/your/obsidian/vault|$OBSIDIAN_PATH|g" docker-compose.yml
fi

# Build Docker image if not skipping
if [ "$SKIP_BUILD" = false ]; then
    print_header "Building Docker Image"
    print_status "Building Kindle Sync Docker image..."
    docker-compose build
    print_status "Docker image built successfully"
fi

# Create systemd service
print_header "Creating System Service"
print_status "Creating systemd service for auto-startup..."

sudo tee /etc/systemd/system/kindle-sync.service > /dev/null << EOF
[Unit]
Description=Kindle Scribe Sync System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/docker-commands.sh start
ExecStop=$PROJECT_DIR/scripts/docker-commands.sh stop
TimeoutStartSec=0
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable kindle-sync.service

print_status "System service created and enabled"

# Create management aliases
print_header "Setting up Management Aliases"
print_status "Adding management aliases to .bashrc..."

# Add aliases to .bashrc
cat >> ~/.bashrc << EOF

# Kindle Scribe Sync Management Aliases
alias kindle-start='cd $PROJECT_DIR && ./scripts/docker-commands.sh start'
alias kindle-stop='cd $PROJECT_DIR && ./scripts/docker-commands.sh stop'
alias kindle-restart='cd $PROJECT_DIR && ./scripts/docker-commands.sh restart'
alias kindle-logs='cd $PROJECT_DIR && ./scripts/docker-commands.sh logs'
alias kindle-status='cd $PROJECT_DIR && ./scripts/docker-commands.sh status'
alias kindle-backup='cd $PROJECT_DIR && ./scripts/docker-commands.sh backup'
alias kindle-update='cd $PROJECT_DIR && ./scripts/docker-commands.sh update'
EOF

print_status "Management aliases added to .bashrc"

# Create update script
print_header "Creating Update Script"
cat > update-kindle-sync.sh << 'EOF'
#!/bin/bash
echo "Updating Kindle Scribe Sync System..."

# Update system packages
sudo apt update && sudo apt upgrade -y

# Update the application
cd /home/pi/kindle-sync
git pull

# Rebuild and restart
./scripts/docker-commands.sh update

echo "Update completed!"
EOF

chmod +x update-kindle-sync.sh
print_status "Update script created: update-kindle-sync.sh"

# Create backup script
print_header "Creating Backup Script"
cat > backup-kindle-sync.sh << EOF
#!/bin/bash
BACKUP_DIR="/home/pi/backups/kindle-sync-\$(date +%Y%m%d_%H%M%S)"
mkdir -p "\$BACKUP_DIR"

echo "Backing up Kindle Scribe Sync System..."

# Backup configuration
cp config.yaml "\$BACKUP_DIR/"
cp .env "\$BACKUP_DIR/"

# Backup Obsidian vault
tar -czf "\$BACKUP_DIR/obsidian-vault.tar.gz" "$OBSIDIAN_PATH"

# Backup logs
if [ -d "logs" ]; then
    cp -r logs "\$BACKUP_DIR/"
fi

echo "Backup completed: \$BACKUP_DIR"
EOF

chmod +x backup-kindle-sync.sh
print_status "Backup script created: backup-kindle-sync.sh"

# Optimize system for Raspberry Pi
print_header "Optimizing System for Raspberry Pi"

# Enable GPU memory split
if ! grep -q "gpu_mem=16" /boot/config.txt; then
    print_status "Enabling GPU memory split..."
    echo "gpu_mem=16" | sudo tee -a /boot/config.txt
fi

# Optimize Docker
if [ ! -f /etc/docker/daemon.json ]; then
    print_status "Optimizing Docker configuration..."
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF
    sudo systemctl restart docker
fi

# Set up firewall
print_header "Setting up Firewall"
if ! command -v ufw &> /dev/null; then
    print_status "Installing UFW firewall..."
    sudo apt install ufw -y
fi

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 22
sudo ufw --force enable

print_status "Firewall configured"

print_header "Setup Complete!"
print_status "Raspberry Pi setup completed successfully!"
print_status ""
print_status "Next steps:"
print_status "1. Edit configuration: nano config.yaml"
print_status "2. Edit environment: nano .env"
print_status "3. Start the service: kindle-start"
print_status "4. View logs: kindle-logs"
print_status "5. Check status: kindle-status"
print_status ""
print_status "Management commands:"
print_status "  kindle-start    - Start the service"
print_status "  kindle-stop     - Stop the service"
print_status "  kindle-restart  - Restart the service"
print_status "  kindle-logs     - View logs"
print_status "  kindle-status   - Check status"
print_status "  kindle-backup   - Backup data"
print_status "  kindle-update   - Update system"
print_status ""
print_status "Files created:"
print_status "  - config.yaml (configuration)"
print_status "  - .env (environment variables)"
print_status "  - update-kindle-sync.sh (update script)"
print_status "  - backup-kindle-sync.sh (backup script)"
print_status ""
print_status "Service:"
print_status "  - Systemd service: kindle-sync.service"
print_status "  - Auto-start: enabled"
print_status "  - Status: sudo systemctl status kindle-sync"
print_status ""
print_warning "Please reboot the system to ensure all changes take effect:"
print_warning "  sudo reboot"
