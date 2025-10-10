"""File watcher for monitoring Obsidian vault changes."""

import time
from pathlib import Path
from typing import Callable, Set, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileMovedEvent
from loguru import logger

from .config import Config


class ObsidianFileHandler(FileSystemEventHandler):
    """Handler for Obsidian file system events."""
    
    def __init__(self, config: Config, callback: Callable[[Path], None]):
        """Initialize the file handler."""
        self.config = config
        self.callback = callback
        self.processed_files: Set[Path] = set()
        self.debounce_time = config.get('advanced.debounce_time', 2.0)
        self.pending_files: dict = {}
        
        # Get file patterns
        self.markdown_pattern = config.get('patterns.markdown_files', '*.md')
        self.pdf_pattern = config.get('patterns.pdf_files', '*.pdf')
        
        logger.info("Obsidian file handler initialized")
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed based on patterns and settings."""
        # Check if file matches patterns
        if not (file_path.match(self.markdown_pattern) or file_path.match(self.pdf_pattern)):
            return False
        
        # Check file size
        max_size = self.config.get('advanced.max_file_size', '50MB')
        max_size_bytes = self._parse_size(max_size)
        if file_path.stat().st_size > max_size_bytes:
            logger.warning(f"File too large to process: {file_path}")
            return False
        
        # Check if file is in sync folder
        sync_folder = self.config.get_sync_folder_path()
        try:
            file_path.relative_to(sync_folder)
            return True
        except ValueError:
            # File is not in sync folder, check if we should watch subfolders
            if self.config.get('obsidian.watch_subfolders', True):
                return True
            return False
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes."""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _schedule_processing(self, file_path: Path):
        """Schedule file processing with debouncing."""
        current_time = time.time()
        
        # Cancel previous processing if file was modified again
        if file_path in self.pending_files:
            self.pending_files[file_path].cancel()
        
        # Schedule new processing
        import threading
        timer = threading.Timer(self.debounce_time, self._process_file, args=[file_path])
        timer.start()
        self.pending_files[file_path] = timer
        
        logger.debug(f"Scheduled processing for {file_path} in {self.debounce_time}s")
    
    def _process_file(self, file_path: Path):
        """Process a file after debounce period."""
        try:
            # Remove from pending
            if file_path in self.pending_files:
                del self.pending_files[file_path]
            
            # Check if file still exists and is recent
            if not file_path.exists():
                logger.debug(f"File no longer exists: {file_path}")
                return
            
            # Check if file was recently modified
            current_time = time.time()
            file_mtime = file_path.stat().st_mtime
            if current_time - file_mtime < self.debounce_time:
                logger.debug(f"File still being modified: {file_path}")
                return
            
            # Process the file
            logger.info(f"Processing file: {file_path}")
            self.callback(file_path)
            self.processed_files.add(file_path)
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if self._should_process_file(file_path):
            self._schedule_processing(file_path)
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if self._should_process_file(file_path):
            self._schedule_processing(file_path)
    
    def on_moved(self, event):
        """Handle file move events."""
        if event.is_directory:
            return
        
        # Handle both source and destination
        if hasattr(event, 'dest_path'):
            dest_path = Path(event.dest_path)
            if self._should_process_file(dest_path):
                self._schedule_processing(dest_path)


class ObsidianFileWatcher:
    """File watcher for Obsidian vault."""
    
    def __init__(self, config: Config, callback: Callable[[Path], None]):
        """Initialize the file watcher."""
        self.config = config
        self.callback = callback
        self.observer = Observer()
        self.handler = ObsidianFileHandler(config, callback)
        self.is_running = False
        
        logger.info("Obsidian file watcher initialized")
    
    def start(self):
        """Start watching the Obsidian vault."""
        vault_path = self.config.get_obsidian_vault_path()
        
        if not vault_path.exists():
            logger.error(f"Obsidian vault path does not exist: {vault_path}")
            raise FileNotFoundError(f"Obsidian vault path does not exist: {vault_path}")
        
        # Create sync folder if it doesn't exist
        sync_folder = self.config.get_sync_folder_path()
        sync_folder.mkdir(parents=True, exist_ok=True)
        
        # Create templates folder if it doesn't exist
        templates_folder = self.config.get_templates_folder_path()
        templates_folder.mkdir(parents=True, exist_ok=True)
        
        # Start watching
        self.observer.schedule(
            self.handler,
            str(vault_path),
            recursive=self.config.get('obsidian.watch_subfolders', True)
        )
        
        self.observer.start()
        self.is_running = True
        
        logger.info(f"Started watching Obsidian vault: {vault_path}")
        logger.info(f"Sync folder: {sync_folder}")
        logger.info(f"Templates folder: {templates_folder}")
    
    def stop(self):
        """Stop watching the Obsidian vault."""
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("Stopped watching Obsidian vault")
    
    def is_alive(self) -> bool:
        """Check if the watcher is still running."""
        return self.observer.is_alive() if self.observer else False
