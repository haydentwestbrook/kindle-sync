#!/bin/bash
# Docker setup script for Kindle Scribe Sync System on Raspberry Pi

set -e

echo "Setting up Kindle Scribe Sync System with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    
    # Update package index
    sudo apt-get update
    
    # Install required packages
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Set up stable repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    echo "Docker installed successfully. Please log out and log back in for group changes to take effect."
    echo "Then run this script again."
    exit 0
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Installing Docker Compose..."
    
    # Get latest version
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    # Download and install
    sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "Docker Compose installed successfully."
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs backups temp data/obsidian

# Set up permissions
echo "Setting up permissions..."
sudo chown -R $USER:$USER logs backups temp data

# Create configuration file if it doesn't exist
if [ ! -f "config.yaml" ]; then
    echo "Creating configuration file..."
    cp config.yaml.example config.yaml
    echo "Please edit config.yaml with your settings before starting the container."
fi

# Create .env file for Docker Compose
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Docker environment variables
TZ=America/New_York
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
KINDLE_EMAIL=your-kindle@kindle.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EOF
    echo "Please edit .env file with your actual values."
fi

# Build the Docker image
echo "Building Docker image..."
docker-compose build

echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your Obsidian vault path and Kindle email"
echo "2. Edit .env file with your environment variables"
echo "3. Update the volume path in docker-compose.yml to point to your Obsidian vault"
echo "4. Start the container: docker-compose up -d"
echo "5. View logs: docker-compose logs -f"
echo ""
echo "For more information, see docs/DOCKER.md"
