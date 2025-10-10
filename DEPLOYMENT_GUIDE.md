# 🚀 Raspberry Pi Deployment Guide

This guide provides multiple ways to deploy the Kindle Scribe Sync System to your Raspberry Pi.

## 📋 Prerequisites

- **Raspberry Pi 4** (recommended) or **Raspberry Pi 3B+**
- **4GB+ RAM** (8GB recommended)
- **32GB+ microSD card**
- **Stable internet connection**
- **SSH access** to your Pi

## 🎯 Deployment Options

### Option 1: Automated Remote Deployment (Recommended)

Deploy from your local machine to the Raspberry Pi:

```bash
# From your local machine
./scripts/deploy-to-pi.sh 192.168.1.100

# With custom settings
./scripts/deploy-to-pi.sh -u pi -k ~/.ssh/id_rsa 192.168.1.100
```

**What this does:**
- Connects to your Pi via SSH
- Installs Docker and dependencies
- Clones the repository
- Sets up configuration
- Builds the Docker image
- Creates necessary directories

### Option 2: Manual Pi Setup

Run the setup script directly on your Raspberry Pi:

```bash
# SSH into your Pi
ssh pi@192.168.1.100

# Clone the repository
git clone https://github.com/haydentwestbrook/kindle-sync.git
cd kindle-sync

# Run the setup script
chmod +x scripts/pi-setup.sh
./scripts/pi-setup.sh
```

### Option 3: Step-by-Step Manual Setup

Follow the detailed guide in `docs/RASPBERRY_PI_DEPLOYMENT.md`

## ⚡ Quick Start Commands

### Deploy from Local Machine
```bash
# Basic deployment
./scripts/deploy-to-pi.sh YOUR_PI_IP

# With custom user and key
./scripts/deploy-to-pi.sh -u pi -k ~/.ssh/id_rsa YOUR_PI_IP

# Skip Docker installation (if already installed)
./scripts/deploy-to-pi.sh --skip-docker YOUR_PI_IP
```

### Setup on Pi
```bash
# Basic setup
./scripts/pi-setup.sh

# With Kindle email
./scripts/pi-setup.sh --kindle-email my-kindle@kindle.com

# With SMTP settings
./scripts/pi-setup.sh \
  --kindle-email my-kindle@kindle.com \
  --smtp-username myemail@gmail.com \
  --smtp-password my-app-password
```

## 🔧 Configuration

After deployment, configure the system:

### 1. Edit Configuration
```bash
# SSH into your Pi
ssh pi@YOUR_PI_IP

# Edit configuration
nano kindle-sync/config.yaml
```

### 2. Edit Environment Variables
```bash
nano kindle-sync/.env
```

### 3. Update Obsidian Vault Path
```bash
# Create your Obsidian vault
mkdir -p /home/pi/obsidian-vault

# Update docker-compose.yml if needed
nano kindle-sync/docker-compose.yml
```

## 🚀 Starting the Service

### Using Management Script
```bash
cd kindle-sync

# Start the service
./scripts/docker-commands.sh start

# View logs
./scripts/docker-commands.sh logs

# Check status
./scripts/docker-commands.sh status
```

### Using Aliases (after setup)
```bash
# Start
kindle-start

# View logs
kindle-logs

# Check status
kindle-status

# Stop
kindle-stop
```

### Using System Service
```bash
# Start service
sudo systemctl start kindle-sync

# Enable auto-start
sudo systemctl enable kindle-sync

# Check status
sudo systemctl status kindle-sync
```

## 📊 Management Commands

### Docker Commands
```bash
./scripts/docker-commands.sh start      # Start container
./scripts/docker-commands.sh stop       # Stop container
./scripts/docker-commands.sh restart    # Restart container
./scripts/docker-commands.sh logs       # View logs
./scripts/docker-commands.sh status     # Check status
./scripts/docker-commands.sh backup     # Backup data
./scripts/docker-commands.sh update     # Update from repo
./scripts/docker-commands.sh cleanup    # Clean up resources
```

### System Commands
```bash
kindle-start      # Start service
kindle-stop       # Stop service
kindle-restart    # Restart service
kindle-logs       # View logs
kindle-status     # Check status
kindle-backup     # Backup data
kindle-update     # Update system
```

## 🔍 Troubleshooting

### Check Service Status
```bash
# Docker container status
docker-compose ps

# System service status
sudo systemctl status kindle-sync

# View logs
docker-compose logs -f kindle-sync
```

### Common Issues

#### Container Won't Start
```bash
# Check Docker
sudo systemctl status docker

# Check configuration
docker-compose config

# Rebuild container
./scripts/docker-commands.sh rebuild
```

#### Permission Issues
```bash
# Fix ownership
sudo chown -R pi:pi /home/pi/kindle-sync
sudo chown -R pi:pi /home/pi/obsidian-vault
```

#### Memory Issues
```bash
# Check memory
free -h

# Check Docker stats
docker stats
```

## 📈 Performance Optimization

### Raspberry Pi 4 Optimizations
- **GPU Memory Split**: 16MB (configured automatically)
- **Docker Resource Limits**: 512MB RAM, 0.5 CPU cores
- **Log Rotation**: 10MB max, 3 files
- **Storage Optimization**: Automatic cleanup

### Monitoring
```bash
# System resources
htop

# Docker containers
docker stats

# Disk usage
df -h
```

## 🔒 Security

### Firewall (configured automatically)
```bash
# Check status
sudo ufw status

# Allow additional ports if needed
sudo ufw allow 8080
```

### Updates
```bash
# Update system
./update-kindle-sync.sh

# Or manually
sudo apt update && sudo apt upgrade -y
cd kindle-sync && git pull
./scripts/docker-commands.sh update
```

## 📁 File Structure

After deployment, your Pi will have:

```
/home/pi/
├── kindle-sync/                 # Main application
│   ├── config.yaml             # Configuration
│   ├── .env                    # Environment variables
│   ├── docker-compose.yml      # Docker configuration
│   ├── logs/                   # Application logs
│   ├── backups/                # Backup files
│   └── scripts/                # Management scripts
├── obsidian-vault/             # Obsidian vault
│   ├── Kindle Sync/            # Sync folder
│   ├── Templates/              # Templates
│   └── Backups/                # File backups
└── backups/                    # System backups
```

## 🆘 Support

### Logs and Debugging
```bash
# Application logs
tail -f kindle-sync/logs/kindle_sync.log

# Docker logs
docker-compose logs -f kindle-sync

# System logs
journalctl -u kindle-sync -f
```

### Getting Help
1. Check the logs: `kindle-logs`
2. Review configuration files
3. Check the detailed guide: `docs/RASPBERRY_PI_DEPLOYMENT.md`
4. Open an issue on GitHub

## 🎉 Success!

Once deployed, your Kindle Scribe Sync System will:

- ✅ **Monitor** your Obsidian vault for changes
- ✅ **Convert** Markdown files to PDF
- ✅ **Send** PDFs to your Kindle via email
- ✅ **Process** PDFs back to Markdown
- ✅ **Backup** all files automatically
- ✅ **Run** continuously in the background
- ✅ **Restart** automatically on boot

Enjoy your automated Kindle Scribe workflow! 🚀
