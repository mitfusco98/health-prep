"""
Comprehensive logging decorators for healthcare application
Logs all edits, deletions, views, and page accesses with detailed context
"""

import logging
from functools import wraps
from flask import request, session, g
from datetime import datetime
import json
import uuid
from models import AdminLog, User, Patient
from app import db

logger = logging.getLogger(__name__)

def log_patient_operation(operation_type):
    """
    Decorator to log patient-related operations (view, edit, delete, create)

    Args:
        operation_type: String describing the operation (view, edit, delete, create)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.now()

            try:
                # Extract patient ID from URL parameters or form data
                patient_id = None
                if 'patient_id' in kwargs:
                    patient_id = kwargs['patient_id']
                elif 'id' in kwargs:
                    patient_id = kwargs['id']
                elif request.view_args and 'id' in request.view_args:
                    patient_id = request.view_args['id']
                elif request.form and 'patient_id' in request.form:
                    patient_id = request.form['patient_id']

                # Get user information
                user_id = session.get('user_id')
                username = session.get('username', 'Unknown')

                # Get patient information if available
                patient_name = 'Unknown'
                if patient_id:
                    try:
                        patient = Patient.query.get(patient_id)
                        if patient:
                            patient_name = patient.full_name
                    except Exception:
                        pass

                # Execute the original function
                result = f(*args, **kwargs)

                # Calculate execution time
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds() * 1000

                # Log the operation
                log_details = {
                    'operation_type': operation_type,
                    'patient_id': patient_id,
                    'patient_name': patient_name,
                    'function_name': f.__name__,
                    'endpoint': request.endpoint,
                    'route': request.path,
                    'method': request.method,
                    'execution_time_ms': execution_time,
                    'user_id': user_id,
                    'username': username,
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }

                # Add form data context for modifications
                if request.method in ['POST', 'PUT', 'PATCH'] and request.form:
                    # Sanitize form data (remove sensitive fields)
                    sanitized_form = {}
                    sensitive_fields = ['password', 'csrf_token']
                    for key, value in request.form.items():
                        if key.lower() not in sensitive_fields:
                            sanitized_form[key] = str(value)[:200]  # Truncate long values
                    log_details['form_data'] = sanitized_form

                # Create admin log entry
                AdminLog.log_event(
                    event_type=f'patient_{operation_type}',
                    user_id=user_id,
                    event_details=json.dumps(log_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )

                db.session.commit()

                return result

            except Exception as e:
                # Log errors
                error_details = {
                    'operation_type': operation_type,
                    'patient_id': patient_id,
                    'function_name': f.__name__,
                    'error_message': str(e),
                    'user_id': session.get('user_id'),
                    'username': session.get('username', 'Unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'success': False
                }

                AdminLog.log_event(
                    event_type=f'patient_{operation_type}_error',
                    user_id=session.get('user_id'),
                    event_details=json.dumps(error_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )

                try:
                    db.session.commit()
                except:
                    db.session.rollback()

                raise

        return decorated_function
    return decorator

def log_admin_operation(operation_type):
    """
    Decorator to log administrative operations
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.now()

            try:
                # Get user information
                user_id = session.get('user_id')
                username = session.get('username', 'Unknown')

                # Execute the original function
                result = f(*args, **kwargs)

                # Calculate execution time
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds() * 1000

                # Log the operation
                log_details = {
                    'operation_type': operation_type,
                    'function_name': f.__name__,
                    'endpoint': request.endpoint,
                    'route': request.path,
                    'method': request.method,
                    'execution_time_ms': execution_time,
                    'user_id': user_id,
                    'username': username,
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }

                # Add query parameters for GET requests
                if request.args:
                    log_details['query_params'] = dict(request.args)

                # Add form data for modifications
                if request.method in ['POST', 'PUT', 'PATCH'] and request.form:
                    sanitized_form = {}
                    sensitive_fields = ['password', 'csrf_token']
                    for key, value in request.form.items():
                        if key.lower() not in sensitive_fields:
                            sanitized_form[key] = str(value)[:200]
                    log_details['form_data'] = sanitized_form

                # Create admin log entry
                AdminLog.log_event(
                    event_type=f'admin_{operation_type}',
                    user_id=user_id,
                    event_details=json.dumps(log_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )

                db.session.commit()

                return result

            except Exception as e:
                # Log errors
                error_details = {
                    'operation_type': operation_type,
                    'function_name': f.__name__,
                    'error_message': str(e),
                    'user_id': session.get('user_id'),
                    'username': session.get('username', 'Unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'success': False
                }

                AdminLog.log_event(
                    event_type=f'admin_{operation_type}_error',
                    user_id=session.get('user_id'),
                    event_details=json.dumps(error_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )

                try:
                    db.session.commit()
                except:
                    db.session.rollback()

                raise

        return decorated_function
    return decorator

def log_data_modification(data_type):
    """
    Decorator to log data modifications (conditions, vitals, documents, etc.)

    Args:
        data_type: String describing the type of data (condition, vital, document, etc.)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.now()

            try:
                # Get user information
                user_id = session.get('user_id')
                username = session.get('username', 'Unknown')

                # Extract relevant IDs from URL parameters or form data
                record_id = None
                patient_id = None

                if 'id' in kwargs:
                    record_id = kwargs['id']
                elif request.view_args and 'id' in request.view_args:
                    record_id = request.view_args['id']

                if 'patient_id' in kwargs:
                    patient_id = kwargs['patient_id']
                elif request.form and 'patient_id' in request.form:
                    patient_id = request.form['patient_id']

                # Execute the original function
                result = f(*args, **kwargs)

                # Calculate execution time
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds() * 1000

                # Log the operation
                log_details = {
                    'data_type': data_type,
                    'record_id': record_id,
                    'patient_id': patient_id,
                    'function_name': f.__name__,
                    'endpoint': request.endpoint,
                    'route': request.path,
                    'method': request.method,
                    'execution_time_ms': execution_time,
                    'user_id': user_id,
                    'username': username,
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }

                # Add form data for modifications
                if request.method in ['POST', 'PUT', 'PATCH'] and request.form:
                    sanitized_form = {}
                    sensitive_fields = ['password', 'csrf_token']
                    for key, value in request.form.items():
                        if key.lower() not in sensitive_fields:
                            sanitized_form[key] = str(value)[:200]
                    log_details['modified_data'] = sanitized_form

                # Create admin log entry
                AdminLog.log_event(
                    event_type=f'data_modification',
                    user_id=user_id,
                    event_details=json.dumps(log_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )

                db.session.commit()

                return result

            except Exception as e:
                # Log errors
                error_details = {
                    'data_type': data_type,
                    'function_name': f.__name__,
                    'error_message': str(e),
                    'user_id': session.get('user_id'),
                    'username': session.get('username', 'Unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'success': False
                }

                AdminLog.log_event(
                    event_type=f'data_modification_error',
                    user_id=session.get('user_id'),
                    event_details=json.dumps(error_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )

                try:
                    db.session.commit()
                except:
                    db.session.rollback()

                raise

        return decorated_function
    return decorator

def log_page_access(page_type):
    """
    Decorator to log page access

    Args:
        page_type: String describing the page type (dashboard, patient_list, etc.)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get user information
                user_id = session.get('user_id')
                username = session.get('username', 'Unknown')

                # Execute the original function
                result = f(*args, **kwargs)

                # Log the page access
                log_details = {
                    'page_type': page_type,
                    'function_name': f.__name__,
                    'endpoint': request.endpoint,
                    'route': request.path,
                    'method': request.method,
                    'user_id': user_id,
                    'username': username,
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.now().isoformat(),
                    'referer': request.headers.get('Referer', ''),
                    'success': True
                }

                # Add query parameters
                if request.args:
                    log_details['query_params'] = dict(request.args)

                # Create admin log entry (only for significant page accesses)
                if page_type in ['admin_dashboard', 'patient_list', 'patient_detail', 'screening_list']:
                    AdminLog.log_event(
                        event_type=f'page_access',
                        user_id=user_id,
                        event_details=json.dumps(log_details),
                        request_id=str(uuid.uuid4()),
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent', '')
                    )

                    db.session.commit()

                return result

            except Exception as e:
                logger.error(f"Error logging page access for {page_type}: {str(e)}")
                # Don't let logging errors break the application
                try:
                    db.session.rollback()
                except:
                    pass
                raise

        return decorated_function
    return decorator