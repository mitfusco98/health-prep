"""
Validation utilities and decorators for POST endpoint validation
"""
from functools import wraps
from flask import request, jsonify, flash, redirect, url_for
from pydantic import ValidationError
import logging
import uuid
from datetime import datetime
import json

logger = logging.getLogger(__name__)

def log_validation_error(schema_name, validation_errors, form_data, user_id=None):
    """Log validation errors to admin logs"""
    try:
        from models import AdminLog
        from app import db
        
        request_id = str(uuid.uuid4())
        
        # Format validation errors for logging
        error_details = {}
        for error in validation_errors:
            field = '.'.join(str(loc) for loc in error['loc'])
            error_details[field] = error['msg']
        
        # Sanitize form data for logging (remove sensitive fields)
        sanitized_data = {}
        sensitive_fields = ['password', 'password_hash', 'csrf_token']
        
        for key, value in form_data.items():
            if key.lower() not in sensitive_fields:
                sanitized_data[key] = str(value)[:100]  # Truncate long values
        
        AdminLog.log_event(
            event_type='validation_error',
            user_id=user_id,
            event_details={
                'schema': schema_name,
                'validation_errors': error_details,
                'form_data_fields': list(sanitized_data.keys()),
                'sanitized_form_data': sanitized_data,
                'error_count': len(validation_errors)
            },
            request_id=request_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.commit()
        
        logger.warning(f"Validation error logged: {schema_name} - {len(validation_errors)} errors")
        
    except Exception as e:
        logger.error(f"Error logging validation error: {str(e)}")


def validate_input(schema_class, redirect_route=None, flash_errors=True):
    """
    Decorator for validating POST request input using Pydantic schemas
    
    Args:
        schema_class: Pydantic model class for validation
        redirect_route: Route to redirect to on validation failure (optional)
        flash_errors: Whether to flash validation errors to user (default: True)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method == 'POST':
                try:
                    # Get form data
                    form_data = request.form.to_dict()
                    
                    # Handle file uploads separately
                    if request.files:
                        for key, file in request.files.items():
                            if file and file.filename:
                                form_data[f'{key}_filename'] = file.filename
                    
                    # Convert date strings to date objects if needed
                    form_data = preprocess_form_data(form_data)
                    
                    # Validate using Pydantic schema
                    validated_data = schema_class(**form_data)
                    
                    # Add validated data to request context
                    request.validated_data = validated_data
                    
                    # Continue with original function
                    return func(*args, **kwargs)
                    
                except ValidationError as e:
                    # Log validation error
                    from flask import session
                    user_id = session.get('user_id')
                    log_validation_error(
                        schema_class.__name__, 
                        e.errors(), 
                        form_data, 
                        user_id
                    )
                    
                    if flash_errors:
                        # Flash user-friendly error messages
                        for error in e.errors():
                            field = error['loc'][-1] if error['loc'] else 'unknown'
                            message = error['msg']
                            flash(f"{field.replace('_', ' ').title()}: {message}", 'error')
                    
                    # Redirect or return JSON error response
                    if redirect_route:
                        return redirect(url_for(redirect_route))
                    elif request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
                        return jsonify({
                            'error': 'Validation failed',
                            'details': e.errors()
                        }), 400
                    else:
                        # Redirect to referrer or home page
                        return redirect(request.referrer or url_for('index'))
                
                except Exception as e:
                    logger.error(f"Unexpected validation error: {str(e)}")
                    if flash_errors:
                        flash('An unexpected error occurred during validation', 'error')
                    return redirect(request.referrer or url_for('index'))
            
            # For non-POST requests, continue normally
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def preprocess_form_data(form_data):
    """
    Preprocess form data to convert strings to appropriate types
    """
    processed_data = {}
    
    for key, value in form_data.items():
        if value == '' or value is None:
            processed_data[key] = None
            continue
            
        # Convert date fields
        if 'date' in key.lower() and isinstance(value, str):
            try:
                from datetime import datetime
                if len(value) == 10:  # YYYY-MM-DD format
                    processed_data[key] = datetime.strptime(value, '%Y-%m-%d').date()
                else:
                    processed_data[key] = value
            except ValueError:
                processed_data[key] = value
        
        # Convert time fields
        elif 'time' in key.lower() and isinstance(value, str):
            try:
                from datetime import datetime
                if ':' in value:
                    processed_data[key] = datetime.strptime(value, '%H:%M').time()
                else:
                    processed_data[key] = value
            except ValueError:
                processed_data[key] = value
        
        # Convert numeric fields
        elif key.endswith('_id') or key in ['patient_id', 'screening_type_id']:
            try:
                processed_data[key] = int(value) if value else None
            except ValueError:
                processed_data[key] = value
        
        # Convert boolean fields
        elif key in ['is_active', 'is_admin']:
            processed_data[key] = value.lower() in ['true', '1', 'on', 'yes']
        
        # Convert numeric vitals
        elif key in ['blood_pressure_systolic', 'blood_pressure_diastolic', 'heart_rate']:
            try:
                processed_data[key] = int(value) if value else None
            except ValueError:
                processed_data[key] = value
        
        elif key in ['temperature', 'weight', 'height']:
            try:
                processed_data[key] = float(value) if value else None
            except ValueError:
                processed_data[key] = value
        
        else:
            processed_data[key] = value
    
    return processed_data


def validate_file_upload(allowed_extensions=None, max_size_mb=10):
    """
    Decorator for validating file uploads
    
    Args:
        allowed_extensions: List of allowed file extensions
        max_size_mb: Maximum file size in MB
    """
    if allowed_extensions is None:
        allowed_extensions = ['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png']
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method == 'POST' and request.files:
                for key, file in request.files.items():
                    if file and file.filename:
                        # Check file extension
                        ext = file.filename.rsplit('.', 1)[-1].lower()
                        if ext not in allowed_extensions:
                            flash(f'File type .{ext} not allowed. Allowed types: {", ".join(allowed_extensions)}', 'error')
                            return redirect(request.referrer or url_for('index'))
                        
                        # Check file size (approximate)
                        file.seek(0, 2)  # Seek to end
                        file_size = file.tell()
                        file.seek(0)  # Reset to beginning
                        
                        if file_size > max_size_mb * 1024 * 1024:
                            flash(f'File too large. Maximum size: {max_size_mb}MB', 'error')
                            return redirect(request.referrer or url_for('index'))
            
            return func(*args, **kwargs)
        return wrapper
    return decorator