"""
Shared utilities module to consolidate duplicate functions across the codebase.
This module abstracts common patterns found in validation, formatting, and logging functions.
"""

import re
import uuid
import logging
import html
from datetime import datetime, date, timedelta
from functools import wraps
from flask import request, session

logger = logging.getLogger(__name__)

# =============================================================================
# VALIDATION UTILITIES (Consolidating utils.py and input_validator.py)
# =============================================================================

def validate_email(email, field_name='email', required=False):
    """
    Unified email validation function.
    Consolidates duplicate email validation from utils.py and input_validator.py
    """
    errors = []

    if not email and not required:
        return errors

    if not email and required:
        errors.append(f'{field_name} is required')
        return errors

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email) or len(email) > 254:
        errors.append(f'{field_name} format is invalid')

    return errors


def validate_phone(phone, field_name='phone', required=False):
    """
    Unified phone number validation function.
    Consolidates duplicate phone validation from utils.py and input_validator.py
    """
    errors = []

    if not phone and not required:
        return errors

    if not phone and required:
        errors.append(f'{field_name} is required')
        return errors

    # Remove all non-digit characters for validation
    digits_only = re.sub(r'\D', '', phone)

    # Should have 10-15 digits (international format)
    if len(digits_only) < 10 or len(digits_only) > 15:
        errors.append(f'{field_name} must contain 10-15 digits')

    return errors


def validate_date_input(date_str, field_name='date', required=False, date_format='%Y-%m-%d'):
    """
    Unified date validation function.
    Consolidates duplicate date validation from utils.py and input_validator.py
    """
    errors = []

    if not date_str and not required:
        return errors, None

    if not date_str and required:
        errors.append(f'{field_name} is required')
        return errors, None

    try:
        parsed_date = datetime.strptime(date_str, date_format).date()

        # Validate reasonable date range for medical applications
        min_date = date(1900, 1, 1)
        max_date = date.today() + timedelta(days=365*2)

        if parsed_date < min_date or parsed_date > max_date:
            errors.append(f'{field_name} must be within reasonable range')

        return errors, parsed_date
    except ValueError:
        errors.append(f'{field_name} must be in {date_format} format')
        return errors, None


def validate_required_fields(data, required_fields):
    """
    Validate that all required fields are present and not empty.
    Consolidates similar functionality across multiple files.
    """
    errors = []
    for field in required_fields:
        if not data.get(field) or (isinstance(data[field], str) and not data[field].strip()):
            errors.append(f'{field} is required')
    return errors


def validate_string_field(value, field_name, min_length=0, max_length=None, pattern=None, allow_empty=False):
    """
    Unified string field validation with length and pattern constraints.
    Consolidates string validation logic from utils.py
    """
    errors = []

    if not value and not allow_empty:
        errors.append(f'{field_name} is required')
        return errors

    if not value and allow_empty:
        return errors

    if not isinstance(value, str):
        errors.append(f'{field_name} must be a string')
        return errors

    if len(value.strip()) < min_length:
        errors.append(f'{field_name} must be at least {min_length} characters long')

    if max_length and len(value) > max_length:
        errors.append(f'{field_name} must be maximum {max_length} characters')

    if pattern and not re.match(pattern, value):
        errors.append(f'{field_name} format is invalid')

    return errors


# =============================================================================
# LOGGING UTILITIES (Consolidating validation_utils.py and input_validator.py)
# =============================================================================

def sanitize_form_data_for_logging(form_data, sensitive_fields=None):
    """
    Sanitize form data for logging by removing sensitive fields and truncating values.
    Consolidates duplicate sanitization logic from validation_utils.py and input_validator.py
    """
    if sensitive_fields is None:
        sensitive_fields = ['password', 'password_hash', 'csrf_token', 'secret', 'token']
    
    sanitized_data = {}
    for key, value in form_data.items():
        if key.lower() not in [field.lower() for field in sensitive_fields]:
            sanitized_data[key] = str(value)[:100] if value else None
    
    return sanitized_data


def log_validation_error_unified(context, validation_errors, form_data, user_id=None):
    """
    Unified validation error logging function.
    Consolidates duplicate logging logic from validation_utils.py and input_validator.py
    """
    try:
        from models import AdminLog
        from app import db
        
        request_id = str(uuid.uuid4())
        
        # Handle different error formats
        if isinstance(validation_errors, list) and validation_errors:
            # Check if it's Pydantic errors (dicts with 'loc' and 'msg')
            if isinstance(validation_errors[0], dict) and 'loc' in validation_errors[0]:
                # Pydantic format
                error_details = {}
                for error in validation_errors:
                    field = '.'.join(str(loc) for loc in error['loc'])
                    error_details[field] = error['msg']
            else:
                # Simple string list format
                error_details = {f'error_{i}': error for i, error in enumerate(validation_errors)}
        else:
            error_details = {'general': str(validation_errors)}
        
        # Sanitize form data
        sanitized_data = sanitize_form_data_for_logging(form_data)
        
        AdminLog.log_event(
            event_type='validation_error',
            user_id=user_id,
            event_details={
                'context': context,
                'validation_errors': error_details,
                'form_data_fields': list(sanitized_data.keys()),
                'sanitized_form_data': sanitized_data,
                'error_count': len(validation_errors) if isinstance(validation_errors, list) else 1
            },
            request_id=request_id,
            ip_address=getattr(request, 'remote_addr', None),
            user_agent=request.headers.get('User-Agent', '') if request else ''
        )
        db.session.commit()
        
        logger.warning(f"Validation error logged: {context} - {len(validation_errors) if isinstance(validation_errors, list) else 1} errors")
        
    except Exception as e:
        logger.error(f"Error logging validation error: {str(e)}")


