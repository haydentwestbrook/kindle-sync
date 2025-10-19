# 📚 Kindle Scribe ↔ Obsidian Sync System - Comprehensive Tutorial

## 🎯 Overview

This comprehensive tutorial will guide you through the complete setup, testing, and deployment of the Kindle Scribe ↔ Obsidian Sync System. This system automatically syncs documents between your Obsidian vault and your Kindle Scribe device, supporting both Markdown to PDF conversion and PDF to Markdown conversion with OCR.

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Deployment Options](#deployment-options)
7. [Production Deployment](#production-deployment)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

---

## 🏗️ System Overview

### What This System Does
- **Watches** your Obsidian vault for new or modified Markdown files
- **Converts** Markdown files to PDF format optimized for Kindle
- **Sends** PDFs to your Kindle via email
- **Receives** emails with PDF attachments and converts them to Markdown
- **Tracks** all operations with comprehensive logging and metrics
- **Monitors** system health and performance

### Key Features
- ✅ **Automated File Watching** - Monitors Obsidian vault for changes
- ✅ **PDF Conversion** - High-quality Markdown to PDF conversion
- ✅ **Email Integration** - Sends to Kindle, receives from any source
- ✅ **OCR Support** - Converts PDF images to searchable Markdown
- ✅ **Health Monitoring** - Comprehensive system health checks
- ✅ **Metrics & Logging** - Detailed performance and operation tracking
- ✅ **Docker Support** - Easy deployment with containers
- ✅ **Raspberry Pi Ready** - Optimized for low-power devices

### Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Obsidian      │    │   Kindle Sync    │    │   Kindle        │
│   Vault         │◄──►│   System         │◄──►│   Device        │
│                 │    │                  │    │                 │
│ • Markdown      │    │ • File Watcher   │    │ • PDF Reader    │
│ • Templates     │    │ • PDF Converter  │    │ • Email Client  │
│ • Sync Folder   │    │ • Email Handler  │    │ • Document      │
└─────────────────┘    │ • Health Monitor │    │   Storage       │
                       │ • Metrics        │    └─────────────────┘
                       └──────────────────┘
```

---

## 🔧 Prerequisites

### System Requirements
- **Python 3.11+** (3.9+ for Raspberry Pi)
- **Git** for version control
- **Docker** (optional, for containerized deployment)
- **Internet connection** for email services

### Required System Packages
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# For PDF conversion and OCR
sudo apt install -y tesseract-ocr tesseract-ocr-eng poppler-utils

# For Docker (optional)
sudo apt install -y docker.io docker-compose
```

### Email Requirements
- **Gmail account** with app-specific password
- **Kindle email address** (from your Amazon account)
- **SMTP access** enabled in Gmail settings

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/haydentwestbrook/kindle-sync.git
cd kindle-sync
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

### 3. Install Pre-commit Hooks (Optional)
```bash
pre-commit install
```

### 4. Set Up Configuration
```bash
# Copy example configuration
cp config.yaml.example config.yaml

# Edit configuration
nano config.yaml
```

---

## ⚙️ Configuration

### Basic Configuration (`config.yaml`)

```yaml
# Obsidian Configuration
obsidian:
  vault_path: "/path/to/your/obsidian/vault"
  sync_folder: "kindle"  # Folder within vault for sync files
  templates_folder: "Templates"
  watch_subfolders: true

# Kindle Configuration
kindle:
  email: "your-kindle@kindle.com"
  approved_senders:
    - "your-email@gmail.com"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "your-email@gmail.com"
  smtp_password: "your-app-password"  # Use app-specific password

# Email Receiving Configuration
email_receiving:
  enabled: true
  imap_server: "imap.gmail.com"
  imap_port: 993
  username: "your-email@gmail.com"
  password: "your-app-password"
  check_interval: 300  # Check every 5 minutes
```

### Advanced Configuration

See [Configuration Guide](CONFIGURATION_GUIDE.md) for detailed configuration options including:
- Database settings
- Monitoring configuration
- Security settings
- Performance tuning

---

## 🧪 Testing

### 1. Run the Test Suite
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run performance benchmarks
pytest tests/benchmarks/ --benchmark-only
```

### 2. Test Core Functionality
```bash
# Test configuration loading
python3 -c "from src.config import Config; config = Config(); print('Config loaded successfully')"

# Test PDF conversion
python3 -c "
from src.pdf_converter import MarkdownToPDFConverter
from src.config import Config
import tempfile
from pathlib import Path

config = Config()
converter = MarkdownToPDFConverter(config)

# Create test markdown
with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    f.write('# Test Document\n\nThis is a test.')
    md_path = Path(f.name)

# Convert to PDF
pdf_path = converter.convert_markdown_to_pdf(md_path)
print(f'PDF created: {pdf_path}')
print(f'Size: {pdf_path.stat().st_size} bytes')
"

# Test file watcher
python3 -c "
from src.file_watcher import ObsidianFileWatcher
from src.config import Config
config = Config()
watcher = ObsidianFileWatcher(config, lambda path: print(f'File changed: {path}'))
print('File watcher initialized successfully')
"
```

### 3. Integration Testing
```bash
# Test complete workflow
python3 test_app.py
```

For detailed testing information, see:
- [Testing Plan](TESTING_PLAN.md)
- [Test Results](TEST_RESULTS.md)
- [Local Testing Plan](LOCAL_TESTING_PLAN.md)

---

## 🚀 Deployment Options

### Option 1: Local Development
```bash
# Run directly
python3 main_enhanced.py

# Run with specific config
python3 main_enhanced.py --config /path/to/config.yaml
```

### Option 2: Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t kindle-sync .
docker run -d --name kindle-sync \
  -v /path/to/obsidian:/app/data/obsidian \
  -v /path/to/config.yaml:/app/config.yaml \
  kindle-sync
```

### Option 3: Raspberry Pi Deployment
```bash
# Use the automated deployment script
./scripts/deploy-to-pi.sh 192.168.1.100

# Or deploy manually
ssh pi@192.168.1.100
git clone https://github.com/haydentwestbrook/kindle-sync.git
cd kindle-sync
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

For detailed deployment guides, see:
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Docker Guide](DOCKER.md)
- [Raspberry Pi Deployment](RASPBERRY_PI_DEPLOYMENT.md)
- [Deployment Success](DEPLOYMENT_SUCCESS.md)

---

## 🏭 Production Deployment

### 1. System Service Setup
```bash
# Create systemd service file
sudo nano /etc/systemd/system/kindle-sync.service
```

**Service file content:**
```ini
[Unit]
Description=Kindle Scribe Obsidian Sync Service
After=network.target

[Service]
User=your-username
Group=your-group
WorkingDirectory=/path/to/kindle-sync
ExecStart=/path/to/kindle-sync/venv/bin/python /path/to/kindle-sync/main_enhanced.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable kindle-sync
sudo systemctl start kindle-sync
sudo systemctl status kindle-sync
```

### 3. Set Up Monitoring
```bash
# Start Prometheus exporter
python3 -m src.monitoring.prometheus_exporter

# Access metrics at http://localhost:8000/metrics
# Access health check at http://localhost:8000/health
```

### 4. Configure Log Rotation
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/kindle-sync
```

**Logrotate configuration:**
```
/var/log/kindle-sync/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 your-username your-group
}
```

---

## 📊 Monitoring & Maintenance

### Health Monitoring
- **Health Endpoint:** `http://localhost:8000/health`
- **Metrics Endpoint:** `http://localhost:8000/metrics`
- **Logs:** `journalctl -u kindle-sync -f`

### Key Metrics to Monitor
- `kindle_sync_processed_files_total` - Total files processed
- `kindle_sync_processing_errors_total` - Processing errors
- `kindle_sync_processing_duration_seconds` - Processing time
- `kindle_sync_health_status` - System health status

### Grafana Dashboard
Import the dashboard from `monitoring/grafana-dashboard.json` to visualize:
- File processing rates
- Error rates
- Processing duration
- System health

### Alerting Rules
Configure Prometheus alerting rules from `monitoring/alerting-rules.yml`:
- High processing errors
- Service down
- High processing duration
- Health check failures

For detailed operational procedures, see [Operational Runbooks](OPERATIONAL_RUNBOOKS.md).

---

## 🔧 Troubleshooting

### Common Issues

#### 1. PDF Conversion Fails
```bash
# Check WeasyPrint installation
python3 -c "import weasyprint; print('WeasyPrint OK')"

# Check system dependencies
sudo apt install -y tesseract-ocr poppler-utils

# Test with ReportLab fallback
# (Already implemented in the code)
```

#### 2. Email Sending Fails
```bash
# Check SMTP configuration
python3 -c "from src.kindle_sync import KindleSync; print('Kindle sync OK')"

# Verify Gmail app password
# Check Gmail settings for app-specific passwords
```

#### 3. File Watching Not Working
```bash
# Check directory permissions
ls -la /path/to/obsidian/vault

# Test file watcher manually
python3 -c "from src.file_watcher import ObsidianFileWatcher; print('File watcher OK')"
```

#### 4. Database Issues
```bash
# Check database file permissions
ls -la /path/to/database.db

# Test database connection
python3 -c "from src.database.manager import DatabaseManager; print('Database OK')"
```

### Debug Mode
```bash
# Run with debug logging
LOG_LEVEL=DEBUG python3 main_enhanced.py

# Check logs
tail -f logs/kindle-sync.log
```

### Network Issues
If you encounter DNS resolution issues:
```bash
# Fix DNS configuration
sudo cp /etc/resolv.conf /etc/resolv.conf.backup
echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf
echo 'nameserver 8.8.4.4' | sudo tee -a /etc/resolv.conf

# Test connectivity
ping github.com
```

---

## 🚀 Advanced Features

### Phase 1: Security & Reliability
- ✅ Input validation and sanitization
- ✅ Error handling and retry mechanisms
- ✅ Secrets management
- ✅ Health checks and monitoring

### Phase 2: Performance & Architecture
- ✅ Asynchronous processing
- ✅ Database integration
- ✅ Metrics collection
- ✅ Configuration management

### Phase 3: Quality & Operations
- ✅ Comprehensive testing suite
- ✅ Code quality tools (Black, isort, Flake8, MyPy)
- ✅ CI/CD pipeline
- ✅ Performance benchmarks

### Phase 4: Advanced Features
- ✅ Distributed tracing with OpenTelemetry
- ✅ Caching layer (memory and Redis)
- ✅ Rate limiting
- ✅ Business metrics and analytics

For detailed implementation information, see [Implementation Summary](IMPLEMENTATION_SUMMARY.md) and [Design Improvements](DESIGN_IMPROVEMENTS.md).

---

## 📚 Additional Resources

### Documentation Files
- [Configuration Guide](CONFIGURATION_GUIDE.md) - Detailed configuration options
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Deployment strategies
- [Docker Guide](DOCKER.md) - Container deployment
- [Raspberry Pi Deployment](RASPBERRY_PI_DEPLOYMENT.md) - Pi-specific setup
- [Testing Guide](TESTING.md) - Testing procedures
- [Operational Runbooks](OPERATIONAL_RUNBOOKS.md) - Operations procedures

### Scripts
- `scripts/deploy-to-pi.sh` - Automated Pi deployment
- `scripts/docker-setup.sh` - Docker environment setup
- `scripts/run-tests.sh` - Test execution
- `fix_dns_and_push.sh` - DNS fix and git push

### Configuration Files
- `config.yaml` - Main configuration
- `docker-compose.yml` - Docker Compose setup
- `pyproject.toml` - Code quality tools configuration
- `.pre-commit-config.yaml` - Pre-commit hooks

---

## 🎯 Quick Start Checklist

### For New Users
- [ ] Clone the repository
- [ ] Set up Python environment
- [ ] Install dependencies
- [ ] Configure `config.yaml`
- [ ] Set up Gmail app password
- [ ] Test core functionality
- [ ] Deploy to your preferred platform
- [ ] Set up monitoring
- [ ] Start the service

### For Developers
- [ ] Set up development environment
- [ ] Install development dependencies
- [ ] Configure pre-commit hooks
- [ ] Run test suite
- [ ] Set up IDE with type checking
- [ ] Review code quality tools
- [ ] Test Docker build
- [ ] Deploy to test environment

### For Production
- [ ] Set up production environment
- [ ] Configure system service
- [ ] Set up monitoring and alerting
- [ ] Configure log rotation
- [ ] Set up backup procedures
- [ ] Test disaster recovery
- [ ] Document operational procedures
- [ ] Train operations team

---

## 🆘 Support

### Getting Help
1. **Check the documentation** - Most issues are covered in the guides above
2. **Review logs** - Check application and system logs for error details
3. **Run health checks** - Use the health endpoint to diagnose issues
4. **Test components** - Use the test scripts to isolate problems

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

### Reporting Issues
When reporting issues, please include:
- System information (OS, Python version, etc.)
- Configuration (sanitized)
- Error logs
- Steps to reproduce
- Expected vs actual behavior

---

## 🎉 Conclusion

This comprehensive tutorial covers everything you need to know to set up, test, and deploy the Kindle Scribe ↔ Obsidian Sync System. The system is designed to be robust, scalable, and easy to maintain, with comprehensive monitoring and operational procedures.

**Key Success Factors:**
- ✅ Proper configuration setup
- ✅ Thorough testing before deployment
- ✅ Monitoring and alerting in place
- ✅ Regular maintenance and updates
- ✅ Backup and recovery procedures

**Next Steps:**
1. Follow the Quick Start Checklist
2. Deploy to your preferred platform
3. Set up monitoring and alerting
4. Start syncing your documents!

Happy syncing! 📚✨
