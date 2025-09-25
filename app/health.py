"""
Health Check Module for Stripe Dashboard
Provides comprehensive health monitoring for Docker deployments
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime
import os
import sqlite3
import psutil
import sys

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """
    Comprehensive health check endpoint for Docker and monitoring systems
    Returns HTTP 200 if all systems are operational, 503 if any critical system fails
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    overall_healthy = True
    
    # 1. Application Health
    try:
        health_status['checks']['application'] = {
            'status': 'healthy',
            'flask_env': current_app.config.get('FLASK_ENV', 'unknown'),
            'debug_mode': current_app.debug,
            'python_version': sys.version
        }
    except Exception as e:
        health_status['checks']['application'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_healthy = False
    
    # 2. Database Health
    try:
        from app import db
        from sqlalchemy import text
        
        # Test database connection using modern SQLAlchemy syntax
        with db.engine.connect() as connection:
            result = connection.execute(text('SELECT 1')).fetchone()
        
        # Get database file info if SQLite
        db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        db_info = {'url_type': 'unknown'}
        
        if 'sqlite' in db_url:
            db_path = db_url.replace('sqlite:///', '')
            if os.path.exists(db_path):
                stat = os.stat(db_path)
                db_info.update({
                    'url_type': 'sqlite',
                    'file_size': stat.st_size,
                    'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        health_status['checks']['database'] = {
            'status': 'healthy',
            'connection': 'ok',
            'info': db_info
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_healthy = False
    
    # 3. Filesystem Health
    try:
        # Check if critical directories are writable
        critical_dirs = [
            '/app/instance',
            '/app/csv_data',
            '/app/logs'
        ]
        
        filesystem_checks = {}
        for directory in critical_dirs:
            if os.path.exists(directory):
                filesystem_checks[directory] = {
                    'exists': True,
                    'writable': os.access(directory, os.W_OK),
                    'readable': os.access(directory, os.R_OK)
                }
            else:
                filesystem_checks[directory] = {
                    'exists': False,
                    'writable': False,
                    'readable': False
                }
        
        health_status['checks']['filesystem'] = {
            'status': 'healthy',
            'directories': filesystem_checks
        }
    except Exception as e:
        health_status['checks']['filesystem'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_healthy = False
    
    # 4. System Resources (if psutil is available)
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_status['checks']['resources'] = {
            'status': 'healthy',
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent_used': memory.percent
            },
            'disk': {
                'total': disk.total,
                'free': disk.free,
                'percent_used': (disk.used / disk.total) * 100
            },
            'cpu_count': psutil.cpu_count()
        }
        
        # Mark as unhealthy if resources are critically low
        if memory.percent > 90 or (disk.used / disk.total) > 0.95:
            health_status['checks']['resources']['status'] = 'warning'
            health_status['checks']['resources']['message'] = 'High resource usage detected'
            
    except ImportError:
        health_status['checks']['resources'] = {
            'status': 'skipped',
            'message': 'psutil not available'
        }
    except Exception as e:
        health_status['checks']['resources'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # 5. Environment Configuration
    try:
        required_env_vars = ['SECRET_KEY', 'DATABASE_URL']
        env_status = {}
        
        for var in required_env_vars:
            env_status[var] = {
                'present': var in os.environ,
                'configured': bool(os.environ.get(var, '').strip())
            }
        
        health_status['checks']['configuration'] = {
            'status': 'healthy',
            'environment_variables': env_status
        }
        
        # Check if any critical env vars are missing
        missing_vars = [var for var in required_env_vars 
                       if not os.environ.get(var, '').strip()]
        if missing_vars:
            health_status['checks']['configuration']['status'] = 'warning'
            health_status['checks']['configuration']['missing_variables'] = missing_vars
            
    except Exception as e:
        health_status['checks']['configuration'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Set overall status
    if overall_healthy:
        health_status['status'] = 'healthy'
        status_code = 200
    else:
        health_status['status'] = 'unhealthy'
        status_code = 503
    
    return jsonify(health_status), status_code

@health_bp.route('/health/simple')
def simple_health_check():
    """
    Simple health check endpoint that just returns 200 OK
    Useful for basic Docker health checks and load balancers
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@health_bp.route('/health/database')
def database_health_check():
    """
    Database-specific health check
    """
    try:
        from app import db
        from sqlalchemy import text
        
        # Test basic connection using modern SQLAlchemy syntax
        with db.engine.connect() as connection:
            result = connection.execute(text('SELECT 1')).fetchone()
        
            # Try to get table count if possible
            try:
                tables_result = connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
                table_count = len(tables_result)
            except:
                table_count = 'unknown'
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'tables': table_count,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@health_bp.route('/health/version')
def version_info():
    """
    Application version and build information
    """
    try:
        version_info = {
            'application': 'Stripe Dashboard',
            'version': '1.0.0',
            'python_version': sys.version,
            'flask_env': current_app.config.get('FLASK_ENV', 'unknown'),
            'build_timestamp': datetime.utcnow().isoformat(),
            'platform': sys.platform
        }
        
        # Add Git commit info if available
        try:
            git_commit = os.environ.get('GIT_COMMIT', 'unknown')
            git_branch = os.environ.get('GIT_BRANCH', 'unknown')
            version_info.update({
                'git_commit': git_commit,
                'git_branch': git_branch
            })
        except:
            pass
        
        return jsonify(version_info), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500