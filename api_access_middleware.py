"""
API Access Logging Middleware
Automatically logs all access to sensitive API endpoints for audit and security purposes.
"""

import logging
from datetime import datetime
from flask import request, session, g
from models import AdminLog, User
from app import db
from datetime import datetime, timedelta
import uuid
import threading
import time
from structured_logging import get_structured_logger

# Create logger for API access middleware
logger = logging.getLogger(__name__)

# Global request tracking cache with thread-safe access
_request_cache = {}
_cache_lock = threading.Lock()

def _cleanup_cache():
    """Clean up old entries from the request cache"""
    current_time = time.time()
    with _cache_lock:
        keys_to_remove = [k for k, v in _request_cache.items() if current_time - v > 5]  # 5 second window
        for key in keys_to_remove:
            del _request_cache[key]

def _is_duplicate_request(user_id, route, method):
    """Check if this is a duplicate request within the time window"""
    current_time = time.time()
    request_key = f"{user_id}:{route}:{method}"

    with _cache_lock:
        if request_key in _request_cache:
            time_diff = current_time - _request_cache[request_key]
            if time_diff < 2:  # 2 second window
                return True

        # Store this request
        _request_cache[request_key] = current_time

    # Cleanup old entries periodically
    if len(_request_cache) > 100:  # Prevent memory buildup
        _cleanup_cache()

    return False

class APIAccessLogger:
    """Centralized API access logging utility."""

    # Define sensitive routes that require access logging
    MONITORED_ROUTES = {
        # API endpoints
        '/api/users',
        '/api/patients', 
        '/api/admin',
        '/api/user',
        '/api/patient',
        # Patient data access
        '/patient/',
        '/patients/',
        '/edit_patient/',
        '/patient_detail/',
        '/patient_documents/',
        '/generate_prep_sheet/',
        '/download_prep_sheet/',
        '/delete_patient/',
        # Medical data access
        '/add_condition/',
        '/add_vitals/',
        '/add_document/',
        '/add_immunization/',
        '/add_alert/',
        '/view_document/',
        '/delete_condition/',
        '/delete_vital/',
        '/delete_document/',
        '/delete_lab/',
        '/delete_imaging/',
        '/delete_consult/',
        '/delete_hospital/',
        '/delete_immunization/',
        '/delete_alert/',
        # Administrative access
        '/admin',
        '/admin_dashboard',
        '/screening_types',
        '/users/',
        # Appointment and visit management
        '/edit_appointment/',
        '/delete_appointment/',
        '/all_visits',
        '/delete_appointments_bulk',
        '/add_appointment',
        # Screening management
        '/screening_list',
        '/add_screening_form',
        '/add_screening_recommendation',
        '/edit_screening/',
        '/delete_screening/',
        '/checklist_settings',
        '/update_checklist_settings',
        '/update_checklist_generation',
        # Home page access
        '/',
        '/date/'
    }

    @staticmethod
    def log_api_access(route, user_id=None, additional_data=None):
        """
        Log API access to admin logs with standardized format.

        Args:
            route: The API route being accessed
            user_id: ID of the user accessing the API
            additional_data: Additional context data for the access
        """
        try:
            # Get user info
            user = None
            if user_id:
                user = User.query.get(user_id)
            elif session.get('user_id'):
                user = User.query.get(session.get('user_id'))

            # Check for duplicate requests using in-memory cache
            method = request.method if request else 'GET'
            user_identifier = user.id if user else 'anonymous'

            if _is_duplicate_request(user_identifier, route, method):
                logger.debug(f"Skipping duplicate request: {user_identifier}:{route}:{method}")
                return

            # Generate unique access ID for tracking
            access_id = str(uuid.uuid4())[:8]

            # Collect request details
            request_details = {
                'access_id': access_id,
                'route': route,
                'method': request.method if request else 'UNKNOWN',
                'user_agent': request.headers.get('User-Agent', 'Unknown') if request else 'Unknown',
                'ip_address': request.remote_addr if request else 'Unknown',
                'query_params': dict(request.args) if request and request.args else {},
                'content_type': request.content_type if request else 'Unknown',
                'user_id': user.id if user else None,
                'username': user.username if user else 'Anonymous'
            }

            # Add additional data if provided
            if additional_data:
                request_details.update(additional_data)

            # Create admin log entry
            admin_log = AdminLog(
                user_id=user.id if user else None,
                event_type='data_access',
                event_details=str(request_details),
                request_id=access_id,
                ip_address=request.remote_addr if request else 'Unknown'
            )

            db.session.add(admin_log)
            db.session.commit()

            # Log to application logger as well
            logger.info(
                f"API access [{access_id}] to {route}: "
                f"User: {user.username if user else 'Anonymous'} "
                f"({user.id if user else 'No ID']), "
                f"IP: {request.remote_addr if request else 'Unknown'}, "
                f"Method: {request.method if request else 'UNKNOWN'}"
            )

        except Exception as e:
            logger.error(f"Failed to log API access: {str(e)}")
            # Don't raise exception to avoid breaking the main application flow

    @staticmethod
    def should_log_route(route_path):
        """Check if a route should be logged."""
        if not route_path:
            return False

        # Skip static file requests
        if route_path.startswith('/static/'):
            return False

        # Check if the route starts with any monitored route or contains sensitive patterns
        for monitored in APIAccessLogger.MONITORED_ROUTES:
            if route_path.startswith(monitored) or monitored in route_path:
                return True

        # Additional patterns for patient data access
        sensitive_patterns = [
            '/patient/',
            '/patients/',
            'patient_detail',
            'edit_appointment',
            'delete_appointment',
            'delete_patient',
            'admin_dashboard',
            'view_document',
            'generate_prep_sheet',
            'all_visits',
            'delete_appointments_bulk',
            'add_condition',
            'add_vitals',
            'add_document',
            'add_immunization',
            'add_alert',
            'edit_patient',
            'screening_list',
            'screening_types',
            'add_screening',
            'edit_screening',
            'delete_screening',
            'checklist_settings'
        ]

        return any(pattern in route_path for pattern in sensitive_patterns)


