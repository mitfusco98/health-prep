from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    SelectField,
    DateField,
    TextAreaField,
    FloatField,
    IntegerField,
    BooleanField,
    HiddenField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    ValidationError,
    NumberRange,
)
from datetime import datetime


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=4, max=64)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


class PatientForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    date_of_birth = DateField(
        "Date of Birth", validators=[DataRequired()], format="%Y-%m-%d"
    )
    sex = SelectField(
        "Sex",
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired()],
    )
    mrn = StringField(
        "Medical Record Number",
        validators=[Optional()],
        description="Leave blank to auto-generate",
    )
    phone = StringField("Phone Number", validators=[Optional()])
    email = StringField("Email", validators=[Optional(), Email()])
    address = TextAreaField("Address", validators=[Optional()])
    insurance = StringField("Insurance", validators=[Optional()])
    submit = SubmitField("Save Patient")

    def validate_date_of_birth(self, field):
        if field.data > datetime.now().date():
            raise ValidationError("Date of birth cannot be in the future")


class ConditionForm(FlaskForm):
    name = StringField(
        "Condition Name", validators=[DataRequired(), Length(min=1, max=200)]
    )
    diagnosed_date = StringField(
        "Date Diagnosed",
        validators=[DataRequired()],
        description="Enter full date (YYYY-MM-DD) or just year (YYYY)",
    )
    is_active = BooleanField("Active Condition", default=True)
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Save Condition")

    def validate_name(self, field):
        """Sanitize and validate condition name"""
        import re
        import html

        # Strip whitespace and escape HTML
        clean_name = html.escape(field.data.strip())

        # Remove dangerous patterns
        dangerous_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<[^>]*>",
        ]

        for pattern in dangerous_patterns:
            clean_name = re.sub(
                pattern, "", clean_name, flags=re.IGNORECASE | re.DOTALL
            )

        # Validate medical condition name format
        if not re.match(r"^[a-zA-Z0-9\s\-\(\)\/\.,]+$", clean_name):
            raise ValidationError("Condition name contains invalid characters")

        field.data = clean_name

    def validate_diagnosed_date(self, field):
        """Custom validator to handle both full dates and year-only dates"""
        import re
        import html
        from datetime import datetime, date

        # Sanitize input
        date_str = html.escape(field.data.strip())

        # Check if it's a 4-digit year only
        if re.match(r"^\d{4}$", date_str):
            year = int(date_str)
            if year < 1900 or year > datetime.now().year:
                raise ValidationError("Year must be between 1900 and current year")
            # Convert year to January 1st of that year for storage
            field.data = f"{year}-01-01"
            return

        # Check if it's a full date in YYYY-MM-DD format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if parsed_date > date.today():
                    raise ValidationError("Date cannot be in the future")
                if parsed_date.year < 1900:
                    raise ValidationError("Year must be 1900 or later")
                return
            except ValueError:
                raise ValidationError("Invalid date format")

        # If neither format matches
        raise ValidationError(
            "Enter either a full date (YYYY-MM-DD) or just a year (YYYY)"
        )

    def validate_notes(self, field):
        """Sanitize notes field"""
        import re
        import html

        if field.data:
            # Strip whitespace and escape HTML
            clean_notes = html.escape(field.data.strip())

            # Remove dangerous patterns
            dangerous_patterns = [
                r"<script.*?>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe.*?>",
                r"<object.*?>",
                r"<embed.*?>",
            ]

            for pattern in dangerous_patterns:
                clean_notes = re.sub(
                    pattern, "", clean_notes, flags=re.IGNORECASE | re.DOTALL
                )

            field.data = clean_notes


class VitalForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    weight = FloatField(
        "Weight (lbs)",
        validators=[
            Optional(),
            NumberRange(min=0, message="Weight must be a positive number"),
        ],
    )
    height = FloatField(
        "Height (in)",
        validators=[
            Optional(),
            NumberRange(min=0, message="Height must be a positive number"),
        ],
    )
    temperature = FloatField(
        "Temperature (°F)",
        validators=[
            Optional(),
            NumberRange(min=0, message="Temperature must be a positive number"),
        ],
    )
    blood_pressure_systolic = IntegerField(
        "Systolic BP",
        validators=[
            Optional(),
            NumberRange(min=1, message="Blood pressure must be a positive number"),
        ],
    )
    blood_pressure_diastolic = IntegerField(
        "Diastolic BP",
        validators=[
            Optional(),
            NumberRange(min=1, message="Blood pressure must be a positive number"),
        ],
    )
    pulse = IntegerField(
        "Pulse (bpm)",
        validators=[
            Optional(),
            NumberRange(min=1, message="Pulse must be a positive number"),
        ],
    )
    respiratory_rate = IntegerField(
        "Respiratory Rate",
        validators=[
            Optional(),
            NumberRange(min=1, message="Respiratory rate must be a positive number"),
        ],
    )
    oxygen_saturation = FloatField(
        "O2 Saturation (%)",
        validators=[
            Optional(),
            NumberRange(
                min=0, max=100, message="Oxygen saturation must be between 0-100%"
            ),
        ],
    )
    submit = SubmitField("Save Vitals")


