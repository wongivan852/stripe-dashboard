"""
Security Configuration for Stripe Dashboard Production Deployment
Dell Server Security Hardening
"""

import os
from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix

def configure_security(app):
    """Configure security settings for production deployment"""
    
    # Trust proxy headers (for reverse proxy setups)
    trusted_proxies = os.getenv('TRUSTED_PROXIES', '192.168.0.0/16,10.0.0.0/8,172.16.0.0/12')
    if trusted_proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent content type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Prevent information disclosure
        response.headers['Server'] = 'Stripe Dashboard'
        
        # Content Security Policy (restrictive but functional)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Feature Policy / Permissions Policy
        response.headers['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), payment=(), '
            'usb=(), magnetometer=(), gyroscope=(), speaker=()'
        )
        
        # Cache control for sensitive data
        if request.endpoint and 'api' in request.endpoint:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
    
    # Request logging for security monitoring
    @app.before_request
    def log_request_info():
        """Log request information for security monitoring"""
        
        # Log potential security threats
        suspicious_patterns = [
            '../', '..\\', '<script', 'javascript:', 'vbscript:',
            'onload=', 'onerror=', 'eval(', 'expression(', 'url(',
            'import(', 'require(', 'system(', 'exec(', 'shell_exec'
        ]
        
        request_url = str(request.url).lower()
        request_data = str(request.get_data()).lower()
        user_agent = str(request.headers.get('User-Agent', '')).lower()
        
        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if (pattern in request_url or 
                pattern in request_data or 
                pattern in user_agent):
                
                app.logger.warning(
                    f"SECURITY ALERT - Suspicious pattern '{pattern}' detected - "
                    f"IP: {request.remote_addr}, URL: {request.url}, "
                    f"User-Agent: {request.headers.get('User-Agent', 'N/A')}"
                )
                break
    
    # Rate limiting helper
    @app.before_request
    def basic_rate_limiting():
        """Basic rate limiting protection"""
        
        # Skip rate limiting for static files
        if request.endpoint == 'static':
            return
        
        # Get client IP
        client_ip = request.remote_addr
        
        # Simple in-memory rate limiting (consider Redis for production clusters)
        if not hasattr(app, 'rate_limit_storage'):
            app.rate_limit_storage = {}
        
        import time
        current_time = time.time()
        
        # Clean old entries (older than 1 hour)
        app.rate_limit_storage = {
            ip: data for ip, data in app.rate_limit_storage.items()
            if current_time - data['last_request'] < 3600
        }
        
        # Check rate limit (100 requests per minute per IP)
        if client_ip in app.rate_limit_storage:
            data = app.rate_limit_storage[client_ip]
            
            # Reset counter if more than 1 minute has passed
            if current_time - data['last_reset'] > 60:
                data['count'] = 0
                data['last_reset'] = current_time
            
            data['count'] += 1
            data['last_request'] = current_time
            
            # Rate limit exceeded
            if data['count'] > 100:
                app.logger.warning(
                    f"RATE LIMIT EXCEEDED - IP: {client_ip}, "
                    f"Requests: {data['count']}, URL: {request.url}"
                )
                # Could return 429 Too Many Requests here
                # return 'Rate limit exceeded', 429
        else:
            app.rate_limit_storage[client_ip] = {
                'count': 1,
                'last_request': current_time,
                'last_reset': current_time
            }
    
    app.logger.info("Security configuration applied successfully")

def validate_request_data(data):
    """Validate and sanitize request data"""
    
    if not data:
        return True
    
    # Convert to string if not already
    data_str = str(data)
    
    # Check for common injection patterns
    dangerous_patterns = [
        'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET',
        'UNION SELECT', 'OR 1=1', 'AND 1=1', '--', '/*', '*/',
        '<script', '</script>', 'javascript:', 'vbscript:',
        'onload=', 'onerror=', 'onclick=', 'onmouseover='
    ]
    
    data_upper = data_str.upper()
    for pattern in dangerous_patterns:
        if pattern in data_upper:
            return False
    
    return True

def get_client_ip(request):
    """Get the real client IP address (handling proxies)"""
    
    # Check X-Forwarded-For header (from reverse proxy)
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # Take the first IP in the chain
        return x_forwarded_for.split(',')[0].strip()
    
    # Check X-Real-IP header
    x_real_ip = request.headers.get('X-Real-IP')
    if x_real_ip:
        return x_real_ip
    
    # Fall back to remote_addr
    return request.remote_addr

class SecurityConfig:
    """Security configuration constants"""
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = 100
    RATE_LIMIT_BURST = 20
    
    # Session security
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload security
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'csv', 'txt', 'pdf'}
    
    # IP whitelist for admin functions (if needed)
    ADMIN_IP_WHITELIST = os.getenv('ADMIN_IP_WHITELIST', '').split(',')
    
    @staticmethod
    def is_safe_filename(filename):
        """Check if filename is safe"""
        if not filename:
            return False
        
        # Check for directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check file extension
        if '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            return ext in SecurityConfig.ALLOWED_EXTENSIONS
        
        return False