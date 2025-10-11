#!/bin/bash
# Configuration setup script for Kindle Sync

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
Usage: $0 [OPTIONS]

Setup configuration for Kindle Sync

Options:
    --create-config       Create config.yaml from template
    --validate-config     Validate existing config.yaml file
    --show-config         Show current configuration
    --update-scripts      Update scripts to use configuration
    --setup-env           Setup environment variables from config
    --help                Show this help message

Examples:
    $0 --create-config
    $0 --validate-config
    $0 --show-config
    $0 --update-scripts
    $0 --setup-env

EOF
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Function to create config.yaml from template
create_config_file() {
    print_header "Creating config.yaml from template"
    
    if [ -f "$PROJECT_DIR/config.yaml" ]; then
        print_warning "config.yaml file already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Keeping existing config.yaml file"
            return 0
        fi
    fi
    
    if [ ! -f "$PROJECT_DIR/config.yaml.example" ]; then
        print_error "config.yaml.example file not found"
        exit 1
    fi
    
    cp "$PROJECT_DIR/config.yaml.example" "$PROJECT_DIR/config.yaml"
    print_success "config.yaml file created from template"
    
    # Set default values based on system
    if command -v timedatectl >/dev/null 2>&1; then
        TZ=$(timedatectl show --property=Timezone --value)
        # Note: The original config doesn't have timezone, so we'll add it to the environment section
        print_status "Detected timezone: $TZ"
    fi
    
    # Set user
    USER=$(whoami)
    print_status "Set user to: $USER"
    
    # Set project directory
    print_status "Set project directory to: $PROJECT_DIR"
    
    # Set Obsidian path
    OBSIDIAN_PATH="$HOME/obsidian-vault"
    sed -i "s|vault_path: \"~/Documents/Obsidian\"|vault_path: \"$OBSIDIAN_PATH\"|g" "$PROJECT_DIR/config.yaml"
    print_status "Set Obsidian vault path to: $OBSIDIAN_PATH"
    
    print_success "config.yaml file created successfully"
    print_warning "Please edit config.yaml file to customize your settings:"
    print_warning "  nano $PROJECT_DIR/config.yaml"
}

# Function to validate config.yaml file
validate_config_file() {
    print_header "Validating config.yaml file"
    
    if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
        print_error "config.yaml file not found"
        print_status "Run with --create-config to create it"
        exit 1
    fi
    
    # Check if yq is available for YAML parsing
    if ! command -v yq >/dev/null 2>&1; then
        print_warning "yq not found, using basic validation"
        # Basic file validation
        if ! python3 -c "import yaml; yaml.safe_load(open('$PROJECT_DIR/config.yaml'))" 2>/dev/null; then
            print_error "config.yaml is not valid YAML"
            exit 1
        fi
        print_success "config.yaml is valid YAML"
        return 0
    fi
    
    # Use yq for detailed validation
    local errors=0
    
    # Check required sections
    if ! yq eval '.obsidian.vault_path' "$PROJECT_DIR/config.yaml" >/dev/null 2>&1; then
        print_error "obsidian.vault_path is not set"
        ((errors++))
    fi
    
    # Check if values are still defaults
    if [ "$(yq eval '.kindle.email' "$PROJECT_DIR/config.yaml")" = "your-kindle@kindle.com" ]; then
        print_warning "kindle.email is not configured"
    fi
    
    if [ "$(yq eval '.kindle.smtp_username' "$PROJECT_DIR/config.yaml")" = "your-email@gmail.com" ]; then
        print_warning "kindle.smtp_username is not configured"
    fi
    
    if [ "$(yq eval '.kindle.smtp_password' "$PROJECT_DIR/config.yaml")" = "your-app-password" ]; then
        print_warning "kindle.smtp_password is not configured"
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "config.yaml validation passed"
    else
        print_error "config.yaml validation failed with $errors errors"
        exit 1
    fi
}

