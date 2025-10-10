# Raspberry Pi Deployment Guide

This guide will help you deploy the Kindle Scribe Sync System to your Raspberry Pi using Docker.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Configuration](#configuration)
- [Management](#management)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)

## Prerequisites

### Hardware Requirements
- **Raspberry Pi 4** (recommended) or **Raspberry Pi 3B+**
- **4GB RAM minimum** (8GB recommended)
- **32GB+ microSD card** (Class 10 or better)
- **Stable internet connection**
- **USB storage** (for Kindle device connection)

### Software Requirements
- **Raspberry Pi OS** (64-bit recommended)
- **Git** (for cloning the repository)
- **Docker** (will be installed by setup script)

## Quick Start

### 1. Clone the Repository
```bash
# SSH into your Raspberry Pi
ssh pi@your-pi-ip-address

# Clone the repository
git clone https://github.com/haydentwestbrook/kindle-sync.git
cd kindle-sync
```

### 2. Run the Setup Script
```bash
# Make the setup script executable
chmod +x scripts/docker-setup.sh

# Run the setup script
./scripts/docker-setup.sh
```

### 3. Configure the Application
```bash
# Edit the configuration file
nano config.yaml

# Edit environment variables
nano .env
```

### 4. Start the Application
```bash
# Make the management script executable
chmod +x scripts/docker-commands.sh

# Start the container
./scripts/docker-commands.sh start

# View logs
./scripts/docker-commands.sh logs
```

## Detailed Setup

### Step 1: Prepare Your Raspberry Pi

#### Update the System
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

#### Install Git
```bash
sudo apt install git -y
```

### Step 2: Clone and Setup the Project

```bash
# Clone the repository
git clone https://github.com/haydentwestbrook/kindle-sync.git
cd kindle-sync

# Run the automated setup
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

The setup script will:
- Install Docker and Docker Compose
- Create necessary directories
- Set up permissions
- Create configuration templates
- Build the Docker image

### Step 3: Configure the Application

#### Edit Configuration File
```bash
nano config.yaml
```

Key settings to configure:
```yaml
obsidian:
  vault_path: "/home/pi/obsidian-vault"  # Path to your Obsidian vault
  sync_folder: "Kindle Sync"
  templates_folder: "Templates"

kindle:
  email: "your-kindle@kindle.com"  # Your Kindle email
  approved_senders: ["your-email@gmail.com"]
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "your-email@gmail.com"
  smtp_password: "your-app-password"  # Gmail App Password

processing:
  ocr:
    language: "eng"
    confidence_threshold: 60
  pdf:
    page_size: "A4"
    margins: [72, 72, 72, 72]
    font_family: "Times-Roman"
    font_size: 12

sync:
  auto_convert_on_save: true
  auto_send_to_kindle: true
  backup_originals: true
  backup_folder: "Backups"

logging:
  level: "INFO"
  file: "kindle_sync.log"
  max_size: "10MB"
  backup_count: 5
```

#### Edit Environment Variables
```bash
nano .env
```

```bash
# Docker environment variables
TZ=America/New_York  # Change to your timezone
OBSIDIAN_VAULT_PATH=/home/pi/obsidian-vault
KINDLE_EMAIL=your-kindle@kindle.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### Update Docker Compose Volume Paths
```bash
nano docker-compose.yml
```

Update the volume mount for your Obsidian vault:
```yaml
volumes:
  # Mount your Obsidian vault
  - /home/pi/obsidian-vault:/app/data/obsidian:rw
  # Mount config file
  - ./config.yaml:/app/config.yaml:ro
  # Mount logs directory
  - ./logs:/app/logs:rw
  # Mount backups directory
  - ./backups:/app/backups:rw
  # Mount temp directory for processing
  - ./temp:/app/temp:rw
```

### Step 4: Create Obsidian Vault Structure

```bash
# Create your Obsidian vault directory
mkdir -p /home/pi/obsidian-vault

# Create the sync folder structure
mkdir -p /home/pi/obsidian-vault/"Kindle Sync"
mkdir -p /home/pi/obsidian-vault/Templates
mkdir -p /home/pi/obsidian-vault/Backups

# Set proper permissions
sudo chown -R pi:pi /home/pi/obsidian-vault
```

### Step 5: Start the Application

```bash
# Start the container
./scripts/docker-commands.sh start

# Check status
./scripts/docker-commands.sh status

# View logs
./scripts/docker-commands.sh logs
```

## Configuration

### Obsidian Vault Setup

1. **Install Obsidian** on your computer
2. **Open the vault** at `/home/pi/obsidian-vault` (mounted from Pi)
3. **Create templates** in the Templates folder
4. **Set up sync** with your preferred cloud service (optional)

### Kindle Email Configuration

1. **Add your email** to approved senders in Amazon Kindle settings
2. **Get Gmail App Password**:
   - Enable 2-factor authentication
   - Generate an app password for the sync system
   - Use this password in the configuration

### File Watching

The system will automatically:
- **Watch** the "Kindle Sync" folder for new files
- **Convert** Markdown files to PDF
- **Send** PDFs to your Kindle via email
- **Backup** original files
- **Process** PDFs from Kindle back to Markdown

## Management

### Using the Management Script

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

# Update from repository
./scripts/docker-commands.sh update

# Backup data
./scripts/docker-commands.sh backup

# Clean up Docker resources
./scripts/docker-commands.sh cleanup
```

### Manual Docker Commands

```bash
# View container status
docker-compose ps

# View logs
docker-compose logs -f kindle-sync

# Execute commands in container
docker-compose exec kindle-sync bash

# View container statistics
docker stats kindle-sync
```

### System Service (Optional)

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
ExecStart=/home/pi/kindle-sync/scripts/docker-commands.sh start
ExecStop=/home/pi/kindle-sync/scripts/docker-commands.sh stop
TimeoutStartSec=0
User=pi

[Install]
WantedBy=multi-user.target
```

Enable the service:
```bash
sudo systemctl enable kindle-sync.service
sudo systemctl start kindle-sync.service
```

## Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check Docker status
sudo systemctl status docker

# Check container logs
docker-compose logs kindle-sync

# Check configuration
docker-compose config
```

#### Permission Issues
```bash
# Fix ownership
sudo chown -R pi:pi /home/pi/kindle-sync
sudo chown -R pi:pi /home/pi/obsidian-vault

# Fix permissions
chmod +x scripts/*.sh
```

#### Memory Issues
```bash
# Check memory usage
free -h
docker stats

# Increase swap if needed
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

#### Network Issues
```bash
# Test email connectivity
docker-compose exec kindle-sync python -c "
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
print('SMTP connection successful')
smtp.quit()
"
```

### Log Analysis

```bash
# View application logs
tail -f logs/kindle_sync.log

# View Docker logs
docker-compose logs -f kindle-sync

# View system logs
journalctl -u docker.service -f
```

### Performance Monitoring

```bash
# Monitor system resources
htop

# Monitor Docker containers
docker stats

# Check disk usage
df -h
du -sh /home/pi/kindle-sync/*
```

## Performance Optimization

### Raspberry Pi 4 Optimization

#### Enable GPU Memory Split
```bash
sudo raspi-config
# Advanced Options > Memory Split > 16
```

#### Overclock (Optional)
```bash
sudo nano /boot/config.txt
# Add:
# arm_freq=1800
# gpu_freq=600
# over_voltage=2
```

#### Optimize Docker
```bash
# Limit Docker memory usage
sudo nano /etc/docker/daemon.json
```

```json
{
  "default-ulimits": {
    "memlock": {
      "Hard": -1,
      "Name": "memlock",
      "Soft": -1
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Resource Limits

The Docker Compose file includes resource limits optimized for Raspberry Pi:

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

### Storage Optimization

```bash
# Clean up old logs
find logs/ -name "*.log" -mtime +7 -delete

# Clean up old backups
find backups/ -type f -mtime +30 -delete

# Clean up Docker
docker system prune -f
```

## Security Considerations

### Firewall Setup
```bash
# Install UFW
sudo apt install ufw -y

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 22
sudo ufw enable
```

### Regular Updates
```bash
# Create update script
nano update-system.sh
```

```bash
#!/bin/bash
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

echo "Updating Kindle Sync..."
cd /home/pi/kindle-sync
git pull
./scripts/docker-commands.sh update

echo "Update completed!"
```

```bash
chmod +x update-system.sh
```

### Backup Strategy
```bash
# Create backup script
nano backup-system.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/pi/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configuration
cp -r /home/pi/kindle-sync/config.yaml "$BACKUP_DIR/"
cp -r /home/pi/kindle-sync/.env "$BACKUP_DIR/"

# Backup Obsidian vault
tar -czf "$BACKUP_DIR/obsidian-vault.tar.gz" /home/pi/obsidian-vault

echo "Backup completed: $BACKUP_DIR"
```

## Support

For issues and questions:
1. Check the logs: `./scripts/docker-commands.sh logs`
2. Review this documentation
3. Check the main project README
4. Open an issue on GitHub

## Next Steps

After successful deployment:
1. **Test the workflow** by creating a Markdown file in the sync folder
2. **Set up Obsidian** to work with the mounted vault
3. **Configure your Kindle** to receive emails from the system
4. **Monitor the logs** to ensure everything is working
5. **Set up regular backups** of your data
