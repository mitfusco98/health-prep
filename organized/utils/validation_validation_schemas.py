"""
Input validation schemas using Pydantic for all POST endpoints
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import date, time, datetime
import re


class PatientSchema(BaseModel):
    """Validation schema for patient creation/updates"""

    first_name: str = Field(
        ..., min_length=1, max_length=50, description="Patient's first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=50, description="Patient's last name"
    )
    date_of_birth: date = Field(..., description="Patient's date of birth")
    gender: str = Field(..., description="Patient's gender")
    phone_number: Optional[str] = Field(
        None, max_length=20, description="Patient's phone number"
    )
    email: Optional[EmailStr] = Field(None, description="Patient's email address")
    address: Optional[str] = Field(
        None, max_length=200, description="Patient's address"
    )
    emergency_contact: Optional[str] = Field(
        None, max_length=100, description="Emergency contact name"
    )
    emergency_phone: Optional[str] = Field(
        None, max_length=20, description="Emergency contact phone"
    )
    mrn: Optional[str] = Field(None, max_length=20, description="Medical Record Number")

    @validator("phone_number", "emergency_phone")
    def validate_phone(cls, v):
        if v and not re.match(
            r"^[\+]?[1-9][\d]{0,15}$",
            v.replace("-", "").replace(" ", "").replace("(", "").replace(")", ""),
        ):
            raise ValueError("Invalid phone number format")
        return v

    @validator("date_of_birth")
    def validate_dob(cls, v):
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if v.year < 1900:
            raise ValueError("Date of birth cannot be before 1900")
        return v


class AppointmentSchema(BaseModel):
    """Validation schema for appointment creation/updates"""

    patient_id: int = Field(..., gt=0, description="Patient ID")
    appointment_date: date = Field(..., description="Appointment date")
    appointment_time: time = Field(..., description="Appointment time")
    appointment_type: Optional[str] = Field(
        None, max_length=100, description="Type of appointment"
    )
    notes: Optional[str] = Field(None, max_length=500, description="Appointment notes")
    status: Optional[str] = Field(
        "Scheduled", regex="^(Scheduled|Completed|Cancelled|No Show)$"
    )

    @validator("appointment_date")
    def validate_appointment_date(cls, v):
        if v < date.today():
            raise ValueError("Appointment date cannot be in the past")
        return v

    @validator("appointment_time")
    def validate_appointment_time(cls, v):
        # Business hours: 8 AM to 4 PM
        if v.hour < 8 or v.hour >= 16:
            raise ValueError("Appointment time must be between 8:00 AM and 4:00 PM")
        # 15-minute intervals only
        if v.minute not in [0, 15, 30, 45]:
            raise ValueError("Appointment time must be in 15-minute intervals")
        return v


class DocumentSchema(BaseModel):
    """Validation schema for document uploads"""

    patient_id: int = Field(..., gt=0, description="Patient ID")
    document_name: str = Field(
        ..., min_length=1, max_length=200, description="Document name"
    )
    document_type: str = Field(
        ..., min_length=1, max_length=50, description="Document type"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Document description"
    )

    @validator("document_type")
    def validate_document_type(cls, v):
        allowed_types = [
            "Lab Report",
            "Imaging",
            "Consultation",
            "Prescription",
            "Insurance",
            "Other",
        ]
        if v not in allowed_types:
            raise ValueError(
                f'Document type must be one of: {", ".join(allowed_types)}'
            )
        return v


class ConditionSchema(BaseModel):
    """Validation schema for medical conditions"""

    patient_id: int = Field(..., gt=0, description="Patient ID")
    condition_name: str = Field(
        ..., min_length=1, max_length=200, description="Condition name"
    )
    diagnosis_date: Optional[date] = Field(None, description="Diagnosis date")
    status: str = Field("Active", regex="^(Active|Resolved|Chronic)$")
    notes: Optional[str] = Field(None, max_length=500, description="Condition notes")

    @validator("diagnosis_date")
    def validate_diagnosis_date(cls, v):
        if v and v > date.today():
            raise ValueError("Diagnosis date cannot be in the future")
        return v


class VitalSchema(BaseModel):
    """Validation schema for vital signs"""

    patient_id: int = Field(..., gt=0, description="Patient ID")
    measurement_date: date = Field(..., description="Measurement date")
    blood_pressure_systolic: Optional[int] = Field(
        None, ge=50, le=300, description="Systolic BP"
    )
    blood_pressure_diastolic: Optional[int] = Field(
        None, ge=30, le=200, description="Diastolic BP"
    )
    heart_rate: Optional[int] = Field(
        None, ge=30, le=300, description="Heart rate (BPM)"
    )
    temperature: Optional[float] = Field(
        None, ge=90.0, le=110.0, description="Temperature (F)"
    )
    weight: Optional[float] = Field(None, ge=0.5, le=1000.0, description="Weight (lbs)")
    height: Optional[float] = Field(
        None, ge=10.0, le=120.0, description="Height (inches)"
    )
    notes: Optional[str] = Field(None, max_length=500, description="Vital signs notes")

    @validator("measurement_date")
    def validate_measurement_date(cls, v):
        if v > date.today():
            raise ValueError("Measurement date cannot be in the future")
        return v


class ImmunizationSchema(BaseModel):
    """Validation schema for immunizations"""

    patient_id: int = Field(..., gt=0, description="Patient ID")
    vaccine_name: str = Field(
        ..., min_length=1, max_length=100, description="Vaccine name"
    )
    administration_date: date = Field(..., description="Administration date")
    lot_number: Optional[str] = Field(
        None, max_length=50, description="Vaccine lot number"
    )
    administered_by: Optional[str] = Field(
        None, max_length=100, description="Administered by"
    )
    site: Optional[str] = Field(None, max_length=50, description="Administration site")
    notes: Optional[str] = Field(None, max_length=500, description="Immunization notes")

    @validator("administration_date")
    def validate_admin_date(cls, v):
        if v > date.today():
            raise ValueError("Administration date cannot be in the future")
        return v


class AlertSchema(BaseModel):
    """Validation schema for patient alerts"""

    patient_id: int = Field(..., gt=0, description="Patient ID")
    alert_type: str = Field(
        ..., regex="^(Allergy|Medical Alert|Insurance|Contact|Other)$"
    )
    message: str = Field(..., min_length=1, max_length=500, description="Alert message")
    severity: str = Field("Medium", regex="^(Low|Medium|High|Critical)$")
    is_active: bool = Field(True, description="Alert active status")


class ScreeningSchema(BaseModel):
    """Validation schema for screening recommendations"""

    patient_id: int = Field(..., gt=0, description="Patient ID")
    screening_type_id: int = Field(..., gt=0, description="Screening type ID")
    due_date: date = Field(..., description="Screening due date")
    status: str = Field("Due", regex="^(Due|Completed|Overdue|Not Applicable)$")
    notes: Optional[str] = Field(None, max_length=500, description="Screening notes")
    last_completed: Optional[date] = Field(None, description="Last completion date")

    @validator("due_date")
    def validate_due_date(cls, v):
        # Allow past dates for overdue screenings
        return v

    @validator("last_completed")
    def validate_last_completed(cls, v):
        if v and v > date.today():
            raise ValueError("Last completed date cannot be in the future")
        return v


class ScreeningTypeSchema(BaseModel):
    """Validation schema for screening types"""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Screening type name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Screening description"
    )
    frequency_months: Optional[int] = Field(
        None, ge=1, le=120, description="Frequency in months"
    )
    age_start: Optional[int] = Field(None, ge=0, le=120, description="Starting age")
    age_end: Optional[int] = Field(None, ge=0, le=120, description="Ending age")
    gender_specific: Optional[str] = Field(None, regex="^(Male|Female|Both)$")

    @validator("age_end")
    def validate_age_range(cls, v, values):
        if (
            v
            and "age_start" in values
            and values["age_start"]
            and v <= values["age_start"]
        ):
            raise ValueError("End age must be greater than start age")
        return v


class LoginSchema(BaseModel):
    """Validation schema for user login"""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, max_length=200, description="Password")

    @validator("username")
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, and underscores"
            )
        return v


class BulkDeleteSchema(BaseModel):
    """Validation schema for bulk delete operations"""

    appointment_ids: Optional[str] = Field(
        None, description="Comma-separated appointment IDs"
    )
    selected_appointments: Optional[List[str]] = Field(
        None, description="List of appointment IDs"
    )
    selected_patients: Optional[List[str]] = Field(
        None, description="List of patient IDs"
    )
    patient_ids: Optional[str] = Field(None, description="Comma-separated patient IDs")

    @validator("appointment_ids", "patient_ids")
    def validate_id_string(cls, v):
        if v:
            try:
                ids = [int(id.strip()) for id in v.split(",") if id.strip()]
                if not ids:
                    raise ValueError("At least one valid ID is required")
                return v
            except ValueError:
                raise ValueError("All IDs must be valid integers")
        return v
