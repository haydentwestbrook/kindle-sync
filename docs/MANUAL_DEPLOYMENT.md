# Manual Raspberry Pi Deployment Guide

## Prerequisites
- Raspberry Pi with SSH enabled
- Your Pi's IP address or hostname
- SSH access (password or SSH key)

## Step 1: Prepare Your Local Machine

```bash
# Create a deployment package
tar -czf kindle-sync-deploy.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='venv' \
    --exclude='Backups' \
    --exclude='test-results*.xml' \
    --exclude='coverage.xml' \
    --exclude='.coverage' \
    .
```

## Step 2: Copy to Raspberry Pi

```bash
# Replace with your Pi's details
scp kindle-sync-deploy.tar.gz pi@YOUR_PI_IP:~/
```

## Step 3: Setup on Raspberry Pi

SSH into your Pi and run:

```bash
# SSH into your Pi
ssh pi@YOUR_PI_IP

# Extract the deployment
tar -xzf kindle-sync-deploy.tar.gz
cd kindle-sync

# Make scripts executable
chmod +x scripts/*.sh

# Run the Pi setup script
./scripts/pi-setup.sh
```

## Step 4: Verify Deployment

```bash
# Check if everything is running
./scripts/docker-commands.sh status

# View logs
./scripts/docker-commands.sh logs

# Check system status
docker compose ps
```

## Step 5: Configure Your System

Edit the configuration file:

```bash
nano config.yaml
```

Update the following settings:
- `obsidian.vault_path`: Path to your Obsidian vault
- `kindle.email`: Your Kindle email address
- `smtp.*`: Your email server settings

## Step 6: Start the System

```bash
# Start the system
./scripts/docker-commands.sh start

# Or use docker compose directly
docker compose up -d
```

## Management Commands

```bash
# View status
./scripts/docker-commands.sh status

# View logs
./scripts/docker-commands.sh logs

# Stop system
./scripts/docker-commands.sh stop

# Restart system
./scripts/docker-commands.sh restart

# Update system
./scripts/docker-commands.sh update

# Backup data
./scripts/docker-commands.sh backup
```

## Troubleshooting

### Check Docker Status
```bash
sudo systemctl status docker
```

### Check Container Logs
```bash
docker compose logs -f
```

### Restart Docker Service
```bash
sudo systemctl restart docker
```

### Check Disk Space
```bash
df -h
```

### Check Memory Usage
```bash
free -h
```
