from datetime import datetime
import enum
import json
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class DocumentType(enum.Enum):
    CLINICAL_NOTE = "Clinical Note"
    DISCHARGE_SUMMARY = "Discharge Summary"
    RADIOLOGY_REPORT = "Radiology Report"
    LAB_REPORT = "Lab Report"
    MEDICATION_LIST = "Medication List"
    REFERRAL = "Referral"
    CONSULTATION = "Consultation"
    OPERATIVE_REPORT = "Operative Report"
    PATHOLOGY_REPORT = "Pathology Report"
    UNKNOWN = "Unknown"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        # Use stronger hashing with higher iteration count and salt rounds
        self.password_hash = generate_password_hash(
            password, method="pbkdf2:sha256:600000", salt_length=32
        )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    sex = db.Column(db.String(10), nullable=False)  # 'Male', 'Female', 'Other'
    mrn = db.Column(db.String(20), unique=True, nullable=False)  # Medical Record Number
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    insurance = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    conditions = db.relationship("Condition", backref="patient", lazy=True)
    immunizations = db.relationship("Immunization", backref="patient", lazy=True)
    vitals = db.relationship("Vital", backref="patient", lazy=True)
    visits = db.relationship("Visit", backref="patient", lazy=True)
    lab_results = db.relationship("LabResult", backref="patient", lazy=True)
    imaging_studies = db.relationship("ImagingStudy", backref="patient", lazy=True)
    consult_reports = db.relationship("ConsultReport", backref="patient", lazy=True)
    hospital_summaries = db.relationship(
        "HospitalSummary", backref="patient", lazy=True
    )
    # Screening relationship is handled in Screening model
    documents = db.relationship("MedicalDocument", backref="patient", lazy=True)
    # Note: The 'appointments' relationship is defined in the Appointment model with a backref

    @property
    def age(self):
        today = datetime.now().date()
        born = self.date_of_birth
        return (
            today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def update_demographics(self, form_data):
        """
        Update patient demographics from form data
        This centralized method ensures all demographics are updated in one place

        Args:
            form_data: Form data containing patient demographic information
        """
        # Update basic information
        self.first_name = form_data.first_name.data
        self.last_name = form_data.last_name.data
        self.date_of_birth = form_data.date_of_birth.data
        self.sex = form_data.sex.data
        self.mrn = form_data.mrn.data
        self.phone = form_data.phone.data
        self.email = form_data.email.data
        self.address = form_data.address.data
        self.insurance = form_data.insurance.data

        # The updated_at column will be automatically updated via SQLAlchemy's onupdate parameter

    def __repr__(self):
        return f"<Patient {self.full_name} (MRN: {self.mrn})>"


class Condition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))  # ICD-10 or other coding system
    diagnosed_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Condition {self.name} for Patient {self.patient_id}>"


class Immunization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    vaccine_name = db.Column(db.String(100), nullable=False)
    administration_date = db.Column(db.Date, nullable=False)
    dose_number = db.Column(db.Integer)
    manufacturer = db.Column(db.String(100))
    lot_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Immunization {self.vaccine_name} for Patient {self.patient_id}>"


class Vital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    weight = db.Column(db.Float)  # kg
    height = db.Column(db.Float)  # cm
    bmi = db.Column(db.Float)
    temperature = db.Column(db.Float)  # °C
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    pulse = db.Column(db.Integer)  # bpm
    respiratory_rate = db.Column(db.Integer)  # breaths per minute
    oxygen_saturation = db.Column(db.Float)  # %
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Vital for Patient {self.patient_id} on {self.date}>"


class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    visit_date = db.Column(db.DateTime, nullable=False)
    visit_type = db.Column(
        db.String(50)
    )  # e.g., 'Annual Physical', 'Follow-up', 'Urgent'
    provider = db.Column(db.String(100))
    reason = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Visit for Patient {self.patient_id} on {self.visit_date}>"


class LabResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    test_name = db.Column(db.String(100), nullable=False)
    test_date = db.Column(db.DateTime, nullable=False)
    result_value = db.Column(db.String(100))
    unit = db.Column(db.String(20))
    reference_range = db.Column(db.String(50))
    is_abnormal = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LabResult {self.test_name} for Patient {self.patient_id}>"


class ImagingStudy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    study_type = db.Column(db.String(100), nullable=False)  # e.g., 'X-Ray', 'MRI', 'CT'
    body_site = db.Column(db.String(100))
    study_date = db.Column(db.DateTime, nullable=False)
    findings = db.Column(db.Text)
    impression = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ImagingStudy {self.study_type} for Patient {self.patient_id}>"


class ConsultReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    specialist = db.Column(db.String(100))
    specialty = db.Column(db.String(100))  # e.g., 'Cardiology', 'Neurology'
    report_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200))
    findings = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ConsultReport from {self.specialist} for Patient {self.patient_id}>"


class HospitalSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    admission_date = db.Column(db.DateTime, nullable=False)
    discharge_date = db.Column(db.DateTime)
    hospital_name = db.Column(db.String(100))
    admitting_diagnosis = db.Column(db.String(200))
    discharge_diagnosis = db.Column(db.String(200))
    procedures = db.Column(db.Text)
    discharge_medications = db.Column(db.Text)
    followup_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<HospitalSummary for Patient {self.patient_id} on {self.admission_date}>"
        )


# ScreeningType model is defined at the bottom of the file to avoid circular imports


class Screening(db.Model):
    """Individual screening assignments for specific patients"""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    screening_type = db.Column(
        db.String(100), nullable=False
    )  # e.g., 'Mammogram', 'Colonoscopy'
    due_date = db.Column(db.Date)
    last_completed = db.Column(db.Date)
    frequency = db.Column(db.String(50))  # e.g., 'Annual', 'Every 5 years'
    priority = db.Column(db.String(20))  # e.g., 'High', 'Medium', 'Low'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship with Patient - simple, non-conflicting relationship
    patient = db.relationship("Patient", backref=db.backref("screenings", lazy=True))

    def __repr__(self):
        return f"<Screening {self.screening_type} for Patient {self.patient_id}>"


class MedicalDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    filename = db.Column(db.String(255))
    document_name = db.Column(db.String(255))  # Descriptive name for the document
    document_type = db.Column(
        db.String(50)
    )  # Stores the string value of DocumentType enum
    content = db.Column(
        db.Text, nullable=True
    )  # Text content (nullable to allow binary-only files)
    binary_content = db.Column(
        db.LargeBinary, nullable=True
    )  # Binary content for images
    is_binary = db.Column(db.Boolean, default=False)  # Flag to indicate binary content
    mime_type = db.Column(db.String(100), nullable=True)  # MIME type for binary content
    source_system = db.Column(db.String(100))  # EMR system name or source
    document_date = db.Column(db.DateTime)
    provider = db.Column(db.String(100))
    doc_metadata = db.Column(db.Text)  # JSON string with additional metadata
    is_processed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship with Patient is already defined in the Patient model

    def __repr__(self):
        display_name = self.document_name if self.document_name else self.filename
        return f'<MedicalDocument "{display_name}" ({self.document_type}) for Patient {self.patient_id}>'


class EHRConnection(db.Model):
    """Configuration for an external EHR system connection"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    vendor = db.Column(db.String(50), nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    auth_type = db.Column(db.String(20), nullable=False)  # 'none', 'api_key', 'oauth'
    api_key = db.Column(db.String(255))
    client_id = db.Column(db.String(255))
    client_secret = db.Column(db.String(255))
    use_auth_header = db.Column(db.Boolean, default=True)
    additional_config = db.Column(db.Text)  # JSON string with any extra configuration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    import_history = db.relationship(
        "EHRImportHistory", backref="connection", lazy=True
    )

    def __repr__(self):
        return f"<EHRConnection {self.name} ({self.vendor})>"

    @property
    def config_dict(self):
        """Return connection configuration as a dictionary"""
        config = {
            "name": self.name,
            "vendor": self.vendor,
            "base_url": self.base_url,
            "auth_type": self.auth_type,
            "use_auth_header": self.use_auth_header,
        }

        if self.auth_type == "api_key" and self.api_key:
            config["api_key"] = self.api_key
        elif self.auth_type == "oauth":
            config["client_id"] = self.client_id
            config["client_secret"] = self.client_secret

        if self.additional_config:
            try:
                additional = json.loads(self.additional_config)
                config.update(additional)
            except json.JSONDecodeError:
                pass

        return config


class EHRImportHistory(db.Model):
    """Record of data imports from EHR systems"""

    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(
        db.Integer, db.ForeignKey("ehr_connection.id"), nullable=False
    )
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"))
    patient_name = db.Column(db.String(200))  # In case the patient wasn't imported
    ehr_patient_id = db.Column(db.String(100))  # ID in the external EHR system
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    imported_data_types = db.Column(
        db.String(255)
    )  # Comma-separated list: 'patient,conditions,vitals,documents'
    imported_items = db.Column(db.Integer, default=0)  # Count of items imported
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)

    def __repr__(self):
        return f'<EHRImportHistory {self.id} for {self.patient_name or "Unknown"} from {self.connection.name if self.connection else "Unknown"}>'


class Appointment(db.Model):
    """Daily appointment schedule for patients"""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    note = db.Column(db.String(200))
    status = db.Column(
        db.String(20), default="OOO"
    )  # Options: 'OOO', 'waiting', 'provider', 'seen'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    patient = db.relationship("Patient", backref=db.backref("appointments", lazy=True))

    @property
    def date_time(self):
        """Return a datetime object combining the date and time"""
        from datetime import datetime as dt

        return dt.combine(self.appointment_date, self.appointment_time)

    def __repr__(self):
        return f"<Appointment for {self.patient.full_name} on {self.appointment_date} at {self.appointment_time}>"


class ScreeningType(db.Model):
    """Defines screening types that can be assigned to patients"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    default_frequency = db.Column(db.String(50))  # e.g., "Annual", "Every 3 years"
    gender_specific = db.Column(db.String(10))  # "Male" or "Female" or None for all
    min_age = db.Column(
        db.Integer
    )  # Minimum age for this screening, null if no minimum
    max_age = db.Column(
        db.Integer
    )  # Maximum age for this screening, null if no maximum
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Don't specify a relationship here since the original Screening table doesn't have a foreign key

    def __repr__(self):
        return f"<ScreeningType {self.name}>"


