"""
Production Logging Configuration for Stripe Dashboard
Dell Server Deployment
"""

import os
import logging
import logging.handlers
from datetime import datetime

def setup_production_logging(app):
    """Configure production-ready logging for Dell server deployment"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(app.root_path, '..', 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure log levels based on environment
    log_level = logging.INFO
    if app.config.get('DEBUG'):
        log_level = logging.DEBUG
    
    # Remove default Flask handlers
    for handler in app.logger.handlers:
        app.logger.removeHandler(handler)
    
    # Application log file with rotation
    app_log_file = os.path.join(log_dir, 'stripe_dashboard.log')
    app_handler = logging.handlers.RotatingFileHandler(
        app_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(log_level)
    
    # Error log file with rotation
    error_log_file = os.path.join(log_dir, 'stripe_dashboard_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    
    # Access log file for monitoring
    access_log_file = os.path.join(log_dir, 'stripe_dashboard_access.log')
    access_handler = logging.handlers.RotatingFileHandler(
        access_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3
    )
    access_handler.setLevel(logging.INFO)
    
    # Console handler for immediate monitoring
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s]: %(message)s'
    )
    
    access_formatter = logging.Formatter(
        '%(asctime)s - %(remote_addr)s - %(method)s %(url)s - %(status_code)s'
    )
    
    # Apply formatters
    app_handler.setFormatter(detailed_formatter)
    error_handler.setFormatter(detailed_formatter)
    console_handler.setFormatter(simple_formatter)
    access_handler.setFormatter(simple_formatter)
    
    # Add handlers to app logger
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
    
    # Set log level
    app.logger.setLevel(log_level)
    
    # Create separate logger for access logs
    access_logger = logging.getLogger('stripe_dashboard.access')
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    
    # Log startup message
    app.logger.info(f"Stripe Dashboard logging initialized - Level: {logging.getLevelName(log_level)}")
    app.logger.info(f"Log directory: {log_dir}")
    
    return app.logger

def log_request(app, request, response):
    """Log HTTP requests for monitoring"""
    access_logger = logging.getLogger('stripe_dashboard.access')
    
    access_logger.info(
        f"{request.remote_addr} - {request.method} {request.url} - "
        f"{response.status_code} - {request.user_agent}"
    )

def log_error(app, error):
    """Log application errors"""
    app.logger.error(f"Application Error: {str(error)}", exc_info=True)

def log_security_event(app, event_type, details):
    """Log security-related events"""
    app.logger.warning(f"SECURITY EVENT - {event_type}: {details}")

class ProductionConfig:
    """Production logging configuration constants"""
    
    LOG_ROTATION_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_LEVEL = logging.INFO
    ERROR_LOG_LEVEL = logging.ERROR
    
    # Log retention (days)
    LOG_RETENTION_DAYS = 30
    
    @staticmethod
    def cleanup_old_logs(log_dir, retention_days=30):
        """Clean up log files older than retention_days"""
        import glob
        import time
        
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
        
        for log_file in glob.glob(os.path.join(log_dir, '*.log*')):
            if os.path.getmtime(log_file) < cutoff_time:
                try:
                    os.remove(log_file)
                    print(f"Cleaned up old log file: {log_file}")
                except OSError:
                    pass