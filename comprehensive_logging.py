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
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    current_time = datetime.now().strftime('%H:%M:%S')
                    
                    for key, value in request.form.items():
                        if key.lower() not in sensitive_fields:
                            sanitized_form[key] = str(value)[:200]  # Truncate long values
                            
                            # Track specific field changes for different types
                            if key in ['first_name', 'last_name', 'date_of_birth', 'sex', 'mrn', 'phone', 'email', 'address', 'insurance']:
                                form_changes[f'demographics_{key}'] = str(value)[:100]
                            elif key in ['alert_type', 'description', 'details', 'severity', 'start_date', 'end_date', 'text', 'priority', 'is_active']:
                                form_changes[f'alert_{key}'] = str(value)[:100]
                                # Store alert-specific data with ALL detailed field names
                                if key == 'description':
                                    log_details['alert_description'] = str(value)[:200]
                                    log_details['alert_text'] = str(value)[:200]  # Legacy compatibility
                                elif key == 'details':
                                    log_details['alert_details'] = str(value)[:500]
                                elif key == 'alert_type':
                                    log_details['alert_type'] = str(value)[:50]
                                elif key == 'severity':
                                    log_details['severity'] = str(value)[:20]
                                    log_details['priority'] = str(value)[:20]  # Map severity to priority
                                elif key == 'start_date':
                                    log_details['alert_start_date'] = str(value)[:20]
                                    log_details['alert_date'] = str(value)[:20]  # Legacy compatibility
                                    log_details['alert_time'] = current_time
                                elif key == 'end_date':
                                    log_details['alert_end_date'] = str(value)[:20]
                                elif key == 'is_active':
                                    log_details['alert_is_active'] = bool(value)
                                elif key == 'text':
                                    log_details['alert_text'] = str(value)[:200]
                            elif key in ['screening_type', 'due_date', 'last_completed', 'priority', 'notes']:
                                form_changes[f'screening_{key}'] = str(value)[:100]
                            elif key in ['appointment_date', 'appointment_time', 'note', 'status']:
                                form_changes[f'appointment_{key}'] = str(value)[:100]
                            # Medical data specific fields with enhanced details
                            elif key in ['condition_name', 'name', 'diagnosis', 'diagnosed_date', 'diagnosis_date', 'severity', 'status', 'is_active', 'notes']:
                                form_changes[f'condition_{key}'] = str(value)[:100]
                                if key in ['condition_name', 'name', 'diagnosis']:
                                    log_details['condition_name'] = str(value)[:100]
                                elif key in ['diagnosed_date', 'diagnosis_date']:
                                    log_details['diagnosis_date'] = str(value)[:20]
                                    log_details['diagnosis_time'] = current_time
                                elif key == 'severity':
                                    log_details['severity'] = str(value)[:20]
                                elif key == 'status':
                                    log_details['status'] = str(value)[:20]
                            elif key in ['test_name', 'test_date', 'result', 'result_value', 'lab_name', 'lab_date', 'value', 'unit', 'reference_range', 'is_abnormal']:
                                form_changes[f'lab_{key}'] = str(value)[:100]
                                if key in ['test_name', 'lab_name']:
                                    log_details['test_name'] = str(value)[:100]
                                elif key in ['test_date', 'lab_date']:
                                    log_details['test_date'] = str(value)[:20]
                                    log_details['test_time'] = current_time
                                elif key in ['result', 'result_value', 'value']:
                                    log_details['result_value'] = str(value)[:100]
                                elif key == 'unit':
                                    log_details['unit'] = str(value)[:20]
                                elif key == 'reference_range':
                                    log_details['reference_range'] = str(value)[:50]
                            elif key in ['vaccine_name', 'vaccination_date', 'administration_date', 'immunization_date', 'lot_number', 'immunization_name', 'dose_number', 'manufacturer']:
                                form_changes[f'immunization_{key}'] = str(value)[:100]
                                if key in ['vaccine_name', 'immunization_name']:
                                    log_details['vaccine_name'] = str(value)[:100]
                                elif key in ['vaccination_date', 'administration_date', 'immunization_date']:
                                    log_details['vaccination_date'] = str(value)[:20]
                                    log_details['vaccination_time'] = current_time
                                elif key == 'lot_number':
                                    log_details['lot_number'] = str(value)[:50]
                                elif key == 'dose_number':
                                    log_details['dose_number'] = str(value)[:10]
                                elif key == 'manufacturer':
                                    log_details['manufacturer'] = str(value)[:50]
                            elif key in ['blood_pressure', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'heart_rate', 'pulse', 'temperature', 'weight', 'height', 'bmi', 'oxygen_saturation', 'respiratory_rate', 'date', 'vital_date', 'measurement_date']:
                                form_changes[f'vital_{key}'] = str(value)[:100]
                                if key in ['date', 'vital_date', 'measurement_date']:
                                    log_details['vital_date'] = str(value)[:20]
                                    log_details['vital_time'] = current_time
                                elif key == 'blood_pressure':
                                    log_details['blood_pressure'] = str(value)[:20]
                                elif key in ['blood_pressure_systolic', 'blood_pressure_diastolic']:
                                    log_details[key] = str(value)[:10]
                                elif key in ['heart_rate', 'pulse']:
                                    log_details['heart_rate'] = str(value)[:10]
                                elif key == 'temperature':
                                    log_details['temperature'] = str(value)[:10]
                                elif key == 'weight':
                                    log_details['weight'] = str(value)[:10]
                                elif key == 'height':
                                    log_details['height'] = str(value)[:10]
                                elif key in ['oxygen_saturation', 'respiratory_rate', 'bmi']:
                                    log_details[key] = str(value)[:10]
                            elif key in ['study_type', 'imaging_type', 'body_site', 'location', 'study_date', 'imaging_date', 'findings', 'impression']:
                                form_changes[f'imaging_{key}'] = str(value)[:100]
                                if key in ['study_type', 'imaging_type']:
                                    log_details['imaging_type'] = str(value)[:100]
                                elif key in ['study_date', 'imaging_date']:
                                    log_details['imaging_date'] = str(value)[:20]
                                    log_details['imaging_time'] = current_time
                                elif key in ['body_site', 'location']:
                                    log_details['body_site'] = str(value)[:50]
                                elif key == 'findings':
                                    log_details['findings'] = str(value)[:200]
                            elif key in ['specialist', 'consultant', 'specialty', 'speciality', 'report_date', 'consult_date', 'reason', 'referral_reason', 'recommendations']:
                                form_changes[f'consult_{key}'] = str(value)[:100]
                                if key in ['specialist', 'consultant']:
                                    log_details['specialist'] = str(value)[:100]
                                elif key in ['specialty', 'speciality']:
                                    log_details['specialty'] = str(value)[:50]
                                elif key in ['report_date', 'consult_date']:
                                    log_details['consult_date'] = str(value)[:20]
                                    log_details['consult_time'] = current_time
                                elif key in ['reason', 'referral_reason']:
                                    log_details['referral_reason'] = str(value)[:200]
                            elif key in ['hospital_name', 'facility', 'admission_date', 'discharge_date', 'admitting_diagnosis', 'discharge_diagnosis', 'procedures']:
                                form_changes[f'hospital_{key}'] = str(value)[:100]
                                if key in ['hospital_name', 'facility']:
                                    log_details['hospital_name'] = str(value)[:100]
                                elif key == 'admission_date':
                                    log_details['admission_date'] = str(value)[:20]
                                    log_details['admission_time'] = current_time
                                elif key == 'discharge_date':
                                    log_details['discharge_date'] = str(value)[:20]
                                elif key == 'admitting_diagnosis':
                                    log_details['admitting_diagnosis'] = str(value)[:200]
                    
                    # Ensure alert data always has time component when date is present
                    if 'alert_date' in log_details and 'alert_time' not in log_details:
                        log_details['alert_time'] = current_time
                    
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
                    
                    # Capture specific details based on data type with enhanced information
                    if data_type == 'alert':
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        # Capture ALL alert fields for comprehensive logging
                        log_details['alert_description'] = request.form.get('description', '')[:200]
                        log_details['alert_details'] = request.form.get('details', '')[:500]
                        log_details['alert_type'] = request.form.get('alert_type', '')
                        log_details['severity'] = request.form.get('severity', '')
                        log_details['start_date'] = request.form.get('start_date', current_date)
                        log_details['end_date'] = request.form.get('end_date', '')
                        log_details['is_active'] = bool(request.form.get('is_active'))
                        log_details['alert_time'] = current_time
                        # Legacy field for backward compatibility
                        log_details['alert_text'] = request.form.get('description', '')[:200]
                        log_details['alert_date'] = request.form.get('start_date', current_date)
                        log_details['priority'] = request.form.get('severity', '')  # Map severity to priority for consistency
                    elif data_type == 'condition':
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        log_details['condition_name'] = request.form.get('name', request.form.get('condition_name', request.form.get('diagnosis', '')))
                        log_details['diagnosis_date'] = request.form.get('diagnosed_date', request.form.get('diagnosis_date', current_date))
                        log_details['diagnosis_time'] = current_time
                        log_details['severity'] = request.form.get('severity', '')
                        log_details['status'] = request.form.get('status', 'Active' if request.form.get('is_active') else 'Inactive')
                        log_details['code'] = request.form.get('code', '')
                    elif data_type == 'vital':
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        log_details['vital_date'] = request.form.get('date', request.form.get('vital_date', request.form.get('measurement_date', current_date)))
                        log_details['vital_time'] = current_time
                        log_details['blood_pressure'] = request.form.get('blood_pressure', '')
                        if not log_details['blood_pressure'] and request.form.get('blood_pressure_systolic') and request.form.get('blood_pressure_diastolic'):
                            log_details['blood_pressure'] = f"{request.form.get('blood_pressure_systolic')}/{request.form.get('blood_pressure_diastolic')}"
                        log_details['heart_rate'] = request.form.get('heart_rate', request.form.get('pulse', ''))
                        log_details['temperature'] = request.form.get('temperature', '')
                        log_details['weight'] = request.form.get('weight', '')
                        log_details['height'] = request.form.get('height', '')
                        log_details['oxygen_saturation'] = request.form.get('oxygen_saturation', '')
                        log_details['respiratory_rate'] = request.form.get('respiratory_rate', '')
                    elif data_type in ['lab', 'test']:
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        log_details['test_name'] = request.form.get('test_name', request.form.get('lab_name', ''))
                        log_details['test_date'] = request.form.get('test_date', request.form.get('lab_date', current_date))
                        log_details['test_time'] = current_time
                        log_details['result_value'] = request.form.get('result_value', request.form.get('result', request.form.get('value', '')))
                        log_details['unit'] = request.form.get('unit', '')
                        log_details['reference_range'] = request.form.get('reference_range', '')
                        log_details['is_abnormal'] = bool(request.form.get('is_abnormal'))
                    elif data_type == 'immunization':
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        log_details['vaccine_name'] = request.form.get('vaccine_name', request.form.get('immunization_name', ''))
                        log_details['vaccination_date'] = request.form.get('administration_date', request.form.get('vaccination_date', request.form.get('immunization_date', current_date)))
                        log_details['vaccination_time'] = current_time
                        log_details['lot_number'] = request.form.get('lot_number', '')
                        log_details['dose_number'] = request.form.get('dose_number', '')
                        log_details['manufacturer'] = request.form.get('manufacturer', '')
                    elif data_type == 'imaging':
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        log_details['imaging_type'] = request.form.get('study_type', request.form.get('imaging_type', ''))
                        log_details['imaging_date'] = request.form.get('study_date', request.form.get('imaging_date', current_date))
                        log_details['imaging_time'] = current_time
                        log_details['body_site'] = request.form.get('body_site', request.form.get('location', ''))
                        log_details['findings'] = request.form.get('findings', '')[:200]
                        log_details['impression'] = request.form.get('impression', '')[:200]
                    elif data_type == 'consult':
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        log_details['specialist'] = request.form.get('specialist', request.form.get('consultant', ''))
                        log_details['specialty'] = request.form.get('specialty', request.form.get('speciality', ''))
                        log_details['consult_date'] = request.form.get('report_date', request.form.get('consult_date', current_date))
                        log_details['consult_time'] = current_time
                        log_details['referral_reason'] = request.form.get('reason', request.form.get('referral_reason', ''))[:200]
                        log_details['findings'] = request.form.get('findings', '')[:200]
                        log_details['recommendations'] = request.form.get('recommendations', '')[:200]
                    elif data_type == 'hospital':
                        log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                        log_details['hospital_name'] = request.form.get('hospital_name', request.form.get('facility', ''))
                        log_details['admission_date'] = request.form.get('admission_date', current_date)
                        log_details['admission_time'] = current_time
                        log_details['discharge_date'] = request.form.get('discharge_date', '')
                        log_details['admitting_diagnosis'] = request.form.get('admitting_diagnosis', '')[:200]
                        log_details['discharge_diagnosis'] = request.form.get('discharge_diagnosis', '')[:200]
                        log_details['procedures'] = request.form.get('procedures', '')[:200]

                # Capture file upload details for document operations
                if data_type == 'document':
                    log_details['action'] = 'add' if request.method == 'POST' else 'edit'
                    log_details['upload_date'] = datetime.now().strftime('%Y-%m-%d')
                    log_details['upload_time'] = datetime.now().strftime('%H:%M:%S')
                    
                    # Get file details from form data
                    log_details['document_name'] = request.form.get('document_name', '')
                    log_details['source_system'] = request.form.get('source_system', '')
                    log_details['document_type'] = request.form.get('document_type', '')
                    log_details['document_date'] = request.form.get('document_date', '')
                    log_details['provider'] = request.form.get('provider', '')
                    
                    # Capture file upload details if files are present
                    if request.files:
                        for file_key, file_obj in request.files.items():
                            if file_obj and file_obj.filename:
                                log_details['file_name'] = file_obj.filename
                                log_details['file_type'] = file_obj.content_type or 'unknown'
                                # Try to get file size
                                try:
                                    file_obj.seek(0, 2)  # Seek to end
                                    file_size = file_obj.tell()
                                    file_obj.seek(0)  # Reset to beginning
                                    log_details['file_size'] = f"{file_size} bytes"
                                except:
                                    log_details['file_size'] = 'unknown'
                                break
                    else:
                        # If no file uploaded, note it was a text-only document
                        log_details['file_name'] = log_details.get('document_name', 'Text Document')
                        log_details['file_type'] = 'text/plain'

                # Create admin log entry - use more specific event type for alerts
                event_type_name = 'data_modification'
                if data_type == 'alert':
                    event_type_name = f'alert_{log_details.get("action", "modification")}'
                
                AdminLog.log_event(
                    event_type=event_type_name,
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