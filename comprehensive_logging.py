"""Enhanced medical data logging for all subsections with form submission details."""
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
                                    log_details['alert_time'] = current_time
                                elif key == 'severity':
                                    log_details['severity'] = str(value)[:20]
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
                    user_id=user_id,
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
    Enhanced decorator for logging data modifications with comprehensive details

    Args:
        data_type: Type of data being modified (e.g., 'vital', 'condition', 'lab', etc.)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, g, session
            from models import AdminLog
            from app import db
            import json

            # Get patient info from URL or form
            patient_id = kwargs.get('patient_id') or request.view_args.get('patient_id')

            # Determine action type from HTTP method and route
            method = request.method
            action = 'view'
            if method == 'POST':
                if 'edit' in request.endpoint or 'update' in request.endpoint or request.form.get('_method') == 'PUT':
                    action = 'edit'
                elif 'delete' in request.endpoint or request.form.get('_method') == 'DELETE':
                    action = 'delete'
                else:
                    action = 'add'
            elif method == 'DELETE':
                action = 'delete'
            elif method == 'PUT':
                action = 'edit'

            # Get form data
            form_data = {}
            if request.form:
                form_data = request.form.to_dict()
            elif request.json:
                form_data = request.json

            # Get patient name if patient_id exists
            patient_name = 'Unknown'
            if patient_id:
                try:
                    from models import Patient
                    patient = Patient.query.get(patient_id)
                    if patient:
                        patient_name = patient.full_name
                except:
                    pass

            current_time = datetime.now().strftime('%H:%M:%S')
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Build comprehensive log details
            log_details = {
                'action': action,
                'data_type': data_type,
                'patient_id': patient_id,
                'patient_name': patient_name,
                'endpoint': request.endpoint,
                'method': method,
                'timestamp': datetime.now().isoformat(),
                'date': current_date,
                'time': current_time
            }

            # Process form data based on data type
            if form_data:
                # Remove sensitive data
                sanitized_form = {k: v for k, v in form_data.items() 
                                if k not in ['csrf_token', 'password', 'confirm_password']}

                form_changes = {}

                # Data type specific field processing
                if data_type == 'vital':
                    for key, value in sanitized_form.items():
                        if key in ['date', 'weight', 'height', 'temperature', 'blood_pressure_systolic', 
                                  'blood_pressure_diastolic', 'pulse', 'respiratory_rate', 'oxygen_saturation', 'bmi']:
                            form_changes[f'vital_{key}'] = str(value)[:50]
                            if key == 'date':
                                log_details['vital_date'] = str(value)[:20]
                                log_details['vital_time'] = current_time
                            elif key == 'weight':
                                log_details['weight'] = str(value)[:10] + ' lbs'
                            elif key == 'height':
                                log_details['height'] = str(value)[:10] + ' in'
                            elif key == 'temperature':
                                log_details['temperature'] = str(value)[:10] + ' °F'
                            elif key in ['blood_pressure_systolic', 'blood_pressure_diastolic']:
                                log_details[key] = str(value)[:10]
                            elif key == 'pulse':
                                log_details['pulse'] = str(value)[:10] + ' bpm'

                elif data_type == 'condition':
                    for key, value in sanitized_form.items():
                        if key in ['name', 'diagnosed_date', 'is_active', 'notes', 'code']:
                            form_changes[f'condition_{key}'] = str(value)[:100]
                            if key == 'name':
                                log_details['condition_name'] = str(value)[:100]
                            elif key == 'diagnosed_date':
                                log_details['diagnosis_date'] = str(value)[:20]
                                log_details['diagnosis_time'] = current_time
                            elif key == 'code':
                                log_details['condition_code'] = str(value)[:20]
                            elif key == 'is_active':
                                log_details['condition_status'] = 'Active' if str(value).lower() in ['true', '1', 'on'] else 'Inactive'

                elif data_type == 'lab':
                    for key, value in sanitized_form.items():
                        if key in ['test_name', 'test_date', 'result_value', 'unit', 'reference_range', 'is_abnormal', 'notes']:
                            form_changes[f'lab_{key}'] = str(value)[:100]
                            if key == 'test_name':
                                log_details['test_name'] = str(value)[:100]
                            elif key == 'test_date':
                                log_details['test_date'] = str(value)[:20]
                                log_details['test_time'] = current_time
                            elif key == 'result_value':
                                log_details['result'] = str(value)[:50]
                            elif key == 'reference_range':
                                log_details['reference_range'] = str(value)[:50]
                            elif key == 'unit':
                                log_details['unit'] = str(value)[:20]
                            elif key == 'is_abnormal':
                                log_details['abnormal_flag'] = 'Yes' if str(value).lower() in ['true', '1', 'on'] else 'No'

                elif data_type == 'immunization':
                    for key, value in sanitized_form.items():
                        if key in ['vaccine_name', 'administration_date', 'dose_number', 'manufacturer', 'lot_number', 'notes']:
                            form_changes[f'immunization_{key}'] = str(value)[:100]
                            if key == 'vaccine_name':
                                log_details['vaccine_name'] = str(value)[:100]
                            elif key == 'administration_date':
                                log_details['immunization_date'] = str(value)[:20]
                                log_details['immunization_time'] = current_time
                            elif key == 'lot_number':
                                log_details['lot_number'] = str(value)[:50]
                            elif key == 'manufacturer':
                                log_details['manufacturer'] = str(value)[:100]
                            elif key == 'dose_number':
                                log_details['dose_number'] = str(value)[:10]

                elif data_type == 'imaging':
                    for key, value in sanitized_form.items():
                        if key in ['study_type', 'body_site', 'study_date', 'findings', 'impression']:
                            form_changes[f'imaging_{key}'] = str(value)[:100]
                            if key == 'study_type':
                                log_details['study_type'] = str(value)[:100]
                            elif key == 'study_date':
                                log_details['study_date'] = str(value)[:20]
                                log_details['study_time'] = current_time
                            elif key == 'body_site':
                                log_details['body_site'] = str(value)[:100]
                            elif key == 'findings':
                                log_details['findings'] = str(value)[:200]
                            elif key == 'impression':
                                log_details['impression'] = str(value)[:200]

                elif data_type == 'consult':
                    for key, value in sanitized_form.items():
                        if key in ['specialist', 'specialty', 'report_date', 'reason', 'findings', 'recommendations']:
                            form_changes[f'consult_{key}'] = str(value)[:100]
                            if key == 'specialist':
                                log_details['specialist'] = str(value)[:100]
                            elif key in ['specialty', 'speciality']:
                                log_details['specialty'] = str(value)[:50]
                            elif key in ['report_date', 'consult_date']:
                                log_details['consult_date'] = str(value)[:20]
                                log_details['consult_time'] = current_time
                            elif key in ['reason', 'referral_reason']:
                                log_details['referral_reason'] = str(value)[:200]
                            elif key == 'findings':
                                log_details['findings'] = str(value)[:200]
                            elif key == 'recommendations':
                                log_details['recommendations'] = str(value)[:200]

                elif data_type == 'hospital':
                    for key, value in sanitized_form.items():
                        if key in ['hospital_name', 'facility', 'admission_date', 'discharge_date', 'admitting_diagnosis', 'discharge_diagnosis', 'procedures']:
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
                            elif key == 'discharge_diagnosis':
                                log_details['discharge_diagnosis'] = str(value)[:200]
                            elif key == 'procedures':
                                log_details['procedures'] = str(value)[:200]

                elif data_type == 'document':
                    # Handle file uploads differently
                    file_info = {}
                    if 'file' in request.files:
                        file = request.files['file']
                        if file and file.filename:
                            file_info = {
                                'file_name': file.filename,
                                'file_type': file.content_type,
                                'file_size': len(file.read()) if hasattr(file, 'read') else 0
                            }
                            file.seek(0)  # Reset file pointer

                    for key, value in sanitized_form.items():
                        if key in ['document_name', 'filename', 'document_type', 'document_date', 'provider', 'source_system', 'notes']:
                            form_changes[f'document_{key}'] = str(value)[:100]
                            if key in ['document_name', 'filename']:
                                log_details['file_name'] = str(value)[:100]
                            elif key == 'document_type':
                                log_details['document_type'] = str(value)[:50]
                            elif key == 'document_date':
                                log_details['document_date'] = str(value)[:20]
                                log_details['document_time'] = current_time
                            elif key == 'provider':
                                log_details['provider'] = str(value)[:100]
                            elif key == 'source_system':
                                log_details['source_system'] = str(value)[:100]

                    # Add file info if available
                    if file_info:
                        log_details.update(file_info)

                elif data_type == 'visit':
                    for key, value in sanitized_form.items():
                        if key in ['visit_date', 'visit_type', 'provider', 'reason', 'notes']:
                            form_changes[f'visit_{key}'] = str(value)[:100]
                            if key == 'visit_date':
                                log_details['visit_date'] = str(value)[:20]
                                log_details['visit_time'] = current_time
                            elif key == 'visit_type':
                                log_details['visit_type'] = str(value)[:50]
                            elif key == 'provider':
                                log_details['provider'] = str(value)[:100]
                            elif key == 'reason':
                                log_details['visit_reason'] = str(value)[:200]

                elif data_type == 'alert':
                    for key, value in sanitized_form.items():
                        if key in ['alert_type', 'description', 'details', 'start_date', 'end_date', 'severity', 'priority', 'is_active']:
                            form_changes[f'alert_{key}'] = str(value)[:100]
                            if key == 'description':
                                log_details['description'] = str(value)[:200]
                            elif key == 'alert_type':
                                log_details['alert_type'] = str(value)[:50]
                            elif key in ['priority', 'severity']:
                                log_details['severity'] = str(value)[:20]
                            elif key == 'start_date':
                                log_details['alert_date'] = str(value)[:20]
                                log_details['start_date'] = str(value)[:20]
                                log_details['alert_time'] = current_time
                            elif key == 'end_date':
                                log_details['end_date'] = str(value)[:20]
                            elif key == 'details':
                                log_details['details'] = str(value)[:200]
                            elif key == 'is_active':
                                log_details['alert_status'] = 'Active' if str(value).lower() in ['true', '1', 'on'] else 'Inactive'

                # Ensure alert data always has time component when date is present
                if 'alert_date' in log_details and 'alert_time' not in log_details:
                    log_details['alert_time'] = current_time

                log_details['form_data'] = sanitized_form
                if form_changes:
                    log_details['form_changes'] = form_changes

            # Execute the original function
            try:
                result = f(*args, **kwargs)
                log_details['status'] = 'success'
            except Exception as e:
                log_details['status'] = 'error'
                log_details['error'] = str(e)[:200]
                raise
            finally:
                # Log the event
                try:
                    user_id = getattr(g, 'current_user', {}).get('id') if hasattr(g, 'current_user') else None

                    AdminLog.log_event(
                        event_type='data_modification',
                        user_id=user_id,
                        event_details=json.dumps(log_details),