class PatientAlert(db.Model):
    """Patient-specific alerts that appear on prep sheets"""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    alert_type = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'Allergy', 'Clinical', 'Administrative'
    description = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    start_date = db.Column(db.Date, default=datetime.utcnow().date)
    end_date = db.Column(db.Date, nullable=True)  # If null, alert is permanent
    is_active = db.Column(db.Boolean, default=True)
    severity = db.Column(db.String(20), default="Medium")  # 'High', 'Medium', 'Low'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    patient = db.relationship("Patient", backref=db.backref("alerts", lazy=True))

    def __repr__(self):
        return f"<PatientAlert {self.description} for Patient {self.patient_id}>"


class ChecklistSettings(db.Model):
    """Settings for the prep sheet quality checklist"""

    id = db.Column(db.Integer, primary_key=True)
    layout_style = db.Column(db.String(20), default="list")  # 'list' or 'table'
    show_notes = db.Column(db.Boolean, default=True)
    status_options = db.Column(
        db.Text, default="due,due_soon,sent_incomplete,completed"
    )  # Comma-separated list
    custom_status_options = db.Column(
        db.Text, nullable=True
    )  # Comma-separated list of custom status options
    content_sources = db.Column(
        db.Text, default="database,age_based,gender_based,condition_based"
    )  # Comma-separated list
    default_items = db.Column(
        db.Text, nullable=True
    )  # Newline-separated list of default items
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def status_options_list(self):
        """Return status options as a list"""
        if not self.status_options:
            return []
        return self.status_options.split(",")

    @property
    def custom_status_list(self):
        """Return custom status options as a list"""
        if not self.custom_status_options:
            return []
        return self.custom_status_options.split(",")

    @property
    def all_status_options(self):
        """Return all status options (default + custom) as a list"""
        all_options = self.status_options_list
        all_options.extend(self.custom_status_list)
        return all_options

    @property
    def content_sources_list(self):
        """Return content sources as a list"""
        if not self.content_sources:
            return []
        return self.content_sources.split(",")

    @property
    def default_items_list(self):
        """Return default items as a list"""
        if not self.default_items:
            return []
        return [item.strip() for item in self.default_items.split("\n") if item.strip()]

    def __repr__(self):
        return f"<ChecklistSettings id={self.id}>"


class AdminLog(db.Model):
    """Admin activity and system event logging"""

    __tablename__ = "admin_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    event_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # login_fail, validation_error, admin_action, etc.
    event_details = db.Column(
        db.Text, nullable=True
    )  # JSON string with additional details
    request_id = db.Column(
        db.String(36), nullable=True, index=True
    )  # UUID for request tracking
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6 address
    user_agent = db.Column(db.String(500), nullable=True)

    # Relationship
    user = db.relationship("User", backref=db.backref("admin_logs", lazy=True))

    def __repr__(self):
        return f"<AdminLog {self.event_type} at {self.timestamp}>"

    @property
    def event_details_dict(self):
        """Return event details as a dictionary"""
        if not self.event_details:
            return {}
        try:
            # First try to parse as JSON
            import json

            return json.loads(self.event_details)
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, try to evaluate as Python dict
            try:
                import ast

                return ast.literal_eval(self.event_details)
            except (ValueError, SyntaxError):
                # If both fail, try to extract basic info from string format
                try:
                    # Handle old string format like "{'route': '/path', 'method': 'GET'}"
                    if self.event_details.strip().startswith(
                        "{"
                    ) and self.event_details.strip().endswith("}"):
                        # Try to fix common formatting issues
                        fixed_details = self.event_details.replace("'", '"')
                        return json.loads(fixed_details)
                except:
                    pass
                # Return raw string in a dict if all else fails
                return {"raw": self.event_details, "parsed": False}

    @classmethod
    def log_event(
        cls,
        event_type,
        user_id=None,
        event_details=None,
        request_id=None,
        ip_address=None,
        user_agent=None,
    ):
        """
        Convenience method to create a new admin log entry

        Args:
            event_type: Type of event (required)
            user_id: ID of the user associated with the event
            event_details: Dictionary or string with event details
            request_id: Request tracking ID
            ip_address: IP address of the request
            user_agent: User agent string
        """
        if isinstance(event_details, dict):
            event_details = json.dumps(event_details)

        log_entry = cls(
            event_type=event_type,
            user_id=user_id,
            event_details=event_details,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        db.session.add(log_entry)
        return log_entry
