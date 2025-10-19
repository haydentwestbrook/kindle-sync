#!/usr/bin/env python3
"""Enhanced main entry point for the Kindle Scribe ↔ Obsidian Sync System with Phase 4 features."""

import asyncio
import signal
import sys
import time
from pathlib import Path
from loguru import logger
import click

from src.config import Config
from src.core.async_processor import AsyncSyncProcessor
from src.core.async_file_watcher import AsyncFileWatcher
from src.monitoring import HealthChecker, MetricsCollector, PrometheusExporter, PROMETHEUS_AVAILABLE
from src.database import DatabaseManager, DATABASE_AVAILABLE
from src.tracing import initialize_tracing, shutdown_tracing
from src.caching import initialize_cache_manager, get_cache_manager
from src.rate_limiting import initialize_rate_limiter, get_rate_limiter
from src.business_metrics import initialize_business_metrics, get_business_metrics


class EnhancedKindleSyncApp:
    """Enhanced application class with Phase 4 features."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the enhanced application."""
        self.config = Config(config_path)
        self.running = False
        
        # Core components
        self.db_manager = None
        self.processor = None
        self.file_watcher = None
        
        # Phase 4 components
        self.tracing_manager = None
        self.cache_manager = None
        self.rate_limiter = None
        self.business_metrics = None
        self.metrics_collector = None
        self.health_checker = None
        self.prometheus_exporter = None
        
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
        log_file = logging_config.get('file', 'logs/kindle_sync.log')
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
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
    
    async def initialize_components(self):
        """Initialize all application components."""
        logger.info("Initializing application components...")
        
        try:
            # Initialize database
            if DATABASE_AVAILABLE:
                db_path = Path(self.config.get("database.path", "data/kindle_sync.db"))
                self.db_manager = DatabaseManager(db_path)
                logger.info("Database manager initialized")
            
            # Initialize tracing
            tracing_config = self.config.get("tracing", {})
            if tracing_config.get("enabled", False):
                if initialize_tracing("kindle-sync", tracing_config):
                    logger.info("Distributed tracing initialized")
                else:
                    logger.warning("Failed to initialize distributed tracing")
            
            # Initialize caching
            cache_config = self.config.get("caching", {})
            if cache_config.get("enabled", True):
                cache_type = cache_config.get("type", "memory")
                if cache_type == "redis":
                    from src.caching.redis_cache import RedisCache
                    cache_backend = RedisCache(cache_config.get("redis", {}))
                else:
                    from src.caching.memory_cache import MemoryCache
                    cache_backend = MemoryCache(
                        max_size=cache_config.get("max_size", 1000),
                        default_ttl=cache_config.get("default_ttl", 3600)
                    )
                
                self.cache_manager = initialize_cache_manager(cache_backend)
                logger.info(f"Caching initialized with {cache_type} backend")
            
            # Initialize rate limiting
            rate_limit_config = self.config.get("rate_limiting", {})
            if rate_limit_config.get("enabled", True):
                limiter_type = rate_limit_config.get("type", "sliding_window")
                self.rate_limiter = initialize_rate_limiter(limiter_type, self.cache_manager)
                logger.info(f"Rate limiting initialized with {limiter_type} algorithm")
            
            # Initialize metrics
            self.metrics_collector = MetricsCollector(self.config, self.db_manager)
            await self.metrics_collector.start()
            logger.info("Metrics collector initialized")
            
            # Initialize business metrics
            self.business_metrics = initialize_business_metrics(self.metrics_collector)
            logger.info("Business metrics initialized")
            
            # Initialize health checker
            self.health_checker = HealthChecker(self.config, self.db_manager)
            logger.info("Health checker initialized")
            
            # Initialize processor
            self.processor = AsyncSyncProcessor(self.config, self.db_manager)
            logger.info("Async processor initialized")
            
            # Initialize file watcher
            self.file_watcher = AsyncFileWatcher(self.config, self.processor)
            logger.info("File watcher initialized")
            
            # Initialize Prometheus exporter
            if PROMETHEUS_AVAILABLE:
                monitoring_config = self.config.get("monitoring", {})
                if monitoring_config.get("enabled", True):
                    self.prometheus_exporter = PrometheusExporter(
                        self.config,
                        self.db_manager,
                        self.metrics_collector,
                        self.health_checker
                    )
                    logger.info("Prometheus exporter initialized")
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def start(self):
        """Start the application."""
        logger.info("Starting Kindle Sync application...")
        
        try:
            # Initialize components
            await self.initialize_components()
            
            # Start Prometheus exporter
            if self.prometheus_exporter:
                monitoring_config = self.config.get("monitoring", {})
                host = monitoring_config.get("exporter_host", "0.0.0.0")
                port = monitoring_config.get("exporter_port", 8080)
                
                # Start the web server in the background
                asyncio.create_task(self._start_prometheus_server(host, port))
                logger.info(f"Prometheus exporter started on {host}:{port}")
            
            # Start file watcher
            self.running = True
            await self.file_watcher.start()
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            await self.shutdown()
            raise
    
    async def _start_prometheus_server(self, host: str, port: int):
        """Start the Prometheus metrics server."""
        try:
            from aiohttp import web
            runner = web.AppRunner(self.prometheus_exporter.app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            logger.info(f"Prometheus server started on {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")
    
    async def shutdown(self):
        """Shutdown the application gracefully."""
        logger.info("Shutting down application...")
        
        try:
            # Stop file watcher
            if self.file_watcher:
                await self.file_watcher.stop()
                logger.info("File watcher stopped")
            
            # Stop metrics collection
            if self.metrics_collector:
                await self.metrics_collector.stop()
                logger.info("Metrics collector stopped")
            
            # Close database
            if self.db_manager:
                self.db_manager.close()
                logger.info("Database connection closed")
            
            # Shutdown tracing
            shutdown_tracing()
            logger.info("Tracing shutdown completed")
            
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def run_health_check(self):
        """Run health check and return status."""
        if self.health_checker:
            return await self.health_checker.run_all_checks()
        return {"status": "healthy", "message": "Health checker not available"}
    
    async def get_metrics_summary(self):
        """Get metrics summary."""
        summary = {}
        
        if self.metrics_collector:
            summary["system_metrics"] = self.metrics_collector.get_metrics_summary()
        
        if self.business_metrics:
            summary["business_metrics"] = self.business_metrics.get_business_summary()
        
        if self.cache_manager:
            summary["cache_stats"] = await self.cache_manager.get_stats()
        
        return summary


@click.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
@click.option('--health-check', is_flag=True, help='Run health check and exit')
@click.option('--metrics', is_flag=True, help='Show metrics and exit')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon')
def main(config: str, health_check: bool, metrics: bool, daemon: bool):
    """Enhanced Kindle Sync application with Phase 4 features."""
    
    app = EnhancedKindleSyncApp(config)
    
    async def run_app():
        if health_check:
            # Run health check
            await app.initialize_components()
            health_status = await app.run_health_check()
            print(f"Health Status: {health_status}")
            return
        
        if metrics:
            # Show metrics
            await app.initialize_components()
            metrics_summary = await app.get_metrics_summary()
            print(f"Metrics Summary: {metrics_summary}")
            return
        
        # Run the application
        try:
            await app.start()
            
            # Keep running until interrupted
            while app.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            await app.shutdown()
    
    # Run the application
    try:
        asyncio.run(run_app())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Failed to run application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
