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
                            elif key in ['alert_type', 'description', 'details', 'severity', 'start_date', 'end_date', 'text', 'priority']:
                                form_changes[f'alert_{key}'] = str(value)[:100]
                                # Store alert-specific data with detailed field names
                                if key == 'text' or key == 'description':
                                    log_details['alert_text'] = str(value)[:200]
                                elif key == 'alert_type':
                                    log_details['alert_type'] = str(value)[:50]
                                elif key == 'priority':
                                    log_details['priority'] = str(value)[:20]
                                elif key == 'start_date':
                                    log_details['alert_date'] = str(value)[:20]
                            elif key in ['screening_type', 'due_date', 'last_completed', 'priority', 'notes']:
                                form_changes[f'screening_{key}'] = str(value)[:100]
                            elif key in ['appointment_date', 'appointment_time', 'note', 'status']:
                                form_changes[f'appointment_{key}'] = str(value)[:100]
                            # Medical data specific fields
                            elif key in ['condition_name', 'diagnosis', 'diagnosis_date', 'severity', 'status']:
                                form_changes[f'condition_{key}'] = str(value)[:100]
                                if key == 'condition_name' or key == 'diagnosis':
                                    log_details['condition_name'] = str(value)[:100]
                                elif key == 'diagnosis_date':
                                    log_details['diagnosis_date'] = str(value)[:20]
                            elif key in ['test_name', 'test_date', 'result', 'lab_name', 'lab_date', 'value']:
                                form_changes[f'lab_{key}'] = str(value)[:100]
                                if key == 'test_name' or key == 'lab_name':
                                    log_details['test_name'] = str(value)[:100]
                                elif key == 'test_date' or key == 'lab_date':
                                    log_details['test_date'] = str(value)[:20]
                                elif key == 'result' or key == 'value':
                                    log_details['result_value'] = str(value)[:100]
                            elif key in ['vaccine_name', 'vaccination_date', 'lot_number', 'immunization_name', 'immunization_date']:
                                form_changes[f'immunization_{key}'] = str(value)[:100]
                                if key == 'vaccine_name' or key == 'immunization_name':
                                    log_details['vaccine_name'] = str(value)[:100]
                                elif key == 'vaccination_date' or key == 'immunization_date':
                                    log_details['vaccination_date'] = str(value)[:20]
                                elif key == 'lot_number':
                                    log_details['lot_number'] = str(value)[:50]
                            elif key in ['blood_pressure', 'heart_rate', 'temperature', 'weight', 'vital_date', 'measurement_date']:
                                form_changes[f'vital_{key}'] = str(value)[:100]
                                if key == 'vital_date' or key == 'measurement_date':
                                    log_details['vital_date'] = str(value)[:20]
                                elif key in ['blood_pressure', 'heart_rate', 'temperature', 'weight']:
                                    log_details[key] = str(value)[:20]
                    
                    log_details['form_data'] = sanitized_form
                    if form_changes:
                        log_details['form_changes'] = form_changes

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

                # Add form data for modifications and capture specific details
                if request.method in ['POST', 'PUT', 'PATCH'] and request.form:
                    sanitized_form = {}
                    sensitive_fields = ['password', 'csrf_token']
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    current_time = datetime.now().strftime('%H:%M:%S')
                    
                    for key, value in request.form.items():
                        if key.lower() not in sensitive_fields:
                            sanitized_form[key] = str(value)[:200]
                    log_details['modified_data'] = sanitized_form
                    
                    # Capture specific details based on data type
                    if data_type == 'alert':
                        log_details['alert_text'] = request.form.get('text', request.form.get('description', ''))[:200]
                        log_details['alert_date'] = request.form.get('start_date', current_date)
                        log_details['alert_time'] = current_time
                        log_details['priority'] = request.form.get('priority', '')
                        log_details['alert_type'] = request.form.get('alert_type', '')
                    elif data_type == 'condition':
                        log_details['condition_name'] = request.form.get('condition_name', request.form.get('diagnosis', ''))
                        log_details['diagnosis_date'] = request.form.get('diagnosis_date', current_date)
                        log_details['severity'] = request.form.get('severity', '')
                        log_details['status'] = request.form.get('status', '')
                    elif data_type == 'vital':
                        log_details['vital_date'] = request.form.get('vital_date', request.form.get('measurement_date', current_date))
                        log_details['vital_time'] = current_time
                        log_details['blood_pressure'] = request.form.get('blood_pressure', '')
                        log_details['heart_rate'] = request.form.get('heart_rate', '')
                        log_details['temperature'] = request.form.get('temperature', '')
                        log_details['weight'] = request.form.get('weight', '')
                    elif data_type in ['lab', 'test']:
                        log_details['test_name'] = request.form.get('test_name', request.form.get('lab_name', ''))
                        log_details['test_date'] = request.form.get('test_date', request.form.get('lab_date', current_date))
                        log_details['test_time'] = current_time
                        log_details['result_value'] = request.form.get('result', request.form.get('value', ''))
                    elif data_type == 'immunization':
                        log_details['vaccine_name'] = request.form.get('vaccine_name', request.form.get('immunization_name', ''))
                        log_details['vaccination_date'] = request.form.get('vaccination_date', request.form.get('immunization_date', current_date))
                        log_details['vaccination_time'] = current_time
                        log_details['lot_number'] = request.form.get('lot_number', '')

                # Capture file upload details for document operations
                if data_type == 'document' and request.files:
                    for file_key, file_obj in request.files.items():
                        if file_obj and file_obj.filename:
                            log_details['file_name'] = file_obj.filename
                            log_details['file_type'] = file_obj.content_type or 'unknown'
                            log_details['upload_date'] = datetime.now().strftime('%Y-%m-%d')
                            log_details['upload_time'] = datetime.now().strftime('%H:%M:%S')
                            # Get file size if available
                            if hasattr(file_obj, 'content_length') and file_obj.content_length:
                                log_details['file_size'] = f"{file_obj.content_length} bytes"
                            break

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