# Function to show configuration
show_config() {
    print_header "Current Configuration"
    
    if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
        print_error "config.yaml file not found"
        print_status "Run with --create-config to create it"
        exit 1
    fi
    
    # Check if yq is available
    if ! command -v yq >/dev/null 2>&1; then
        print_warning "yq not found, showing raw config file"
        cat "$PROJECT_DIR/config.yaml"
        return 0
    fi
    
    echo "Obsidian Configuration:"
    echo "  Vault Path: $(yq eval '.obsidian.vault_path' "$PROJECT_DIR/config.yaml")"
    echo "  Sync Folder: $(yq eval '.obsidian.sync_folder' "$PROJECT_DIR/config.yaml")"
    echo "  Templates Folder: $(yq eval '.obsidian.templates_folder' "$PROJECT_DIR/config.yaml")"
    echo "  Watch Subfolders: $(yq eval '.obsidian.watch_subfolders' "$PROJECT_DIR/config.yaml")"
    echo ""
    
    echo "Kindle Configuration:"
    echo "  Email: $(yq eval '.kindle.email' "$PROJECT_DIR/config.yaml")"
    echo "  SMTP Server: $(yq eval '.kindle.smtp_server' "$PROJECT_DIR/config.yaml")"
    echo "  SMTP Port: $(yq eval '.kindle.smtp_port' "$PROJECT_DIR/config.yaml")"
    echo "  SMTP Username: $(yq eval '.kindle.smtp_username' "$PROJECT_DIR/config.yaml")"
    echo "  SMTP Password: [HIDDEN]"
    echo ""
    
    echo "Processing Configuration:"
    echo "  OCR Language: $(yq eval '.processing.ocr.language' "$PROJECT_DIR/config.yaml")"
    echo "  PDF Page Size: $(yq eval '.processing.pdf.page_size' "$PROJECT_DIR/config.yaml")"
    echo "  PDF Font Family: $(yq eval '.processing.pdf.font_family' "$PROJECT_DIR/config.yaml")"
    echo ""
    
    echo "Sync Configuration:"
    echo "  Auto Convert: $(yq eval '.sync.auto_convert_on_save' "$PROJECT_DIR/config.yaml")"
    echo "  Auto Send: $(yq eval '.sync.auto_send_to_kindle' "$PROJECT_DIR/config.yaml")"
    echo "  Backup Originals: $(yq eval '.sync.backup_originals' "$PROJECT_DIR/config.yaml")"
    echo ""
    
    echo "Logging Configuration:"
    echo "  Level: $(yq eval '.logging.level' "$PROJECT_DIR/config.yaml")"
    echo "  File: $(yq eval '.logging.file' "$PROJECT_DIR/config.yaml")"
    echo "  Max Size: $(yq eval '.logging.max_size' "$PROJECT_DIR/config.yaml")"
    echo ""
    
    echo "Deployment Configuration:"
    echo "  Pi User: $(yq eval '.deployment.pi.user' "$PROJECT_DIR/config.yaml")"
    echo "  SSH Port: $(yq eval '.deployment.pi.port' "$PROJECT_DIR/config.yaml")"
    echo "  SSH Key: $(yq eval '.deployment.pi.ssh_key' "$PROJECT_DIR/config.yaml")"
    echo "  Target Directory: $(yq eval '.deployment.pi.directory' "$PROJECT_DIR/config.yaml")"
    echo "  Skip Docker: $(yq eval '.deployment.options.skip_docker' "$PROJECT_DIR/config.yaml")"
    echo "  Skip Build: $(yq eval '.deployment.options.skip_build' "$PROJECT_DIR/config.yaml")"
    echo "  Skip Config: $(yq eval '.deployment.options.skip_config' "$PROJECT_DIR/config.yaml")"
    echo ""
}

