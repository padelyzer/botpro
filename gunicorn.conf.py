#!/usr/bin/env python3
"""
=============================================================================
BotPhia Trading API - Production Gunicorn Configuration
=============================================================================
Optimized production configuration for high-performance trading operations
"""

import os
import multiprocessing
from gunicorn.glogging import Logger
import structlog

# =============================================================================
# Server Configuration
# =============================================================================

# Bind to all interfaces on port 8080
bind = "0.0.0.0:8080"

# Worker Configuration
# Use number of CPU cores * 2 + 1 for optimal performance
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Worker class for async applications
worker_class = "uvicorn.workers.UvicornWorker"

# Worker connections (for async workers)
worker_connections = int(os.environ.get("GUNICORN_WORKER_CONNECTIONS", 1000))

# Maximum requests per worker before restart (prevents memory leaks)
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 100))

# Worker timeout settings
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 30))

# =============================================================================
# Security Configuration
# =============================================================================

# Limit request header size
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# SSL Configuration (if enabled)
keyfile = os.environ.get("SSL_KEYFILE")
certfile = os.environ.get("SSL_CERTFILE")
ca_certs = os.environ.get("SSL_CA_CERTS")

# Security headers
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# =============================================================================
# Process Management
# =============================================================================

# Process names for monitoring
proc_name = "botphia-trading-api"

# User and group (ensure these exist in container)
user = "botphia"
group = "botphia"

# Working directory
chdir = "/app"

# Daemon mode (set to False for container deployment)
daemon = False

# PID file
pidfile = "/app/data/gunicorn.pid"

# Temporary directory
tmp_upload_dir = "/app/data/tmp"

# =============================================================================
# Logging Configuration
# =============================================================================

# Log level
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Log files
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"

# Access log format with detailed information
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s %(p)s'

# Disable access log to stdout in production (use file logging)
disable_redirect_access_to_syslog = True

# Log configuration
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'json',
            'filename': '/app/logs/gunicorn.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'gunicorn.error': {
            'level': loglevel.upper(),
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['file'],
            'propagate': False,
        },
    },
    'root': {
        'level': loglevel.upper(),
        'handlers': ['console'],
    }
}

# =============================================================================
# Performance Tuning
# =============================================================================

# Preload application for better performance
preload_app = True

# Enable SO_REUSEPORT for better load balancing
reuse_port = True

# Worker restart threshold
max_worker_memory = int(os.environ.get("MAX_WORKER_MEMORY", 200 * 1024 * 1024))  # 200MB

# =============================================================================
# Health Checks and Monitoring
# =============================================================================

def when_ready(server):
    """Called when the server is ready to serve requests"""
    server.log.info("BotPhia Trading API server ready to serve requests")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal"""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called before forking a worker"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_fork(server, worker):
    """Called after forking a worker"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_worker_init(worker):
    """Called after a worker has been forked"""
    worker.log.info(f"Worker initialized (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal"""
    worker.log.info(f"Worker aborted (pid: {worker.pid})")

def pre_exec(server):
    """Called before exec-ing into a new process"""
    server.log.info("Forked child, re-executing")

def on_exit(server):
    """Called when the server is shutting down"""
    server.log.info("BotPhia Trading API server shutting down")

def on_reload(server):
    """Called when the server is reloaded"""
    server.log.info("BotPhia Trading API server reloaded")

# =============================================================================
# Environment-specific overrides
# =============================================================================

# Development overrides
if os.environ.get("ENVIRONMENT", "production").lower() == "development":
    reload = True
    workers = 1
    loglevel = "debug"
    accesslog = "-"  # Log to stdout in development

# Production optimizations
if os.environ.get("ENVIRONMENT", "production").lower() == "production":
    preload_app = True
    worker_class = "uvicorn.workers.UvicornWorker"
    
    # Enable memory monitoring in production
    def worker_memory_monitor(worker):
        \"\"\"Monitor worker memory usage\"\"\"
        import psutil
        process = psutil.Process(worker.pid)
        memory_info = process.memory_info()
        if memory_info.rss > max_worker_memory:
            worker.log.warning(f"Worker {worker.pid} using {memory_info.rss / 1024 / 1024:.1f}MB, restarting")
            worker.alive = False

# =============================================================================
# Custom Logger Class
# =============================================================================

class StructuredLogger(Logger):
    \"\"\"Custom logger with structured logging for better monitoring\"\"\"
    
    def setup(self, cfg):
        super().setup(cfg)
        # Configure structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

# Use custom logger
logger_class = StructuredLogger