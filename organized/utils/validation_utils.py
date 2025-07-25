"""
Validation utilities consolidated from validators.py, validation_utils.py, and input_validator.py
Provides centralized validation functions for forms and data input
"""

import re
from datetime import datetime, date
from typing import Optional, Dict, List, Any


def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return False
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)
    # Check if it's 10 or 11 digits (with or without country code)
    return len(digits) in [10, 11]


def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
    """Validate date string format"""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False


def validate_time(time_str: str, time_format: str = "%H:%M") -> bool:
    """Validate time string format"""
    if not time_str:
        return False
    try:
        datetime.strptime(time_str, time_format)
        return True
    except ValueError:
        return False


def validate_required_fields(
    data: Dict[str, Any], required_fields: List[str]
) -> List[str]:
    """Validate that all required fields are present and not empty"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field] or str(data[field]).strip() == "":
            missing_fields.append(field)
    return missing_fields


def validate_patient_data(form_data: Dict[str, str]) -> Dict[str, List[str]]:
    """Validate patient form data"""
    errors = {}

    # Required fields
    required = ["first_name", "last_name", "date_of_birth", "gender"]
    missing = validate_required_fields(form_data, required)
    if missing:
        errors["required"] = [f"Field '{field}' is required" for field in missing]

    # Email validation
    email = form_data.get("email", "").strip()
    if email and not validate_email(email):
        errors["email"] = ["Invalid email format"]

    # Phone validation
    phone = form_data.get("phone", "").strip()
    if phone and not validate_phone(phone):
        errors["phone"] = ["Invalid phone number format"]

    # Date of birth validation
    dob = form_data.get("date_of_birth", "").strip()
    if dob and not validate_date(dob):
        errors["date_of_birth"] = ["Invalid date format (YYYY-MM-DD expected)"]
    elif dob:
        try:
            birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
            if birth_date > date.today():
                errors["date_of_birth"] = ["Date of birth cannot be in the future"]
        except ValueError:
            pass  # Already handled above

    return errors


def validate_appointment_data(form_data: Dict[str, str]) -> Dict[str, List[str]]:
    """Validate appointment form data"""
    errors = {}

    # Required fields
    required = ["patient_id", "appointment_date", "appointment_time"]
    missing = validate_required_fields(form_data, required)
    if missing:
        errors["required"] = [f"Field '{field}' is required" for field in missing]

    # Date validation
    apt_date = form_data.get("appointment_date", "").strip()
    if apt_date and not validate_date(apt_date):
        errors["appointment_date"] = ["Invalid date format (YYYY-MM-DD expected)"]
    elif apt_date:
        try:
            appointment_date = datetime.strptime(apt_date, "%Y-%m-%d").date()
            if appointment_date < date.today():
                errors["appointment_date"] = ["Appointment date cannot be in the past"]
        except ValueError:
            pass

    # Time validation
    apt_time = form_data.get("appointment_time", "").strip()
    if apt_time and not validate_time(apt_time):
        errors["appointment_time"] = ["Invalid time format (HH:MM expected)"]

    # Patient ID validation
    patient_id = form_data.get("patient_id", "").strip()
    if patient_id:
        try:
            int(patient_id)
        except ValueError:
            errors["patient_id"] = ["Invalid patient ID"]

    return errors


def validate_screening_data(form_data: Dict[str, str]) -> Dict[str, List[str]]:
    """Validate screening form data"""
    errors = {}

    # Required fields
    required = ["patient_id", "screening_type"]
    missing = validate_required_fields(form_data, required)
    if missing:
        errors["required"] = [f"Field '{field}' is required" for field in missing]

    # Date validations
    due_date = form_data.get("due_date", "").strip()
    if due_date and not validate_date(due_date):
        errors["due_date"] = ["Invalid due date format (YYYY-MM-DD expected)"]

    last_completed = form_data.get("last_completed", "").strip()
    if last_completed and not validate_date(last_completed):
        errors["last_completed"] = [
            "Invalid completion date format (YYYY-MM-DD expected)"
        ]

    # Patient ID validation
    patient_id = form_data.get("patient_id", "").strip()
    if patient_id:
        try:
            int(patient_id)
        except ValueError:
            errors["patient_id"] = ["Invalid patient ID"]

    return errors


def validate_vital_data(form_data: Dict[str, str]) -> List[str]:
    """Validate vital signs form data"""
    errors = []

    # Date validation
    date_str = form_data.get("date", "").strip()
    if not date_str:
        errors.append("Date is required")
    elif not validate_date(date_str):
        errors.append("Invalid date format (YYYY-MM-DD expected)")
    else:
        try:
            vital_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if vital_date > date.today():
                errors.append("Vital signs date cannot be in the future")
        except ValueError:
            errors.append("Invalid date format")

    # Numeric field validations
    numeric_fields = {
        "blood_pressure_systolic": (50, 300, "Systolic blood pressure"),
        "blood_pressure_diastolic": (30, 200, "Diastolic blood pressure"),
        "heart_rate": (30, 300, "Heart rate"),
        "temperature": (90.0, 110.0, "Temperature"),
        "weight": (0.5, 1000.0, "Weight"),
        "height": (10.0, 120.0, "Height"),
    }

    for field, (min_val, max_val, field_name) in numeric_fields.items():
        value = form_data.get(field, "").strip()
        if value:
            try:
                num_value = float(value)
                if num_value < min_val or num_value > max_val:
                    errors.append(f"{field_name} must be between {min_val} and {max_val}")
            except ValueError:
                errors.append(f"{field_name} must be a valid number")

    return errors


def validate_condition_data(form_data: Dict[str, str]) -> List[str]:
    """Validate condition form data"""
    errors = []

    # Required fields
    condition_name = form_data.get("condition_name", "").strip()
    if not condition_name:
        errors.append("Condition name is required")

    # Date validation
    diagnosis_date = form_data.get("diagnosis_date", "").strip()
    if diagnosis_date and not validate_date(diagnosis_date):
        errors.append("Invalid diagnosis date format (YYYY-MM-DD expected)")
    elif diagnosis_date:
        try:
            diag_date = datetime.strptime(diagnosis_date, "%Y-%m-%d").date()
            if diag_date > date.today():
                errors.append("Diagnosis date cannot be in the future")
        except ValueError:
            errors.append("Invalid diagnosis date format")

    # Severity validation
    severity = form_data.get("severity", "").strip()
    if severity and severity not in ["mild", "moderate", "severe"]:
        errors.append("Severity must be mild, moderate, or severe")

    # Status validation
    status = form_data.get("status", "").strip()
    if status and status not in ["active", "resolved", "chronic", "recurrent"]:
        errors.append("Status must be active, resolved, chronic, or recurrent")

    return errors


def sanitize_input(text: str) -> str:
    """Sanitize user input by removing potentially harmful characters"""
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove script tags and content
    text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", '"', "'", "&", ";"]
    for char in dangerous_chars:
        text = text.replace(char, "")

    return text.strip()


def validate_file_upload(
    filename: str, allowed_extensions: List[str] = None
) -> Dict[str, List[str]]:
    """Validate file upload"""
    errors = {}

    if not filename:
        errors["filename"] = ["No file selected"]
        return errors

    if allowed_extensions is None:
        allowed_extensions = ["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png"]

    # Check file extension
    if "." not in filename:
        errors["extension"] = ["File must have an extension"]
    else:
        extension = filename.rsplit(".", 1)[1].lower()
        if extension not in allowed_extensions:
            errors["extension"] = [
                f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
            ]

    return errors
