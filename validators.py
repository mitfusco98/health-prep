from pydantic import BaseModel, ValidationError, validator, EmailStr
from typing import Optional, List, Union
from datetime import date, datetime
import re
from flask import request, jsonify, abort
import functools
import logging

logger = logging.getLogger(__name__)

# Patient validation schemas
class PatientCreateSchema(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    mrn: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    insurance: Optional[str] = None

    @validator('first_name', 'last_name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 100:
            raise ValueError('Name must be 100 characters or less')
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', v):
            raise ValueError('Name can only contain letters, spaces, hyphens, and apostrophes')
        return v.strip()

    @validator('date_of_birth')
    def validate_dob(cls, v):
        if v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        if v < date(1900, 1, 1):
            raise ValueError('Date of birth cannot be before 1900')
        return v

    @validator('sex')
    def validate_sex(cls, v):
        if v not in ['Male', 'Female', 'Other']:
            raise ValueError('Sex must be Male, Female, or Other')
        return v

    @validator('mrn')
    def validate_mrn(cls, v):
        if v is not None:
            if not re.match(r'^[A-Za-z0-9\-]+$', v):
                raise ValueError('MRN can only contain letters, numbers, and hyphens')
            if len(v) < 3 or len(v) > 20:
                raise ValueError('MRN must be between 3 and 20 characters')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) < 10 or len(digits_only) > 15:
                raise ValueError('Phone number must contain 10-15 digits')
        return v

    @validator('address')
    def validate_address(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('Address must be 500 characters or less')
        return v

    @validator('insurance')
    def validate_insurance(cls, v):
        if v is not None and len(v) > 200:
            raise ValueError('Insurance must be 200 characters or less')
        return v

class PatientUpdateSchema(PatientCreateSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None

# Appointment validation schemas
class AppointmentCreateSchema(BaseModel):
    patient_id: int
    appointment_date: date
    appointment_time: str
    note: Optional[str] = None

    @validator('patient_id')
    def validate_patient_id(cls, v):
        if v <= 0:
            raise ValueError('Patient ID must be a positive integer')
        return v

    @validator('appointment_date')
    def validate_appointment_date(cls, v):
        if v < date.today():
            raise ValueError('Appointment date cannot be in the past')
        return v

    @validator('appointment_time')
    def validate_appointment_time(cls, v):
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Time must be in HH:MM format')

        # Validate business hours (8:00 AM to 4:00 PM)
        hour, minute = map(int, v.split(':'))
        if hour < 8 or hour >= 16:
            raise ValueError('Appointment time must be between 8:00 AM and 4:00 PM')
        if minute not in [0, 15, 30, 45]:
            raise ValueError('Appointment time must be in 15-minute increments')
        return v

    @validator('note')
    def validate_note(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('Note must be 500 characters or less')
        return v

class AppointmentUpdateSchema(AppointmentCreateSchema):
    patient_id: Optional[int] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[str] = None

# Condition validation schemas
class ConditionCreateSchema(BaseModel):
    name: str
    diagnosed_date: date
    is_active: bool = True
    notes: Optional[str] = None

    @validator('diagnosed_date')
    def validate_diagnosed_date(cls, v):
        import re
        import html
        from datetime import datetime, date as date_type

        # If it's already a date object, validate it
        if isinstance(v, date_type):
            if v > date_type.today():
                raise ValueError('Diagnosis date cannot be in the future')
            return v

        # If it's a string, handle both formats
        if isinstance(v, str):
            # Sanitize input first
            date_str = html.escape(v.strip())

            # Validate format to prevent injection
            if not re.match(r'^[\d\-]+$', date_str):
                raise ValueError('Date contains invalid characters')

            # Check if it's a 4-digit year only
            if re.match(r'^\d{4}$', date_str):
                year = int(date_str)
                if year < 1900 or year > datetime.now().year:
                    raise ValueError('Year must be between 1900 and current year')
                # Convert year to January 1st of that year
                return date_type(year, 1, 1)

            # Check if it's a full date
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                try:
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if parsed_date > date_type.today():
                        raise ValueError('Date cannot be in the future')
                    return parsed_date
                except ValueError:
                    raise ValueError('Invalid date format')

            raise ValueError('Enter either a full date (YYYY-MM-DD) or just a year (YYYY)')

        raise ValueError('Invalid date format')

    @validator('name')
    def validate_name(cls, v):
        import re
        import html

        if not v:
            raise ValueError('Condition name is required')

        # Sanitize input
        clean_name = html.escape(str(v).strip())

        # Remove dangerous patterns
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<[^>]*>'
        ]

        for pattern in dangerous_patterns:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE | re.DOTALL)

        # Validate medical condition name format
        if not re.match(r'^[a-zA-Z0-9\s\-\(\)\/\.,]+$', clean_name):
            raise ValueError('Condition name contains invalid characters')

        if len(clean_name) > 200:
            raise ValueError('Condition name must be 200 characters or less')

        return clean_name

    @validator('notes')
    def validate_notes(cls, v):
        if v is not None and len(v) > 2000:
            raise ValueError('Notes must be 2000 characters or less')
        return v

# Vitals validation schemas
class VitalsCreateSchema(BaseModel):
    date: date
    weight: Optional[float] = None
    height: Optional[float] = None
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    pulse: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None

    @validator('date')
    def validate_date(cls, v):
        if v > date.today():
            raise ValueError('Vitals date cannot be in the future')
        return v

    @validator('weight')
    def validate_weight(cls, v):
        if v is not None and (v <= 0 or v > 1000):
            raise ValueError('Weight must be between 0 and 1000 lbs')
        return v

    @validator('height')
    def validate_height(cls, v):
        if v is not None and (v <= 0 or v > 120):
            raise ValueError('Height must be between 0 and 120 inches')
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < 90 or v > 110):
            raise ValueError('Temperature must be between 90 and 110°F')
        return v

    @validator('blood_pressure_systolic')
    def validate_systolic(cls, v):
        if v is not None and (v < 50 or v > 300):
            raise ValueError('Systolic blood pressure must be between 50 and 300')
        return v

    @validator('blood_pressure_diastolic')
    def validate_diastolic(cls, v):
        if v is not None and (v < 30 or v > 200):
            raise ValueError('Diastolic blood pressure must be between 30 and 200')
        return v

    @validator('pulse')
    def validate_pulse(cls, v):
        if v is not None and (v < 30 or v > 250):
            raise ValueError('Pulse must be between 30 and 250 bpm')
        return v

    @validator('respiratory_rate')
    def validate_respiratory_rate(cls, v):
        if v is not None and (v < 5 or v > 50):
            raise ValueError('Respiratory rate must be between 5 and 50')
        return v

    @validator('oxygen_saturation')
    def validate_oxygen_saturation(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Oxygen saturation must be between 0 and 100%')
        return v

# Document validation schemas
class DocumentUploadSchema(BaseModel):
    document_name: str
    source_system: str
    document_date: date
    document_type: str
    notes: Optional[str] = None

    @validator('document_name')
    def validate_document_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Document name cannot be empty')
        if len(v) > 200:
            raise ValueError('Document name must be 200 characters or less')
        return v.strip()

    @validator('source_system')
    def validate_source_system(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Source system cannot be empty')
        if len(v) > 100:
            raise ValueError('Source system must be 100 characters or less')
        return v.strip()

    @validator('document_date')
    def validate_document_date(cls, v):
        if v > date.today():
            raise ValueError('Document date cannot be in the future')
        return v

    @validator('document_type')
    def validate_document_type(cls, v):
        valid_types = ['LAB_REPORT', 'RADIOLOGY_REPORT', 'CONSULTATION', 
                      'DISCHARGE_SUMMARY', 'CLINICAL_NOTE', 'OTHER']
        if v not in valid_types:
            raise ValueError(f'Document type must be one of: {", ".join(valid_types)}')
        return v

    @validator('notes')
    def validate_notes(cls, v):
        if v is not None and len(v) > 1000:
            raise ValueError('Notes must be 1000 characters or less')
        return v

# Validation decorator
def validate_schema(schema_class, source='form'):
    """
    Decorator to validate request data against a Pydantic schema

    Args:
        schema_class: The Pydantic model class to validate against
        source: Where to get data from ('form', 'json', 'args')
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Get data based on source
                if source == 'form':
                    data = request.form.to_dict()
                elif source == 'json':
                    data = request.get_json() or {}
                elif source == 'args':
                    data = request.args.to_dict()
                else:
                    data = {}

                # Handle empty strings and convert types
                cleaned_data = {}
                for key, value in data.items():
                    if value == '' or value is None:
                        cleaned_data[key] = None
                    else:
                        cleaned_data[key] = value

                # Validate against schema
                validated_data = schema_class(**cleaned_data)

                # Add validated data to request context
                request.validated_data = validated_data.dict()

                logger.info(f"Schema validation successful for {f.__name__}")
                return f(*args, **kwargs)

            except ValidationError as e:
                error_messages = []
                for error in e.errors():
                    field = error['loc'][0] if error['loc'] else 'unknown'
                    message = error['msg']
                    error_messages.append(f"{field}: {message}")

                logger.warning(f"Schema validation failed for {f.__name__}: {error_messages}")

                # Return appropriate error response
                if request.headers.get('Content-Type') == 'application/json' or \
                   request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'error': 'Validation failed',
                        'details': error_messages
                    }), 400
                else:
                    # For form submissions, flash error and redirect back
                    from flask import flash, redirect, url_for
                    for error_msg in error_messages:
                        flash(f"Validation error: {error_msg}", 'error')
                    return redirect(request.referrer or url_for('patient_list'))

            except Exception as e:
                logger.error(f"Unexpected error in schema validation: {str(e)}")
                abort(500, description="Internal server error during validation")

        return wrapper
    return decorator

# Additional validation utilities
def validate_file_upload(file, allowed_types=None, max_size_mb=10):
    """
    Validate uploaded files

    Args:
        file: The uploaded file object
        allowed_types: List of allowed MIME types
        max_size_mb: Maximum file size in MB
    """
    if not file or not file.filename:
        raise ValueError("No file provided")

    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValueError(f"File size must be less than {max_size_mb}MB")

    # Check file type if specified
    if allowed_types:
        import magic
        file_content = file.read(1024)
        file.seek(0)

        detected_mime = magic.from_buffer(file_content, mime=True)
        if detected_mime not in allowed_types:
            raise ValueError(f"File type not allowed. Allowed types: {', '.join(allowed_types)}")

    # Check for malicious filename patterns
    filename = file.filename.lower()
    dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    if any(pattern in filename for pattern in dangerous_patterns):
        raise ValueError("Filename contains invalid characters")

    # Check for executable extensions
    dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', 
                           '.js', '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg', 
                           '.sh', '.ps1']
    if any(filename.endswith(ext) for ext in dangerous_extensions):
        raise ValueError("Executable files are not allowed")

    return True

def sanitize_sql_input(value):
    """
    Additional SQL injection protection
    """
    if not value:
        return value

    # Remove dangerous SQL patterns
    dangerous_patterns = [
        r'(union\s+select)', r'(drop\s+table)', r'(delete\s+from)',
        r'(insert\s+into)', r'(update\s+\w+\s+set)', r'(exec\s*\()',
        r'(script\s*>)', r'(javascript:)', r'(vbscript:)',
        r'(onload\s*=)', r'(onerror\s*=)', r'(\bor\b\s+1\s*=\s*1)',
        r'(\band\b\s+1\s*=\s*1)', r'(;\s*drop)', r'(;\s*delete)',
        r'(;\s*insert)', r'(;\s*update)'
    ]

    cleaned_value = str(value)
    for pattern in dangerous_patterns:
        cleaned_value = re.sub(pattern, '', cleaned_value, flags=re.IGNORECASE)

    return cleaned_value