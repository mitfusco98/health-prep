"""
Validation middleware to automatically log all validation failures across the application.
"""

import logging
from functools import wraps
from flask import request, session
from models import AdminLog, User
from app import db
import uuid
from datetime import datetime
import json


# Configure structured logging
def get_logger():
    """Configure and return a logger instance with JSON formatting."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)  # Set the desired log level

    # Create a handler that outputs JSON format
    handler = logging.StreamHandler()
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format."""

    def format(self, record):
        log_data = {
            "time": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        return json.dumps(log_data)


class StructuredLogger:
    """Utility for structured logging with different event types and severities."""

    def __init__(self, category):
        self.logger = logging.getLogger(category)
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = JsonFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, event_type, message, severity="info", additional_data=None):
        """Log a general event with associated metadata."""
        extra_data = {
            "event_type": event_type,
            "severity": severity,
        }
        if additional_data:
            extra_data.update(additional_data)

        log_message = f"[{event_type}] {message}"
        log_level = getattr(self.logger, severity.lower(), self.logger.info)
        log_level(log_message, extra={"extra_data": extra_data})

    def log_security_event(
        self, event_type, description, severity="medium", additional_data=None
    ):
        """Specifically log security-related events with descriptions and severity levels."""
        extra_data = {
            "event_type": event_type,
            "severity": severity,
            "description": description,
        }
        if additional_data:
            extra_data.update(additional_data)

        log_message = f"[SECURITY] [{event_type}] {description}"
        if severity.lower() == "high":
            log_level = self.logger.error
        elif severity.lower() == "medium":
            log_level = self.logger.warning
        else:
            log_level = self.logger.info

        log_level(log_message, extra={"extra_data": extra_data})


def get_structured_logger(category):
    """Retrieve a structured logger instance."""
    return StructuredLogger(category)


# Create logger for validation middleware
logger = logging.getLogger(__name__)


class ValidationLogger:
    """Centralized validation logging utility."""

    @staticmethod
    def log_validation_failure(
        endpoint, validation_errors, form_data=None, user_id=None
    ):
        """
        Log validation failure to admin logs with standardized format.

        Args:
            endpoint: The endpoint where validation failed
            validation_errors: List or dict of validation errors
            form_data: Form data that failed validation (sensitive data excluded)
            user_id: ID of the user who triggered the validation failure
        """
        try:
            # Generate unique request ID for tracking
            request_id = str(uuid.uuid4())[:8]

            # Get user info
            user = None
            if user_id:
                user = User.query.get(user_id)
            elif session.get("user_id"):
                user = User.query.get(session.get("user_id"))

            # Sanitize form data (remove sensitive fields)
            safe_form_data = (
                ValidationLogger._sanitize_form_data(form_data) if form_data else {}
            )

            # Format validation errors
            if isinstance(validation_errors, dict):
                error_summary = "; ".join(
                    [
                        f"{field}: {', '.join(errors)}"
                        for field, errors in validation_errors.items()
                    ]
                )
            elif isinstance(validation_errors, list):
                error_summary = "; ".join(str(error) for error in validation_errors)
            else:
                error_summary = str(validation_errors)

            # Create detailed log entry
            details = {
                "request_id": request_id,
                "endpoint": endpoint,
                "method": request.method if request else "UNKNOWN",
                "user_agent": (
                    request.headers.get("User-Agent", "Unknown")
                    if request
                    else "Unknown"
                ),
                "ip_address": request.remote_addr if request else "Unknown",
                "validation_errors": validation_errors,
                "form_fields": list(safe_form_data.keys()) if safe_form_data else [],
                "error_count": (
                    len(validation_errors)
                    if isinstance(validation_errors, (dict, list))
                    else 1
                ),
            }

            # Create admin log entry
            admin_log = AdminLog(
                user_id=user.id if user else None,
                event_type="validation_error",
                event_details=str(details),
                request_id=request_id,
                ip_address=request.remote_addr if request else "Unknown",
            )

            db.session.add(admin_log)
            db.session.commit()

            # Log to application logger as well
            structured_logger = get_structured_logger("validation")
            structured_logger.log_event(
                "validation_failure",
                "Validation failure detected",
                severity="warning",
                additional_data={
                    "request_id": request_id,
                    "endpoint": endpoint,
                    "method": request.method if request else "UNKNOWN",
                    "user_agent": (
                        request.headers.get("User-Agent", "Unknown")
                        if request
                        else "Unknown"
                    ),
                    "ip_address": request.remote_addr if request else "Unknown",
                    "validation_errors": validation_errors,
                    "form_fields": (
                        list(safe_form_data.keys()) if safe_form_data else []
                    ),
                    "error_count": (
                        len(validation_errors)
                        if isinstance(validation_errors, (dict, list))
                        else 1
                    ),
                    "user": user.username if user else "Anonymous",
                },
            )

        except Exception as e:
            logger.error(f"Failed to log validation failure: {str(e)}")
            # Don't raise exception to avoid breaking the main application flow

    @staticmethod
    def _sanitize_form_data(form_data):
        """Remove sensitive data from form data before logging."""
        if not form_data:
            return {}

        sensitive_fields = {
            "password",
            "password_hash",
            "confirm_password",
            "current_password",
            "new_password",
            "old_password",
            "csrf_token",
            "api_key",
            "secret",
            "token",
            "auth_token",
            "session_token",
            "ssn",
            "social_security",
        }

        sanitized = {}
        for key, value in form_data.items():
            if key.lower() in sensitive_fields or "password" in key.lower():
                sanitized[key] = "[REDACTED]"
            else:
                # Limit value length to prevent log bloat
                sanitized[key] = (
                    str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                )

        return sanitized


