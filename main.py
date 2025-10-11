#!/usr/bin/env python3
"""Main entry point for the Kindle Scribe ↔ Obsidian Sync System."""

import sys
import signal
import time
from pathlib import Path
from loguru import logger
import click

from src.config import Config
from src.sync_processor import SyncProcessor
from src.email_receiver import EmailReceiver


class KindleSyncApp:
    """Main application class."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the application."""
        self.config = Config(config_path)
        self.processor = SyncProcessor(self.config)
        self.email_receiver = EmailReceiver(self.config)
        self.running = False
        self.last_email_check = 0
        
        # Set up logging
        self._setup_logging()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """Set up logging configuration."""
        logging_config = self.config.get_logging_config()
        
        # Remove default logger
        logger.remove()
        
        # Add console logger
        logger.add(
            sys.stderr,
            level=logging_config.get('level', 'INFO'),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        # Add file logger
        log_file = logging_config.get('file', 'kindle_sync.log')
        logger.add(
            log_file,
            level=logging_config.get('level', 'INFO'),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=logging_config.get('max_size', '10MB'),
            retention=logging_config.get('backup_count', 5)
        )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _check_emails(self):
        """Check for new emails periodically."""
        current_time = time.time()
        check_interval = self.email_receiver.imap_config.get("check_interval", 300)
        
        # Check if it's time to check emails
        if current_time - self.last_email_check >= check_interval:
            try:
                logger.debug("Starting email check...")
                
                # Process new emails
                processed_files = self.email_receiver.check_for_new_emails()
                
                if processed_files:
                    logger.info(f"Processed {len(processed_files)} PDF files from emails")
                    
                    # Trigger file processing for each PDF
                    for pdf_path in processed_files:
                        # The file watcher should pick up these new files automatically
                        # But we can also trigger processing directly if needed
                        logger.info(f"New PDF from email: {pdf_path}")
                else:
                    logger.debug("No new PDF files found in emails")
                
                self.last_email_check = current_time
                logger.debug("Email check completed successfully")
                
            except Exception as e:
                logger.error(f"Error checking emails: {e}")
                # Still update the last check time to avoid rapid retries
                self.last_email_check = current_time
    
    def start(self):
        """Start the sync system."""
        try:
            logger.info("Starting Kindle Scribe ↔ Obsidian Sync System")
            
            # Start the processor
            if not self.processor.start():
                logger.error("Failed to start sync processor")
                return False
            
            self.running = True
            
            # Main loop
            while self.running:
                time.sleep(1)
                
                # Check if file watcher is still alive
                if not self.processor.file_watcher.is_alive():
                    logger.error("File watcher stopped unexpectedly")
                    break
                
                # Check for new emails periodically
                self._check_emails()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            return False
        finally:
            self.stop()
    
    def stop(self):
        """Stop the sync system."""
        logger.info("Stopping sync system...")
        self.processor.stop()
        self.running = False
        logger.info("Sync system stopped")
    
    def get_stats(self):
        """Get processing statistics."""
        return self.processor.get_statistics()


@click.group()
def cli():
    """Kindle Scribe ↔ Obsidian Sync System."""
    pass


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon')
def start(config: str, daemon: bool):
    """Start the sync system."""
    app = KindleSyncApp(config)
    
    if daemon:
        # TODO: Implement daemon mode
        click.echo("Daemon mode not yet implemented")
        return
    
    try:
        app.start()
    except KeyboardInterrupt:
        click.echo("\nShutdown requested by user")
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
@click.option('--kindle-path', '-k', help='Path to Kindle documents folder')
def sync_from_kindle(config: str, kindle_path: str):
    """Sync documents from Kindle to Obsidian."""
    app = KindleSyncApp(config)
    
    try:
        kindle_path_obj = Path(kindle_path) if kindle_path else None
        synced_count = app.processor.sync_from_kindle(kindle_path_obj)
        click.echo(f"Synced {synced_count} files from Kindle")
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
@click.option('--max-age', '-a', default=30, help='Maximum age in days for cleanup')
def cleanup(config: str, max_age: int):
    """Clean up old files."""
    app = KindleSyncApp(config)
    
    try:
        cleaned_count = app.processor.cleanup_old_files(max_age)
        click.echo(f"Cleaned up {cleaned_count} old files")
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
def stats(config: str):
    """Show processing statistics."""
    app = KindleSyncApp(config)
    
    try:
        stats = app.get_stats()
        click.echo("Processing Statistics:")
        for key, value in stats.items():
            click.echo(f"  {key}: {value}")
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
def validate(config: str):
    """Validate configuration."""
    try:
        app = KindleSyncApp(config)
        if app.config.validate():
            click.echo("Configuration is valid")
        else:
            click.echo("Configuration validation failed")
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
