"""
Structured logging configuration for the healthcare management system.
Provides JSON-formatted logs for machine parsing and log aggregation.
"""
import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, session, g
import uuid


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record):
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }

        # Add request context if available
        try:
            if request:
                log_entry['request'] = {
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'endpoint': request.endpoint
                }

                # Add session info if available
                if session:
                    log_entry['session'] = {
                        'session_id': session.get('session_id'),
                        'user_id': session.get('user_id'),
                        'username': session.get('username')
                    }

                # Add security context if available
                if hasattr(g, 'security_context'):
                    log_entry['security'] = g.security_context

        except RuntimeError:
            # Outside of request context
            pass

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'exc_info', 'exc_text', 'stack_info']:
                extra_fields[key] = value

        if extra_fields:
            log_entry['extra'] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StructuredLogger:
    """Structured logger with predefined log patterns for healthcare app"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_patient_access(self, patient_id: int, action: str, user_id: Optional[int] = None, 
                          username: Optional[str] = None, additional_data: Optional[Dict] = None):
        """Log patient data access events - only log suspicious activities"""
        # Only log if there's a security concern or error
        if action.startswith('DELETE') or action.startswith('ERROR'):
            self.logger.warning(
                f"Patient data access: {action}",
                extra={
                    'event_type': 'patient_access',
                    'patient_id': patient_id,
                    'action': action,
                    'user_id': user_id or session.get('user_id'),
                    'username': username or session.get('username'),
                    'additional_data': additional_data or {}
                }
            )

    def log_security_event(self, event_type: str, severity: str, description: str, 
                          additional_data: Optional[Dict] = None):
        """Log security-related events"""
        self.logger.warning(
            f"Security event: {description}",
            extra={
                'event_type': 'security',
                'security_event_type': event_type,
                'severity': severity,
                'description': description,
                'additional_data': additional_data or {}
            }
        )

    def log_database_operation(self, operation: str, table: str, record_id: Optional[int] = None,
                              success: bool = True, error_message: Optional[str] = None):
        """Log database operations"""
        level = logging.INFO if success else logging.ERROR
        message = f"Database {operation} on {table}"
        if not success:
            message += f" failed: {error_message}"

        self.logger.log(
            level,
            message,
            extra={
                'event_type': 'database_operation',
                'operation': operation,
                'table': table,
                'record_id': record_id,
                'success': success,
                'error_message': error_message
            }
        )

    def log_api_request(self, endpoint: str, method: str, status_code: int, 
                       response_time_ms: Optional[float] = None, 
                       additional_data: Optional[Dict] = None):
        """Log API requests and responses - only log errors and warnings"""
        # Only log failed requests to reduce console clutter
        if status_code >= 400:
            self.logger.warning(
                f"API request: {method} {endpoint} - {status_code}",
                extra={
                    'event_type': 'api_request',
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': status_code,
                    'response_time_ms': response_time_ms,
                    'additional_data': additional_data or {}
                }
            )

    def log_admin_action(self, action: str, target: str, user_id: Optional[int] = None,
                        username: Optional[str] = None, additional_data: Optional[Dict] = None):
        """Log administrative actions"""
        self.logger.warning(
            f"Admin action: {action} on {target}",
            extra={
                'event_type': 'admin_action',
                'action': action,
                'target': target,
                'user_id': user_id or session.get('user_id'),
                'username': username or session.get('username'),
                'additional_data': additional_data or {}
            }
        )

    def log_authentication_event(self, event_type: str, username: Optional[str] = None,
                                success: bool = True, reason: Optional[str] = None):
        """Log authentication events"""
        level = logging.INFO if success else logging.WARNING
        message = f"Authentication {event_type}"
        if not success:
            message += f" failed: {reason}"

        self.logger.log(
            level,
            message,
            extra={
                'event_type': 'authentication',
                'auth_event_type': event_type,
                'username': username,
                'success': success,
                'reason': reason
            }
        )

    def log_file_operation(self, operation: str, filename: str, file_type: Optional[str] = None,
                          file_size: Optional[int] = None, success: bool = True, 
                          error_message: Optional[str] = None):
        """Log file upload/download operations"""
        level = logging.INFO if success else logging.ERROR
        message = f"File {operation}: {filename}"
        if not success:
            message += f" failed: {error_message}"

        self.logger.log(
            level,
            message,
            extra={
                'event_type': 'file_operation',
                'operation': operation,
                'filename': filename,
                'file_type': file_type,
                'file_size': file_size,
                'success': success,
                'error_message': error_message
            }
        )


def setup_structured_logging(app, log_level=logging.INFO):
    """Setup structured JSON logging for the Flask application"""

    # Create JSON formatter
    json_formatter = JSONFormatter()

    # Setup console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(log_level)

    # Setup file handler for persistent logs
    file_handler = logging.FileHandler('healthcare_app.log')
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure Flask app logger
    app.logger.handlers = []
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)

    # Suppress noisy third-party loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    return StructuredLogger('healthcare_app')


def get_structured_logger(name: str = 'healthcare_app') -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


# Create correlation ID for request tracing
def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing"""
    return str(uuid.uuid4())


def add_correlation_id_to_request():
    """Add correlation ID to the current request context"""
    if not hasattr(g, 'correlation_id'):
        g.correlation_id = generate_correlation_id()
    return g.correlation_id


def log_security_event(event_type, description, severity='medium', additional_data=None):
    """Log security-related events with additional context"""
    extra_data = {
        'event_type': 'security',
        'security_event_type': event_type,
        'severity': severity,
        'description': description,
        'additional_data': additional_data or {}
    }

    # Check for invalid patient ID attempts (allow 0 for bulk operations)
    if 'patient_id' in request.view_args:
        patient_id = request.view_args['patient_id']
        if patient_id < 0:  # Only reject negative numbers, allow 0 for bulk operations
            log_security_event('invalid_parameter', f'Invalid patient ID attempted: {patient_id}', 
                             severity='medium', 
                             additional_data={'parameter': 'patient_id', 'value': patient_id})

# Validate patient_id if present in URL parameters (allow 0 for bulk operations)
    if 'patient_id' in request.view_args:
        patient_id = request.view_args.get('patient_id')
        if patient_id is not None and patient_id < 0:  # Only reject negative numbers
            log_security_event('invalid_parameter', f'Invalid patient ID attempted: {patient_id}', 
                             severity='medium', 
                             additional_data={'parameter': 'patient_id', 'value': patient_id})