def auto_log_validation_failures(f):
    """
    Decorator to automatically log validation failures for any route.

    Usage:
        @app.route('/some-endpoint', methods=['POST'])
        @auto_log_validation_failures
        def some_endpoint():
            # Your route logic here
            pass
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Execute the original function
            return f(*args, **kwargs)
        except Exception as e:
            # Check if this is a validation-related exception
            if _is_validation_error(e):
                ValidationLogger.log_validation_failure(
                    endpoint=request.endpoint or f.__name__,
                    validation_errors=[str(e)],
                    form_data=request.form.to_dict() if request.form else None,
                    user_id=session.get("user_id"),
                )
            # Re-raise the exception to maintain normal error handling
            raise

    return decorated_function


def _is_validation_error(exception):
    """Determine if an exception is validation-related."""
    validation_indicators = [
        "validation",
        "invalid",
        "required",
        "format",
        "constraint",
        "field",
        "form",
        "input",
        "data",
    ]

    error_message = str(exception).lower()
    exception_type = type(exception).__name__.lower()

    return any(
        indicator in error_message or indicator in exception_type
        for indicator in validation_indicators
    )


def validate_patient_id(patient_id):
    """Validate patient ID parameter"""
    # Allow patient_id=0 for bulk operations, but reject negative numbers
    if patient_id is None or patient_id < 0:
        raise ValueError("Invalid patient ID")


# Flask middleware for automatic validation logging
def register_validation_middleware(app):
    """Register validation middleware with the Flask app."""

    @app.before_request
    def track_validation_context():
        """Store request context for validation logging."""
        # Store original form data for potential validation logging
        if request.method in ["POST", "PUT", "PATCH"] and request.form:
            request._original_form_data = request.form.to_dict()

    @app.errorhandler(400)
    def handle_validation_error(error):
        """Automatically log 400 Bad Request errors which often indicate validation failures."""
        if request.method in ["POST", "PUT", "PATCH"]:
            ValidationLogger.log_validation_failure(
                endpoint=request.endpoint or "unknown",
                validation_errors=[f"Bad Request: {str(error)}"],
                form_data=getattr(request, "_original_form_data", None),
                user_id=session.get("user_id"),
            )

        # Return the original error response
        return (
            error.get_response() if hasattr(error, "get_response") else str(error)
        ), 400

    logger.info("Validation middleware registered successfully")
