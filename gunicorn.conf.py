"""
Gunicorn Configuration for Stripe Dashboard Production Deployment
Dell Server Optimized Settings
"""

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Load application code before the worker processes are forked
preload_app = True

# Application
wsgi_module = "wsgi:application"

# Logging
accesslog = "/var/log/stripe-dashboard/access.log"
errorlog = "/var/log/stripe-dashboard/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "stripe-dashboard"

# Server mechanics
daemon = False
pidfile = "/var/run/stripe-dashboard/gunicorn.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = "/tmp"

# SSL (uncomment if using HTTPS)
# keyfile = "/path/to/ssl/private.key"
# certfile = "/path/to/ssl/certificate.crt"
# ssl_version = 2
# ciphers = "TLSv1.2"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
enable_stdio_inheritance = True
capture_output = True

# Environment variables
raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=/opt/stripe-dashboard',
]

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Stripe Dashboard server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Stripe Dashboard server is shutting down")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Stripe Dashboard server is reloading")