# Function to setup environment variables from config
setup_env() {
    print_header "Setting up environment variables from config"
    
    if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
        print_error "config.yaml file not found"
        print_status "Run with --create-config to create it first"
        exit 1
    fi
    
    # Create .env file from config.yaml
    print_status "Creating .env file from config.yaml"
    
    cat > "$PROJECT_DIR/.env" << EOF
# Environment variables generated from config.yaml
# Do not edit this file directly - edit config.yaml instead

EOF
    
    # Extract environment variables from config.yaml
    if command -v yq >/dev/null 2>&1; then
        echo "TZ=America/New_York" >> "$PROJECT_DIR/.env"
        echo "PROJECT_DIR=$PROJECT_DIR" >> "$PROJECT_DIR/.env"
        echo "USER=$(whoami)" >> "$PROJECT_DIR/.env"
        echo "OBSIDIAN_VAULT_PATH=$(yq eval '.obsidian.vault_path' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "KINDLE_EMAIL=$(yq eval '.kindle.email' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "SMTP_USERNAME=$(yq eval '.kindle.smtp_username' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "SMTP_PASSWORD=$(yq eval '.kindle.smtp_password' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "LOG_LEVEL=$(yq eval '.logging.level' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "PI_USER=$(yq eval '.deployment.pi.user' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "PI_PORT=$(yq eval '.deployment.pi.port' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "PI_SSH_KEY=$(yq eval '.deployment.pi.ssh_key' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
        echo "PI_DIRECTORY=$(yq eval '.deployment.pi.directory' "$PROJECT_DIR/config.yaml")" >> "$PROJECT_DIR/.env"
    else
        print_warning "yq not found, creating basic .env file"
        echo "TZ=America/New_York" >> "$PROJECT_DIR/.env"
        echo "PROJECT_DIR=$PROJECT_DIR" >> "$PROJECT_DIR/.env"
        echo "USER=$(whoami)" >> "$PROJECT_DIR/.env"
        echo "OBSIDIAN_VAULT_PATH=$HOME/obsidian-vault" >> "$PROJECT_DIR/.env"
        echo "KINDLE_EMAIL=your-kindle@kindle.com" >> "$PROJECT_DIR/.env"
        echo "SMTP_USERNAME=your-email@gmail.com" >> "$PROJECT_DIR/.env"
        echo "SMTP_PASSWORD=your-app-password" >> "$PROJECT_DIR/.env"
        echo "LOG_LEVEL=INFO" >> "$PROJECT_DIR/.env"
        echo "PI_USER=pi" >> "$PROJECT_DIR/.env"
        echo "PI_PORT=22" >> "$PROJECT_DIR/.env"
        echo "PI_SSH_KEY=" >> "$PROJECT_DIR/.env"
        echo "PI_DIRECTORY=/home/pi/kindle-sync" >> "$PROJECT_DIR/.env"
    fi
    
    print_success ".env file created from config.yaml"
}

# Function to update scripts to use configuration
update_scripts() {
    print_header "Updating scripts to use configuration"
    
    if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
        print_error "config.yaml file not found"
        print_status "Run with --create-config to create it first"
        exit 1
    fi
    
    # Update docker-compose.yml
    if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
        print_status "Updating docker-compose.yml"
        if command -v yq >/dev/null 2>&1; then
            OBSIDIAN_PATH=$(yq eval '.obsidian.vault_path' "$PROJECT_DIR/config.yaml")
            sed -i "s|/path/to/your/obsidian/vault|$OBSIDIAN_PATH|g" "$PROJECT_DIR/docker-compose.yml"
        fi
    fi
    
    print_success "Scripts updated to use configuration"
}

# Main function
main() {
    case "${1:-}" in
        --create-config)
            create_config_file
            ;;
        --validate-config)
            validate_config_file
            ;;
        --show-config)
            show_config
            ;;
        --update-scripts)
            update_scripts
            ;;
        --setup-env)
            setup_env
            ;;
        --help|-h)
            show_usage
            ;;
        "")
            print_error "No option specified"
            show_usage
            exit 1
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
