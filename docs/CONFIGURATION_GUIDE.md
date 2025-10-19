# Configuration Guide

## Overview

The Kindle Sync system uses a centralized `config.yaml` file to manage all configuration settings, environment variables, and deployment options. This approach provides better organization, validation, and maintainability compared to scattered environment variables.

## Quick Start

### 1. Create Configuration File

```bash
# Create config.yaml from template
./scripts/setup-env.sh --create-config
```

### 2. Customize Your Settings

Edit the `config.yaml` file with your specific settings:

```bash
nano config.yaml
```

### 3. Validate Configuration

```bash
# Validate your configuration
./scripts/setup-env.sh --validate-config
```

### 4. Generate Environment Variables (Optional)

If you need environment variables for scripts:

```bash
# Generate .env file from config.yaml
./scripts/setup-env.sh --setup-env
```

## Configuration Structure

The `config.yaml` file is organized into logical sections:

### System Configuration
```yaml
system:
  timezone: "America/New_York"
  project_dir: "/home/pi/kindle-sync"
  user: "pi"
```

### Obsidian Configuration
```yaml
obsidian:
  vault_path: "/home/pi/obsidian-vault"
  sync_folder: "Kindle Sync"
  templates_folder: "Templates"
  backups_folder: "Backups"
```

### Kindle Configuration
```yaml
kindle:
  email: "your-kindle@kindle.com"
  approved_senders:
    - "your-email@gmail.com"
  usb_path: "/media/pi/Kindle/documents"
```

### Email/SMTP Configuration
```yaml
email:
  smtp:
    host: "smtp.gmail.com"
    port: 587
    username: "your-email@gmail.com"
    password: "your-app-password"
    use_tls: true
```

### Docker Configuration
```yaml
docker:
  container:
    name: "kindle-sync"
    image: "kindle-sync"
  resources:
    memory_limit: "512m"
    cpu_limit: "1.0"
```

## Setup Script Commands

The `scripts/setup-env.sh` script provides several commands:

### `--create-config`
Creates a new `config.yaml` file from the template with system-specific defaults.

### `--validate-config`
Validates the existing `config.yaml` file for required settings and proper format.

### `--show-config`
Displays the current configuration in a readable format.

### `--setup-env`
Generates a `.env` file from the `config.yaml` settings for scripts that need environment variables.

### `--update-scripts`
Updates existing scripts to use the configuration file.

## Environment Variable Override

You can override any configuration setting using environment variables. The format is:

```
SECTION_SUBSECTION_SETTING=value
```

For example:
- `OBSIDIAN_VAULT_PATH=/custom/path` overrides `obsidian.vault_path`
- `KINDLE_EMAIL=custom@kindle.com` overrides `kindle.email`
- `SMTP_USERNAME=custom@gmail.com` overrides `email.smtp.username`

## Deployment Integration

The configuration system integrates with all deployment scripts:

### Raspberry Pi Deployment
```bash
# Deploy with custom configuration
./scripts/deploy-to-pi.sh 192.168.1.100
```

The deployment script will:
1. Copy your `config.yaml` to the Pi
2. Generate environment variables
3. Update Docker Compose files
4. Configure the system

### Docker Deployment
```bash
# Start with configuration
docker compose up -d
```

The Docker Compose file automatically uses settings from `config.yaml`.

## Best Practices

### 1. Version Control
- **DO** commit `config.yaml.example` to version control
- **DON'T** commit your actual `config.yaml` with sensitive data
- **DO** use environment variables for sensitive data in production

### 2. Security
- Use app-specific passwords for email accounts
- Store sensitive data in environment variables
- Use proper file permissions (644 for config files)

### 3. Organization
- Group related settings together
- Use descriptive section names
- Add comments for complex configurations

### 4. Validation
- Always validate configuration before deployment
- Test configuration changes in a development environment
- Use the validation script regularly

## Troubleshooting

### Configuration Not Loading
```bash
# Check if config.yaml exists and is valid
./scripts/setup-env.sh --validate-config
```

### Environment Variables Not Working
```bash
# Regenerate .env file from config.yaml
./scripts/setup-env.sh --setup-env
```

### Scripts Not Using Configuration
```bash
# Update scripts to use configuration
./scripts/setup-env.sh --update-scripts
```

### YAML Syntax Errors
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

## Advanced Configuration

### Custom Settings
Add custom settings to the `advanced.custom` section:

```yaml
advanced:
  custom:
    my_setting: "value"
    another_setting: 123
```

### Integration Settings
Configure external integrations:

```yaml
integrations:
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/..."
    channel: "#kindle-sync"

  discord:
    enabled: false
    webhook_url: ""
```

### Performance Tuning
Adjust performance settings:

```yaml
performance:
  max_concurrent_files: 5
  processing_timeout: 300
  memory_limit_mb: 512
```

## Migration from .env Files

If you're migrating from a `.env` file setup:

1. **Create new config.yaml**:
   ```bash
   ./scripts/setup-env.sh --create-config
   ```

2. **Copy your settings** from the old `.env` file to the appropriate sections in `config.yaml`

3. **Validate the configuration**:
   ```bash
   ./scripts/setup-env.sh --validate-config
   ```

4. **Generate new .env file** (if needed):
   ```bash
   ./scripts/setup-env.sh --setup-env
   ```

5. **Update scripts**:
   ```bash
   ./scripts/setup-env.sh --update-scripts
   ```

## Support

For configuration issues:
1. Check the validation output: `./scripts/setup-env.sh --validate-config`
2. Review the configuration: `./scripts/setup-env.sh --show-config`
3. Check the logs for specific error messages
4. Refer to the main documentation in `docs/`
