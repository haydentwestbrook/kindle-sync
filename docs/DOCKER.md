# Docker Deployment Guide

This guide explains how to deploy the Kindle Scribe ↔ Obsidian Sync System using Docker on your Raspberry Pi.

## Prerequisites

- Raspberry Pi 3 or newer (recommended: Pi 4 with 4GB+ RAM)
- Raspberry Pi OS (or compatible Linux distribution)
- Internet connection
- At least 2GB free disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd kindle-sync
```

### 2. Run the Setup Script

```bash
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

### 3. Configure the System

Edit the configuration files:

```bash
# Edit main configuration
nano config.yaml

# Edit environment variables
nano .env

# Update volume paths in docker-compose.yml
nano docker-compose.yml
```

### 4. Start the Container

```bash
docker-compose up -d
```

### 5. Monitor the System

```bash
# View logs
docker-compose logs -f

# Check status
./scripts/docker-commands.sh status
```

## Detailed Setup

### Docker Installation

If Docker is not installed, the setup script will install it automatically. For manual installation:

```bash
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

# Log out and log back in for group changes to take effect
```

### Configuration

#### 1. Main Configuration (`config.yaml`)

```yaml
# Obsidian Configuration
obsidian:
  vault_path: "/app/data/obsidian"  # Path inside container
  sync_folder: "Kindle Sync"
  templates_folder: "Templates"

# Kindle Configuration
kindle:
  email: "your-kindle@kindle.com"
  approved_senders:
    - "your-email@gmail.com"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "your-email@gmail.com"
  smtp_password: "your-app-password"
```

#### 2. Environment Variables (`.env`)

```bash
TZ=America/New_York
OBSIDIAN_VAULT_PATH=/home/pi/Documents/Obsidian
KINDLE_EMAIL=your-kindle@kindle.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### 3. Docker Compose Configuration

Update the volume paths in `docker-compose.yml`:

```yaml
volumes:
  # Mount your Obsidian vault
  - /home/pi/Documents/Obsidian:/app/data/obsidian:rw
  # Mount config file
  - ./config.yaml:/app/config.yaml:ro
  # Mount logs directory
  - ./logs:/app/logs:rw
  # Mount backups directory
  - ./backups:/app/backups:rw
```

## Management Commands

Use the provided management script for easy container management:

```bash
# Start the container
./scripts/docker-commands.sh start

# Stop the container
./scripts/docker-commands.sh stop

# Restart the container
./scripts/docker-commands.sh restart

# View logs
./scripts/docker-commands.sh logs

# Check status and statistics
./scripts/docker-commands.sh status

# Rebuild the container
./scripts/docker-commands.sh rebuild

# Update the container
./scripts/docker-commands.sh update

# Clean up Docker resources
./scripts/docker-commands.sh cleanup

# Backup data
./scripts/docker-commands.sh backup

# Restore from backup
./scripts/docker-commands.sh restore
```

## Resource Optimization

### Raspberry Pi 4 (4GB+)

```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
    reservations:
      memory: 512M
      cpus: '0.5'
```

### Raspberry Pi 3 or Lower

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

## Volume Mounts

### Required Mounts

- **Obsidian Vault**: Mount your Obsidian vault directory
- **Configuration**: Mount the config.yaml file
- **Logs**: Mount logs directory for persistence
- **Backups**: Mount backups directory for persistence

### Optional Mounts

- **Temp Directory**: For temporary file processing
- **Source Code**: For development (mount entire project directory)

## Networking

The container runs in a bridge network by default. For external access:

```yaml
ports:
  - "8080:80"  # If you add a web interface
```

## Security Considerations

### File Permissions

```bash
# Set proper permissions
sudo chown -R $USER:$USER logs backups temp data
chmod 755 logs backups temp data
```

### Non-Root User

The container runs as a non-root user (`kindlesync`) for security.

### Volume Security

- Use read-only mounts for configuration files
- Limit write access to necessary directories only

## Monitoring and Logging

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service logs
docker-compose logs kindle-sync
```

### Health Checks

The container includes health checks:

```bash
# Check container health
docker-compose ps

# View health check logs
docker inspect kindle-sync | grep -A 10 Health
```

### Statistics

```bash
# View processing statistics
./scripts/docker-commands.sh status

# View resource usage
docker stats kindle-sync
```

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs

# Check configuration
docker-compose config

# Validate configuration
docker-compose exec kindle-sync python main.py validate
```

**Permission denied errors:**
```bash
# Fix permissions
sudo chown -R $USER:$USER logs backups temp data
chmod 755 logs backups temp data
```

**Out of memory errors:**
```bash
# Reduce resource limits in docker-compose.yml
# Or add swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**Volume mount issues:**
```bash
# Check if paths exist
ls -la /path/to/your/obsidian/vault

# Check Docker volume mounts
docker inspect kindle-sync | grep -A 20 Mounts
```

### Performance Optimization

**For better performance:**

1. **Use SSD storage** for the Obsidian vault
2. **Increase swap space** if running low on memory
3. **Optimize resource limits** based on your Pi model
4. **Use tmpfs** for temporary files:

```yaml
volumes:
  - type: tmpfs
    target: /app/temp
    tmpfs:
      size: 100M
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup
./scripts/docker-commands.sh backup

# Restore from backup
./scripts/docker-commands.sh restore
```

### Manual Backups

```bash
# Backup configuration
cp config.yaml backups/config_$(date +%Y%m%d).yaml

# Backup logs
tar -czf backups/logs_$(date +%Y%m%d).tar.gz logs/

# Backup data
tar -czf backups/data_$(date +%Y%m%d).tar.gz data/
```

## Updates

### Update the Application

```bash
# Pull latest changes
git pull

# Update container
./scripts/docker-commands.sh update
```

### Update Docker

```bash
# Update Docker
sudo apt-get update
sudo apt-get upgrade docker-ce docker-ce-cli containerd.io
```

## Development

### Development Mode

For development, create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  kindle-sync:
    volumes:
      - .:/app:rw  # Mount source code
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    command: ["python", "main.py", "start", "--debug"]
```

### Debugging

```bash
# Run container in interactive mode
docker-compose run --rm kindle-sync bash

# Execute commands in running container
docker-compose exec kindle-sync python main.py validate

# View container processes
docker-compose exec kindle-sync ps aux
```

## Production Deployment

### Systemd Service

Create a systemd service for automatic startup:

```bash
sudo nano /etc/systemd/system/kindle-sync.service
```

```ini
[Unit]
Description=Kindle Scribe Sync System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/kindle-sync
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl enable kindle-sync.service
sudo systemctl start kindle-sync.service
```

### Cron Jobs

Set up automated tasks:

```bash
# Edit crontab
crontab -e

# Add entries
# Clean up old files daily at 2 AM
0 2 * * * cd /home/pi/kindle-sync && ./scripts/docker-commands.sh cleanup

# Backup data weekly on Sunday at 3 AM
0 3 * * 0 cd /home/pi/kindle-sync && ./scripts/docker-commands.sh backup
```
