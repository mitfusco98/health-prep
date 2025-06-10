"""
Simple input validation system for POST endpoints with comprehensive error logging
"""
import re
import uuid
import logging
from datetime import datetime, date
from functools import wraps
from flask import request, flash, redirect, url_for, session

logger = logging.getLogger(__name__)


# Import validation functions from shared utilities
from shared_utilities import validate_email, validate_phone, validate_date_input as validate_date_format, log_validation_error_unified as log_validation_error


def validate_patient_data(form_data):
    """Validate patient form data"""
    errors = []

    # Required fields
    if not form_data.get('first_name', '').strip():
        errors.append("First name is required")
    elif len(form_data.get('first_name', '')) > 50:
        errors.append("First name must be less than 50 characters")

    if not form_data.get('last_name', '').strip():
        errors.append("Last name is required")
    elif len(form_data.get('last_name', '')) > 50:
        errors.append("Last name must be less than 50 characters")

    # Date of birth validation
    if form_data.get('date_of_birth'):
        is_valid, date_errors = validate_date_format(form_data['date_of_birth'], "Date of birth")
        if not is_valid:
            errors.extend(date_errors)
    else:
        errors.append("Date of birth is required")

    # Gender validation
    if form_data.get('gender') not in ['Male', 'Female', 'Other']:
        errors.append("Gender must be Male, Female, or Other")

    # Phone number validation
    phone = form_data.get('phone_number', '').strip()
    is_valid, phone_errors = validate_phone(phone)
    if not is_valid:
        errors.extend(phone_errors)

    # Email validation
    email = form_data.get('email', '').strip()
    is_valid, email_errors = validate_email(email)
    if not is_valid:
        errors.extend(email_errors)

    return errors


def validate_appointment_data(form_data):
    """Validate appointment form data"""
    errors = []

    # Patient ID validation
    try:
        patient_id = int(form_data.get('patient_id', 0))
        if patient_id <= 0:
            errors.append("Valid patient must be selected")
    except (ValueError, TypeError):
        errors.append("Valid patient must be selected")

    # Date validation
    if form_data.get('appointment_date'):
        is_valid, date_errors = validate_date_format(form_data['appointment_date'], "Appointment date")
        if not is_valid:
            errors.extend(date_errors)
    else:
        errors.append("Appointment date is required")

    # Time validation
    if form_data.get('appointment_time'):
        try:
            app_time = datetime.strptime(form_data['appointment_time'], '%H:%M').time()
            if app_time.hour < 8 or app_time.hour >= 16:
                errors.append("Appointment time must be between 8:00 AM and 4:00 PM")
            if app_time.minute not in [0, 15, 30, 45]:
                errors.append("Appointment time must be in 15-minute intervals")
        except ValueError:
            errors.append("Invalid appointment time format")
    else:
        errors.append("Appointment time is required")

    return errors


def validate_login_data(form_data):
    """Validate login form data"""
    errors = []

    username = form_data.get('username', '').strip()
    password = form_data.get('password', '')

    if not username:
        errors.append("Username is required")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters")
    elif not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append("Username can only contain letters, numbers, and underscores")

    if not password:
        errors.append("Password is required")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters")

    return errors


def validate_bulk_delete_data(form_data):
    """Validate bulk delete operations"""
    errors = []

    # Check for appointment IDs
    appointment_ids = form_data.get('appointment_ids', '').strip()
    selected_appointments = form_data.getlist('selected_appointments[]') if hasattr(form_data, 'getlist') else []

    if appointment_ids:
        try:
            ids = [int(id.strip()) for id in appointment_ids.split(',') if id.strip()]
            if not ids:
                errors.append("At least one valid appointment ID is required")
        except ValueError:
            errors.append("All appointment IDs must be valid numbers")
    elif not selected_appointments:
        errors.append("No appointments selected for deletion")

    return errors


def validate_post_input(validator_func):
    """
    Decorator for validating POST request input

    Args:
        validator_func: Function to validate form data, returns list of errors
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method == 'POST':
                form_data = request.form.to_dict()

                # Run validation
                validation_errors = validator_func(form_data)

                if validation_errors:
                    # Log validation error
                    user_id = session.get('user_id')
                    log_validation_error(
                        request.endpoint, 
                        validation_errors, 
                        form_data, 
                        user_id
                    )

                    # Flash error messages to user
                    for error in validation_errors:
                        flash(error, 'error')

                    # Redirect back to referrer or appropriate page
                    return redirect(request.referrer or url_for('index'))

            # Continue with original function if validation passes
            return func(*args, **kwargs)

        return wrapper
    return decorator


# Convenience decorators for specific validation types
def validate_patient_input(func):
    """Decorator for patient form validation"""
    return validate_post_input(validate_patient_data)(func)


def validate_appointment_input(func):
    """Decorator for appointment form validation"""
    return validate_post_input(validate_appointment_data)(func)


def validate_login_input(func):
    """Decorator for login form validation"""
    return validate_post_input(validate_login_data)(func)


def validate_bulk_delete_input(func):
    """Decorator for bulk delete validation"""
    return validate_post_input(validate_bulk_delete_data)(func)