class VisitForm(FlaskForm):
    visit_date = DateField("Visit Date", validators=[DataRequired()], format="%Y-%m-%d")
    visit_type = SelectField(
        "Visit Type",
        choices=[
            ("Annual Physical", "Annual Physical"),
            ("Follow-up", "Follow-up"),
            ("Urgent", "Urgent"),
            ("Specialist Consult", "Specialist Consult"),
            ("Telemedicine", "Telemedicine"),
            ("Other", "Other"),
        ],
    )
    provider = StringField("Provider", validators=[DataRequired()])
    reason = StringField("Reason for Visit", validators=[DataRequired()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save Visit")


class LabResultForm(FlaskForm):
    test_name = StringField("Test Name", validators=[DataRequired()])
    test_date = DateField("Test Date", validators=[DataRequired()], format="%Y-%m-%d")
    result_value = StringField("Result", validators=[DataRequired()])
    unit = StringField("Unit", validators=[Optional()])
    reference_range = StringField("Reference Range", validators=[Optional()])
    is_abnormal = BooleanField("Abnormal Result")
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save Lab Result")


class ImagingStudyForm(FlaskForm):
    study_type = SelectField(
        "Study Type",
        choices=[
            ("X-Ray", "X-Ray"),
            ("MRI", "MRI"),
            ("CT", "CT Scan"),
            ("Ultrasound", "Ultrasound"),
            ("PET", "PET Scan"),
            ("Mammogram", "Mammogram"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()],
    )
    body_site = StringField("Body Site", validators=[DataRequired()])
    study_date = DateField("Study Date", validators=[DataRequired()], format="%Y-%m-%d")
    findings = TextAreaField("Findings", validators=[Optional()])
    impression = TextAreaField("Impression", validators=[Optional()])
    submit = SubmitField("Save Imaging Study")


class ConsultReportForm(FlaskForm):
    specialist = StringField("Specialist Name", validators=[DataRequired()])
    specialty = StringField("Specialty", validators=[DataRequired()])
    report_date = DateField(
        "Report Date", validators=[DataRequired()], format="%Y-%m-%d"
    )
    reason = StringField("Reason for Consult", validators=[DataRequired()])
    findings = TextAreaField("Findings", validators=[Optional()])
    recommendations = TextAreaField("Recommendations", validators=[Optional()])
    submit = SubmitField("Save Consult Report")


class HospitalSummaryForm(FlaskForm):
    admission_date = DateField(
        "Admission Date", validators=[DataRequired()], format="%Y-%m-%d"
    )
    discharge_date = DateField(
        "Discharge Date", validators=[Optional()], format="%Y-%m-%d"
    )
    hospital_name = StringField("Hospital Name", validators=[DataRequired()])
    admitting_diagnosis = StringField(
        "Admitting Diagnosis", validators=[DataRequired()]
    )
    discharge_diagnosis = StringField("Discharge Diagnosis", validators=[Optional()])
    procedures = TextAreaField("Procedures", validators=[Optional()])
    discharge_medications = TextAreaField(
        "Discharge Medications", validators=[Optional()]
    )
    followup_instructions = TextAreaField(
        "Follow-up Instructions", validators=[Optional()]
    )
    submit = SubmitField("Save Hospital Summary")


class ScreeningForm(FlaskForm):
    screening_type = StringField("Screening Type", validators=[DataRequired()])
    due_date = DateField("Due Date", validators=[Optional()], format="%Y-%m-%d")
    last_completed = DateField(
        "Last Completed", validators=[Optional()], format="%Y-%m-%d"
    )
    frequency = StringField("Frequency", validators=[Optional()])
    priority = SelectField(
        "Priority",
        choices=[("High", "High"), ("Medium", "Medium"), ("Low", "Low")],
        validators=[Optional()],
    )
    notes = TextAreaField("Notes", validators=[Optional()])


class ScreeningTypeForm(FlaskForm):
    """Form for adding or editing screening types"""

    name = StringField(
        "Name",
        validators=[DataRequired()],
        description="Name of the screening (e.g., 'Mammogram', 'Colonoscopy')",
    )
    description = TextAreaField(
        "Description",
        validators=[Optional()],
        description="Detailed description of this screening test",
    )

    frequency_number = IntegerField(
        "Frequency Number",
        validators=[Optional(), NumberRange(min=1, max=999)],
        description="Number for frequency (e.g., 1, 3, 6)",
    )
    frequency_unit = SelectField(
        "Frequency Unit",
        choices=[
            ("", "Select unit"),
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
            ("years", "Years")
        ],
        validators=[Optional()],
        description="Time unit for frequency",
    )
    gender_specific = SelectField(
        "Gender Specific",
        choices=[("", "All Genders"), ("Male", "Male Only"), ("Female", "Female Only")],
        validators=[Optional()],
        description="Is this screening specific to a particular gender?",
    )
    min_age = IntegerField(
        "Minimum Age",
        validators=[Optional(), NumberRange(min=0, max=120)],
        description="Minimum age to start this screening (leave blank if not age-specific)",
    )
    max_age = IntegerField(
        "Maximum Age",
        validators=[Optional(), NumberRange(min=0, max=120)],
        description="Maximum age for this screening (leave blank if no upper limit)",
    )
    is_active = BooleanField(
        "Active",
        default=True,
        description="Whether this screening should appear in checklists",
    )
    submit = SubmitField("Save Screening")


class ImmunizationForm(FlaskForm):
    vaccine_name = StringField("Vaccine Name", validators=[DataRequired()])
    administration_date = DateField(
        "Administration Date", validators=[DataRequired()], format="%Y-%m-%d"
    )
    dose_number = IntegerField("Dose Number", validators=[Optional()])
    manufacturer = StringField("Manufacturer", validators=[Optional()])
    lot_number = StringField("Lot Number", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save Immunization")


class CSVUploadForm(FlaskForm):
    file = FileField(
        "CSV File", validators=[FileRequired(), FileAllowed(["csv"], "CSV files only!")]
    )
    submit = SubmitField("Upload")


class DocumentUploadForm(FlaskForm):
    file = FileField(
        "Document File (Optional)",
        validators=[
            Optional(),
            FileAllowed(
                ["txt", "pdf", "jpg", "jpeg", "png"],
                "Only text, PDF and common image formats allowed",
            ),
            lambda form, field: (
                len(field.data.read()) <= 10 * 1024 * 1024 if field.data else True
            ),  # 10MB limit
        ],
    )
    document_name = StringField(
        "File Name",
        validators=[DataRequired()],
        description="Give this document a descriptive name",
    )
    source_system = StringField(
        "Source System/Origin",
        validators=[DataRequired()],
        default="HealthPrep",
        description="The EMR or healthcare system that produced this document",
    )
    document_date = DateField(
        "Document Date",
        validators=[DataRequired()],
        format="%Y-%m-%d",
        default=datetime.utcnow().date(),
        description="Date when this document was created",
    )
    document_type = SelectField(
        "Document Type",
        validators=[DataRequired()],
        choices=[
            ("LAB_REPORT", "Lab Report"),
            ("RADIOLOGY_REPORT", "Imaging Report"),
            ("CONSULTATION", "Consult"),
            ("DISCHARGE_SUMMARY", "Hospital Record"),
            ("CLINICAL_NOTE", "Clinical Note"),
            ("OTHER", "Other"),
        ],
        description="The type of document being uploaded",
    )
    notes = TextAreaField(
        "Notes",
        validators=[Optional()],
        description="Any additional notes about this document",
    )
    submit = SubmitField("Upload Document")


class AppointmentForm(FlaskForm):
    patient_id = SelectField("Patient", validators=[DataRequired()], coerce=int)
    appointment_date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    appointment_time = SelectField(
        "Time",
        validators=[DataRequired()],
        description="Available 15-minute time slots between 8:00 AM and 4:00 PM",
    )
    note = StringField(
        "Appointment Note",
        validators=[Optional()],
        render_kw={"placeholder": "Brief description of appointment purpose"},
    )
    submit = SubmitField("Save Appointment")

    def __init__(self, *args, **kwargs):
        super(AppointmentForm, self).__init__(*args, **kwargs)
        # Generate time slots from 8:00 AM to 4:00 PM in 15-minute increments
        time_slots = []
        for hour in range(8, 16):  # 8 AM to 4 PM (16:00)
            for minute in [0, 15, 30, 45]:
                # Format as HH:MM for value and readable time for label
                time_value = f"{hour:02d}:{minute:02d}"
                # AM/PM format for display
                if hour < 12:
                    time_label = f"{hour}:{minute:02d} AM"
                elif hour == 12:
                    time_label = f"12:{minute:02d} PM"
                else:
                    time_label = f"{hour-12}:{minute:02d} PM"

                time_slots.append((time_value, time_label))

        self.appointment_time.choices = time_slots


class PatientAlertForm(FlaskForm):
    alert_type = SelectField(
        "Alert Type",
        validators=[DataRequired()],
        choices=[
            ("Allergy", "Allergy"),
            ("Clinical", "Clinical Alert"),
            ("Administrative", "Administrative"),
            ("Medication", "Medication Alert"),
            ("Lab", "Lab Alert"),
            ("Other", "Other"),
        ],
    )
    description = StringField(
        "Alert Description",
        validators=[DataRequired(), Length(max=200)],
        description="Brief description of the alert",
    )
    details = TextAreaField(
        "Alert Details",
        validators=[Optional()],
        description="Additional information about this alert",
    )
    start_date = DateField(
        "Start Date",
        validators=[DataRequired()],
        format="%Y-%m-%d",
        default=datetime.utcnow().date(),
    )
    is_active = BooleanField(
        "Active", default=True, description="Uncheck to deactivate this alert"
    )
    severity = SelectField(
        "Severity",
        validators=[DataRequired()],
        choices=[("High", "High"), ("Medium", "Medium"), ("Low", "Low")],
    )
    submit = SubmitField("Save Alert")