# =============================================================================
# INPUT SANITIZATION (Consolidating app.py sanitize_input)
# =============================================================================

def sanitize_user_input(value, max_length=None, allow_html=False, field_type='general'):
    """
    Comprehensive input sanitization to prevent XSS and injection attacks.
    Consolidates the sanitize_input function from app.py
    """
    if not value:
        return value

    # Convert to string if not already
    value = str(value).strip()
    original_value = value

    # Enforce maximum length
    if max_length and len(value) > max_length:
        value = value[:max_length]
        logger.warning(f"Input truncated from {len(original_value)} to {max_length} characters")

    # Remove or escape HTML unless explicitly allowed
    if not allow_html:
        value = html.escape(value)

    # Remove potentially dangerous characters
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

    # Enhanced dangerous patterns
    dangerous_patterns = [
        r'(union\s+select)', r'(drop\s+table)', r'(delete\s+from)',
        r'(insert\s+into)', r'(update\s+\w+\s+set)', r'(exec\s*\()',
        r'(script\s*>)', r'(javascript:)', r'(vbscript:)',
        r'(onload\s*=)', r'(onerror\s*=)', r'(\bor\b\s+1\s*=\s*1)',
        r'(\band\b\s+1\s*=\s*1)', r'(;\s*drop)', r'(;\s*delete)',
        r'(;\s*insert)', r'(;\s*update)', r'(--\s*)', r'(/\*.*?\*/)',
        r'(xp_cmdshell)', r'(sp_executesql)', r'(eval\s*\()',
        r'(<iframe)', r'(<object)', r'(<embed)', r'(<form)',
        r'(data:text/html)', r'(data:application)', r'(\bvoid\s*\()'
    ]

    for pattern in dangerous_patterns:
        old_value = value
        value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
        if old_value != value:
            logger.warning(f"Dangerous pattern removed: {pattern}")

    # Field-specific validation
    if field_type == 'email':
        if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            logger.warning(f"Invalid email format: {value}")
            return None
    elif field_type == 'phone':
        digits_only = re.sub(r'\D', '', value)
        if value and (len(digits_only) < 10 or len(digits_only) > 15):
            logger.warning(f"Invalid phone format: {value}")
            return None
    elif field_type == 'name':
        if value and not re.match(r'^[a-zA-Z\s\-\'\.]+$', value):
            logger.warning(f"Invalid name format: {value}")
            return None
    elif field_type == 'mrn':
        if value and not re.match(r'^[A-Za-z0-9\-]+$', value):
            logger.warning(f"Invalid MRN format: {value}")
            return None

    # Log if significant changes were made
    if original_value != value and len(original_value) > 0:
        logger.info(f"Input sanitized: '{original_value[:50]}...' -> '{value[:50]}...'")

    return value


# =============================================================================
# FORMATTING UTILITIES (Consolidating demo_routes.py template filters)
# =============================================================================

def format_datetime_display(value, format='%B %d, %Y'):
    """
    Format a datetime object to a readable string.
    Consolidates the datetime filter from demo_routes.py
    """
    if value is None:
        return ""
    return value.strftime(format)


def format_date_of_birth(value):
    """
    Format a date object to MM/DD/YYYY format for date of birth.
    Consolidates the dob filter from demo_routes.py
    """
    if value is None:
        return ""
    return value.strftime('%m/%d/%Y')


def format_timestamp_to_est(utc_timestamp):
    """
    Convert UTC timestamp to EST and format for display.
    Consolidates the timestamp_to_est filter from demo_routes.py
    """
    from datetime import timezone, timedelta
    if utc_timestamp:
        # EST is UTC-5, EDT is UTC-4. For simplicity, using EST offset
        est_offset = timedelta(hours=-5)
        est_timezone = timezone(est_offset)
        est_time = utc_timestamp.replace(tzinfo=timezone.utc).astimezone(est_timezone)
        return est_time.strftime('%m/%d %H:%M EST')
    return ''


# =============================================================================
# ERROR HANDLING UTILITIES (Consolidating app.py error handlers)
# =============================================================================

def get_remote_address():
    """
    Get the remote address from request, handling proxy scenarios.
    Consolidates duplicate remote address logic from app.py
    """
    if not request:
        return 'unknown'
    
    # Check for forwarded headers first (for proxy scenarios)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(',')[0].strip()
    
    return request.remote_addr or 'unknown'


def create_api_error_response(error_message, status_code):
    """
    Create standardized API error response.
    Consolidates error response logic from app.py error handlers
    """
    from flask import jsonify
    return jsonify({'error': error_message}), status_code


def should_return_json_response():
    """
    Determine if the request should receive a JSON response.
    Consolidates the API path checking logic from app.py error handlers
    """
    return request and request.path.startswith('/api/')


# =============================================================================
# DECORATOR UTILITIES
# =============================================================================

def validation_decorator(validation_func):
    """
    Generic validation decorator that can be used with any validation function.
    Consolidates validation decorator patterns across the codebase.
    """
    def decorator(route_func):
        @wraps(route_func)
        def wrapper(*args, **kwargs):
            if request.method == 'POST':
                form_data = request.form.to_dict()
                errors = validation_func(form_data)
                
                if errors:
                    user_id = session.get('user_id')
                    log_validation_error_unified(
                        f"{route_func.__name__}_validation",
                        errors,
                        form_data,
                        user_id
                    )
                    
                    if should_return_json_response():
                        return create_api_error_response('Validation failed', 400)
                    else:
                        from flask import flash, redirect, url_for
                        for error in errors:
                            flash(error, 'error')
                        return redirect(request.referrer or url_for('home'))
            
            return route_func(*args, **kwargs)
        return wrapper
    return decorator