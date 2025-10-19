# Deployment Options Guide

## Overview

You now have multiple ways to deploy your Kindle Sync system to a Raspberry Pi, with full configuration support for Pi user, SSH keys, and deployment options.

## Deployment Methods

### 1. Configuration-Based Deployment (Recommended)

Use the new `deploy-with-config.sh` script that reads all settings from your `config.yaml`:

```bash
# Deploy using config.yaml settings
./scripts/deploy-with-config.sh 192.168.1.100

# Dry run to see what would be deployed
./scripts/deploy-with-config.sh --dry-run 192.168.1.100

# Use a different config file
./scripts/deploy-with-config.sh --config my-config.yaml 192.168.1.100
```

### 2. Enhanced Original Deployment Script

The original `deploy-to-pi.sh` script now supports reading from config.yaml:

```bash
# Deploy with config file
./scripts/deploy-to-pi.sh --config config.yaml 192.168.1.100

# Override specific settings from command line
./scripts/deploy-to-pi.sh --config config.yaml -u myuser -k ~/.ssh/id_rsa 192.168.1.100

# Traditional command-line deployment
./scripts/deploy-to-pi.sh -u pi -k ~/.ssh/id_rsa -p 2222 192.168.1.100
```

## Configuration Options

### Pi Connection Settings

In your `config.yaml`, you can configure:

```yaml
deployment:
  pi:
    user: "pi"                        # SSH username
    port: 22                          # SSH port
    ssh_key: "/path/to/your/key"      # SSH private key path
    directory: "/home/pi/kindle-sync" # Target directory on Pi
```

### Deployment Options

```yaml
deployment:
  options:
    skip_docker: false                # Skip Docker installation
    skip_build: false                 # Skip Docker image build
    skip_config: false                # Skip configuration setup
```

## Examples

### Basic Deployment with Config

1. **Configure your settings**:
   ```bash
   nano config.yaml
   ```

2. **Set your Pi connection details**:
   ```yaml
   deployment:
     pi:
       user: "pi"
       port: 22
       ssh_key: "/home/user/.ssh/id_rsa"
       directory: "/home/pi/kindle-sync"
   ```

3. **Deploy**:
   ```bash
   ./scripts/deploy-with-config.sh 192.168.1.100
   ```

### SSH Key Authentication

If you want to use SSH key authentication:

1. **Generate SSH key** (if you don't have one):
   ```bash
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```

2. **Copy public key to Pi**:
   ```bash
   ssh-copy-id -i ~/.ssh/id_rsa.pub pi@192.168.1.100
   ```

3. **Configure in config.yaml**:
   ```yaml
   deployment:
     pi:
       ssh_key: "/home/user/.ssh/id_rsa"
   ```

4. **Deploy**:
   ```bash
   ./scripts/deploy-with-config.sh 192.168.1.100
   ```

### Custom Pi User

If your Pi uses a different username:

```yaml
deployment:
  pi:
    user: "myuser"
    directory: "/home/myuser/kindle-sync"
```

### Custom SSH Port

If your Pi uses a non-standard SSH port:

```yaml
deployment:
  pi:
    port: 2222
```

### Skip Steps for Faster Deployment

If you've already set up Docker or want to skip certain steps:

```yaml
deployment:
  options:
    skip_docker: true                 # Skip Docker installation
    skip_build: false                 # Still build the image
    skip_config: true                 # Skip config setup
```

## Command Line Overrides

You can still override config file settings with command line options:

```bash
# Use config file but override user and SSH key
./scripts/deploy-to-pi.sh --config config.yaml -u myuser -k ~/.ssh/my_key 192.168.1.100

# Use config file but skip Docker installation
./scripts/deploy-to-pi.sh --config config.yaml --skip-docker 192.168.1.100
```

## Dry Run Mode

Test your deployment without making changes:

```bash
./scripts/deploy-with-config.sh --dry-run 192.168.1.100
```

This will show you exactly what commands would be executed without actually running them.

## Troubleshooting

### SSH Connection Issues

1. **Test SSH connection manually**:
   ```bash
   ssh pi@192.168.1.100
   ```

2. **Check SSH key permissions**:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   chmod 644 ~/.ssh/id_rsa.pub
   ```

3. **Verify SSH key path in config**:
   ```yaml
   deployment:
     pi:
       ssh_key: "/home/user/.ssh/id_rsa"  # Use absolute path
   ```

### Configuration Issues

1. **Validate your config**:
   ```bash
   ./scripts/setup-env.sh --validate-config
   ```

2. **Show current configuration**:
   ```bash
   ./scripts/setup-env.sh --show-config
   ```

3. **Check if yq is installed** (for advanced config parsing):
   ```bash
   # Install yq if needed
   sudo apt install yq
   # or
   pip install yq
   ```

### Permission Issues

1. **Make sure scripts are executable**:
   ```bash
   chmod +x scripts/*.sh
   ```

2. **Check Pi user permissions**:
   ```bash
   # On the Pi, make sure the user can write to the target directory
   sudo chown -R pi:pi /home/pi/kindle-sync
   ```

## Best Practices

1. **Use SSH keys** instead of passwords for security
2. **Test with dry run** before actual deployment
3. **Keep your config.yaml** in version control (without sensitive data)
4. **Use absolute paths** for SSH keys
5. **Validate configuration** before deployment
6. **Backup your Pi** before major deployments

## Quick Reference

| Command | Description |
|---------|-------------|
| `./scripts/deploy-with-config.sh IP` | Deploy using config.yaml |
| `./scripts/deploy-with-config.sh --dry-run IP` | Test deployment |
| `./scripts/deploy-to-pi.sh --config config.yaml IP` | Deploy with config override |
| `./scripts/setup-env.sh --show-config` | Show current config |
| `./scripts/setup-env.sh --validate-config` | Validate config |
