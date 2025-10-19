# Kindle Scribe ↔ Obsidian Sync System

An automated system for syncing documents between your Kindle Scribe and Obsidian vault, enabling a seamless writing and annotation workflow.

## 📚 Documentation

**📖 [Comprehensive Tutorial](docs/COMPREHENSIVE_TUTORIAL.md)** - Complete guide from setup to production  
**📋 [Documentation Index](docs/README.md)** - All documentation organized by topic  
**⚙️ [Configuration Guide](docs/CONFIGURATION_GUIDE.md)** - Detailed configuration options  
**🚀 [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Deployment strategies and options

## 🚀 Quick Start

1. **Clone and setup:**
   ```bash
   git clone https://github.com/haydentwestbrook/kindle-sync.git
   cd kindle-sync
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure:**
   ```bash
   cp config.yaml.example config.yaml
   nano config.yaml  # Edit with your settings
   ```

3. **Test:**
   ```bash
   python3 test_app.py
   ```

4. **Deploy:**
   ```bash
   # Local
   python3 main_enhanced.py
   
   # Docker
   docker-compose up -d
   
   # Raspberry Pi
   ./scripts/deploy-to-pi.sh 192.168.1.100
   ```

**For detailed instructions, see the [Comprehensive Tutorial](docs/COMPREHENSIVE_TUTORIAL.md).**

## Workflow Overview

1. **Write on Kindle Scribe** → Export as PDF
2. **Extract text from PDF** → Convert to Markdown in Obsidian
3. **Edit in Obsidian** → Write second drafts in Markdown
4. **Convert Markdown to PDF** → Optimized for Kindle Scribe
5. **Send PDF to Kindle** → For annotation and review

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kindle Scribe │    │   Sync System    │    │  Obsidian Vault │
│                 │    │                  │    │                 │
│ • Handwritten   │◄──►│ • File Watcher   │◄──►│ • Markdown      │
│   Notes         │    │ • PDF Converter  │    │   Files         │
│ • PDFs          │    │ • Kindle Sync    │    │ • Templates     │
│ • Annotations   │    │ • OCR Processing │    │ • Plugins       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features

- **Automated File Watching**: Monitors Obsidian vault for changes
- **PDF ↔ Markdown Conversion**: Bidirectional conversion with OCR
- **Kindle-Optimized PDFs**: Proper formatting for Kindle Scribe
- **Email Integration**: Send to Kindle via email
- **USB Sync**: Direct file transfer when connected
- **Template System**: Consistent formatting across documents

## Requirements

- Python 3.8+
- Obsidian with required plugins
- Kindle Scribe with Send to Kindle email configured
- Internet connection for email sync

## Installation

### Docker Deployment (Recommended for Raspberry Pi)

1. **Clone this repository**
   ```bash
   git clone <repository-url>
   cd kindle-sync
   ```

2. **Run the Docker setup script**
   ```bash
   chmod +x scripts/docker-setup.sh
   ./scripts/docker-setup.sh
   ```

3. **Configure your settings**
   - Edit `config.yaml` with your Obsidian vault path and Kindle email
   - Edit `.env` with your environment variables
   - Update volume paths in `docker-compose.yml`

4. **Start the container**
   ```bash
   docker-compose up -d
   ```

5. **Monitor the system**
   ```bash
   ./scripts/docker-commands.sh status
   docker-compose logs -f
   ```

### Local Installation

1. **Clone this repository**
   ```bash
   git clone <repository-url>
   cd kindle-sync
   ```

2. **Run the installation script**
   ```bash
   # Linux/macOS
   ./scripts/install.sh
   
   # Windows
   scripts\install.bat
   ```

3. **Configure your settings**
   - Copy `config.yaml.example` to `config.yaml`
   - Edit with your Obsidian vault path and Kindle email
   - Set up SMTP credentials

4. **Start the sync system**
   ```bash
   python main.py start
   ```

### Manual Installation

1. Install Python dependencies: `pip install -r requirements.txt`
2. Install system dependencies for OCR (see SETUP.md)
3. Configure your settings in `config.yaml`
4. Set up Obsidian plugins
5. Run the sync system

## Usage

### Docker Deployment

1. **Start the container**: `docker-compose up -d`
2. **Write on your Kindle Scribe**
3. **Export documents and place in the sync folder**
4. **Edit markdown files in Obsidian**
5. **PDFs are automatically generated and sent to Kindle**

### Local Installation

1. Start the sync system: `python main.py start`
2. Write on your Kindle Scribe
3. Export documents and place in the sync folder
4. Edit markdown files in Obsidian
5. PDFs are automatically generated and sent to Kindle

### Management Commands

**Docker:**
```bash
./scripts/docker-commands.sh start    # Start container
./scripts/docker-commands.sh stop     # Stop container
./scripts/docker-commands.sh logs     # View logs
./scripts/docker-commands.sh status   # Check status
```

**Local:**
```bash
python main.py start                  # Start sync system
python main.py sync-from-kindle       # Sync from Kindle
python main.py cleanup                # Clean up old files
python main.py stats                  # View statistics
```

## Configuration

### Docker Deployment

- **`config.yaml`**: Main configuration file
- **`.env`**: Environment variables
- **`docker-compose.yml`**: Container configuration
- **`docker-compose.override.yml`**: Custom overrides

### Local Installation

See `config.yaml` for detailed configuration options including:
- Obsidian vault path
- Kindle email address
- Sync folders
- PDF formatting options
- OCR settings

## Documentation

- **[Docker Deployment Guide](docs/DOCKER.md)** - Complete Docker setup and management
- **[Setup Guide](docs/SETUP.md)** - Detailed installation instructions
- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage instructions

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section in the documentation
2. Review the log files
3. Create an issue on the project repository
