"""
Admin logging middleware consolidated from admin_middleware.py, api_access_middleware.py, and comprehensive_logging.py
Provides centralized logging for all admin and API access activities
"""
from functools import wraps
from flask import request, session, g, current_app
from datetime import datetime
import json
import uuid
from typing import Optional, Dict, Any


class AdminLogger:
    """Centralized admin logging utility"""
    
    # Monitored routes for automatic logging
    MONITORED_ROUTES = {
        # API endpoints
        '/api/users', '/api/patients', '/api/admin', '/api/user', '/api/patient',
        # Patient data access
        '/patient/', '/patients/', '/edit_patient/', '/patient_detail/',
        '/patient_documents/', '/generate_prep_sheet/', '/download_prep_sheet/',
        '/delete_patient/',
        # Medical data access
        '/add_condition/', '/add_vitals/', '/add_document/', '/add_immunization/',
        '/add_alert/', '/view_document/', '/delete_condition/', '/delete_vital/',
        '/delete_document/', '/delete_lab/', '/delete_imaging/', '/delete_consult/',
        '/delete_hospital/', '/delete_immunization/', '/delete_alert/',
        # Administrative access
        '/admin', '/admin_dashboard', '/screening_types', '/users/',
        # Appointment and visit management
        '/edit_appointment/', '/delete_appointment/', '/all_visits',
        '/delete_appointments_bulk', '/add_appointment',
        # Screening management
        '/screening_list', '/add_screening_form', '/add_screening_recommendation',
        '/edit_screening/', '/delete_screening/', '/checklist_settings',
        '/update_checklist_settings', '/update_checklist_generation',
        # Home page access
        '/', '/date/'
    }
    
    @staticmethod
    def log_event(event_type: str, user_id: Optional[int] = None, 
                  event_details: Optional[str] = None, request_id: Optional[str] = None,
                  ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log an admin event to the database"""
        try:
            from models import AdminLog
            from app import db
            
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())[:8]
            
            # Get IP and user agent from request if not provided
            if not ip_address:
                ip_address = request.remote_addr or '127.0.0.1'
            if not user_agent:
                user_agent = request.headers.get('User-Agent', 'Unknown')
            
            log_entry = AdminLog(
                event_type=event_type,
                user_id=user_id,
                event_details=event_details,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.now()
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Failed to log admin event: {str(e)}")
    
    @staticmethod
    def log_data_modification(action: str, data_type: str, record_id: Optional[int] = None,
                            patient_id: Optional[int] = None, patient_name: Optional[str] = None,
                            form_changes: Optional[Dict] = None, additional_data: Optional[Dict] = None):
        """Log data modification events with standardized format"""
        try:
            from flask_login import current_user
            user_id = current_user.id if current_user.is_authenticated else None
        except:
            user_id = None
        
        log_details = {
            'action': action,
            'data_type': data_type,
            'timestamp': datetime.now().isoformat(),
            'endpoint': request.endpoint or 'unknown',
            'method': request.method,
            'ip_address': request.remote_addr or '127.0.0.1'
        }
        
        if record_id:
            log_details[f'{data_type}_id'] = record_id
        if patient_id:
            log_details['patient_id'] = patient_id
        if patient_name:
            log_details['patient_name'] = patient_name
        if form_changes:
            log_details['form_changes'] = form_changes
        if additional_data:
            log_details.update(additional_data)
        
        AdminLogger.log_event(
            event_type='data_modification',
            user_id=user_id,
            event_details=json.dumps(log_details),
            request_id=f'{data_type}_{action}_{record_id or "new"}'
        )
    
    @staticmethod
    def should_log_route(route_path: str) -> bool:
        """Check if a route should be logged"""
        return any(monitored in route_path for monitored in AdminLogger.MONITORED_ROUTES)


def admin_required(f):
    """Decorator to protect admin routes and log access attempts"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            from flask_login import current_user
            
            # Log the access attempt
            AdminLogger.log_event(
                event_type='admin_access_attempt',
                user_id=current_user.id if current_user.is_authenticated else None,
                event_details=json.dumps({
                    'route': request.path,
                    'method': request.method,
                    'success': current_user.is_authenticated and getattr(current_user, 'is_admin', False),
                    'timestamp': datetime.now().isoformat()
                }),
                request_id=f'admin_access_{datetime.now().timestamp()}'
            )
            
            if not current_user.is_authenticated:
                from flask import redirect, url_for, flash
                flash('Please log in to access the admin area.', 'warning')
                return redirect(url_for('login'))
            
            if not getattr(current_user, 'is_admin', False):
                from flask import render_template
                return render_template('403.html'), 403
            
            return f(*args, **kwargs)
            
        except Exception as e:
            current_app.logger.error(f"Admin middleware error: {str(e)}")
            from flask import render_template
            return render_template('500.html'), 500
    
    return decorated_function


def log_api_access(f):
    """Decorator to automatically log API access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log API access
        try:
            from flask_login import current_user
            user_id = current_user.id if current_user.is_authenticated else None
        except:
            user_id = None
        
        AdminLogger.log_event(
            event_type='api_access',
            user_id=user_id,
            event_details=json.dumps({
                'route': request.path,
                'method': request.method,
                'args': dict(request.args),
                'timestamp': datetime.now().isoformat()
            }),
            request_id=f'api_{request.path.replace("/", "_")}_{datetime.now().timestamp()}'
        )
        
        return f(*args, **kwargs)
    
    return decorated_function


def register_admin_logging_middleware(app):
    """Register admin logging middleware with Flask app"""
    
    @app.before_request
    def log_admin_routes():
        """Automatically log access to monitored routes"""
        if AdminLogger.should_log_route(request.path):
            try:
                from flask_login import current_user
                user_id = current_user.id if current_user.is_authenticated else None
            except:
                user_id = None
            
            AdminLogger.log_event(
                event_type='route_access',
                user_id=user_id,
                event_details=json.dumps({
                    'route': request.path,
                    'method': request.method,
                    'timestamp': datetime.now().isoformat()
                }),
                request_id=f'route_{request.path.replace("/", "_")}_{datetime.now().timestamp()}'
            )
    
    @app.after_request
    def log_response_status(response):
        """Log response status for monitored routes"""
        if AdminLogger.should_log_route(request.path) and response.status_code >= 400:
            try:
                from flask_login import current_user
                user_id = current_user.id if current_user.is_authenticated else None
            except:
                user_id = None
            
            AdminLogger.log_event(
                event_type='error_response',
                user_id=user_id,
                event_details=json.dumps({
                    'route': request.path,
                    'method': request.method,
                    'status_code': response.status_code,
                    'timestamp': datetime.now().isoformat()
                }),
                request_id=f'error_{response.status_code}_{datetime.now().timestamp()}'
            )
        
        return response


def log_validation_error(endpoint: str, validation_errors: Dict, form_data: Dict, user_id: Optional[int] = None):
    """Log form validation errors for admin tracking"""
    AdminLogger.log_event(
        event_type='validation_error',
        user_id=user_id,
        event_details=json.dumps({
            'endpoint': endpoint,
            'validation_errors': validation_errors,
            'form_data_keys': list(form_data.keys()),  # Log keys only for privacy
            'timestamp': datetime.now().isoformat()
        }),
        request_id=f'validation_error_{endpoint}_{datetime.now().timestamp()}'
    )