def log_api_access(f):
    """
    Decorator to automatically log API access for specific routes.

    Usage:
        @app.route('/api/patients', methods=['GET'])
        @log_api_access
        def api_patients():
            # Your API logic here
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log the API access before executing the function
        route = request.endpoint or f.__name__
        user_id = session.get('user_id')

        APIAccessLogger.log_api_access(
            route=request.path,
            user_id=user_id,
            additional_data={
                'function_name': f.__name__,
                'endpoint': route
            }
        )

        # Execute the original function
        return f(*args, **kwargs)

    return decorated_function


# Flask middleware for automatic API access logging
def register_api_access_middleware(app):
    """Register API access middleware with the Flask app."""

    @app.before_request
    def log_api_access_automatically():
        """Automatically log access to monitored API routes."""
        if request.path and APIAccessLogger.should_log_route(request.path):
            try:
                # Extract user ID and username from session
                user_id = session.get('user_id')
                username = session.get('username', 'Unknown')

                # Extract patient ID from URL if present
                patient_id = None
                appointment_id = None
                import re

                # Match patterns like /patient/123 or /edit_patient/123
                patient_match = re.search(r'/(?:patient|edit_patient|patient_detail)/(\d+)', request.path)
                if patient_match:
                    patient_id = patient_match.group(1)

                # Match appointment patterns
                appointment_match = re.search(r'/(?:edit_appointment|delete_appointment)/(\d+)', request.path)
                if appointment_match:
                    appointment_id = appointment_match.group(1)

                # Get additional context
                additional_data = {
                    'method': request.method,
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', '')[:200],
                    'username': username,
                    'referer': request.headers.get('Referer', ''),
                    'timestamp': datetime.utcnow().isoformat()
                }

                # Add specific IDs if found
                if patient_id:
                    additional_data['patient_id'] = patient_id
                    additional_data['access_type'] = 'patient_data'

                if appointment_id:
                    additional_data['appointment_id'] = appointment_id
                    additional_data['access_type'] = 'appointment_data'

                # Add form data context for POST requests (sanitized)
                if request.method == 'POST' and request.form:
                    form_fields = [field for field in request.form.keys() if 'password' not in field.lower()]
                    additional_data['form_fields'] = form_fields
                    additional_data['action_type'] = 'data_modification'

                # Determine access category
                if 'admin' in request.path.lower():
                    additional_data['access_category'] = 'administrative'
                elif any(pattern in request.path for pattern in ['patient', 'appointment', 'document']):
                    additional_data['access_category'] = 'patient_data'
                else:
                    additional_data['access_category'] = 'general'

                # Log the access with structured logging
                structured_logger = get_structured_logger('api_access')

                # Log the access with structured logging
                structured_logger.log_patient_access(
                    patient_id=patient_id if patient_id else 0,
                    action=f"{additional_data['method']} {request.path}",
                    user_id=user_id,
                    username=username,
                    additional_data={
                        'ip_address': additional_data['ip_address'],
                        'user_agent': additional_data['user_agent'],
                        'appointment_id': appointment_id,
                        'endpoint': request.path
                    }
                )
            except Exception as e:
                logger.error(f"Error in automatic API access logging: {str(e)}")

    @app.after_request
    def log_api_response_status(response):
        """Log API response status for monitored routes."""
        if request.path and APIAccessLogger.should_log_route(request.path):
            try:
                # Log response status for audit trail
                access_details = {
                    'route': request.path,
                    'response_status': response.status_code,
                    'response_size': len(response.get_data()),
                    'user_id': session.get('user_id'),
                    'timestamp': datetime.utcnow().isoformat()
                }

                logger.info(f"API response: {request.path} -> {response.status_code}")

            except Exception as e:
                logger.error(f"Failed to log API response: {str(e)}")

        return response

    logger.info("API access middleware registered successfully")