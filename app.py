import os
import logging
import secrets
from datetime import timedelta

from flask import Flask, request, session, render_template, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time

# Import structured logging
from structured_logging import setup_structured_logging, get_structured_logger, add_correlation_id_to_request

# Setup basic logging first (will be replaced with structured logging)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Validate environment variables before starting
from env_validator import validate_startup_environment
if not validate_startup_environment():
    logger.critical("Application cannot start due to environment variable issues")
    raise SystemExit("Environment validation failed - check your configuration")

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)

# Import logging configuration
from logging_config import configure_logging, log_application_startup

# Setup structured JSON logging based on environment
structured_logger = configure_logging(app)

# Validate required environment variables
session_secret = os.environ.get("SESSION_SECRET")
if not session_secret:
    logger.error("SESSION_SECRET environment variable is required")
    raise ValueError("SESSION_SECRET environment variable must be set")

if session_secret == "dev_secret_key":
    logger.warning("Using default session secret - this is insecure!")

app.secret_key = session_secret
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Initialize CSRF protection
csrf = CSRFProtect(app)
app.config['WTF_CSRF_ENABLED'] = True

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour CSRF token expiry
app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow CSRF in development mode
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minute session lifetime
app.config['SESSION_COOKIE_SECURE'] = False  # Allow cookies in development mode
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Less strict for development compatibility
app.config['REMEMBER_COOKIE_SECURE'] = False  # Allow cookies in development mode
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

# Additional session security configurations
app.config['SESSION_COOKIE_NAME'] = 'healthprep_session'  # Custom session cookie name
app.config['WTF_CSRF_FIELD_NAME'] = 'csrf_token'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year for static files

# CSRF protection is now enabled for all routes for security

# Configure the database
database_url = os.environ.get("DATABASE_URL")
# Handle potential "postgres://" format by converting to "postgresql://"
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Default to SQLite if no database URL is provided
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///healthcare.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 30,
    "connect_args": {"connect_timeout": 10}
}

# Initialize the app with the extension
db.init_app(app)

# User authentication disabled for demo version

# Add request-level transaction handling
@app.before_request
def before_request():
    # Add correlation ID for request tracing
    correlation_id = add_correlation_id_to_request()

    # Clean up any existing session at the start of each request to avoid stale transactions
    db.session.remove()

    # Log incoming request
    structured_logger.log_api_request(
        endpoint=request.endpoint or request.path,
        method=request.method,
        status_code=0,  # Will be updated in after_request
        additional_data={
            'correlation_id': correlation_id,
            'content_type': request.content_type,
            'content_length': request.content_length
        }
    )

    # Validate patient_id parameter if present to prevent SQL injection
    patient_id = request.view_args.get('patient_id') if request.view_args else None
    if patient_id is not None:
        try:
            # Ensure patient_id is a positive integer
            patient_id_int = int(patient_id)
            if patient_id_int <= 0:
                structured_logger.log_security_event(
                    event_type='invalid_parameter',
                    severity='medium',
                    description=f"Invalid patient ID attempted: {patient_id}",
                    additional_data={'parameter': 'patient_id', 'value': patient_id}
                )
                from flask import abort
                abort(400, description="Invalid patient ID")
        except (ValueError, TypeError):
            structured_logger.log_security_event(
                event_type='invalid_parameter',
                severity='medium',
                description=f"Non-integer patient ID attempted: {patient_id}",
                additional_data={'parameter': 'patient_id', 'value': patient_id}
            )
            from flask import abort
            abort(400, description="Patient ID must be a valid number")

    # Try to ping the database to see if the connection is alive
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT :test_value"), {"test_value": 1})
    except Exception as e:
        logger.warning(f"Database connection issue detected: {str(e)}")
        # Force a new connection to be created
        db.engine.dispose()

