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
    Decorator to log patient-related operations (view, edit, delete, add)
    Standardized to only use: view, edit, delete, add

    Args:
        operation_type: String describing the operation (view, edit, delete, add)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.now()

            try:
                # Standardize operation types
                standardized_ops = {
                    'view': 'view', 'view_patient': 'view', 'patient_view': 'view',
                    'edit': 'edit', 'edit_patient': 'edit', 'patient_edit': 'edit', 'update': 'edit',
                    'delete': 'delete', 'delete_patient': 'delete', 'patient_delete': 'delete', 'remove': 'delete',
                    'add': 'add', 'add_patient': 'add', 'patient_add': 'add', 'create': 'add', 'new': 'add',
                    'add_appointment': 'add', 'edit_appointment': 'edit', 'delete_appointment': 'delete'
                }
                
                standardized_operation = standardized_ops.get(operation_type.lower(), operation_type)

                # Extract patient ID from URL parameters or form data
                patient_id = None
                if 'patient_id' in kwargs:
                    patient_id = kwargs['patient_id']
                elif 'id' in kwargs:
                    patient_id = kwargs['id']
                elif request.view_args and 'id' in request.view_args:
                    patient_id = request.view_args['id']
                elif request.view_args and 'patient_id' in request.view_args:
                    patient_id = request.view_args['patient_id']
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

                # Log the operation with standardized action
                log_details = {
                    'action': standardized_operation,  # Standardized action
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

                # Enhanced form data capture for different types of changes
                if request.method in ['POST', 'PUT', 'PATCH'] and request.form:
                    # Sanitize form data (remove sensitive fields)
                    sanitized_form = {}
                    sensitive_fields = ['password', 'csrf_token']
                    form_changes = {}
                    
                    for key, value in request.form.items():
                        if key.lower() not in sensitive_fields:
                            sanitized_form[key] = str(value)[:200]  # Truncate long values
                            
                            # Track specific field changes for different types
                            if key in ['first_name', 'last_name', 'date_of_birth', 'sex', 'mrn', 'phone', 'email', 'address', 'insurance']:
                                form_changes[f'demographics_{key}'] = str(value)[:100]
                            elif key in ['alert_type', 'description', 'details', 'severity', 'start_date', 'end_date']:
                                form_changes[f'alert_{key}'] = str(value)[:100]
                            elif key in ['screening_type', 'due_date', 'last_completed', 'priority', 'notes']:
                                form_changes[f'screening_{key}'] = str(value)[:100]
                            elif key in ['appointment_date', 'appointment_time', 'note', 'status']:
                                form_changes[f'appointment_{key}'] = str(value)[:100]
                    
                    log_details['form_data'] = sanitized_form
                    if form_changes:
                        log_details['form_changes'] = form_changes
                    
                    # Extract specific appointment data if available
                    if 'appointment' in f.__name__.lower() or 'appointment' in request.path:
                        appointment_changes = {}
                        if 'appointment_date' in request.form:
                            appointment_changes['date'] = request.form['appointment_date']
                        if 'appointment_time' in request.form:
                            appointment_changes['time'] = request.form['appointment_time']
                        if 'note' in request.form:
                            appointment_changes['note'] = request.form['note']
                        if 'patient_id' in request.form:
                            appointment_changes['patient_reassigned'] = request.form['patient_id']
                        if 'status' in request.form:
                            appointment_changes['status'] = request.form['status']
                        if appointment_changes:
                            log_details['appointment_changes'] = appointment_changes

                # Extract appointment ID from URL if present
                appointment_id = None
                if 'appointment_id' in kwargs:
                    appointment_id = kwargs['appointment_id']
                elif request.view_args and 'appointment_id' in request.view_args:
                    appointment_id = request.view_args['appointment_id']
                elif '/appointments/' in request.path:
                    try:
                        # Extract appointment ID from URL path
                        path_parts = request.path.split('/')
                        if 'appointments' in path_parts:
                            apt_index = path_parts.index('appointments')
                            if apt_index + 1 < len(path_parts):
                                appointment_id = int(path_parts[apt_index + 1])
                    except (ValueError, IndexError):
                        pass

                if appointment_id:
                    log_details['appointment_id'] = appointment_id

                # Create admin log entry with standardized event type
                AdminLog.log_event(
                    event_type=standardized_operation,  # Use standardized action as event type
                    user_id=user_id,
                    event_details=json.dumps(log_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )

                try:
                    db.session.commit()
                except Exception as commit_error:
                    logger.warning(f"Failed to commit admin log: {str(commit_error)}")
                    db.session.rollback()

                return result

            except Exception as e:
                # Log errors with better error handling
                try:
                    error_details = {
                        'action': f'{standardized_operation}_error',
                        'patient_id': patient_id if 'patient_id' in locals() else None,
                        'patient_name': patient_name if 'patient_name' in locals() else 'Unknown',
                        'function_name': f.__name__,
                        'error_message': str(e),
                        'user_id': session.get('user_id'),
                        'username': session.get('username', 'Unknown'),
                        'timestamp': datetime.now().isoformat(),
                        'success': False
                    }

                    AdminLog.log_event(
                        event_type='error',
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
                except Exception as log_error:
                    logger.error(f"Failed to log error: {str(log_error)}")

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