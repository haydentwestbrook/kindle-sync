# GitHub Actions Deployment Guide

This guide explains how to deploy the Kindle Sync application to your Raspberry Pi using GitHub Actions, providing automated deployment with comprehensive logging and monitoring.

## 🎯 Benefits of GitHub Actions Deployment

- **Automated Deployment**: Deploy with a single click or automatically on code changes
- **Comprehensive Logging**: Full visibility into deployment process
- **Environment Management**: Separate staging and production environments
- **Service Management**: Start, stop, restart, and monitor the service remotely
- **Testing Integration**: Run tests before deployment
- **Rollback Capability**: Easy to revert to previous versions

## 🔧 Setup Requirements

### 1. GitHub Repository Secrets

You need to add the following secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following repository secrets:

#### Required Secrets:
- `PI_SSH_PRIVATE_KEY`: Your SSH private key for connecting to the Pi
- `PI_SSH_PUBLIC_KEY`: Your SSH public key (for reference)

#### Optional Secrets:
- `PI_IP`: Default IP address (can be overridden in workflow)
- `PI_USER`: Default username (can be overridden in workflow)

### 2. SSH Key Setup

Generate SSH keys if you don't have them:
```bash
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_actions_deploy
```

Add the public key to your Pi:
```bash
ssh-copy-id -i ~/.ssh/github_actions_deploy.pub hayden@192.168.0.12
```

Add the private key to GitHub secrets:
```bash
cat ~/.ssh/github_actions_deploy
# Copy the output and paste it as PI_SSH_PRIVATE_KEY secret
```

### 3. Pi Configuration

Ensure your Pi is accessible from the internet or configure port forwarding:
- **Local Network**: Works if GitHub Actions runner can reach your Pi
- **Internet Access**: Configure router port forwarding for SSH (port 22)
- **VPN**: Use a VPN connection for secure access

## 🚀 Available Workflows

### 1. Deploy to Raspberry Pi (`deploy-to-pi.yml`)

**Triggers:**
- Manual dispatch (workflow_dispatch)
- Push to main branch (when source files change)

**Features:**
- Runs tests before deployment
- Updates system packages
- Installs dependencies
- Sets up Python environment
- Creates systemd service
- Comprehensive logging

**Usage:**
1. Go to **Actions** tab in GitHub
2. Select **Deploy to Raspberry Pi**
3. Click **Run workflow**
4. Configure parameters:
   - Pi IP Address
   - SSH Username
   - Skip tests (optional)
   - Environment (production/staging/development)

### 2. Manage Service (`manage-service.yml`)

**Triggers:**
- Manual dispatch only

**Actions:**
- `status`: Check service status
- `start`: Start the service
- `stop`: Stop the service
- `restart`: Restart the service
- `logs`: View service logs
- `update-config`: Update configuration and restart

**Usage:**
1. Go to **Actions** tab in GitHub
2. Select **Manage Kindle Sync Service**
3. Click **Run workflow**
4. Choose the action to perform

### 3. Test Deployment (`test-deployment.yml`)

**Triggers:**
- Manual dispatch only

**Test Types:**
- `connectivity`: Test SSH and internet connectivity
- `dependencies`: Test all Python and system dependencies
- `service`: Test service status and health
- `file-processing`: Test Markdown/PDF conversion
- `email`: Test email configuration
- `all`: Run all tests

**Usage:**
1. Go to **Actions** tab in GitHub
2. Select **Test Deployment**
3. Click **Run workflow**
4. Choose test type

## 📋 Deployment Process

### Automatic Deployment (on push to main):
1. **Test Phase**: Run linting, type checking, and unit tests
2. **Deploy Phase**: 
   - Test SSH connection
   - Update system packages
   - Install dependencies
   - Setup Python environment
   - Create directory structure
   - Configure systemd service
   - Start service
   - Verify deployment

### Manual Deployment:
1. Go to Actions → Deploy to Raspberry Pi
2. Click "Run workflow"
3. Configure parameters
4. Monitor progress in real-time
5. Review deployment logs

## 🔍 Monitoring and Logs

### GitHub Actions Logs:
- Real-time deployment progress
- Detailed step-by-step logging
- Error reporting with context
- Success/failure notifications

### Pi Service Logs:
```bash
# View service status
sudo systemctl status kindle-sync.service

# View service logs
sudo journalctl -u kindle-sync.service -f

# View application logs
tail -f /home/hayden/kindle-sync/kindle_sync.log
```

## 🛠️ Service Management

### Via GitHub Actions:
- Use the "Manage Kindle Sync Service" workflow
- Choose from: status, start, stop, restart, logs, update-config

### Via SSH:
```bash
# Connect to Pi
ssh hayden@192.168.0.12

# Service management
sudo systemctl status kindle-sync.service
sudo systemctl start kindle-sync.service
sudo systemctl stop kindle-sync.service
sudo systemctl restart kindle-sync.service

# View logs
sudo journalctl -u kindle-sync.service -f
```

## 🔒 Security Considerations

### SSH Key Security:
- Use dedicated SSH keys for GitHub Actions
- Rotate keys regularly
- Use key passphrases
- Limit key permissions on Pi

### Network Security:
- Use VPN for internet access
- Configure firewall rules
- Use non-standard SSH ports
- Enable SSH key-only authentication

### Pi Security:
- Keep system updated
- Use strong passwords
- Enable fail2ban
- Regular security audits

## 🚨 Troubleshooting

### Common Issues:

#### SSH Connection Failed:
- Check Pi IP address and network connectivity
- Verify SSH key is correctly added to GitHub secrets
- Ensure SSH service is running on Pi
- Check firewall settings

#### Deployment Fails:
- Check GitHub Actions logs for specific errors
- Verify Pi has sufficient disk space and memory
- Ensure all dependencies can be installed
- Check Python version compatibility

#### Service Won't Start:
- Check service logs: `sudo journalctl -u kindle-sync.service`
- Verify configuration file syntax
- Check file permissions
- Ensure all dependencies are installed

### Debug Commands:
```bash
# Test SSH connection
ssh -i ~/.ssh/github_actions_deploy hayden@192.168.0.12 "echo 'SSH works'"

# Check service status
sudo systemctl status kindle-sync.service

# View detailed logs
sudo journalctl -u kindle-sync.service --no-pager -l

# Test Python environment
cd /home/hayden/kindle-sync && source venv/bin/activate && python -c "import simple_sync"
```

## 📈 Advanced Features

### Environment Management:
- Separate staging and production deployments
- Environment-specific configurations
- Automated testing in staging before production

### Monitoring Integration:
- Prometheus metrics collection
- Grafana dashboards
- Alert notifications
- Performance monitoring

### Backup and Recovery:
- Automated configuration backups
- Service state snapshots
- Quick rollback procedures
- Disaster recovery planning

## 🎉 Success Indicators

After successful deployment, you should see:
- ✅ All tests passing
- ✅ Service running and active
- ✅ Dependencies properly installed
- ✅ Configuration files in place
- ✅ Directory structure created
- ✅ Logs being generated

## 📞 Support

If you encounter issues:
1. Check the GitHub Actions logs
2. Review the troubleshooting section
3. Test individual components
4. Check Pi system resources
5. Verify network connectivity

The GitHub Actions deployment provides a robust, automated way to deploy and manage your Kindle Sync application with full visibility and control.