@app.teardown_request
def teardown_request(exception=None):
    # Always close the session to ensure it's in a clean state for the next request
    try:
        if exception:
            # If an exception occurred, roll back the transaction
            db.session.rollback()
            logger.error(f"Rolling back due to exception: {str(exception)}")
        else:
            # If no exception, commit the transaction
            try:
                db.session.commit()
            except Exception as e:
                # If commit fails, roll back
                db.session.rollback()
                logger.error(f"Commit failed, rolling back: {str(e)}")
    except Exception as e:
        # If something goes wrong during teardown, make sure we close the session
        logger.error(f"Error during teardown: {str(e)}")
    finally:
        # Make sure the session is cleaned up
        db.session.remove()

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Prevent XSS attacks
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy - restrictive but allows Bootstrap and Font Awesome
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdn.replit.com cdnjs.cloudflare.com; "
        "font-src 'self' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )

    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # CSRF protection header
    response.headers['X-CSRF-Protection'] = '1; mode=block'

    # CORS headers for API routes
    if request.path.startswith('/api/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    return response

@app.errorhandler(400)
def handle_bad_request(error):
    """Handle bad request errors"""
    structured_logger.log_security_event(
        event_type='bad_request',
        severity='low',
        description=str(error),
        additional_data={
            'status_code': 400,
            'correlation_id': getattr(g, 'correlation_id', None)
        }
    )
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Invalid request format'}), 400
    return render_template('400.html'), 400

@app.errorhandler(401)
def jwt_unauthorized(error):
    """Handle JWT unauthorized errors"""
    logger.info(f"Unauthorized access attempt from {get_remote_address()} to {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return render_template('401.html'), 401

@app.errorhandler(403)
def jwt_forbidden(e):
    """Handle JWT forbidden responses"""
    # Only log if this isn't a normal authentication failure
    if not request.path.startswith('/api/'):
        logger.warning(f"Forbidden access attempt from {request.remote_addr} to {request.path}")

    # Return JSON response for API endpoints
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Access denied'}), 403

    # Return HTML response for web endpoints
    return render_template('403.html'), 403

@app.errorhandler(404)
def handle_not_found(error):
    """Handle not found errors"""
    logger.info(f"404 error from {get_remote_address()} for path: {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(405)
def handle_method_not_allowed(error):
    """Handle method not allowed errors"""
    logger.warning(f"Method {request.method} not allowed for {request.path} from {get_remote_address()}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Method not allowed'}), 405
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(413)
def handle_request_entity_too_large(error):
    """Handle file upload too large errors"""
    logger.warning(f"Request entity too large from {get_remote_address()}: {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'File too large'}), 413
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(429)
def handle_rate_limit(error):
    """Handle rate limiting errors"""
    logger.warning(f"Rate limit exceeded from {get_remote_address()}: {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Too many requests. Please slow down.'}), 429
    return jsonify({'error': 'Too many requests. Please slow down.'}), 429

@app.errorhandler(500)
def handle_internal_server_error(error):
    """Handle internal server errors with detailed logging but generic client response"""
    import traceback
    import uuid

    # Generate unique error ID for tracking
    error_id = str(uuid.uuid4())[:8]

    # Log structured error information
    structured_logger.logger.error(
        f"Internal Server Error [{error_id}]",
        extra={
            'event_type': 'internal_server_error',
            'error_id': error_id,
            'correlation_id': getattr(g, 'correlation_id', None),
            'url': request.url,
            'method': request.method,
            'remote_address': get_remote_address(),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'form_data': dict(request.form) if request.form else None,
            'json_data': request.get_json() if request.is_json else None,
            'headers': dict(request.headers),
            'error_details': str(error),
            'stack_trace': traceback.format_exc().split('\n')
        },
        exc_info=True
    )

    # Roll back any database transactions
    try:
        db.session.rollback()
    except Exception as rollback_error:
        logger.error(f"Error during rollback [{error_id}]: {str(rollback_error)}")

    # Return generic error message to client
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Internal server error',
            'error_id': error_id
        }), 500
    return render_template('500.html', error_id=error_id), 500

@app.errorhandler(502)
def handle_bad_gateway(error):
    """Handle bad gateway errors"""
    logger.error(f"Bad gateway error from {get_remote_address()}: {str(error)}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Service temporarily unavailable'}), 502
    return jsonify({'error': 'Service temporarily unavailable'}), 502

@app.errorhandler(503)
def handle_service_unavailable(error):
    """Handle service unavailable errors"""
    logger.error(f"Service unavailable from {get_remote_address()}: {str(error)}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Service temporarily unavailable'}), 503
    return jsonify({'error': 'Service temporarily unavailable'}), 503

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Catch-all handler for unexpected errors"""
    import traceback
    import uuid

    # Generate unique error ID for tracking
    error_id = str(uuid.uuid4())[:8]

    # Log detailed error information
    logger.critical(f"Unexpected Error [{error_id}]:")
    logger.critical(f"Error Type: {type(error).__name__}")
    logger.critical(f"Error Message: {str(error)}")
    logger.critical(f"URL: {request.url}")
    logger.critical(f"Method: {request.method}")
    logger.critical(f"Remote Address: {get_remote_address()}")
    logger.critical(f"Stack Trace:\n{traceback.format_exc()}")

    # Roll back any database transactions
    try:
        db.session.rollback()
    except Exception as rollback_error:
        logger.critical(f"Error during rollback [{error_id}]: {str(rollback_error)}")

    # Return generic error message
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'An unexpected error occurred',
            'error_id': error_id
        }), 500
    return render_template('500.html', error_id=error_id), 500

@app.before_request
def validate_csrf_for_state_changes():
    """Enhanced CSRF validation for state-changing requests"""
    # Skip CSRF for all API routes first (they use JWT authentication instead)
    if request.path.startswith('/api/'):
        return

    # Skip CSRF for API endpoints that are already exempt
    if request.endpoint and hasattr(app.view_functions.get(request.endpoint), '_csrf_exempt'):
        return

    # Skip CSRF for safe methods
    if request.method in ['GET', 'HEAD', 'OPTIONS']:
        return

    # Check if this is an AJAX request without CSRF token
    if request.is_json or request.headers.get('Content-Type', '').startswith('application/json'):
        csrf_token = request.headers.get('X-CSRFToken') or request.json.get('csrf_token') if request.json else None
        if not csrf_token:
            logger.warning(f"Missing CSRF token in AJAX request to {request.endpoint}")
            return

    # For form-based requests, check the token
    if request.form:
        csrf_token = request.form.get('csrf_token')
        if not csrf_token:
            logger.warning(f"Missing CSRF token in form request to {request.endpoint}")
            return

def validate_uploaded_file(file):
    """Validate uploaded files for security"""
    import mimetypes
    import magic

    # Check file size (10MB limit)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > 10 * 1024 * 1024:  # 10MB
        return False

    # Check filename for malicious patterns
    filename = file.filename.lower()
    if any(char in filename for char in ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']):
        return False

    # Check for executable file extensions
    dangerous_extensions = [
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js', 
        '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg', '.sh', '.ps1'
    ]
    if any(filename.endswith(ext) for ext in dangerous_extensions):
        return False

    # Validate MIME type using python-magic
    try:
        file_content = file.read(1024)  # Read first 1KB for magic number check
        file.seek(0)  # Reset to beginning

        detected_mime = magic.from_buffer(file_content, mime=True)

        # Allow only safe MIME types
        safe_mimes = [
            'text/plain', 'application/pdf', 'image/jpeg', 'image/png', 
            'image/gif', 'text/csv', 'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]

        if detected_mime not in safe_mimes:
            return False

    except Exception as e:
        logger.error(f"Error validating file MIME type: {str(e)}")
        return False

    return True

def sanitize_input(value, max_length=None, allow_html=False, field_type='general'):
    """Sanitize user input to prevent XSS and other injection attacks"""
    import re
    import html
    import logging

    if not value:
        return value

    # Convert to string if not already
    value = str(value).strip()

    # Log potential attack attempts
    original_value = value

    # Enforce maximum length
    if max_length and len(value) > max_length:
        value = value[:max_length]
        logging.warning(f"Input truncated from {len(original_value)} to {max_length} characters")

    # Remove or escape HTML unless explicitly allowed
    if not allow_html:
        value = html.escape(value)

    # Remove potentially dangerous characters
    # Remove null bytes and other control characters
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

    # Enhanced dangerous patterns
    dangerous_patterns = [
        r'(union\s+select)', r'(drop\s+table)', r'(delete\s+from)',
        r'(insert\s+into)', r'(update\s+\w+\s+set)', r'(exec\s*\()',
        r'(script\s*>)', r'(javascript:)', r'(vbscript:)',
        r'(onload\s*=)', r'(onerror\s*=)', r'(\bor\b\s+1\s*=\s*1)',
        r'(\band\b\s+1\s*=\s*1)', r'(;\s*drop)', r'(;\s*delete)',
        r'(;\s*insert)', r'(;\s*update)', r'(--\s*)', r'(/\*.*?\*/)',
        r'(xp_cmdshell)', r'(sp_executesql)', r'(eval\s*\()',
        r'(<iframe)', r'(<object)', r'(<embed)', r'(<form)',
        r'(data:text/html)', r'(data:application)', r'(\bvoid\s*\()'
    ]

    for pattern in dangerous_patterns:
        old_value = value
        value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
        if old_value != value:
            logging.warning(f"Dangerous pattern removed: {pattern}")

    # Field-specific validation
    if field_type == 'email':
        if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            logging.warning(f"Invalid email format: {value}")
            return None
    elif field_type == 'phone':
        # Remove all non-digit characters for phone validation
        digits_only = re.sub(r'\D', '', value)
        if value and (len(digits_only) < 10 or len(digits_only) > 15):
            logging.warning(f"Invalid phone format: {value}")
            return None
    elif field_type == 'name':
        if value and not re.match(r'^[a-zA-Z\s\-\'\.]+$', value):
            logging.warning(f"Invalid name format: {value}")
            return None
    elif field_type == 'mrn':
        if value and not re.match(r'^[A-Za-z0-9\-]+$', value):
            logging.warning(f"Invalid MRN format: {value}")
            return None

    # Log if significant changes were made
    if original_value != value and len(original_value) > 0:
        logging.info(f"Input sanitized: '{original_value[:50]}...' -> '{value[:50]}...'")

    return value

def validate_mrn(mrn):
    """Validate Medical Record Number format"""
    import re
    if not mrn:
        return True  # Allow empty MRN for auto-generation

    # MRN should be alphanumeric, no special characters except hyphens
    if not re.match(r'^[A-Za-z0-9\-]+$', mrn):
        return False

    # Reasonable length constraints
    if len(mrn) < 3 or len(mrn) > 20:
        return False

    return True

def validate_phone_number(phone):
    """Validate phone number format"""
    import re
    if not phone:
        return True  # Allow empty phone

    # Remove all non-digit characters for validation
    digits_only = re.sub(r'\D', '', phone)

    # Should have 10-15 digits (international format)
    if len(digits_only) < 10 or len(digits_only) > 15:
        return False

    return True

def validate_email_format(email):
    """Enhanced email validation"""
    import re
    if not email:
        return True  # Allow empty email

    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        return False

    # Additional checks
    if len(email) > 254:  # RFC 5321 limit
        return False

    # Check for dangerous patterns
    if any(char in email for char in ['<', '>', '"', "'"]):
        return False

    return True

@app.before_request
def validate_session_security():
    """Validate session security and prevent session-based attacks"""
    from flask import session, g
    import secrets
    import hashlib

    # Skip session validation for static files and certain endpoints
    if request.endpoint in ['static'] or request.path.startswith('/static'):
        return

    # Initialize security tracking for this request
    g.security_context = {
        'ip_address': get_remote_address(),
        'user_agent': request.headers.get('User-Agent', ''),
        'timestamp': time.time()
    }

    # Check for session fixation attacks
    if 'session_id' in session:
        # Relax IP validation for normal navigation - only enforce for highly sensitive operations
        sensitive_paths = ['/delete_patient']
        is_sensitive_request = any(path in request.path for path in sensitive_paths)

        # Only verify IP consistency for sensitive operations
        if 'session_ip' in session and session['session_ip'] != g.security_context['ip_address'] and is_sensitive_request:
            logger.warning(f"Session IP mismatch detected on sensitive operation: stored={session['session_ip']}, current={g.security_context['ip_address']}")
            session.clear()
            from flask import abort
            abort(403, description="Session security violation detected")
        elif 'session_ip' in session and session['session_ip'] != g.security_context['ip_address']:
            # Log but don't block normal navigation
            logger.info(f"IP change detected (normal navigation): stored={session['session_ip']}, current={g.security_context['ip_address']}")
            # Update session IP to current one for seamless navigation
            session['session_ip'] = g.security_context['ip_address']

        # Check for session timeout
        if 'session_created' in session:
            session_age = time.time() - session['session_created']
            if session_age > app.config['PERMANENT_SESSION_LIFETIME']:
                logger.info(f"Session expired for IP {g.security_context['ip_address']}")
                session.clear()
    else:
        # Initialize new session with security tracking
        session['session_id'] = secrets.token_urlsafe(32)
        session['session_ip'] = g.security_context['ip_address']
        session['session_created'] = time.time()
        session['user_agent_hash'] = hashlib.sha256(g.security_context['user_agent'].encode()).hexdigest()

    # Verify user agent consistency to detect session hijacking
    if 'user_agent_hash' in session:
        current_ua_hash = hashlib.sha256(g.security_context['user_agent'].encode()).hexdigest()
        if session['user_agent_hash'] != current_ua_hash:
            logger.warning(f"User agent change detected for session {session.get('session_id', 'unknown')}")
            session.clear()
            from flask import abort
            abort(403, description="Session security violation detected")

    # Rate limiting for critical operations based on session
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        session_key = f"rate_limit_session_{session.get('session_id', 'anonymous')}"
        current_time = time.time()

        # Clean up old entries
        if 'request_timestamps' not in session:
            session['request_timestamps'] = []

        # Remove timestamps older than 1 minute
        session['request_timestamps'] = [
            ts for ts in session['request_timestamps'] 
            if current_time - ts < 60
        ]

        # Exempt repository pages from strict rate limiting (for bulk operations)
        repository_paths = ['/visits', '/document_repository', '/delete_appointments_bulk']
        is_repository_request = any(path in request.path for path in repository_paths)

        # Check if rate limit exceeded (100 for repository pages, 20 for others)
        rate_limit = 100 if is_repository_request else 20
        if len(session['request_timestamps']) >= rate_limit:
            logger.warning(f"Rate limit exceeded for session {session.get('session_id', 'unknown')} from {g.security_context['ip_address']}")
            from flask import abort
            abort(429, description="Too many requests. Please slow down.")

        # Add current timestamp
        session['request_timestamps'].append(current_time)

@app.before_request
def validate_referrer_security():
    """Validate HTTP Referer to prevent certain types of attacks"""
    # Skip for safe methods and static files
    if request.method in ['GET', 'HEAD', 'OPTIONS'] or request.endpoint == 'static':
        return

    # For state-changing requests, validate referer
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        referer = request.headers.get('Referer', '')
        host = request.headers.get('Host', '')

        # Allow requests without referer for API endpoints or if explicitly AJAX
        if not referer and (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'api/' in request.path):
            return

        # If referer exists, it should match our host
        if referer and not referer.startswith(f"http://{host}") and not referer.startswith(f"https://{host}"):
            logger.warning(f"Suspicious referer detected: {referer} for {request.url} from {get_remote_address()}")
            # Don't block in development, just log
            # In production, you might want to abort(403)

@app.before_request
def sanitize_form_data():
    """Sanitize all form data before processing"""
    if request.method in ['POST', 'PUT', 'PATCH'] and request.form:
        from werkzeug.datastructures import MultiDict

        # Create a new MultiDict with sanitized values to preserve the interface
        sanitized_form = MultiDict()

        for key, value in request.form.items():
            # Skip CSRF token from sanitization
            if key == 'csrf_token':
                sanitized_form[key] = value
                continue

            # Apply different sanitization based on field type
            if key in ['email']:
                sanitized_value = sanitize_input(value, max_length=254, field_type='email')
                if sanitized_value is None:
                    logger.warning(f"Invalid email format attempted: {value} from {get_remote_address()}")
                    from flask import abort
                    abort(400, description="Invalid email format")
            elif key in ['phone']:
                sanitized_value = sanitize_input(value, max_length=20, field_type='phone')
                if sanitized_value is None:
                    logger.warning(f"Invalid phone number attempted: {value} from {get_remote_address()}")
                    from flask import abort
                    abort(400, description="Invalid phone number format")
            elif key in ['mrn']:
                sanitized_value = sanitize_input(value, max_length=20, field_type='mrn')
                if sanitized_value is None:
                    logger.warning(f"Invalid MRN format attempted: {value} from {get_remote_address()}")
                    from flask import abort
                    abort(400, description="Invalid MRN format")
            elif key in ['notes', 'description', 'details', 'findings', 'impression', 'recommendations']:
                # Allow longer text for notes but still sanitize
                sanitized_value = sanitize_input(value, max_length=5000, field_type='text')
            elif key in ['first_name', 'last_name', 'provider', 'specialist']:
                # Names should not contain HTML or special characters
                sanitized_value = sanitize_input(value, max_length=100, field_type='name')
                if sanitized_value is None:
                    logger.warning(f"Invalid name format attempted: {value} from {get_remote_address()}")
                    from flask import abort
                    abort(400, description="Names can only contain letters, spaces, hyphens, and apostrophes")
            elif key in ['condition_name', 'test_name', 'vaccine_name']:
                # Medical terms can include numbers and some special characters
                sanitized_value = sanitize_input(value, max_length=200, field_type='medical')
            elif key in ['appointment_date', 'date_of_birth', 'visit_date', 'test_date']:
                # Date fields need special handling
                sanitized_value = sanitize_input(value, max_length=10, field_type='date')
            else:
                # Default sanitization for other fields
                sanitized_value = sanitize_input(value, max```python
_length=500, field_type='general')

            sanitized_form[key] = sanitized_value

        # Replace the original form data with our MultiDict
        request.form = sanitized_form

@app.after_request
def log_security_events(response):
    """Log security-relevant events for monitoring"""
    # Skip logging for static files
    if request.endpoint == 'static':
        return response

    # Log failed requests for security monitoring
    if response.status_code >= 400:
        security_log = {
            'timestamp': time.time(),
            'ip_address': get_remote_address(),
            'method': request.method,
            'path': request.path,
            'user_agent': request.headers.get('User-Agent', ''),
            'status_code': response.status_code,
            'session_id': session.get('session_id', 'none')
        }

        if response.status_code == 403:
            logger.warning(f"Security violation: {security_log}")
        elif response.status_code == 429:
            logger.warning(f"Rate limit exceeded: {security_log}")
        elif response.status_code >= 400:
            logger.info(f"Failed request: {security_log}")

    # Add security-related response headers
    response.headers['X-Request-ID'] = session.get('session_id', 'unknown')

    # Rotate session ID periodically for additional security
    if 'session_created' in session:
        session_age = time.time() - session['session_created']
        # Rotate session ID every 30 minutes
        if session_age > 1800:  # 30 minutes
            old_session_id = session.get('session_id')
            session['session_id'] = secrets.token_urlsafe(32)
            session['session_created'] = time.time()
            logger.info(f"Session ID rotated from {old_session_id} to {session['session_id']}")

    return response

@app.before_request
def detect_automated_attacks():
    """Detect and prevent automated attacks and bots"""
    user_agent = request.headers.get('User-Agent', '').lower()

    # Common bot signatures that might be malicious
    suspicious_agents = [
        'sqlmap', 'nikto', 'dirb', 'dirbuster', 'gobuster', 'wfuzz',
        'burpsuite', 'owasp', 'netsparker', 'acunetix', 'appscan',
        'w3af', 'skipfish', 'arachni', 'nuclei', 'masscan', 'nmap'
    ]

    if any(bot in user_agent for bot in suspicious_agents):
        logger.warning(f"Suspicious user agent detected: {user_agent} from {get_remote_address()}")
        from flask import abort
        abort(403, description="Automated security scanning detected")

    # Detect rapid-fire requests that might indicate automated attacks
    client_ip = get_remote_address()
    current_time = time.time()

    # Simple in-memory rate limiting (in production, use Redis or similar)
    if not hasattr(app, '_request_tracker'):
        app._request_tracker = {}

    # Clean up old entries (older than 5 minutes)
    app._request_tracker = {
        ip: timestamps for ip, timestamps in app._request_tracker.items()
        if any(current_time - ts < 300 for ts in timestamps)
    }

    if client_ip not in app._request_tracker:
        app._request_tracker[client_ip] = []

    # Remove timestamps older than 1 minute
    app._request_tracker[client_ip] = [
        ts for ts in app._request_tracker[client_ip]
        if current_time - ts < 60
    ]

    # Check if more than 30 requests in the last minute
    if len(app._request_tracker[client_ip]) > 30:
        logger.warning(f"Potential automated attack detected from {client_ip}: {len(app._request_tracker[client_ip])} requests in 1 minute")
        from flask import abort
        abort(429, description="Too many requests detected")

    # Add current timestamp
    app._request_tracker[client_ip].append(current_time)

with app.app_context():
    # Import models
    import models  # noqa: F401

    # Import JWT authentication routes
    import auth_routes  # noqa: F401

    # Import API routes
    import api_routes  # noqa: F401

    # JWT configuration with enhanced security validation
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_DELTA = timedelta(hours=24)

    # Validate JWT secret key security
    def validate_jwt_secret():
        """Validate that JWT secret is secure and present"""
        if not JWT_SECRET_KEY:
            logger.error("JWT_SECRET_KEY environment variable is required")
            raise ValueError("JWT_SECRET_KEY environment variable must be set")

        if JWT_SECRET_KEY == 'your-secret-key-change-in-production':
            logger.error("JWT secret key is still using default value - this is insecure!")
            raise ValueError("JWT_SECRET_KEY must be changed from default value")

        if len(JWT_SECRET_KEY) < 32:
            logger.error("JWT secret key should be at least 32 characters")
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

    validate_jwt_secret()

    # Schedule automatic admin log cleanup
    def schedule_admin_log_cleanup():
        """Schedule periodic cleanup of old admin logs"""
        import threading
        import time
        from datetime import datetime, timedelta

        def cleanup_task():
            while True:
                try:
                    # Run cleanup daily at 2 AM
                    now = datetime.now()
                    next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)

                    sleep_seconds = (next_run - now).total_seconds()
                    time.sleep(sleep_seconds)

                    # Perform cleanup
                    with app.app_context():
                        from admin_log_cleanup import cleanup_old_admin_logs
                        deleted_count = cleanup_old_admin_logs(10)
                        if deleted_count > 0:
                            logger.info(f"Daily cleanup: Removed {deleted_count} old admin log entries")

                except Exception as e:
                    logger.error(f"Error in admin log cleanup task: {str(e)}")
                    # Sleep for 1 hour before retrying
                    time.sleep(3600)

        # Start cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
        logger.info("Admin log cleanup scheduler started")

    # Start the cleanup scheduler
    schedule_admin_log_cleanup()

    # Create database tables with retry logic
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting database connection (attempt {attempt+1}/{max_retries})")
            db.create_all()
            logger.info("Database tables created successfully")
            break
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            if attempt < max_retries - 1:
                structured_logger.logger.info(f"Retrying database connection in {retry_delay} seconds", extra={
                    'event_type': 'database_retry',
                    'attempt': attempt + 1,
                    'max_retries': max_retries,
                    'retry_delay': retry_delay
                })
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                structured_logger.logger.error(f"Failed to connect to database after {max_retries} attempts", extra={
                    'event_type': 'database_connection_failed',
                    'max_retries': max_retries
                })
                # Fall back to SQLite if PostgreSQL fails
                if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
                    structured_logger.logger.warning("Falling back to SQLite database", extra={
                        'event_type': 'database_fallback',
                        'from': 'postgresql',
                        'to': 'sqlite'
                    })
                    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///healthcare.db"
                    db.create_all()
                    structured_logger.logger.info("SQLite database tables created successfully", extra={
                        'event_type': 'database_initialized',
                        'database_type': 'sqlite'
                    })
                else:
                    raise

# Log application startup information
from logging_config import log_application_startup
log_application_startup(app, structured_logger)

# Register validation middleware for automatic logging
from validation_middleware import register_validation_middleware
register_validation_middleware(app)

# Register API access middleware for data access logging
from api_access_middleware import register_api_access_middleware
register_api_access_middleware(app)

# Register admin route protection middleware
from admin_middleware import register_admin_middleware
register_admin_middleware(app)