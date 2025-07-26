from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    send_file,
    jsonify,
    make_response,
)
import time as time_module  # Rename to avoid conflicts
import json
import logging
from datetime import datetime, date, time, timedelta
from sqlalchemy import func
from app import app, db, csrf
from db_utils import safe_db_operation, fresh_session_operation, with_db_retry
from models import (
    Patient,
    Condition,
    Vital,
    MedicalDocument,
    LabResult,
    ImagingStudy,
    ConsultReport,
    HospitalSummary,
    ScreeningType,
    Screening,
    Appointment,
    DocumentType,
    Immunization,
    PatientAlert,
)
from input_validator import (
    validate_patient_input,
    validate_appointment_input,
    validate_login_input,
    validate_bulk_delete_input,
    log_validation_error,
)


# Define a context processor for global template functions
@app.context_processor
def utility_processor():
    def get_all_patients():
        from models import Patient
        import logging

        try:
            # Ensure any previous transaction issues are cleared
            db.session.rollback()
            # Get patients with optimized query (exclude large binary content)
            return Patient.query.order_by(Patient.last_name, Patient.first_name).all()
        except Exception as e:
            # Log error and return empty list instead of crashing
            logging.error(f"Error fetching patients in utility_processor: {str(e)}")
            return []

    # Add cache-busting timestamp for static files
    def cache_bust():
        return {"cache_bust": int(time_module.time())}

    return {"get_all_patients": get_all_patients, "cache_bust": cache_bust()}


# Import template filter functions from shared utilities
from shared_utilities import (
    format_datetime_display,
    format_date_of_birth,
    format_timestamp_to_est,
)

# Register template filters using consolidated functions
app.template_filter("datetime")(format_datetime_display)
app.template_filter("dob")(format_date_of_birth)
app.template_filter("timestamp_to_est")(format_timestamp_to_est)
from forms import (
    PatientForm,
    ConditionForm,
    VitalForm,
    VisitForm,
    LabResultForm,
    ImagingStudyForm,
    ConsultReportForm,
    HospitalSummaryForm,
    ScreeningForm,
    CSVUploadForm,
    DocumentUploadForm,
    AppointmentForm,
    ImmunizationForm,
    PatientAlertForm,
)
from comprehensive_logging import (
    log_patient_operation,
    log_admin_operation,
    log_data_modification,
    log_page_access,
)
from models import (
    Patient,
    Condition,
    Vital,
    Visit,
    LabResult,
    ImagingStudy,
    ConsultReport,
    HospitalSummary,
    Screening,
    MedicalDocument,
    DocumentType,
    Appointment,
    Immunization,
    PatientAlert,
)
from utils import (
    process_csv_upload,
    generate_prep_sheet,
    evaluate_screening_needs,
    process_document_upload,
    get_patient_documents_summary,
    extract_document_text_from_url,
    group_documents_by_type,
)
from prep_doc_utils import generate_prep_sheet_doc
from appointment_utils import (
    detect_appointment_conflicts,
    format_conflict_message,
    get_available_time_slots,
    get_booked_time_slots,
    DEFAULT_APPOINTMENT_DURATION,
)
from admin_log_viewer import format_log_details as format_event_details
from datetime import datetime, timedelta
import json
import logging
import uuid

# Create logger for this module
logger = logging.getLogger(__name__)


def _patient_meets_trigger_conditions(patient_conditions, screening_type):
    """
    Enhanced condition matching for screening type trigger conditions
    Supports robust matching of condition variants and related codes
    
    Args:
        patient_conditions: List of patient's Condition objects
        screening_type: ScreeningType object with trigger_conditions
    
    Returns:
        bool: True if patient meets trigger conditions
    """
    trigger_conditions = screening_type.get_trigger_conditions()
    if not trigger_conditions:
        return True  # No trigger conditions means all patients qualify
    
    # Define condition variant mappings for better matching
    condition_variants = {
        'diabetes': [
            'diabetes mellitus', 'diabetes', 'diabetic', 'type 1 diabetes', 'type 2 diabetes',
            'type i diabetes', 'type ii diabetes', 'insulin dependent diabetes',
            'non-insulin dependent diabetes', 'gestational diabetes', 'dm', 't1dm', 't2dm'
        ],
        'hypertension': [
            'hypertension', 'high blood pressure', 'elevated blood pressure', 'htn',
            'essential hypertension', 'primary hypertension', 'secondary hypertension',
            'hypertensive', 'blood pressure'
        ],
        'hyperlipidemia': [
            'hyperlipidemia', 'dyslipidemia', 'high cholesterol', 'elevated cholesterol',
            'lipid disorder', 'cholesterol', 'hypercholesterolemia'
        ],
        'obesity': [
            'obesity', 'obese', 'overweight', 'excessive weight', 'morbid obesity'
        ]
    }
    
    # ICD-10 code relationships for condition matching
    diabetes_codes = ['E10', 'E11', 'E12', 'E13', 'E14', '73211009', 'Z79.4']
    hypertension_codes = ['I10', 'I11', 'I12', 'I13', 'I15', '38341003']
    lipid_codes = ['E78', 'E78.0', 'E78.1', 'E78.2', 'E78.5', '55822004']
    
    def normalize_condition_name(name):
        """Normalize condition name for better matching"""
        if not name:
            return ""
        normalized = name.lower().strip()
        # Remove common prefixes/suffixes that might interfere with matching
        normalized = normalized.replace('essential ', '').replace('primary ', '')
        normalized = normalized.replace(' mellitus', '').replace(' disorder', '')
        normalized = normalized.replace('type 1 ', 'type i ').replace('type 2 ', 'type ii ')
        return normalized
    
    def codes_are_related(patient_code, trigger_code):
        """Check if codes are related (same condition family)"""
        if not patient_code or not trigger_code:
            return False
        
        # Direct match
        if patient_code == trigger_code:
            return True
        
        # Check if both codes are in same condition family
        patient_code_prefix = patient_code[:3] if len(patient_code) >= 3 else patient_code
        
        if patient_code in diabetes_codes or patient_code_prefix == 'E11':
            return trigger_code in diabetes_codes or trigger_code == '73211009'
        if patient_code in hypertension_codes or patient_code_prefix == 'I10':
            return trigger_code in hypertension_codes or trigger_code == '38341003'
        if patient_code in lipid_codes or patient_code_prefix == 'E78':
            return trigger_code in lipid_codes or trigger_code == '55822004'
        
        return False
    
    def condition_names_match(patient_name, trigger_name):
        """Enhanced condition name matching with variants"""
        patient_normalized = normalize_condition_name(patient_name)
        trigger_normalized = normalize_condition_name(trigger_name)
        
        # Direct substring match
        if trigger_normalized in patient_normalized or patient_normalized in trigger_normalized:
            return True
        
        # Check against condition variant mappings
        for condition_family, variants in condition_variants.items():
            trigger_matches_family = any(variant in trigger_normalized for variant in variants)
            patient_matches_family = any(variant in patient_normalized for variant in variants)
            
            if trigger_matches_family and patient_matches_family:
                return True
        
        # Word-based matching for complex condition names
        trigger_words = set(trigger_normalized.replace('-', ' ').split())
        patient_words = set(patient_normalized.replace('-', ' ').split())
        
        # If significant overlap in key words
        key_words = {'diabetes', 'hypertension', 'cholesterol', 'lipid', 'blood', 'pressure'}
        trigger_key_words = trigger_words.intersection(key_words)
        patient_key_words = patient_words.intersection(key_words)
        
        if trigger_key_words and patient_key_words and trigger_key_words.intersection(patient_key_words):
            return True
        
        return False
    
    # Check each patient condition against trigger conditions
    for condition in patient_conditions:
        condition_name = condition.name or ""
        condition_code = condition.code or ""
        
        for trigger in trigger_conditions:
            # Enhanced code matching
            if 'code' in trigger and condition_code:
                if codes_are_related(condition_code, trigger['code']):
                    return True
            
            # Enhanced name matching
            if 'display' in trigger:
                if condition_names_match(condition_name, trigger['display']):
                    return True
    
    return False


def log_validation_error(endpoint, validation_errors, form_data, user_id=None):
    """Log form validation errors to admin logs - delegates to centralized middleware"""
    from validation_middleware import ValidationLogger

    ValidationLogger.log_validation_failure(
        endpoint, validation_errors, form_data, user_id
    )


@app.route("/")
def redirect_to_home():
    """Redirect root path to home page"""
    return redirect(url_for("index"))


@app.route("/home")
@app.route("/home/date/<date_str>")
@log_page_access("home_dashboard")
def index(date_str=None):
    """Application home page - Demo version with sample patients"""
    # Get stats for the dashboard
    patient_count = Patient.query.count()
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    recent_lab_results = (
        LabResult.query.order_by(LabResult.test_date.desc()).limit(5).all()
    )
    
    # Get screening statistics for "patients with screenings due" counter
    try:
        from screening_performance_optimizer import screening_optimizer
        screening_stats = screening_optimizer.get_screening_stats()
        # Count patients with Due status screenings
        patients_with_due_screenings = screening_stats.get('by_status', {}).get('Due', 0)
    except Exception as e:
        print(f"Error getting screening stats for home page: {e}")
        patients_with_due_screenings = 0

    # Get recent documents
    # Get recent documents and total document count with retry logic for connection issues
    recent_documents = []
    total_documents = 0
    try:
        # Optimize query by only selecting needed fields to avoid loading large binary content
        recent_documents = (
            MedicalDocument.query
            .with_entities(
                MedicalDocument.id,
                MedicalDocument.document_name, 
                MedicalDocument.filename,
                MedicalDocument.document_type,
                MedicalDocument.created_at,
                MedicalDocument.patient_id
            )
            .order_by(MedicalDocument.created_at.desc())
            .limit(10)
            .all()
        )
        total_documents = MedicalDocument.query.count()
    except (OperationalError, DisconnectionError) as e:
        if "SSL connection has been closed" in str(e):
            print("Database connection lost, attempting to reconnect...")
            db.session.remove()
            try:
                recent_documents = (
                    MedicalDocument.query.order_by(MedicalDocument.created_at.desc())
                    .limit(10)
                    .all()
                )
                total_documents = MedicalDocument.query.count()
            except Exception as retry_error:
                print(f"Database retry failed: {retry_error}")
                recent_documents = []
                total_documents = 0
        else:
            raise

    # Get selected date's appointments or default to today
    today = datetime.now().date()

    # Check for date from query parameters
    selected_date_param = request.args.get(
        "selected_date"
    )  # From the date picker in the form
    date_str_param = request.args.get("date_str")  # Legacy parameter

    # The refresh parameter is used as a cache-busting mechanism
    refresh_param = request.args.get("refresh")

    # Give priority to the selected_date in query params, then date_str in query params, then URL param, then default to today
    if selected_date_param:
        try:
            selected_date = datetime.strptime(selected_date_param, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today
            flash("Invalid date format. Showing today's appointments.", "warning")
    elif date_str:
        try:
            # Parse the date string (format: YYYY-MM-DD)
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            # If date is invalid, default to today
            selected_date = today
            flash("Invalid date format. Showing today's appointments.", "warning")
    else:
        selected_date = today

    # Get previous and next day for navigation
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    # Generate timestamp for cache-busting
    timestamp = int(time_module.time())

    # Get appointments for the selected date
    try:
        from sqlalchemy import func

        appointments = (
            Appointment.query.filter(
                func.date(Appointment.appointment_date) == func.date(selected_date)
            )
            .order_by(Appointment.appointment_time)
            .all()
        )
    except Exception as e:
        # Fallback to original query
        appointments = (
            Appointment.query.filter(Appointment.appointment_date == selected_date)
            .order_by(Appointment.appointment_time)
            .all()
        )

    # Remove excessive debug logging that was cluttering console output

    return render_template(
        "index.html",
        patient_count=patient_count,
        patients=patients,
        upcoming_visits=appointments,  # Use the appointments for the selected date for the counter
        recent_lab_results=recent_lab_results,
        recent_documents=recent_documents,
        total_documents=total_documents,
        todays_appointments=appointments,
        selected_date=selected_date,
        prev_date=prev_date,
        next_date=next_date,
        today_date=today,
        timestamp=timestamp,
        screening_count=patients_with_due_screenings,  # Add screening due count for dashboard sync
    )


@app.route("/patients")
def patient_list():
    """Display all patients with search functionality"""
    search_query = request.args.get("search", "").strip()
    sort_field = request.args.get("sort", "last_name")
    sort_order = request.args.get("order", "asc")

    # Build the query
    query = Patient.query

    # Apply search filter if provided
    if search_query:
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(f"%{search_query}%"),
                Patient.last_name.ilike(f"%{search_query}%"),
                Patient.mrn.ilike(f"%{search_query}%"),
            )
        )

    # Apply sorting
    if sort_field == "first_name":
        order_by = (
            Patient.first_name.asc()
            if sort_order == "asc"
            else Patient.first_name.desc()
        )
    elif sort_field == "dob":
        order_by = (
            Patient.date_of_birth.asc()
            if sort_order == "asc"
            else Patient.date_of_birth.desc()
        )
    elif sort_field == "mrn":
        order_by = Patient.mrn.asc() if sort_order == "asc" else Patient.mrn.desc()
    else:  # default to last_name
        order_by = (
            Patient.last_name.asc() if sort_order == "asc" else Patient.last_name.desc()
        )

    patients = query.order_by(order_by).all()

    return render_template(
        "patient_list.html", patients=patients, search_query=search_query
    )


@app.route("/patients/add", methods=["GET", "POST"])
@safe_db_operation
@validate_patient_input
def add_patient():
    """Add a new patient"""
    app.logger.info(f"Add patient route accessed, method: {request.method}")

    # Initialize form
    form = PatientForm()

    if request.method == "POST":
        app.logger.debug(f"Form data received: {request.form}")

        try:
            # Get form data directly from request
            new_mrn = request.form.get("mrn")

            # If MRN is not provided or is empty, generate one
            if not new_mrn or new_mrn.strip() == "":
                from utils import get_next_available_mrn

                new_mrn = get_next_available_mrn()
                app.logger.info(f"Auto-generated MRN: {new_mrn}")

            # Check if MRN already exists
            existing_patient = Patient.query.filter_by(mrn=new_mrn).first()
            if existing_patient:
                flash(
                    "A patient with this Medical Record Number already exists.",
                    "danger",
                )
                return render_template(
                    "patient_form.html", form=form, title="Add Patient"
                )

            # Parse and convert date string to date object
            dob_str = request.form.get("date_of_birth")
            dob = None
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("Invalid date format for Date of Birth.", "danger")
                    return render_template(
                        "patient_form.html", form=form, title="Add Patient"
                    )

            # Create new patient with form data
            patient = Patient(
                first_name=request.form.get("first_name"),
                last_name=request.form.get("last_name"),
                date_of_birth=dob,
                sex=request.form.get("sex"),
                mrn=new_mrn,
                phone=request.form.get("phone"),
                email=request.form.get("email"),
                address=request.form.get("address"),
                insurance=request.form.get("insurance"),
            )

            # Add to session and flush to get the ID
            db.session.add(patient)
            db.session.flush()

            app.logger.info(
                f"New patient created: {patient.first_name} {patient.last_name} (ID: {patient.id}, MRN: {patient.mrn})"
            )

            # Evaluate and add appropriate screenings for the new patient
            evaluate_screening_needs(patient)

            # Commit all changes
            db.session.commit()
            app.logger.info(f"Patient {patient.id} successfully saved to database")

            flash("Patient added successfully.", "success")
            return redirect(url_for("patient_detail", patient_id=patient.id))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding patient: {str(e)}")
            flash(f"Error adding patient: {str(e)}", "danger")

    return render_template("patient_form.html", form=form, title="Add Patient")


@app.route("/patients/<int:patient_id>")
@safe_db_operation
@log_patient_operation("view_patient")
def patient_detail(patient_id):
    """Display patient details"""
    app.logger.info(f"Viewing patient details for ID: {patient_id}")
    try:
        patient = Patient.query.get_or_404(patient_id)
        app.logger.info(f"Found patient: {patient.full_name}")
    except Exception as e:
        app.logger.error(f"Error retrieving patient: {str(e)}")
        flash(f"Error retrieving patient information: {str(e)}", "danger")
        return redirect(url_for("index"))

    # Get the most recent vital signs
    recent_vitals = (
        Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).first()
    )

    # Get all vital signs for history
    all_vitals = (
        Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).all()
    )

    # Get the most recent lab results
    recent_labs = (
        LabResult.query.filter_by(patient_id=patient_id)
        .order_by(LabResult.test_date.desc())
        .limit(5)
        .all()
    )

    # Get the active conditions
    active_conditions = Condition.query.filter_by(
        patient_id=patient_id, is_active=True
    ).all()

    # Get past visits
    past_visits = (
        Visit.query.filter_by(patient_id=patient_id)
        .order_by(Visit.visit_date.desc())
        .all()
    )

    # Get screening recommendations with optimized query
    screenings = (
        Screening.query
        .filter_by(patient_id=patient_id)
        .join(ScreeningType, Screening.screening_type == ScreeningType.name)
        .filter(ScreeningType.is_active == True)
        .order_by(Screening.due_date)
        .all()
    )

    # Get immunization records
    immunizations = (
        Immunization.query.filter_by(patient_id=patient_id)
        .order_by(Immunization.administration_date.desc())
        .all()
    )

    # Get upcoming visit if any
    upcoming_visit = (
        Visit.query.filter(
            Visit.patient_id == patient_id, Visit.visit_date > datetime.now()
        )
        .order_by(Visit.visit_date)
        .first()
    )

    # Get past appointments (already occurred)
    current_date = datetime.now().date()
    past_appointments = (
        Appointment.query.filter(
            Appointment.patient_id == patient_id,
            db.or_(
                Appointment.appointment_date < current_date,
                db.and_(
                    Appointment.appointment_date == current_date,
                    Appointment.appointment_time < datetime.now().time(),
                ),
            ),
        )
        .order_by(
            Appointment.appointment_date.desc(), Appointment.appointment_time.desc()
        )
        .all()
    )

    # Get upcoming appointments (scheduled but not yet occurred)
    upcoming_appointments = (
        Appointment.query.filter(
            Appointment.patient_id == patient_id,
            db.or_(
                Appointment.appointment_date > current_date,
                db.and_(
                    Appointment.appointment_date == current_date,
                    Appointment.appointment_time >= datetime.now().time(),
                ),
            ),
        )
        .order_by(Appointment.appointment_date, Appointment.appointment_time)
        .all()
    )

    # Get patient documents
    documents = (
        MedicalDocument.query.filter_by(patient_id=patient_id)
        .order_by(MedicalDocument.document_date.desc())
        .all()
    )

    # Organize documents by type - support both legacy and new document types
    lab_documents = [
        doc for doc in documents if doc.document_type in ["LAB_REPORT", "LABORATORIES"]
    ]
    imaging_documents = [
        doc
        for doc in documents
        if doc.document_type in ["RADIOLOGY_REPORT", "IMAGING"]
    ]
    consult_documents = [
        doc for doc in documents if doc.document_type in ["CONSULTATION", "CONSULTS"]
    ]
    hospital_documents = [
        doc
        for doc in documents
        if doc.document_type in ["DISCHARGE_SUMMARY", "HOSPITAL_RECORDS"]
    ]
    
    # Other documents (not categorized as lab, imaging, consult, or hospital)
    categorized_types = {
        "LAB_REPORT", "LABORATORIES",
        "RADIOLOGY_REPORT", "IMAGING",
        "CONSULTATION", "CONSULTS",
        "DISCHARGE_SUMMARY", "HOSPITAL_RECORDS"
    }
    other_documents = [
        doc for doc in documents 
        if doc.document_type not in categorized_types or doc.document_type is None
    ]

    # Helper function for templates to access current date
    def now():
        app.logger.info("now() function called in patient_detail template")
        current_date = datetime.now().date()
        app.logger.info(f"Current date: {current_date}, type: {type(current_date)}")
        return current_date

    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())

    response = make_response(
        render_template(
            "patient_detail.html",
            patient=patient,
            recent_vitals=recent_vitals,
            all_vitals=all_vitals,
            recent_labs=recent_labs,
            active_conditions=active_conditions,
            past_visits=past_visits,
            screenings=screenings,
            immunizations=immunizations,
            upcoming_visit=upcoming_visit,
            documents=documents,
            cache_timestamp=cache_timestamp,
            lab_documents=lab_documents,
            imaging_documents=imaging_documents,
            consult_documents=consult_documents,
            hospital_documents=hospital_documents,
            other_documents=other_documents,
            past_appointments=past_appointments,
            upcoming_appointments=upcoming_appointments,
            now=now,
        )
    )

    # Add cache control headers to force fresh content
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@safe_db_operation
@log_patient_operation("edit_patient")
def edit_patient(patient_id):
    """Edit patient information"""
    app.logger.info(f"Editing patient with ID: {patient_id}, method: {request.method}")
    patient = Patient.query.get_or_404(patient_id)

    # For GET requests, initialize form with patient data
    form = PatientForm(obj=patient)

    if request.method == "POST":
        # For POST requests, get form data directly from request
        app.logger.debug(f"Form data received: {request.form}")

        # CSRF token is already being validated by the input in the template
        # Extract and process the form data
        try:
            # Check if MRN is being changed and already exists
            new_mrn = request.form.get("mrn")
            if new_mrn != patient.mrn and Patient.query.filter_by(mrn=new_mrn).first():
                flash(
                    "A patient with this Medical Record Number already exists.",
                    "danger",
                )
                return render_template(
                    "patient_form.html",
                    form=form,
                    title="Patient Demographics",
                    patient=patient,
                )

            # Store old values to check what changed
            old_dob = patient.date_of_birth

            # Update patient fields from form data
            patient.first_name = request.form.get("first_name")
            patient.last_name = request.form.get("last_name")

            # Parse and convert date string to date object
            dob_str = request.form.get("date_of_birth")
            if dob_str:
                try:
                    patient.date_of_birth = datetime.strptime(
                        dob_str, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    flash("Invalid date format for Date of Birth.", "danger")
                    return render_template(
                        "patient_form.html",
                        form=form,
                        title="Patient Demographics",
                        patient=patient,
                    )

            patient.sex = request.form.get("sex")
            patient.mrn = new_mrn
            patient.phone = request.form.get("phone")
            patient.email = request.form.get("email")
            patient.address = request.form.get("address")
            patient.insurance = request.form.get("insurance")

            # Force the session to recognize the changes
            db.session.add(patient)
            db.session.flush()

            app.logger.info(
                f"Patient data updated: {patient.first_name} {patient.last_name} (DOB: {patient.date_of_birth})"
            )

            # If date of birth changed, re-evaluate screening needs
            if old_dob != patient.date_of_birth:
                evaluate_screening_needs(patient)

            # Explicitly commit the changes
            db.session.commit()
            app.logger.info(f"Patient {patient.id} successfully saved to database")

            flash("Patient demographics updated successfully.", "success")
            return redirect(url_for("patient_detail", patient_id=patient.id))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating patient: {str(e)}")
            flash(f"Error updating patient: {str(e)}", "danger")

    return render_template(
        "patient_form.html", form=form, title="Patient Demographics", patient=patient
    )


@app.route("/patients/<int:patient_id>/prep_sheet", defaults={"cache_buster": None})
@app.route("/patients/<int:patient_id>/prep_sheet/<int:cache_buster>")
def generate_patient_prep_sheet(patient_id, cache_buster=None):
    """Generate a preparation sheet for the patient"""

    def now():
        return datetime.now()

    patient = Patient.query.get_or_404(patient_id)

    # Get the date of the last visit
    last_visit = (
        Visit.query.filter_by(patient_id=patient_id)
        .order_by(Visit.visit_date.desc())
        .first()
    )
    last_visit_date = last_visit.visit_date if last_visit else None

    # Get data since the last visit or in the last 90 days if no previous visit
    cutoff_date = (
        last_visit_date if last_visit_date else datetime.now() - timedelta(days=90)
    )

    # Get past 3 appointments for the patient
    past_appointments = (
        Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date < datetime.now(),
        )
        .order_by(Appointment.appointment_date.desc())
        .limit(3)
        .all()
    )

    # Get recent data for the prep sheet using enhanced medical data parser
    from medical_data_parser import MedicalDataParser
    
    # Get checklist settings for cutoff dates
    from checklist_routes import get_or_create_settings
    checklist_settings = get_or_create_settings()
    
    # Initialize medical data parser with patient-specific settings
    data_parser = MedicalDataParser(patient_id, checklist_settings)
    filtered_medical_data = data_parser.get_all_filtered_data()
    
    # Extract filtered data for template compatibility
    recent_labs = filtered_medical_data['labs']['data']
    recent_imaging = filtered_medical_data['imaging']['data']
    recent_consults = filtered_medical_data['consults']['data']
    recent_hospital = filtered_medical_data['hospital_visits']['data']
    
    # Get recent vitals (using original cutoff logic for now)
    recent_vitals = (
        Vital.query.filter(Vital.patient_id == patient_id, Vital.date > cutoff_date)
        .order_by(Vital.date.desc())
        .all()
    )

    active_conditions = Condition.query.filter_by(
        patient_id=patient_id, is_active=True
    ).all()

    screenings = (
        Screening.query
        .filter_by(patient_id=patient_id)
        .join(ScreeningType, Screening.screening_type_id == ScreeningType.id)
        .filter(ScreeningType.is_active == True)
        .options(
            db.joinedload(Screening.screening_type),
            db.selectinload(Screening.documents)
        )
        .all()
    )

    # Get immunizations
    immunizations = (
        Immunization.query.filter_by(patient_id=patient_id)
        .order_by(Immunization.administration_date.desc())
        .all()
    )
    
    # Get all patient documents for categorization
    documents = (
        MedicalDocument.query.filter_by(patient_id=patient_id)
        .order_by(MedicalDocument.document_date.desc())
        .all()
    )
    
    # Categorize documents for "other" section (documents not in main categories)
    categorized_types = {
        "LAB_REPORT", "LABORATORIES",
        "RADIOLOGY_REPORT", "IMAGING",
        "CONSULTATION", "CONSULTS", 
        "DISCHARGE_SUMMARY", "HOSPITAL_RECORDS"
    }
    other_documents = [
        doc for doc in documents 
        if doc.document_type not in categorized_types or doc.document_type is None
    ]

    # Get past 3 appointments for the patient
    past_appointments = (
        Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date < datetime.now(),
        )
        .order_by(Appointment.appointment_date.desc())
        .limit(3)
        .all()
    )

    # 🚀 SEAMLESS INTEGRATION: Use automated screening engine for all applicable screening types
    # This automatically includes ALL active screening types without manual intervention
    # Use unified screening engine instead of old automated engine
    from unified_screening_engine import unified_engine
    
    # Get checklist settings for filtering and customization (not gatekeeper)
    from checklist_routes import get_or_create_settings
    checklist_settings = get_or_create_settings()
    
    # Use automated engine to get all applicable screening types for this patient
    # Use unified screening engine for refresh operations
    screening_engine = unified_engine
    # Generate patient screenings using unified engine
    automated_screenings = screening_engine.generate_patient_screenings(patient.id)
    
    # Extract screening type names from automated engine results  
    # DECOUPLED: No filtering by default_items here - unified engine determines eligibility only
    recommended_screenings = [screening['screening_type'] for screening in automated_screenings]
    
    print(f"🔍 Automated screening engine found {len(recommended_screenings)} applicable screenings for {patient.first_name} {patient.last_name}: {recommended_screenings}")
    print(f"📋 Default items filtering is now handled only in prep sheet template, not in parsing logic")
    
    # Fallback if no screenings found (edge case protection)
    if not recommended_screenings:
        # Basic screenings for all patients (only as fallback)
        recommended_screenings = ["Vaccination History", "Lipid Panel", "A1c", "Colonoscopy"]
        
        # Add sex-specific screenings for females
        if patient.sex and patient.sex.lower() == "female":
            recommended_screenings.extend(["Pap Smear", "Mammogram", "DEXA Scan"])

    # Add existing screenings if they're not already included
    for screening in screenings:
        if screening.screening_type not in recommended_screenings:
            recommended_screenings.append(screening.screening_type)

    # Generate a prep sheet summary with decoupled filtering
    prep_sheet_data = generate_prep_sheet(
        patient,
        recent_vitals,
        recent_labs,
        recent_imaging,
        recent_consults,
        recent_hospital,
        active_conditions,
        screenings,
        last_visit_date,
        past_appointments,
    )
    
    # Pass default_items settings to template for prep sheet filtering (decoupled from parsing)
    prep_sheet_filter_items = []
    if checklist_settings.default_items:
        prep_sheet_filter_items = checklist_settings.default_items_list

    # Get enhanced screening recommendations with document relationships using new system
    try:
        # Get existing screenings with document relationships
        patient_screenings = Screening.query.filter_by(patient_id=patient_id).all()
        
        # Create mapping of screening names to document match data for template
        screening_document_matches = {}
        document_screening_data = {
            'screening_recommendations': [],
            'summary': {
                'total_matches': 0,
                'unique_screenings': len(patient_screenings),
                'high_confidence_count': 0,
                'medium_confidence_count': 0,
                'low_confidence_count': 0
            }
        }
        
        for screening in patient_screenings:
            matched_docs = screening.matched_documents
            if matched_docs:
                # For each screening, create entry with document data
                document_screening_data['screening_recommendations'].append({
                    'screening_name': screening.screening_type,
                    'status': screening.status,
                    'last_completed': screening.last_completed,
                    'frequency': screening.frequency,
                    'notes': screening.notes,
                    'matched_documents': matched_docs,
                    'document_count': len(matched_docs)
                })
                
                # Create template mapping for backward compatibility
                if matched_docs:
                    best_doc = matched_docs[0]  # Use first document as "best match"
                    confidence = 0.85  # Default high confidence for automated matches
                    
                    screening_document_matches[screening.screening_type] = {
                        'status_notes': f"Status: {screening.status}",
                        'confidence': confidence,
                        'confidence_percent': int(confidence * 100),
                        'document_name': best_doc.filename,
                        'document_id': best_doc.id,
                        'match_source': 'automated_screening_engine',
                        'recommendation_status': screening.status,
                        'matched_documents': matched_docs,
                        'all_documents': [
                            {
                                'id': doc.id,
                                'filename': doc.filename,
                                'document_name': doc.document_name,
                                'confidence': 0.85  # Default confidence
                            } for doc in matched_docs
                        ]
                    }
                    
                    # Update summary counts
                    document_screening_data['summary']['total_matches'] += len(matched_docs)
                    if confidence >= 0.8:
                        document_screening_data['summary']['high_confidence_count'] += 1
                    elif confidence >= 0.6:
                        document_screening_data['summary']['medium_confidence_count'] += 1
                    else:
                        document_screening_data['summary']['low_confidence_count'] += 1
        
        print(f"Found {len(patient_screenings)} screenings with {document_screening_data['summary']['total_matches']} total document matches")
        
    except Exception as e:
        # Fallback - don't break prep sheet if document matching fails
        print(f"Document matching error: {str(e)}")
        import traceback
        traceback.print_exc()
        document_screening_data = {
            'screening_recommendations': [],
            'summary': {'total_matches': 0, 'unique_screenings': 0}
        }
        screening_document_matches = {}

    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())

    # Get checklist settings for display options (if not already loaded)
    if not "checklist_settings" in locals():
        from checklist_routes import get_or_create_settings

        checklist_settings = get_or_create_settings()

    # Response with cache-control headers to prevent caching
    response = make_response(
        render_template(
            "prep_sheet.html",
            patient=patient,
            prep_sheet=prep_sheet_data,
            recent_vitals=recent_vitals[0] if recent_vitals else None,
            recent_labs=recent_labs,
            recent_imaging=recent_imaging,
            recent_consults=recent_consults,
            recent_hospital=recent_hospital,
            settings=checklist_settings,
            active_conditions=active_conditions,
            screenings=screenings,
            immunizations=immunizations,
            recommended_screenings=recommended_screenings,
            last_visit_date=last_visit_date,
            past_appointments=past_appointments,
            today=datetime.now(),
            cache_timestamp=cache_timestamp,
            checklist_settings=checklist_settings,
            prep_sheet_filter_items=prep_sheet_filter_items,  # Decoupled filtering for prep sheet only
            # Enhanced document matching data
            document_screening_data=document_screening_data,
            screening_document_matches=screening_document_matches,
            # Enhanced medical data with documents and cutoff filtering
            filtered_medical_data=filtered_medical_data,
            # Other documents for miscellaneous section
            other_documents=other_documents,
        )
    )

    # Add cache control headers to force fresh content
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.route("/screening-types", methods=["GET"])
@app.route("/admin/screening-types", methods=["GET"])
def screening_types():
    """Admin interface for managing screening types"""
    screening_types = ScreeningType.query.order_by(ScreeningType.name).all()

    from forms import ScreeningTypeForm

    # Create forms for add and edit modals
    add_form = ScreeningTypeForm()
    edit_form = ScreeningTypeForm()

    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())

    return render_template(
        "screening_types.html",
        title="Screening Types Management",
        screening_types=screening_types,
        add_form=add_form,
        edit_form=edit_form,
        cache_timestamp=cache_timestamp,
    )


@app.route("/screening-types/add", methods=["GET"])
def add_screening_type_form():
    """Display form to add a new screening type"""
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())
    
    # Get existing screening names for autocomplete
    existing_screening_names = [st.name for st in ScreeningType.query.with_entities(ScreeningType.name).distinct().all()]

    return render_template("add_screening_type.html", 
                         cache_timestamp=cache_timestamp,
                         existing_screening_names=existing_screening_names)






@app.route("/screening-types/add", methods=["POST"])
@safe_db_operation
def add_screening_type():
    """Add a new screening type"""
    from forms import ScreeningTypeForm
    from screening_keyword_manager import ScreeningKeywordManager
    import json

    form = ScreeningTypeForm()

    if form.validate_on_submit():
        # Get form data with proper handling
        frequency_number = request.form.get('frequency_number')
        frequency_unit = request.form.get('frequency_unit')
        gender_specific = request.form.get('gender_specific')
        min_age = request.form.get('min_age')
        max_age = request.form.get('max_age')
        is_active = 'is_active' in request.form
        
        screening_type = ScreeningType(
            name=form.name.data,
            description="",  # No longer using description field
            frequency_number=int(frequency_number) if frequency_number else None,
            frequency_unit=frequency_unit if frequency_unit else None,
            gender_specific=gender_specific if gender_specific else None,
            min_age=int(min_age) if min_age else None,
            max_age=int(max_age) if max_age else None,
            is_active=is_active,
            status='active' if is_active else 'inactive',
        )
        
        # Process keyword fields from the form
        import json
        try:
            # Unified keywords (used for both content and filename parsing)
            keywords_data = request.form.get('keywords_json') or request.form.get('keywords')
            if keywords_data:
                keywords = json.loads(keywords_data)
                # Convert to simple list format if needed
                keyword_list = []
                for keyword in keywords:
                    if isinstance(keyword, str) and keyword.strip():
                        keyword_list.append(keyword.strip())
                    elif isinstance(keyword, dict) and keyword.get('keyword'):
                        keyword_list.append(keyword['keyword'].strip())
                
                if keyword_list:
                    screening_type.set_content_keywords(keyword_list)
            
            # Document section as document keywords
            document_section = request.form.get('document_section')
            if document_section:
                # Use document section as document keyword
                screening_type.set_document_keywords([document_section])
            
            # Trigger conditions (existing functionality)
            trigger_conditions_data = request.form.get('trigger_conditions')
            if trigger_conditions_data:
                trigger_conditions = json.loads(trigger_conditions_data)
                screening_type.set_trigger_conditions(trigger_conditions)
                
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Error processing keyword data: {e}")
            # Continue without keywords if there's an error
            pass

        # Handle trigger conditions if provided
        trigger_conditions_data = request.form.get('trigger_conditions')
        print(f"Trigger conditions data received: {trigger_conditions_data}")
        if trigger_conditions_data and trigger_conditions_data.strip():
            try:
                import html
                # Decode HTML entities before parsing JSON more comprehensively
                decoded_data = html.unescape(trigger_conditions_data)
                decoded_data = decoded_data.replace('&quot;', '"').replace('&#x27;', "'").replace('&amp;', '&')
                print(f"Decoded trigger conditions data: {decoded_data}")
                trigger_conditions = json.loads(decoded_data)
                print(f"Parsed trigger conditions: {trigger_conditions}")
                if isinstance(trigger_conditions, list):
                    screening_type.set_trigger_conditions(trigger_conditions)
                    print(f"Set trigger conditions for screening type {screening_type.name}")
            except json.JSONDecodeError as e:
                print(f"Warning: Error processing trigger conditions data: {e}")
                # Continue without trigger conditions if there's an error
                pass
        else:
            # Clear trigger conditions if none provided
            screening_type.set_trigger_conditions([])
            print("Cleared trigger conditions")

        db.session.add(screening_type)
        db.session.commit()
        
        # After commit, ensure trigger conditions are saved
        if trigger_conditions_data and trigger_conditions_data.strip():
            try:
                trigger_conditions = json.loads(trigger_conditions_data)
                if isinstance(trigger_conditions, list):
                    screening_type.set_trigger_conditions(trigger_conditions)
                    db.session.commit()
                    print(f"Re-saved trigger conditions after commit for {screening_type.name}")
            except json.JSONDecodeError:
                pass

        # Handle keywords if provided - check multiple possible field names
        keywords_data = request.form.get('keywords') or request.form.get('keywords_json')
        if keywords_data and keywords_data.strip():
            try:
                import html
                # Fix HTML entity encoding issues
                decoded_keywords = html.unescape(keywords_data)
                decoded_keywords = decoded_keywords.replace('&quot;', '"').replace('&#x27;', "'").replace('&amp;', '&')
                
                keywords = json.loads(decoded_keywords)
                
                # Convert to simple list format for storage
                keyword_list = []
                if isinstance(keywords, list):
                    for keyword in keywords:
                        if isinstance(keyword, str) and keyword.strip():
                            keyword_list.append(keyword.strip())
                        elif isinstance(keyword, dict) and keyword.get('keyword'):
                            keyword_list.append(keyword['keyword'].strip())
                
                # Store keywords directly in the screening type
                if keyword_list:
                    screening_type.set_content_keywords(keyword_list)
                    print(f"Successfully saved {len(keyword_list)} keywords: {keyword_list}")
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing keywords JSON: {str(e)} - Data: '{keywords_data[:100]}...'")
                # Don't fail the entire operation for keyword errors
                pass
            except Exception as e:
                print(f"Error adding keywords: {str(e)}")
                # Don't fail the entire operation for keyword errors
                pass

        # Enhanced admin logging for screening type addition
        from models import AdminLog
        import json

        log_details = {
            "action": "add",
            "data_type": "screening_type",
            "screening_type_name": screening_type.name,
            "description": screening_type.description or "",
            "default_frequency": screening_type.default_frequency or "",
            "gender_specific": screening_type.gender_specific or "All Genders",
            "min_age": (
                screening_type.min_age if screening_type.min_age is not None else "None"
            ),
            "max_age": (
                screening_type.max_age if screening_type.max_age is not None else "None"
            ),
            "is_active": screening_type.is_active,
            "created_date": (
                screening_type.created_at.strftime("%Y-%m-%d")
                if screening_type.created_at
                else str(date.today())
            ),
            "created_time": (
                screening_type.created_at.strftime("%H:%M:%S")
                if screening_type.created_at
                else datetime.now().strftime("%H:%M:%S")
            ),
            "endpoint": "add_screening_type",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            from flask_login import current_user

            user_id = current_user.id if current_user.is_authenticated else None
        except:
            user_id = None

        AdminLog.log_event(
            event_type="data_modification",
            user_id=user_id,
            event_details=json.dumps(log_details),
            request_id=f"screening_type_add_{screening_type.id}",
            ip_address=request.remote_addr or "127.0.0.1",
            user_agent=request.headers.get("User-Agent", "Unknown"),
        )

        flash(
            f'Screening type "{screening_type.name}" has been added successfully.',
            "success",
        )
        
        # ✅ New screening type added - unified engine will handle screening generation automatically
        print(f"✅ New screening type '{screening_type.name}' added - unified engine will handle screening generation")
        logger.info(f"Added new screening type {screening_type.name} - unified engine will generate screenings on demand")
    else:
        for field, errors in form.errors.items():
            flash(f"{form[field].label.text}: {', '.join(errors)}", "danger")

    # Redirect back to screening list with 'types' tab active and timestamp for cache busting
    timestamp = int(time_module.time())
    return redirect(url_for("screening_list", tab="types", _t=timestamp))


@app.route("/screening-types/<int:screening_type_id>/edit", methods=["GET", "POST"])
@safe_db_operation
def edit_screening_type(screening_type_id):
    """Edit an existing screening type"""
    screening_type = ScreeningType.query.get_or_404(screening_type_id)

    from forms import ScreeningTypeForm

    # For GET requests, pre-populate the form with existing data
    if request.method == "GET":
        form = ScreeningTypeForm(obj=screening_type)
        # Pass trigger conditions to template for JavaScript population
        trigger_conditions_json = screening_type.trigger_conditions or '[]'
        timestamp = int(time_module.time())
        return render_template(
            "edit_screening_type.html",
            form=form,
            screening_type=screening_type,
            trigger_conditions_json=trigger_conditions_json,
            cache_timestamp=timestamp,
        )
    else:
        form = ScreeningTypeForm()

    if request.method == "POST" and form.validate_on_submit():
        # ENHANCED: Capture "before" state for selective refresh - ALL FIELDS
        old_state = {
            'name': screening_type.name,
            'frequency_number': screening_type.frequency_number,
            'frequency_unit': screening_type.frequency_unit,
            'gender_specific': screening_type.gender_specific,
            'min_age': screening_type.min_age,
            'max_age': screening_type.max_age,
            'is_active': screening_type.is_active,
            'keywords': screening_type.get_all_keywords(),
            'trigger_conditions': screening_type.get_trigger_conditions(),
            'description': screening_type.description
        }

        # Update the screening type with form data
        screening_type.name = form.name.data
        screening_type.description = ""  # No longer using description field
        screening_type.frequency_number = form.frequency_number.data
        screening_type.frequency_unit = (
            form.frequency_unit.data if form.frequency_unit.data else None
        )
        screening_type.gender_specific = (
            form.gender_specific.data if form.gender_specific.data else None
        )
        screening_type.min_age = form.min_age.data
        screening_type.max_age = form.max_age.data
        # Track status change for reactivation logic
        old_status = screening_type.is_active
        new_status = form.is_active.data
        
        # Capture "after" state
        new_state = {
            'name': screening_type.name,
            'frequency_number': screening_type.frequency_number,
            'frequency_unit': screening_type.frequency_unit,
            'gender_specific': screening_type.gender_specific,
            'min_age': screening_type.min_age,
            'max_age': screening_type.max_age,
            'is_active': screening_type.is_active,
            'keywords': screening_type.get_all_keywords(),
            'trigger_conditions': screening_type.get_trigger_conditions()
        }
        
        # Use variant manager to sync status across all related variants
        from screening_variant_manager import ScreeningVariantManager
        variant_manager = ScreeningVariantManager()
        
        if old_status != new_status:
            # Sync status across all related variants (including exact duplicates)
            success = variant_manager.sync_single_variant_status(screening_type.id, new_status)
            if not success:
                flash(f'Warning: Could not sync status across all variants for "{screening_type.name}"', "warning")
        else:
            # Even if status didn't change, ensure this individual record is set correctly
            screening_type.is_active = new_status
        
        screening_type.status = 'active' if new_status else 'inactive'

        # Process keyword fields from the form (unified approach)
        import json
        try:
            # Unified keywords (used for both content and filename parsing)
            keywords_data = request.form.get('keywords_json') or request.form.get('keywords')
            if keywords_data and keywords_data.strip():
                try:
                    keywords = json.loads(keywords_data)
                    # Convert to simple list format if needed
                    keyword_list = []
                    for keyword in keywords:
                        if isinstance(keyword, str) and keyword.strip():
                            keyword_list.append(keyword.strip())
                        elif isinstance(keyword, dict) and keyword.get('keyword'):
                            keyword_list.append(keyword['keyword'].strip())
                    
                    screening_type.set_content_keywords(keyword_list)
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON in keywords field, skipping: '{keywords_data[:50]}...'")
                    screening_type.set_content_keywords([])
            else:
                screening_type.set_content_keywords([])
            
            # Document section as document keywords
            document_section = request.form.get('document_section')
            if document_section and document_section.strip():
                screening_type.set_document_keywords([document_section])
            else:
                screening_type.set_document_keywords([])
                
        except Exception as e:
            print(f"Warning: Error processing keyword data: {e}")
            # Continue without updating keywords if there's an error

        # Handle trigger conditions if provided
        trigger_conditions_data = request.form.get('trigger_conditions')
        print(f"Edit - Trigger conditions data received: {trigger_conditions_data}")
        if trigger_conditions_data and trigger_conditions_data.strip():
            try:
                import json as json_module
                import html
                # Decode HTML entities before parsing JSON
                decoded_data = html.unescape(trigger_conditions_data)
                print(f"Edit - Decoded trigger conditions data: {decoded_data}")
                trigger_conditions = json_module.loads(decoded_data)
                print(f"Edit - Parsed trigger conditions: {trigger_conditions}")
                if isinstance(trigger_conditions, list):
                    screening_type.set_trigger_conditions(trigger_conditions)
                    print(f"Edit - Set trigger conditions for screening type {screening_type.name}")
            except json_module.JSONDecodeError as e:
                print(f"Edit - Error parsing trigger conditions JSON: {str(e)}")
        else:
            # Clear trigger conditions if none provided
            screening_type.set_trigger_conditions([])
            print("Edit - Cleared trigger conditions")

        # Handle keywords if provided - check multiple possible field names
        keywords_data = request.form.get('keywords') or request.form.get('keywords_json')
        print(f"Keywords data received: {keywords_data}")
        
        if keywords_data and keywords_data.strip():
            try:
                import json as json_module
                import html
                
                # Fix HTML entity encoding issues more comprehensively
                decoded_keywords = html.unescape(keywords_data)
                decoded_keywords = decoded_keywords.replace('&quot;', '"').replace('&#x27;', "'").replace('&amp;', '&')
                print(f"Decoded keywords data: {decoded_keywords}")
                
                keywords = json_module.loads(decoded_keywords)
                print(f"Parsed keywords: {keywords}")
                
                # Convert to simple list format for storage
                keyword_list = []
                if isinstance(keywords, list):
                    for keyword in keywords:
                        if isinstance(keyword, str) and keyword.strip():
                            keyword_list.append(keyword.strip())
                        elif isinstance(keyword, dict) and keyword.get('keyword'):
                            keyword_list.append(keyword['keyword'].strip())
                
                # Store keywords directly in the screening type
                if keyword_list:
                    screening_type.set_content_keywords(keyword_list)
                    print(f"Successfully saved {len(keyword_list)} keywords: {keyword_list}")
                else:
                    screening_type.set_content_keywords([])
                    print("Cleared keywords")
                    
            except json_module.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in keywords field: {e}")
                # Clear keywords if invalid JSON
                screening_type.set_content_keywords([])
            except Exception as e:
                print(f"Error processing keywords: {str(e)}")
                # Clear keywords if error
                screening_type.set_content_keywords([])
        else:
            # Clear keywords if no data provided
            screening_type.set_content_keywords([])
            print("No keywords data provided - cleared existing keywords")

        try:
            # Store original values for change tracking
            original_data = {
                "name": screening_type.name,
                "description": screening_type.description,
                "default_frequency": screening_type.default_frequency,
                "gender_specific": screening_type.gender_specific,
                "min_age": screening_type.min_age,
                "max_age": screening_type.max_age,
                "is_active": screening_type.is_active,
            }

            db.session.commit()

            # Enhanced admin logging for screening type edit
            from models import AdminLog
            import json

            # Track what changed
            form_changes = {}
            if original_data["name"] != screening_type.name:
                form_changes["name"] = (
                    f"{original_data['name']} → {screening_type.name}"
                )
            if original_data["description"] != screening_type.description:
                form_changes["description"] = (
                    f"{original_data['description'] or 'None'} → {screening_type.description or 'None'}"
                )
            if original_data["default_frequency"] != screening_type.default_frequency:
                form_changes["default_frequency"] = (
                    f"{original_data['default_frequency'] or 'None'} → {screening_type.default_frequency or 'None'}"
                )
            if original_data["gender_specific"] != screening_type.gender_specific:
                form_changes["gender_specific"] = (
                    f"{original_data['gender_specific'] or 'All'} → {screening_type.gender_specific or 'All'}"
                )
            if original_data["min_age"] != screening_type.min_age:
                form_changes["min_age"] = (
                    f"{original_data['min_age'] or 'None'} → {screening_type.min_age or 'None'}"
                )
            if original_data["max_age"] != screening_type.max_age:
                form_changes["max_age"] = (
                    f"{original_data['max_age'] or 'None'} → {screening_type.max_age or 'None'}"
                )
            if original_data["is_active"] != screening_type.is_active:
                form_changes["is_active"] = (
                    f"{original_data['is_active']} → {screening_type.is_active}"
                )

            log_details = {
                "action": "edit",
                "data_type": "screening_type",
                "screening_type_id": screening_type.id,
                "screening_type_name": screening_type.name,
                "description": screening_type.description or "",
                "default_frequency": screening_type.default_frequency or "",
                "gender_specific": screening_type.gender_specific or "All Genders",
                "min_age": (
                    screening_type.min_age
                    if screening_type.min_age is not None
                    else "None"
                ),
                "max_age": (
                    screening_type.max_age
                    if screening_type.max_age is not None
                    else "None"
                ),
                "is_active": screening_type.is_active,
                "updated_date": (
                    screening_type.updated_at.strftime("%Y-%m-%d")
                    if screening_type.updated_at
                    else str(date.today())
                ),
                "updated_time": (
                    screening_type.updated_at.strftime("%H:%M:%S")
                    if screening_type.updated_at
                    else datetime.now().strftime("%H:%M:%S")
                ),
                "form_changes": form_changes,
                "endpoint": "edit_screening_type",
                "method": "POST",
                "timestamp": datetime.now().isoformat(),
            }

            try:
                from flask_login import current_user

                user_id = current_user.id if current_user.is_authenticated else None
            except:
                user_id = None

            AdminLog.log_event(
                event_type="data_modification",
                user_id=user_id,
                event_details=json.dumps(log_details),
                request_id=f"screening_type_edit_{screening_type.id}",
                ip_address=request.remote_addr or "127.0.0.1",
                user_agent=request.headers.get("User-Agent", "Unknown"),
            )


            
            # ENHANCED: Use selective refresh manager for intelligent updates
            changes_detected = []
            
            # Capture "after" state for comparison
            new_state = {
                'name': screening_type.name,
                'frequency_number': screening_type.frequency_number,
                'frequency_unit': screening_type.frequency_unit,
                'gender_specific': screening_type.gender_specific,
                'min_age': screening_type.min_age,
                'max_age': screening_type.max_age,
                'is_active': screening_type.is_active,
                'keywords': screening_type.get_all_keywords(),
                'trigger_conditions': screening_type.get_trigger_conditions(),
                'description': screening_type.description
            }
            
            # Detect specific changes for selective refresh
            from selective_screening_refresh_manager import selective_refresh_manager, ChangeType
            
            for field, old_val in old_state.items():
                new_val = new_state.get(field)
                if old_val != new_val:
                    print(f"🔍 Detected change in {field}: {old_val} → {new_val}")
                    
                    # Map field changes to change types
                    if field == 'is_active':
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, ChangeType.ACTIVATION_STATUS, old_val, new_val
                        )
                        changes_detected.append(f"activation status")
                    elif field in ['frequency_number', 'frequency_unit']:
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, ChangeType.FREQUENCY, old_val, new_val
                        )
                        changes_detected.append(f"frequency settings")
                    elif field in ['min_age', 'max_age']:
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, ChangeType.AGE_CRITERIA, old_val, new_val
                        )
                        changes_detected.append(f"age criteria")
                    elif field == 'gender_specific':
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, ChangeType.GENDER_CRITERIA, old_val, new_val
                        )
                        changes_detected.append(f"gender criteria")
                    elif field == 'keywords':
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, ChangeType.KEYWORDS, old_val, new_val
                        )
                        changes_detected.append(f"keywords")
                    elif field == 'trigger_conditions':
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, ChangeType.TRIGGER_CONDITIONS, old_val, new_val
                        )
                        changes_detected.append(f"trigger conditions")
                    elif field == 'name':
                        # Handle name changes with checklist synchronization
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, ChangeType.NAME_CHANGE, old_val, new_val
                        )
                        changes_detected.append(f"name")
                        
                        # Immediately update checklist default items to reflect name change
                        try:
                            from models import ChecklistSettings
                            settings = ChecklistSettings.query.first()
                            if settings and settings.default_items:
                                # Replace old name with new name in default items
                                default_items_list = settings.default_items_list or []
                                if old_val in default_items_list:
                                    # Replace old name with new name
                                    updated_items = [new_val if item == old_val else item for item in default_items_list]
                                    settings.default_items = '\n'.join(updated_items)
                                    db.session.commit()
                                    print(f"✅ Updated checklist default items: {old_val} → {new_val}")
                        except Exception as checklist_error:
                            print(f"⚠️ Failed to update checklist items for name change: {checklist_error}")
            
            # Process selective refresh if changes detected
            if changes_detected:
                try:
                    # Use background processing for better performance
                    from background_screening_processor import background_processor, TaskPriority
                    from screening_cache_manager import screening_cache_manager
                    
                    # Invalidate relevant cache entries
                    screening_cache_manager.invalidate_screening_type(screening_type.id)
                    
                    # Determine if this should be processed immediately or in background
                    if ChangeType.ACTIVATION_STATUS in [change.change_type for change in selective_refresh_manager.change_log[-len(changes_detected):]]:
                        # Activation changes need immediate processing for user feedback
                        stats = selective_refresh_manager.process_selective_refresh()
                        
                        if stats.affected_patients > 0:
                            flash(f'Screening type "{screening_type.name}" updated. {stats.screenings_updated} screenings refreshed for {stats.affected_patients} patients in {stats.processing_time:.1f}s.', "success")
                        else:
                            flash(f'Screening type "{screening_type.name}" updated successfully.', "success")
                    else:
                        # Other changes can be processed in background
                        affected_patients = set()
                        for change in selective_refresh_manager.change_log[-len(changes_detected):]:
                            affected_patients.update(selective_refresh_manager.get_affected_patients(change))
                            
                        if affected_patients:
                            task_id = background_processor.submit_screening_refresh_task(
                                patient_ids=list(affected_patients),
                                screening_type_ids=[screening_type.id],
                                priority=TaskPriority.NORMAL,
                                context={"changes": changes_detected, "screening_type_name": screening_type.name}
                            )
                            flash(f'Screening type "{screening_type.name}" updated. Refreshing {len(affected_patients)} affected patients in background (Task: {task_id[:8]}).', "info")
                        else:
                            flash(f'Screening type "{screening_type.name}" updated successfully.', "success")
                            
                except Exception as refresh_error:
                    print(f"⚠️ Selective refresh error: {refresh_error}")
                    flash(f'Screening type "{screening_type.name}" updated. Changes will take effect on next page refresh.', "warning")
            else:
                # No significant changes detected, just update the record
                flash(f'Screening type "{screening_type.name}" has been updated successfully.', "success")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating screening type: {str(e)}")
            flash(f"Error updating screening type: {str(e)}", "danger")
            timestamp = int(time_module.time())
            return render_template(
                "edit_screening_type.html",
                form=form,
                screening_type=screening_type,
                cache_timestamp=timestamp,
            )

        # Redirect back to screening list with 'types' tab active and timestamp for cache busting
        timestamp = int(time_module.time())
        return redirect(url_for("screening_list", tab="types", t=timestamp))

    # For GET requests or if validation fails, render the form page
    timestamp = int(time_module.time())
    trigger_conditions_json = screening_type.trigger_conditions or '[]'
    return render_template(
        "edit_screening_type.html",
        form=form,
        screening_type=screening_type,
        trigger_conditions_json=trigger_conditions_json,
        cache_timestamp=timestamp,
    )


@app.route("/screening-types/<int:screening_type_id>/delete")
@safe_db_operation
def delete_screening_type(screening_type_id):
    """Delete a screening type"""
    screening_type = ScreeningType.query.get_or_404(screening_type_id)

    # Check if this screening type is used in any patient screenings
    patient_screenings = Screening.query.filter_by(
        screening_type=screening_type.name
    ).count()

    if patient_screenings > 0:
        # Instead of deleting, mark as inactive using variant manager
        from screening_variant_manager import ScreeningVariantManager
        variant_manager = ScreeningVariantManager()
        
        # Sync deactivation across all related variants
        success = variant_manager.sync_single_variant_status(screening_type.id, False)
        if not success:
            # Fallback to direct deactivation if variant sync fails
            screening_type.is_active = False
            db.session.commit()

        # Enhanced admin logging for screening type deactivation
        from models import AdminLog
        import json

        log_details = {
            "action": "deactivate",
            "data_type": "screening_type",
            "screening_type_id": screening_type.id,
            "screening_type_name": screening_type.name,
            "description": screening_type.description or "",
            "default_frequency": screening_type.default_frequency or "",
            "gender_specific": screening_type.gender_specific or "All Genders",
            "min_age": (
                screening_type.min_age if screening_type.min_age is not None else "None"
            ),
            "max_age": (
                screening_type.max_age if screening_type.max_age is not None else "None"
            ),
            "is_active": False,
            "patient_usage_count": patient_screenings,
            "deactivation_reason": f"Used by {patient_screenings} patient(s)",
            "deactivated_date": str(date.today()),
            "deactivated_time": datetime.now().strftime("%H:%M:%S"),
            "endpoint": "delete_screening_type",
            "method": "GET",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            from flask_login import current_user

            user_id = current_user.id if current_user.is_authenticated else None
        except:
            user_id = None

        AdminLog.log_event(
            event_type="data_modification",
            user_id=user_id,
            event_details=json.dumps(log_details),
            request_id=f"screening_type_deactivate_{screening_type.id}",
            ip_address=request.remote_addr or "127.0.0.1",
            user_agent=request.headers.get("User-Agent", "Unknown"),
        )

        flash(
            f'Screening type "{screening_type.name}" has been marked as inactive because it is used by {patient_screenings} patient(s).',
            "warning",
        )
        
        # ✅ EDGE CASE HANDLER: Handle screening type deactivation
        try:
            from automated_edge_case_handler import handle_screening_type_change
            status_result = handle_screening_type_change(screening_type_id, False)
            logger.info(f"Auto-handled screening type deactivation for {screening_type.name}")
        except Exception as e:
            logger.error(f"Auto-refresh failed after screening type deactivation: {e}")
            # Don't fail the deactivation if auto-refresh fails
    else:
        name = screening_type.name
        screening_type_id = screening_type.id

        # Enhanced admin logging for screening type deletion
        from models import AdminLog
        import json

        log_details = {
            "action": "permanent_delete",
            "data_type": "screening_type",
            "screening_type_id": screening_type_id,
            "screening_type_name": name,
            "description": screening_type.description or "",
            "default_frequency": screening_type.default_frequency or "",
            "gender_specific": screening_type.gender_specific or "All Genders",
            "min_age": (
                screening_type.min_age if screening_type.min_age is not None else "None"
            ),
            "max_age": (
                screening_type.max_age if screening_type.max_age is not None else "None"
            ),
            "is_active": screening_type.is_active,
            "patient_usage_count": 0,
            "deleted_date": str(date.today()),
            "deleted_time": datetime.now().strftime("%H:%M:%S"),
            "endpoint": "delete_screening_type",
            "method": "GET",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            from flask_login import current_user

            user_id = current_user.id if current_user.is_authenticated else None
        except:
            user_id = None

        AdminLog.log_event(
            event_type="data_modification",
            user_id=user_id,
            event_details=json.dumps(log_details),
            request_id=f"screening_type_delete_{screening_type_id}",
            ip_address=request.remote_addr or "127.0.0.1",
            user_agent=request.headers.get("User-Agent", "Unknown"),
        )

        # PERMANENT DELETE: Remove screening type from software entirely
        db.session.delete(screening_type)
        db.session.commit()
        flash(f'Screening type "{name}" has been permanently deleted from the software.', "success")

    # Redirect back to screening list with 'types' tab active and timestamp for cache busting
    timestamp = int(time_module.time())
    return redirect(url_for("screening_list", tab="types", _t=timestamp))


@app.route("/patients/<int:patient_id>/download_prep_sheet")
def download_patient_prep_sheet(patient_id):
    """Generate and download a Word document prep sheet for the patient"""
    patient = Patient.query.get_or_404(patient_id)

    # Get the date of the last visit
    last_visit = (
        Visit.query.filter_by(patient_id=patient_id)
        .order_by(Visit.visit_date.desc())
        .first()
    )
    last_visit_date = last_visit.visit_date if last_visit else None

    # Get all conditions regardless of date
    conditions = Condition.query.filter_by(patient_id=patient_id).all()

    # Get all screenings with optimized query
    screenings = (
        Screening.query
        .filter_by(patient_id=patient_id)
        .join(ScreeningType, Screening.screening_type_id == ScreeningType.id)
        .filter(ScreeningType.is_active == True)
        .options(
            db.joinedload(Screening.screening_type),
            db.selectinload(Screening.documents)
        )
        .all()
    )

    # Get the most recent vitals
    vitals = (
        Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).all()
    )

    # Get recent data (last 6 months)
    six_months_ago = datetime.now() - timedelta(days=180)

    labs = (
        LabResult.query.filter(
            LabResult.patient_id == patient_id, LabResult.test_date >= six_months_ago
        )
        .order_by(LabResult.test_date.desc())
        .all()
    )

    imaging = (
        ImagingStudy.query.filter(
            ImagingStudy.patient_id == patient_id,
            ImagingStudy.study_date >= six_months_ago,
        )
        .order_by(ImagingStudy.study_date.desc())
        .all()
    )

    consults = (
        ConsultReport.query.filter(
            ConsultReport.patient_id == patient_id,
            ConsultReport.report_date >= six_months_ago,
        )
        .order_by(ConsultReport.report_date.desc())
        .all()
    )

    hospital = (
        HospitalSummary.query.filter(
            HospitalSummary.patient_id == patient_id,
            HospitalSummary.admission_date >= six_months_ago,
        )
        .order_by(HospitalSummary.admission_date.desc())
        .all()
    )

    # Get immunizations
    immunizations = (
        Immunization.query.filter_by(patient_id=patient_id)
        .order_by(Immunization.administration_date.desc())
        .all()
    )

    # Get past 3 appointments for the patient
    past_appointments = (
        Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date < datetime.now(),
        )
        .order_by(Appointment.appointment_date.desc())
        .limit(3)
        .all()
    )

    # Generate the Word document
    doc_bytes = generate_prep_sheet_doc(
        patient,
        conditions=conditions,
        screenings=screenings,
        vitals=vitals,
        labs=labs,
        imaging=imaging,
        past_appointments=past_appointments,
        consults=consults,
        hospital=hospital,
        immunizations=immunizations,
        last_visit_date=last_visit_date,
    )

    # Create a response with the document
    from io import BytesIO

    doc_io = BytesIO(doc_bytes)

    filename = f"PrepSheet_{patient.last_name}_{patient.first_name}_{datetime.now().strftime('%Y%m%d')}.docx"

    return send_file(
        doc_io,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.route("/patients/<int:patient_id>/save_prep_sheet", methods=["POST"])
@safe_db_operation
def save_prep_sheet(patient_id):
    """Save the current state of a prep sheet as a document in the patient's records"""
    try:
        patient = Patient.query.get_or_404(patient_id)

        # Get the JSON data from the request
        data = request.get_json(silent=True) or {}

        # Create date from the string in format YYYY-MM-DD
        date_str = data.get("date", "")
        try:
            current_date = (
                datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_str
                else datetime.now().date()
            )
        except ValueError:
            current_date = datetime.now().date()

        # Get the checked screening items
        checked_screenings = data.get("checked_screenings", [])

        # Get the detailed screening data (with statuses and notes)
        screening_data = data.get("screening_data", [])

        # Get the date of the last completed appointment
        last_appointment = (
            Appointment.query.filter(
                Appointment.patient_id == patient_id,
                Appointment.status == "completed",
                Appointment.appointment_date < datetime.now(),
            )
            .order_by(Appointment.appointment_date.desc())
            .first()
        )

        last_appointment_date = (
            last_appointment.appointment_date if last_appointment else None
        )

        # Create HTML content for the document
        html_content = f"""
        <div class="prep-sheet-content">
            <h2>Prep Sheet - {current_date.strftime('%m/%d/%Y')}</h2>
            
            <div class="patient-info">
                <h3>Patient Information</h3>
                <p><strong>Name:</strong> {patient.first_name} {patient.last_name}</p>
                <p><strong>DOB:</strong> {patient.date_of_birth.strftime('%m/%d/%Y')}</p>
                <p><strong>MRN:</strong> {patient.mrn}</p>
                <p><strong>Sex:</strong> {patient.sex}</p>
                <p><strong>Last Visit:</strong> {last_appointment_date.strftime('%m/%d/%Y') if last_appointment_date else 'None'}</p>
            </div>
            
            <div class="screening-checklist">
                <h3>Checked Screening Items</h3>
        """

        if screening_data:
            html_content += "<table class='table table-bordered'>"
            html_content += (
                "<thead><tr><th>Screening</th><th>Status & Notes</th></tr></thead>"
            )
            html_content += "<tbody>"

            for item in screening_data:
                screening_name = item.get("item", "")

                # Check for consolidated field first
                consolidated_text = item.get("consolidated", "")

                # Fall back to separate status and notes if no consolidated field
                if not consolidated_text:
                    status = item.get("status", "")
                    note = item.get("notes", "")

                    if status and note:
                        consolidated_text = f"{status} - {note}"
                    else:
                        consolidated_text = status or note

                html_content += f"<tr>"
                html_content += f"<td>{screening_name}</td>"
                html_content += f"<td>{consolidated_text}</td>"
                html_content += f"</tr>"

            html_content += "</tbody></table>"
        elif checked_screenings:
            # Fallback for older format
            html_content += "<ul>"
            for screening in checked_screenings:
                html_content += f"<li>{screening}</li>"
            html_content += "</ul>"
        else:
            html_content += "<p>No screening items were checked.</p>"

        html_content += """
            </div>
        </div>
        """

        # Create metadata JSON
        metadata_dict = {
            "checked_screenings": checked_screenings,
            "creation_date": current_date.strftime("%Y-%m-%d"),
            "screening_data": screening_data,
        }
        metadata_json = json.dumps(metadata_dict)

        # Create a new medical document
        document = MedicalDocument(
            patient_id=patient_id,
            document_type="prep_sheet",
            filename=f'Prep_Sheet_{current_date.strftime("%Y%m%d")}.html',
            document_name=f'Prep Sheet - {current_date.strftime("%m/%d/%Y")}',
            content=html_content,
            is_binary=False,
            mime_type="text/html",
            document_date=datetime.now(),
            source_system="HealthPrep",
            provider="System",
            doc_metadata=metadata_json,
        )

        # Add and commit to database
        db.session.add(document)
        db.session.commit()

        return jsonify(
            {"status": "success", "message": "Prep sheet saved successfully"}
        )

    except Exception as e:
        # Log the error
        logging.error(f"Error saving prep sheet: {str(e)}")

        # Rollback the session
        db.session.rollback()

        # Return error response
        return (
            jsonify(
                {"status": "error", "message": f"Failed to save prep sheet: {str(e)}"}
            ),
            500,
        )


@app.route("/patients/<int:patient_id>/condition", methods=["GET", "POST"])
def add_condition(patient_id):
    """Add a medical condition to a patient"""
    patient = Patient.query.get_or_404(patient_id)
    form = ConditionForm()

    if form.validate_on_submit():
        condition = Condition(
            patient_id=patient_id,
            name=form.name.data,
            code=None,  # No code field in the form, use None
            diagnosed_date=form.diagnosed_date.data,
            is_active=form.is_active.data,
            notes=form.notes.data,
        )

        db.session.add(condition)
        db.session.commit()

        # Re-evaluate screening needs based on new condition
        evaluate_screening_needs(patient)

        flash("Condition added successfully.", "success")
        return redirect(url_for("patient_detail", patient_id=patient_id))

    return render_template("condition_form.html", form=form, patient=patient)


@app.route("/patients/<int:patient_id>/immunization", methods=["GET", "POST"])
def add_immunization(patient_id):
    """Add an immunization record to a patient"""
    patient = Patient.query.get_or_404(patient_id)
    form = ImmunizationForm()

    if form.validate_on_submit():
        immunization = Immunization(
            patient_id=patient_id,
            vaccine_name=form.vaccine_name.data,
            administration_date=form.administration_date.data,
            dose_number=form.dose_number.data,
            manufacturer=form.manufacturer.data,
            lot_number=form.lot_number.data,
            notes=form.notes.data,
        )

        db.session.add(immunization)
        db.session.commit()

        flash("Immunization record added successfully.", "success")
        return redirect(url_for("patient_detail", patient_id=patient_id))

    return render_template("immunization_form.html", form=form, patient=patient)


@app.route("/patients/<int:patient_id>/immunization/<int:immunization_id>/delete")
def delete_immunization(patient_id, immunization_id):
    """Delete a patient's immunization record"""
    patient = Patient.query.get_or_404(patient_id)
    immunization = Immunization.query.get_or_404(immunization_id)

    if immunization.patient_id != patient_id:
        abort(403)  # Forbidden if immunization doesn't belong to this patient

    db.session.delete(immunization)
    db.session.commit()

    flash("Immunization record deleted successfully.", "success")
    return redirect(url_for("patient_detail", patient_id=patient_id))


@app.route("/patients/<int:patient_id>/add_alert", methods=["GET", "POST"])
@log_patient_operation("add")
def add_alert(patient_id):
    """Add an alert for a patient"""
    patient = Patient.query.get_or_404(patient_id)
    form = PatientAlertForm()

    if form.validate_on_submit():
        try:
            alert = PatientAlert(
                patient_id=patient_id,
                alert_type=form.alert_type.data,
                description=form.description.data,
                details=form.details.data,
                start_date=form.start_date.data,
                end_date=None,
                is_active=form.is_active.data,
                severity=form.severity.data,
            )

            db.session.add(alert)
            db.session.commit()

            # Log the successful alert addition with detailed information
            try:
                import uuid
                from models import AdminLog
                from datetime import datetime
                import json

                # Create comprehensive log entry for alert addition
                log_details = {
                    "action": "add",
                    "data_type": "alert",
                    "patient_id": patient_id,
                    "patient_name": patient.full_name,
                    "alert_id": alert.id,
                    "alert_description": form.description.data or "",
                    "alert_details": form.details.data or "",
                    "alert_notes": form.details.data or "",  # Explicit notes field
                    "alert_type": form.alert_type.data or "",
                    "severity": form.severity.data or "",
                    "priority": form.severity.data or "",  # Map severity to priority
                    "alert_start_date": (
                        form.start_date.data.strftime("%Y-%m-%d")
                        if form.start_date.data
                        else ""
                    ),
                    "alert_is_active": form.is_active.data,
                    "alert_time": datetime.now().strftime("%H:%M:%S"),
                    "alert_date": (
                        form.start_date.data.strftime("%Y-%m-%d")
                        if form.start_date.data
                        else ""
                    ),
                    "alert_text": form.description.data or "",  # Legacy compatibility
                    "user_id": session.get("user_id"),
                    "username": session.get("username", "Unknown"),
                    "endpoint": "add_alert",
                    "method": "POST",
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                }

                AdminLog.log_event(
                    event_type="alert_add",
                    user_id=session.get("user_id"),
                    event_details=json.dumps(log_details),
                    request_id=str(uuid.uuid4()),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent", ""),
                )

                db.session.commit()
            except Exception as log_error:
                logger.error(f"Error logging alert addition: {str(log_error)}")
                # Don't let logging errors break the alert creation
                pass

            flash("Alert added successfully.", "success")
            return redirect(url_for("patient_detail", patient_id=patient_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding alert: {str(e)}", "error")

    return render_template(
        "alert_form.html", form=form, patient=patient, title="Add Alert"
    )


@app.route(
    "/patients/<int:patient_id>/edit_alert/<int:alert_id>", methods=["GET", "POST"]
)
@log_patient_operation("edit")
def edit_alert(patient_id, alert_id):
    """Edit a patient alert"""
    patient = Patient.query.get_or_404(patient_id)
    alert = PatientAlert.query.get_or_404(alert_id)

    # Verify the alert belongs to this patient
    if alert.patient_id != patient_id:
        flash("Alert does not belong to this patient.", "error")
        return redirect(url_for("patient_detail", patient_id=patient_id))

    form = PatientAlertForm(obj=alert)

    if form.validate_on_submit():
        try:
            alert.alert_type = form.alert_type.data
            alert.description = form.description.data
            alert.details = form.details.data
            alert.start_date = form.start_date.data
            alert.end_date = None
            alert.is_active = form.is_active.data
            alert.severity = form.severity.data

            db.session.commit()
            flash("Alert updated successfully.", "success")
            return redirect(url_for("patient_detail", patient_id=patient_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating alert: {str(e)}", "error")

    return render_template(
        "alert_form.html", form=form, patient=patient, alert=alert, title="Edit Alert"
    )


@app.route("/patients/<int:patient_id>/delete_alert/<int:alert_id>")
@log_patient_operation("delete")
def delete_alert(patient_id, alert_id):
    """Delete a patient alert"""
    try:
        alert = PatientAlert.query.get_or_404(alert_id)

        # Verify the alert belongs to this patient
        if alert.patient_id != patient_id:
            flash("Alert does not belong to this patient.", "error")
            return redirect(url_for("patient_detail", patient_id=patient_id))

        # Log comprehensive alert details before deletion
        try:
            import uuid
            from models import AdminLog
            from datetime import datetime
            from flask import session
            import json

            # Capture ALL alert fields before deletion including notes - using same field names as add/edit
            deletion_log_details = {
                "action": "delete",
                "data_type": "alert",
                "patient_id": patient_id,
                "patient_name": alert.patient.full_name if alert.patient else "Unknown",
                "alert_id": alert_id,
                # Use consistent field names with add/edit operations
                "alert_description": alert.description or "",
                "alert_details": alert.details or "",
                "alert_notes": alert.details
                or "",  # Explicit notes field for consistency
                "alert_type": alert.alert_type or "",
                "severity": alert.severity or "",
                "priority": alert.severity
                or "",  # Map severity to priority for consistency
                "alert_start_date": (
                    alert.start_date.strftime("%Y-%m-%d") if alert.start_date else ""
                ),
                "alert_is_active": alert.is_active,
                "created_at": (
                    alert.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if alert.created_at
                    else ""
                ),
                "updated_at": (
                    alert.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    if alert.updated_at
                    else ""
                ),
                "deletion_time": datetime.now().strftime("%H:%M:%S"),
                "deletion_date": datetime.now().strftime("%Y-%m-%d"),
                "alert_time": datetime.now().strftime("%H:%M:%S"),
                "user_id": session.get("user_id"),
                "username": session.get("username", "Unknown"),
                "endpoint": "delete_alert",
                "method": "GET",
                "timestamp": datetime.now().isoformat(),
                "success": True,
                # Legacy field mappings for backward compatibility
                "alert_text": alert.description or "",
                "alert_date": (
                    alert.start_date.strftime("%Y-%m-%d") if alert.start_date else ""
                ),
                # Additional deleted prefixed fields for deletion-specific searches
                "deleted_alert_description": alert.description or "",
                "deleted_alert_details": alert.details or "",
                "deleted_alert_notes": alert.details or "",
                "deleted_alert_type": alert.alert_type or "",
                "deleted_severity": alert.severity or "",
                "deleted_priority": alert.severity or "",
                "deleted_start_date": (
                    alert.start_date.strftime("%Y-%m-%d") if alert.start_date else ""
                ),
                "deleted_is_active": alert.is_active,
            }

            AdminLog.log_event(
                event_type="data_modification",
                user_id=session.get("user_id"),
                event_details=json.dumps(deletion_log_details),
                request_id=str(uuid.uuid4()),
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
            )

            db.session.commit()
        except Exception as log_error:
            logger.error(f"Error logging alert deletion: {str(log_error)}")
            # Don't let logging errors break the deletion
            pass

        db.session.delete(alert)
        db.session.commit()
        flash("Alert deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting alert: {str(e)}", "error")

    return redirect(url_for("patient_detail", patient_id=patient_id))


@app.route("/patients/<int:patient_id>/vitals", methods=["GET", "POST"])
def add_vitals(patient_id):
    """Add vital signs for a patient"""
    patient = Patient.query.get_or_404(patient_id)
    form = VitalForm()

    # Populate the height field from the last recorded vital signs
    last_vitals = (
        Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).first()
    )
    if last_vitals and not form.height.data and request.method == "GET":
        # Convert from cm to inches for display
        form.height.data = last_vitals.height / 2.54  # Convert cm to inches

    if form.validate_on_submit():
        # Convert the form data from American units to metric for database storage
        weight_kg = (
            form.weight.data / 2.20462 if form.weight.data else None
        )  # Convert lbs to kg
        height_cm = (
            form.height.data * 2.54 if form.height.data else None
        )  # Convert inches to cm
        temperature_c = (
            (form.temperature.data - 32) * 5 / 9 if form.temperature.data else None
        )  # Convert °F to °C

        # Calculate BMI if weight and height are provided
        bmi = None
        if weight_kg and height_cm:
            # BMI = weight(kg) / (height(m))^2
            height_m = height_cm / 100  # convert cm to m
            bmi = round(weight_kg / (height_m * height_m), 1)

        vital = Vital(
            patient_id=patient_id,
            date=form.date.data,
            weight=weight_kg,
            height=height_cm,
            bmi=bmi,
            temperature=temperature_c,
            blood_pressure_systolic=form.blood_pressure_systolic.data,
            blood_pressure_diastolic=form.blood_pressure_diastolic.data,
            pulse=form.pulse.data,
            respiratory_rate=form.respiratory_rate.data,
            oxygen_saturation=form.oxygen_saturation.data,
        )

        db.session.add(vital)
        db.session.commit()

        flash("Vital signs added successfully.", "success")
        return redirect(url_for("patient_detail", patient_id=patient_id))

    return render_template("vitals_form.html", form=form, patient=patient)


@app.route("/patients/<int:patient_id>/documents")
def patient_documents(patient_id):
    """View a patient's documents"""
    patient = Patient.query.get_or_404(patient_id)

    # Get all documents for this patient
    all_documents = (
        MedicalDocument.query.filter_by(patient_id=patient_id)
        .order_by(MedicalDocument.document_date.desc())
        .all()
    )

    # Group documents by type
    grouped_documents = group_documents_by_type(all_documents)

    # Get recent documents for the sidebar
    recent_documents = all_documents[:5] if all_documents else []

    # Count total documents
    document_count = len(all_documents)

    # Helper function for templates to access current date
    def now():
        app.logger.info("now() function called in patient_documents template")
        current_date = datetime.now().date()
        app.logger.info(f"Current date: {current_date}, type: {type(current_date)}")
        return current_date

    return render_template(
        "patient_documents.html",
        patient=patient,
        documents=grouped_documents,
        recent_documents=recent_documents,
        document_count=document_count,
        now=now,
    )


@app.route("/patients/document/add", methods=["GET", "POST"])
def add_document_unified():
    """Unified document upload for all patients and subsections"""
    form = DocumentUploadForm()
    
    # Populate patient choices
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    form.patient_id.choices = [(p.id, f"{p.full_name} (MRN: {p.mrn})") for p in patients]
    
    # Smart defaults from query parameters
    default_patient_id = request.args.get("patient_id", type=int)
    default_subsection = request.args.get("subsection")
    
    # Set defaults if provided
    if request.method == "GET":
        if default_patient_id:
            form.patient_id.data = default_patient_id
        if default_subsection:
            # Ensure the subsection value is valid for the form choices
            valid_choices = [choice[0] for choice in form.document_type.choices]
            if default_subsection in valid_choices:
                form.document_type.data = default_subsection

    if form.validate_on_submit():
        # Get the selected patient
        patient_id = form.patient_id.data
        patient = Patient.query.get_or_404(patient_id)
        
        # Initialize variables with default values
        content = None
        binary_content = None
        is_binary = False
        mime_type = None
        filename = None
        document_metadata = {}

        # Process the uploaded document if a file is present
        if form.file.data:
            # Get the uploaded file
            file = form.file.data
            filename = file.filename

            # CRITICAL FIX: Ensure file stream is at beginning
            file.seek(0)
            
            # Check if the file is an image or binary type
            mime_type = file.content_type
            is_binary = mime_type and (
                mime_type.startswith("image/") or not mime_type.startswith("text/")
            )

            if is_binary:
                # Store as binary for images and other binary types
                binary_content = file.read()
                print(f"📄 Binary file upload: {filename}, size: {len(binary_content)} bytes, type: {mime_type}")
                
                # VALIDATION: Ensure we actually got data
                if len(binary_content) == 0:
                    flash(f"⚠️ Error: File '{filename}' appears to be empty or could not be read. Please try uploading again.", "error")
                    return render_template(
                        "document_upload.html",
                        form=form,
                        title=title,
                        unified_upload=True,
                    )
                
                content = None
                document_metadata = {"mime_type": mime_type, "filename": filename}
            else:
                # Read file content as text for text-based files
                file_content = file.read()
                try:
                    # Try to decode as UTF-8 text
                    content = file_content.decode("utf-8", errors="replace")
                    binary_content = None
                    # Process document to classify it
                    try:
                        from medical_document_parser import process_document_upload
                        document_metadata = process_document_upload(content, filename)
                    except ImportError:
                        document_metadata = {"filename": filename, "content_preview": content[:200]}
                except:
                    # If decoding fails, treat as binary
                    binary_content = file_content
                    content = None
                    document_metadata = {
                        "mime_type": mime_type or "application/octet-stream",
                        "filename": filename,
                    }
        else:
            # No file uploaded - create a reference-only document entry
            document_metadata = {
                "is_reference_only": True,
                "manual_entry": True,
            }

        try:
            # Create the medical document record
            document = MedicalDocument(
                patient_id=patient_id,
                filename=filename,
                document_name=form.document_name.data,
                document_type=form.document_type.data,
                content=content,
                binary_content=binary_content,
                is_binary=is_binary,
                mime_type=mime_type,
                source_system=form.source_system.data,
                document_date=form.document_date.data,
                doc_metadata=json.dumps(document_metadata) if document_metadata else None,
            )

            db.session.add(document)
            db.session.commit()

            # ENHANCED: Trigger OCR processing if needed
            try:
                from ocr_document_processor import ocr_processor
                
                # Check if document needs OCR and process it
                ocr_result = ocr_processor.process_document_ocr(document.id)
                
                if ocr_result['success'] and ocr_result['ocr_applied']:
                    print(f"🔍 OCR processed document {document.id}: {ocr_result['extracted_text_length']} characters extracted with {ocr_result['confidence_score']}% confidence")
                    
                    # Trigger selective refresh for documents with new OCR content
                    from selective_screening_refresh_manager import selective_refresh_manager, ChangeType
                    
                    # Mark all screening types as potentially affected by new document content
                    from models import ScreeningType
                    active_screening_types = ScreeningType.query.filter_by(is_active=True).all()
                    
                    for screening_type in active_screening_types:
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type.id, 
                            ChangeType.KEYWORDS,  # New document content affects keyword matching
                            "no_ocr_content", 
                            f"new_document_{document.id}_with_ocr",
                            affected_criteria={"patient_id": patient_id}
                        )
                    
                    # Process selective refresh for affected patient
                    refresh_stats = selective_refresh_manager.process_selective_refresh()
                    print(f"📊 OCR triggered selective refresh: {refresh_stats.screenings_updated} screenings updated")
                    
                    # Enhanced success message with OCR info
                    ocr_info = ""
                    if ocr_result['confidence_score'] >= 80:
                        ocr_info = " (High-quality text extraction completed)"
                    elif ocr_result['confidence_score'] >= 60:
                        ocr_info = " (Text extraction completed)"
                    else:
                        ocr_info = " (Text extraction completed with low confidence)"
                        
                elif ocr_result['success'] and not ocr_result['ocr_applied']:
                    print(f"✅ Text-based document uploaded for patient {patient_id} - no OCR needed")
                    ocr_info = ""
                    
                else:
                    print(f"⚠️ OCR processing failed for document {document.id}: {ocr_result.get('error', 'Unknown error')}")
                    ocr_info = " (Note: Text extraction failed - document uploaded successfully)"
                    
            except Exception as ocr_error:
                print(f"⚠️ OCR processing error for document {document.id}: {ocr_error}")
                ocr_info = ""
                # Continue with successful upload even if OCR fails
            
            # Success message and redirect
            subsection_name = dict(form.document_type.choices).get(form.document_type.data, "Document")
            flash(f"{subsection_name} document '{form.document_name.data}' uploaded successfully for {patient.full_name}!{ocr_info}", "success")
            
            print(f"✅ Document uploaded for patient {patient_id} with OCR processing")
            logger.info(f"Document uploaded for patient {patient_id} with OCR integration")
            
            # Redirect to patient detail page
            return redirect(url_for("patient_detail", patient_id=patient_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error uploading document: {str(e)}", "error")
            app.logger.error(f"Document upload error: {str(e)}")

    # Set title and determine if we have defaults
    title = "Upload Medical Document"
    if default_patient_id:
        patient = Patient.query.get(default_patient_id)
        if patient:
            title = f"Upload Document for {patient.full_name}"
    
    return render_template(
        "document_upload.html",
        form=form,
        title=title,
        unified_upload=True,
    )


@app.route("/patients/<int:patient_id>/document/add", methods=["GET", "POST"])
def add_document(patient_id):
    """Add a document for a specific patient (redirects to unified upload)"""
    # Get query parameters to preserve
    subsection = request.args.get("type")
    
    # Build redirect URL with smart defaults
    redirect_params = {"patient_id": patient_id}
    if subsection:
        # Map old type parameter to new subsection format
        type_mapping = {
            "lab": "LABORATORIES",
            "imaging": "IMAGING", 
            "consult": "CONSULTS",
            "hospital": "HOSPITAL_RECORDS",
            "other": "OTHER"
        }
        redirect_params["subsection"] = type_mapping.get(subsection.lower(), "OTHER")
    
    return redirect(url_for("add_document_unified", **redirect_params))


@app.route('/documents/<int:document_id>/process-ocr', methods=['POST'])
@csrf.exempt  # OCR processing is internal and doesn't require CSRF protection
def process_document_ocr_route(document_id):
    """Process document with OCR via AJAX"""
    try:
        logger.info(f"OCR processing request for document {document_id}")
        
        # Validate document exists
        document = MedicalDocument.query.get(document_id)
        if not document:
            return jsonify({
                'success': False,
                'error': f'Document {document_id} not found'
            }), 404
        
        # Use OCR processor directly instead of universal display
        from ocr_document_processor import OCRDocumentProcessor
        
        # Process OCR using force_reprocess parameter through the wrapper function
        from ocr_document_processor import process_document_with_ocr
        ocr_result = process_document_with_ocr(document_id, force_reprocess=True)
        
        if ocr_result['success']:
            # Trigger screening refresh if OCR was applied
            if ocr_result.get('ocr_applied'):
                try:
                    from unified_screening_engine import UnifiedScreeningEngine
                    engine = UnifiedScreeningEngine()
                    
                    # Re-evaluate screenings for the patient
                    screenings_updated = engine.generate_patient_screenings(document.patient_id)
                    
                    logger.info(f"OCR processing triggered screening refresh for patient {document.patient_id}: {len(screenings_updated)} screenings updated")
                    
                except Exception as refresh_error:
                    logger.warning(f"OCR screening refresh failed: {refresh_error}")
            
            return jsonify({
                'success': True,
                'message': f'OCR processing completed successfully',
                'ocr_applied': ocr_result.get('ocr_applied', False),
                'confidence': ocr_result.get('confidence_score'),
                'text_length': ocr_result.get('extracted_text_length', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': ocr_result.get('error', 'OCR processing failed')
            }), 500
            
    except Exception as e:
        logger.error(f"OCR processing error for document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500


@app.route("/documents/<int:document_id>")
def view_document(document_id):
    """View a document with comprehensive error handling and universal display protocol"""
    try:
        # Validate document ID
        if not document_id or document_id <= 0:
            flash("Invalid document ID provided", "error")
            return redirect(url_for('document_repository'))
        
        # Check if document exists
        document = MedicalDocument.query.get(document_id)
        if not document:
            flash(f"Document #{document_id} not found. It may have been deleted.", "error")
            # Get return_to parameter to redirect back appropriately
            return_to = request.args.get("return_to")
            if return_to:
                try:
                    return redirect(return_to)
                except:
                    pass
            return redirect(url_for('document_repository'))
        
        # Validate patient exists
        patient = Patient.query.get(document.patient_id)
        if not patient:
            flash(f"Patient associated with document #{document_id} not found", "error")
            return redirect(url_for('document_repository'))
        
        # Basic access control check
        # TODO: Enhance with role-based permissions
        try:
            # For now, allow access to all logged-in users
            # This can be enhanced with specific permission checks
            pass
        except Exception as access_error:
            flash("You don't have permission to view this document", "error")
            return redirect(url_for('document_repository'))
        
        # Get the return_to parameter (if provided)
        return_to = request.args.get("return_to", None)

        # Get metadata if available
        metadata = {}
        if document.doc_metadata:
            try:
                metadata = json.loads(document.doc_metadata)
            except json.JSONDecodeError as e:
                print(f"Error parsing document metadata for document {document_id}: {e}")
                metadata = {}
            except Exception as e:
                print(f"Unexpected error parsing metadata: {e}")
                metadata = {}

        return render_template(
            "document_view.html",
            document=document,
            patient=patient,
            return_to=return_to,
            metadata=metadata,
        )
        
    except Exception as e:
        print(f"Unexpected error in view_document for ID {document_id}: {e}")
        flash("An error occurred while loading the document", "error")
        return redirect(url_for('document_repository'))


@app.route("/documents/<int:document_id>/image")
def document_image(document_id):
    """Serve a document's binary content as an image"""
    document = MedicalDocument.query.get_or_404(document_id)

    if not document.binary_content:
        abort(404)

    # Determine mime type for the response
    mime_type = document.mime_type or "application/octet-stream"

    # Create a response with the binary content
    response = make_response(document.binary_content)
    response.headers.set("Content-Type", mime_type)
    return response


@app.route("/documents/repository")
def document_repository():
    """Display all documents in the repository with patient information"""
    # Get search query parameter
    search_query = request.args.get("search", "")

    # Get patient filter parameter
    selected_patient_id = request.args.get("patient_id", "")
    if selected_patient_id and selected_patient_id.isdigit():
        selected_patient_id = int(selected_patient_id)
    else:
        selected_patient_id = None

    # Create query with eager loading of patient relationship
    query = MedicalDocument.query.join(Patient).options(
        db.joinedload(MedicalDocument.patient)
    )

    # Apply patient filter if provided
    if selected_patient_id:
        query = query.filter(MedicalDocument.patient_id == selected_patient_id)

    # Apply search filter if provided
    if search_query:
        query = query.filter(
            db.or_(
                MedicalDocument.document_name.ilike(f"%{search_query}%"),
                MedicalDocument.document_type.ilike(f"%{search_query}%"),
                MedicalDocument.source_system.ilike(f"%{search_query}%"),
                Patient.first_name.ilike(f"%{search_query}%"),
                Patient.last_name.ilike(f"%{search_query}%"),
            )
        )

    # Sort by most recent first
    all_documents = query.order_by(MedicalDocument.created_at.desc()).all()

    # Get all patients for the dropdown filter
    all_patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()

    app.logger.info(f"Found {len(all_documents)} documents in repository")

    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())

    # Create response with cache control headers
    response = make_response(
        render_template(
            "document_repository.html",
            all_documents=all_documents,
            all_patients=all_patients,
            selected_patient_id=selected_patient_id,
            search_query=search_query,
            cache_timestamp=cache_timestamp,
        )
    )

    # Add cache control headers to force fresh content
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.route("/documents/<int:document_id>/delete", methods=["POST"])
def delete_document_from_repository(document_id):
    """Delete a single document from repository"""
    try:
        document = MedicalDocument.query.get_or_404(document_id)
        document_name = document.document_name
        
        patient_id = document.patient_id  # Store patient ID before deletion
        
        # Check which screenings will be affected before deletion
        affected_screenings = []
        if hasattr(document, 'screenings') and document.screenings:
            affected_screenings = [(s.id, s.screening_type, s.status) for s in document.screenings]
        
        db.session.delete(document)
        db.session.commit()
        
        # ENHANCED: Trigger selective refresh for document deletion
        try:
            if affected_screenings:
                print(f"🔄 Document deletion affects {len(affected_screenings)} screenings for patient {patient_id}")
                
                # Use selective refresh manager for document deletion impacts
                from selective_screening_refresh_manager import selective_refresh_manager, ChangeType
                
                # Mark affected screening types as needing document relationship recalculation
                affected_types = set()
                for screening_id, screening_type, old_status in affected_screenings:
                    if screening_type:
                        affected_types.add(screening_type)
                
                # Trigger selective refresh for each affected screening type
                for screening_type_name in affected_types:
                    screening_type_obj = ScreeningType.query.filter_by(name=screening_type_name).first()
                    if screening_type_obj:
                        selective_refresh_manager.mark_screening_type_dirty(
                            screening_type_obj.id, 
                            ChangeType.KEYWORDS,  # Document changes affect keyword matching
                            f"document_{document_id}_present", 
                            f"document_{document_id}_deleted",
                            affected_criteria={"patient_id": patient_id}
                        )
                
                # Process selective refresh for affected patients only
                stats = selective_refresh_manager.process_selective_refresh()
                print(f"✅ Selective refresh completed: {stats.screenings_updated} screenings updated for {stats.affected_patients} patients")
            else:
                print(f"✅ Document deleted for patient {patient_id} - no screening relationships affected")
                
        except Exception as refresh_error:
            print(f"⚠️ Document deletion selective refresh error: {refresh_error}")
            # Continue with successful deletion even if refresh fails
        
        logger.info(f"Document deleted for patient {patient_id} with selective refresh handling")
        
        return jsonify({"success": True, "message": f"Document '{document_name}' deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/documents/bulk-delete", methods=["POST"])
def bulk_delete_documents():
    """Delete multiple documents"""
    try:
        data = request.get_json()
        document_ids = data.get('document_ids', [])
        
        if not document_ids:
            return jsonify({"success": False, "error": "No documents selected"}), 400
            
        # Get documents to delete
        documents = MedicalDocument.query.filter(MedicalDocument.id.in_(document_ids)).all()
        
        if not documents:
            return jsonify({"success": False, "error": "No documents found"}), 404
            
        deleted_count = len(documents)
        document_names = [doc.document_name for doc in documents]
        
        # Use the new document deletion handler for bulk deletion
        from document_deletion_handler import document_deletion_handler
        
        total_updated_screenings = 0
        deletion_errors = []
        
        for document in documents:
            deletion_result = document_deletion_handler.handle_document_deletion(document.id)
            if deletion_result.get('success'):
                updated_screenings = deletion_result.get('updated_screenings', [])
                total_updated_screenings += len(updated_screenings)
            else:
                deletion_errors.append(f"Document {document.document_name}: {deletion_result.get('error', 'Unknown error')}")
        
        # Return results
        if deletion_errors:
            return jsonify({
                "success": False, 
                "error": f"Some deletions failed: {'; '.join(deletion_errors)}",
                "partial_success": True,
                "updated_screenings": total_updated_screenings
            }), 207  # Multi-status
        else:
            return jsonify({
                "success": True, 
                "message": f"Deleted {deleted_count} documents successfully",
                "updated_screenings": total_updated_screenings
            })
                
    except Exception as e:
        logger.error(f"Bulk deletion error: {e}")
        return jsonify({"success": False, "error": f"Bulk deletion failed: {str(e)}"}), 500


@app.route("/import-from-url", methods=["POST"])
def import_from_url():
    """Import document content from a URL"""
    url = request.form.get("url")
    patient_id = request.form.get("patient_id")

    if not url or not patient_id:
        return jsonify({"success": False, "error": "Missing URL or patient ID"})

    try:
        # Extract text from the URL
        document_text = extract_document_text_from_url(url)

        if not document_text:
            return jsonify(
                {
                    "success": False,
                    "error": "Could not extract text from the provided URL",
                }
            )

        # Process the document
        document_metadata = process_document_upload(document_text, f"Import from {url}")

        # Create new document
        document = MedicalDocument(
            patient_id=patient_id,
            filename=f"Import from {url}",
            document_type=document_metadata.get(
                "document_type", DocumentType.UNKNOWN.value
            ),
            content=document_text,
            source_system="Web Import",
            document_date=datetime.now(),
            doc_metadata=json.dumps(document_metadata),
        )

        db.session.add(document)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "document_id": document.id,
                "document_type": document.document_type,
                "message": "Document imported successfully!",
            }
        )
    except Exception as e:
        logging.error(f"Error importing from URL: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


from flask import session, redirect, url_for, flash
from forms import LoginForm, RegistrationForm
from models import User
from werkzeug.security import check_password_hash


@app.route("/login", methods=["GET", "POST"])
@validate_login_input
def login():
    """Web-based login using sessions"""
    form = LoginForm()
    if form.validate_on_submit():
        # Find user by username or email
        user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.username.data)
        ).first()

        if user and user.check_password(form.password.data):
            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin
            flash("Login successful!", "success")
            logger.info(f"Successful login for user: {user.username}")

            # Log successful login
            try:
                import uuid
                from models import AdminLog

                request_id = str(uuid.uuid4())

                AdminLog.log_event(
                    event_type="login_success",
                    user_id=user.id,
                    event_details={
                        "username": user.username,
                        "is_admin": user.is_admin,
                        "login_method": "web_form",
                    },
                    request_id=request_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent", ""),
                )
                db.session.commit()
            except Exception as e:
                logger.error(f"Error logging successful login: {str(e)}")
                db.session.rollback()

            # Redirect admin users to admin dashboard
            if user.is_admin:
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("index"))
        else:
            flash("Invalid username or password", "error")
            logger.warning(f"Failed login attempt for username: {form.username.data}")

            # Log failed login attempt with detailed information
            try:
                import uuid
                from models import AdminLog

                request_id = str(uuid.uuid4())

                # Determine the specific reason for failure
                user_exists = User.query.filter(
                    (User.username == form.username.data)
                    | (User.email == form.username.data)
                ).first()

                if user_exists:
                    reason = "invalid_password"
                else:
                    reason = "user_not_found"

                AdminLog.log_event(
                    event_type="login_fail",
                    user_id=None,
                    event_details={
                        "attempted_username": form.username.data,
                        "login_method": "web_form",
                        "reason": reason,
                        "ip_address": request.remote_addr,
                        "user_agent": request.headers.get("User-Agent", ""),
                        "timestamp": datetime.now().isoformat(),
                    },
                    request_id=request_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent", ""),
                )
                db.session.commit()
            except Exception as e:
                logger.error(f"Error logging failed login: {str(e)}")
                db.session.rollback()

    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Web-based registration using sessions"""
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()

        if existing_user:
            flash("Username or email already exists", "error")
        else:
            # Create new user
            new_user = User(
                username=form.username.data, email=form.email.data, is_admin=False
            )
            new_user.set_password(form.password.data)

            db.session.add(new_user)
            db.session.commit()

            # Auto-login the new user
            session["user_id"] = new_user.id
            session["username"] = new_user.username
            session["is_admin"] = new_user.is_admin
            flash("Registration successful!", "success")
            logger.info(f"New user registered and logged in: {new_user.username}")
            return redirect(url_for("index"))

    return render_template("register.html", form=form)


@app.route("/logout")
def logout():
    """Web-based logout that clears the session"""
    username = session.get("username", "Unknown")
    session.clear()
    flash("You have been logged out.", "info")
    logger.info(f"User logged out: {username}")
    return redirect(url_for("index"))


@app.route("/admin")
@app.route("/admin_dashboard")
def admin_dashboard():
    """Admin dashboard with system statistics and logs"""
    # Check if user is logged in and is admin
    if not session.get("user_id") or not session.get("is_admin"):
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("login"))

    # Log admin dashboard access
    try:
        import uuid
        from models import AdminLog

        request_id = str(uuid.uuid4())

        AdminLog.log_event(
            event_type="admin_dashboard_access",
            user_id=session.get("user_id"),
            event_details={
                "action": "admin_dashboard_viewed",
                "username": session.get("username"),
                "timestamp": datetime.now().isoformat(),
            },
            request_id=request_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
        db.session.commit()
    except Exception as e:
        logger.error(f"Error logging admin dashboard access: {str(e)}")
        db.session.rollback()

    # Get system statistics
    total_patients = Patient.query.count()
    todays_appointments = Appointment.query.filter(
        func.date(Appointment.appointment_date) == func.date(datetime.now())
    ).count()

    # Get overdue screenings
    today = datetime.now().date()
    overdue_screenings = Screening.query.filter(Screening.due_date < today).count()

    # Get total appointments
    total_appointments = Appointment.query.count()

    # Get total documents
    total_documents = MedicalDocument.query.count()

    # Get total users
    from models import User

    total_users = User.query.count()

    # Get recent login failures from admin logs
    recent_login_failures = 0

    # Get paginated admin logs with comprehensive logging data
    page = request.args.get("page", 1, type=int)
    per_page = 20  # Number of logs per page

    recent_admin_logs = []
    admin_logs_pagination = None
    try:
        from models import AdminLog

        # Get comprehensive admin logs including all user activities
        admin_logs_pagination = AdminLog.query.order_by(
            AdminLog.timestamp.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        recent_admin_logs = admin_logs_pagination.items

        # Count recent login failures (last 24 hours)
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        recent_login_failures = AdminLog.query.filter(
            AdminLog.event_type == "login_fail",
            AdminLog.timestamp >= twenty_four_hours_ago,
        ).count()

        # Also include appointment edits and other user activities in the count
        recent_user_activities = AdminLog.query.filter(
            AdminLog.timestamp >= twenty_four_hours_ago
        ).count()

        print(
            f"Admin Dashboard: Found {len(recent_admin_logs)} recent logs, {recent_login_failures} login failures, {recent_user_activities} total activities in last 24h"
        )

    except Exception as e:
        logger.warning(f"Could not fetch admin logs: {str(e)}")
        recent_login_failures = 0

    # Get recent patients
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()

    # Get recent appointments
    recent_appointments = (
        Appointment.query.order_by(Appointment.appointment_date.desc()).limit(5).all()
    )

    # Get recent documents
    recent_documents = (
        MedicalDocument.query.order_by(MedicalDocument.created_at.desc()).limit(5).all()
    )

    # Get all users for user management section
    all_users = User.query.order_by(User.username).all()

    # Count admin users for the safeguard logic
    admin_count = User.query.filter_by(is_admin=True).count()

    # Create database statistics object
    db_stats = {
        "patients": total_patients,
        "appointments": total_appointments,
        "documents": total_documents,
        "users": total_users,
        "screenings": Screening.query.count(),
        "admin_logs": len(recent_admin_logs),
    }

    # Debug logging to see what we're passing to template
    print(f"Admin Dashboard Template Data:")
    print(f"- Total patients: {total_patients}")
    print(f"- Recent admin logs count: {len(recent_admin_logs)}")
    print(f"- Recent login failures: {recent_login_failures}")
    if recent_admin_logs:
        print(
            f"- Sample recent log: {recent_admin_logs[0].event_type} at {recent_admin_logs[0].timestamp}"
        )

    return render_template(
        "admin_dashboard.html",
        total_patients=total_patients,
        todays_appointments=todays_appointments,
        overdue_screenings=overdue_screenings,
        total_appointments=total_appointments,
        total_documents=total_documents,
        total_users=total_users,
        recent_login_failures=recent_login_failures,
        recent_admin_logs=recent_admin_logs,
        admin_logs_pagination=admin_logs_pagination,
        recent_patients=recent_patients,
        recent_appointments=recent_appointments,
        recent_documents=recent_documents,
        all_users=all_users,
        admin_count=admin_count,
        db_stats=db_stats,
        format_event_details=format_event_details,
    )


# Error handlers
@app.route("/admin/cleanup-orphaned-documents", methods=["POST"])
def cleanup_orphaned_documents():
    """Admin utility to clean up orphaned document relationships"""
    # Check if user is logged in and is admin
    if not session.get("user_id") or not session.get("is_admin"):
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("login"))
        
    try:
        from automated_screening_routes import cleanup_orphaned_screening_documents
        cleaned_count = cleanup_orphaned_screening_documents()
        
        if cleaned_count > 0:
            flash(f"Successfully cleaned up {cleaned_count} orphaned document relationships", "success")
        else:
            flash("No orphaned document relationships found", "info")
            
    except Exception as e:
        flash(f"Error during cleanup: {str(e)}", "error")
        print(f"Admin cleanup error: {e}")
    
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/validate-document-relationships", methods=["GET"])
def validate_document_relationships():
    """Admin utility to validate document relationships across all screenings"""
    # Check if user is logged in and is admin
    if not session.get("user_id") or not session.get("is_admin"):
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("login"))
        
    try:
        validation_results = []
        total_screenings = 0
        total_valid_documents = 0
        total_invalid_relationships = 0
        
        all_screenings = Screening.query.all()
        total_screenings = len(all_screenings)
        
        for screening in all_screenings:
            # Get document count before validation
            raw_doc_count = screening.documents.count()
            
            # Get valid documents after validation
            valid_documents = screening.get_valid_documents_with_access_check()
            valid_doc_count = len(valid_documents)
            
            total_valid_documents += valid_doc_count
            invalid_count = raw_doc_count - valid_doc_count
            total_invalid_relationships += invalid_count
            
            if invalid_count > 0 or valid_doc_count > 0:
                validation_results.append({
                    'screening_id': screening.id,
                    'screening_type': screening.screening_type,
                    'patient_name': f"{screening.patient.first_name} {screening.patient.last_name}",
                    'raw_documents': raw_doc_count,
                    'valid_documents': valid_doc_count,
                    'invalid_relationships': invalid_count,
                    'status': screening.status
                })
        
        summary = {
            'total_screenings': total_screenings,
            'total_valid_documents': total_valid_documents,
            'total_invalid_relationships': total_invalid_relationships,
            'validation_results': validation_results
        }
        
        return render_template('admin_document_validation.html', **summary)
        
    except Exception as e:
        flash(f"Error during validation: {str(e)}", "error")
        print(f"Document validation error: {e}")
        return redirect(url_for('admin_dashboard'))

@app.route("/admin/users/<int:user_id>/delete", methods=["GET", "POST"])
@safe_db_operation
def delete_user(user_id):
    """Delete a user account with admin safeguard"""
    print(f"Delete user request received for user ID: {user_id}")
    print(f"Request method: {request.method}")
    print(f"Current user: {session.get('username')} (ID: {session.get('user_id')})")
    print(f"Is admin: {session.get('is_admin')}")

    # Check if user is logged in and is admin
    if not session.get("user_id") or not session.get("is_admin"):
        print("Access denied - insufficient privileges")
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("login"))

    try:
        user_to_delete = User.query.get_or_404(user_id)
        print(
            f"Found user to delete: {user_to_delete.username} (Admin: {user_to_delete.is_admin})"
        )

        # Get current admin count
        admin_count = User.query.filter_by(is_admin=True).count()
        print(f"Current admin count: {admin_count}")

        # Prevent deletion if this is the last admin user
        if user_to_delete.is_admin and admin_count <= 1:
            print("Deletion blocked - would remove last admin user")
            flash(
                "Cannot delete the last admin user. At least one admin must remain.",
                "danger",
            )
            return redirect(url_for("admin_dashboard"))

        # Store user info for confirmation message
        username = user_to_delete.username

        # Delete associated admin logs (set user_id to NULL instead of deleting logs)
        from models import AdminLog

        AdminLog.query.filter_by(user_id=user_id).update({"user_id": None})

        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        print(f"Successfully deleted user: {username}")

        flash(f'User "{username}" has been deleted successfully.', "success")

        # Log the admin action
        try:
            import uuid

            request_id = str(uuid.uuid4())

            AdminLog.log_event(
                event_type="admin_action",
                user_id=session.get("user_id"),
                event_details={
                    "action": "user_deleted",
                    "deleted_user": username,
                    "deleted_user_id": user_id,
                    "admin_user": session.get("username"),
                },
                request_id=request_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
            )
            db.session.commit()
            print(f"Admin action logged for user deletion: {username}")
        except Exception as e:
            logger.error(f"Error logging user deletion: {str(e)}")
            # Don't let logging errors break the main function
            pass

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        flash(f"Error deleting user: {str(e)}", "danger")

    return redirect(url_for("admin_dashboard"))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.route("/screenings")
def screening_list():
    """High-performance screening list with optimized database queries and caching"""

    # Import datetime at the function level to avoid naming conflicts
    from datetime import datetime as dt_module
    
    # Define now() function to use in templates for date comparisons
    def now():
        return dt_module.now()

    # Define today at the start to ensure it's always available
    today = dt_module.now().date()

    # Get the tab parameter (screenings or types)
    tab = request.args.get("tab", "screenings")
    
    # Performance optimization: Use intelligent caching for expensive queries
    from intelligent_cache_manager import get_cache_manager
    cache_manager = get_cache_manager()

    # Get the search query parameter
    search_query = request.args.get("search", "")
    
    # Log screening list access with search parameters
    if search_query or tab != "screenings":
        from models import AdminLog
        import json
        
        log_details = {
            "action": "access",
            "data_type": "screening_list",
            "tab": tab,
            "search_query": search_query,
            "has_search": bool(search_query),
            "endpoint": "screening_list",
            "method": "GET",
            "timestamp": datetime.now().isoformat(),
        }
        
        try:
            from flask_login import current_user
            user_id = current_user.id if current_user.is_authenticated else None
        except:
            user_id = None
            
        # Generate shorter request ID to fit database constraint (36 chars max)
        import uuid
        request_id = str(uuid.uuid4())[:32]  # Use first 32 chars of UUID
        
        AdminLog.log_event(
            event_type="data_access",
            user_id=user_id,
            event_details=json.dumps(log_details),
            request_id=request_id,
            ip_address=request.remote_addr or "127.0.0.1",
            user_agent=request.headers.get("User-Agent", "Unknown"),
        )

    # Import the checklist settings model and helper function
    from models import ChecklistSettings, Patient, Screening, ScreeningType, MedicalDocument
    
    # Get or create checklist settings for the checklist tab
    def get_or_create_settings():
        """Get or create checklist settings"""
        settings = ChecklistSettings.query.first()
        if not settings:
            settings = ChecklistSettings()
            db.session.add(settings)
            db.session.commit()
        return settings

    # Get settings for all tabs (needed for confidence thresholds)
    settings = get_or_create_settings()
    
    # Variables for checklist tab
    active_screening_types = []
    if tab == "checklist":
        # Debug: Check what settings we're sending to template
        print(f"=== CHECKLIST TAB DEBUG ===")
        print(f"Settings object: {settings}")
        print(f"Status options list (property): {settings.status_options_list}")
        print(f"Default items list: {settings.default_items_list}")
        print(f"=== END DEBUG ===")
        # Get active screening types instead of default_items_list
        # Get active screening types using cache
        try:
            from intelligent_cache_manager import get_cache_manager
            cache_mgr = get_cache_manager()
            active_screening_types_data = cache_mgr.cache_screening_types(active_only=True)
            
            # Convert cached data back to model-like objects for template compatibility
            class ScreeningTypeProxy:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            
            active_screening_types = [ScreeningTypeProxy(st_data) for st_data in active_screening_types_data]
            
        except Exception as e:
            print(f"Cache error for active screening types, falling back to database: {e}")
            active_screening_types = ScreeningType.query.filter_by(is_active=True).order_by(ScreeningType.name).all()

    # Create forms for screening type management
    from forms import ScreeningTypeForm

    add_form = ScreeningTypeForm()
    edit_form = ScreeningTypeForm()

    # If we're on the screening types tab
    screening_types = []
    if tab == "types":
        # Get all screening types
        screening_types_query = ScreeningType.query.order_by(ScreeningType.name)

        screening_types = screening_types_query.all()

    # Check if this is a refresh request (can be triggered from any tab)
    refresh_requested = request.args.get('regenerate') == 'true'
    selective_refresh_requested = request.args.get('selective') == 'true'
    
    if refresh_requested:
        try:
            # TIMEOUT-SAFE SMART REFRESH: Prevents worker crashes and timeouts
            from timeout_safe_refresh import timeout_safe_refresh
            
            success_count, total_patients, error_message = timeout_safe_refresh.safe_smart_refresh()
            
            if error_message:
                flash(f"Smart refresh partially completed: updated {success_count} patients. {error_message}", "warning")
            else:
                flash(f"Smart refresh completed successfully: updated screenings for {success_count} of {total_patients} patients", "success")
            
            # Redirect back to remove the regenerate parameter from URL while preserving search
            redirect_params = {'tab': tab}
            if search_query:
                redirect_params['search'] = search_query
            return redirect(url_for('screening_list', **redirect_params))
            
        except Exception as e:
            app.logger.error(f"Error in timeout-safe refresh: {e}")
            import traceback
            traceback.print_exc()
            flash("Smart refresh system error. Please try again.", "danger")

    
    # For the screenings tab, load existing screenings from database
    screenings = []
    cutoff_info = {}
    total_screenings_before_cutoff = 0
    screenings_hidden_by_cutoff = 0
    
    if tab == "screenings":
        # ✅ USE ENHANCED SCREENING ENGINE WITH DOCUMENT PRIORITIZATION
        print("🚀 Using enhanced screening engine for /screenings page")
        from unified_screening_engine import unified_engine
        
        # Get all patients and generate screenings using unified engine
        all_patients = Patient.query.all()
        all_generated_screenings = []
        
        for patient in all_patients:
            try:
                patient_screenings = unified_engine.generate_patient_screenings(patient.id)
                for screening_data in patient_screenings:
                    # Convert to Screening-like object for compatibility
                    class ScreeningProxy:
                        def __init__(self, data, patient):
                            self.patient_id = patient.id
                            self.patient = patient
                            self.screening_type = data['screening_type']
                            self.status = data['status']
                            self.due_date = data.get('due_date')
                            self.last_completed = data.get('last_completed')
                            # APPLY ENHANCED SCREENING ENGINE: Use prioritized documents instead of all matches
                            all_docs = data.get('matched_documents', [])
                            prioritized_docs = data.get('prioritized_documents', all_docs)  # Use prioritized if available
                            self.documents = prioritized_docs  # Store prioritized documents for display
                            self.notes = f"Enhanced engine - {len(prioritized_docs)}/{len(all_docs)} docs shown"
                            self.id = f"unified_{patient.id}_{data['screening_type']}"
                        
                        def get_valid_documents_with_access_check(self, user=None):
                            """Get documents with access permission validation - Template compatibility method"""
                            try:
                                # Return the prioritized documents stored during initialization
                                # These have already been filtered for relevancy by the enhanced engine
                                return self.documents if self.documents else []
                            except Exception as e:
                                print(f"Error in ScreeningProxy.get_valid_documents_with_access_check: {e}")
                                return []
                        
                        @property
                        def matched_documents(self):
                            """Property for template compatibility"""
                            return self.documents if self.documents else []
                        
                        @property 
                        def document_count(self):
                            """Property for template compatibility"""
                            return len(self.documents) if self.documents else 0
                        
                        def get_document_confidence(self, document_id):
                            """Get confidence score for a specific document - Template compatibility method"""
                            try:
                                # Since these are prioritized documents from enhanced engine, 
                                # they already have high relevance confidence
                                if self.documents:
                                    for doc in self.documents:
                                        if hasattr(doc, 'id') and doc.id == document_id:
                                            # Return high confidence for prioritized documents
                                            return 0.9
                                return 0.8  # Default confidence for matched documents
                            except:
                                return 0.8
                        
                        @property
                        def frequency(self):
                            """Get screening frequency from screening type configuration - Sources from /screenings?tab=types"""
                            try:
                                # Get the actual ScreeningType from database to access frequency configuration
                                from models import ScreeningType
                                screening_type_obj = ScreeningType.query.filter_by(name=self.screening_type).first()
                                
                                if screening_type_obj and screening_type_obj.frequency_number and screening_type_obj.frequency_unit:
                                    # Format frequency display: "1 year", "6 months", etc.
                                    unit = screening_type_obj.frequency_unit.lower()
                                    # Handle pluralization properly
                                    if screening_type_obj.frequency_number == 1:
                                        # Singular: remove 's' if present (e.g., "years" -> "year")
                                        if unit.endswith('s'):
                                            unit = unit[:-1]
                                    elif not unit.endswith('s'):
                                        # Plural: add 's' if not already plural
                                        unit = unit + 's'
                                    return f"{screening_type_obj.frequency_number} {unit}"
                                return "Not specified"
                            except Exception as e:
                                print(f"Error getting frequency for {self.screening_type}: {e}")
                                return "Not specified"
                    
                    all_generated_screenings.append(ScreeningProxy(screening_data, patient))
            except Exception as patient_error:
                print(f"Error generating screenings for patient {patient.id}: {patient_error}")
                continue
        
        print(f"✅ Generated {len(all_generated_screenings)} screenings using enhanced engine")
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        status_filter = request.args.get('status', '')
        screening_type_filter = request.args.get('screening_type', '')
        
        # Apply filters to generated screenings
        screenings_filtered = all_generated_screenings
        
        if status_filter:
            screenings_filtered = [s for s in screenings_filtered if s.status == status_filter]
            
        if screening_type_filter:
            # Check if this is a consolidated screening type - if so, show all variants
            from screening_variant_manager import variant_manager
            variants = variant_manager.find_screening_variants(screening_type_filter)
            
            if variants and len(variants) > 1:
                # This is a consolidated type with multiple variants - show all variants
                variant_names = [v.name for v in variants]
                screenings_filtered = [s for s in screenings_filtered if s.screening_type in variant_names]
            else:
                # Regular single screening type filtering
                screenings_filtered = [s for s in screenings_filtered if s.screening_type == screening_type_filter]

        # Apply search filter if provided
        if search_query:
            if ' ' in search_query:
                # Exact patient name match for dropdown selection
                screenings_filtered = [s for s in screenings_filtered 
                                    if f"{s.patient.first_name} {s.patient.last_name}" == search_query]
            else:
                # Fallback to partial matching for screening types and patient names
                screenings_filtered = [s for s in screenings_filtered 
                                    if (search_query.lower() in s.patient.first_name.lower() or
                                        search_query.lower() in s.patient.last_name.lower() or
                                        search_query.lower() in s.screening_type.lower())]

        # Sort screenings by priority
        screenings_filtered.sort(key=lambda s: (
            0 if s.status == "Due" else
            1 if s.status == "Due Soon" else
            2 if s.status == "Incomplete" else 3,
            s.patient.last_name,
            s.patient.first_name
        ))
        
        # Apply pagination
        total_count = len(screenings_filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        screenings = screenings_filtered[start_idx:end_idx]
        
        # Create pagination info for template
        pagination_info = {
            'current_page': page,
            'total_pages': (total_count + page_size - 1) // page_size,
            'total_count': total_count,
            'page_size': page_size,
            'has_prev': page > 1,
            'has_next': end_idx < total_count,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if end_idx < total_count else None
        }
        
        filters_info = {}
        metadata = {'source': 'enhanced_screening_engine'}
        
        # Get screening statistics for enhanced mode
        stats = {'by_status': {}, 'by_type': {}, 'total_count': total_count}
        
        # Set variables for template compatibility
        total_screenings_before_cutoff = total_count
        screenings_hidden_by_cutoff = 0
        
        # Import cutoff utilities for legacy compatibility
        from cutoff_utils import get_cutoff_date_for_patient
        
        # Get cutoff settings info for display (screening-specific cutoffs removed)
        settings = get_or_create_settings()
        cutoff_info = {
            'general_cutoff_months': settings.cutoff_months,
            'labs_cutoff_months': settings.labs_cutoff_months,
            'imaging_cutoff_months': settings.imaging_cutoff_months,
            'consults_cutoff_months': settings.consults_cutoff_months,
            'hospital_cutoff_months': settings.hospital_cutoff_months,
            'has_cutoffs': (settings.cutoff_months and settings.cutoff_months > 0) or 
                          any([settings.labs_cutoff_months, settings.imaging_cutoff_months, 
                               settings.consults_cutoff_months, settings.hospital_cutoff_months]),
        }
    else:
        # For other tabs, don't process screenings
        screenings = []

    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())

    # Get all active screening types for the Add Recommendation modal - use cache
    try:
        from intelligent_cache_manager import get_cache_manager
        cache_mgr = get_cache_manager()
        all_screening_types_data = cache_mgr.cache_screening_types(active_only=True)
        
        # Convert cached data back to model-like objects for template compatibility
        class ScreeningTypeProxy:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        all_screening_types = [ScreeningTypeProxy(st_data) for st_data in all_screening_types_data]
        
    except Exception as e:
        print(f"Cache error for all screening types, falling back to database: {e}")
        # ✅ Filter only active screening types using direct query
        all_screening_types = ScreeningType.query.filter_by(is_active=True).order_by(ScreeningType.name).all()

    # Get all patients for the Add Recommendation modal
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()

    # Get filter options for screenings tab
    distinct_statuses = []
    if tab == "screenings":
        # Get distinct statuses for filter dropdown - ONLY FROM ACTIVE SCREENING TYPES
        distinct_statuses = [row[0] for row in db.session.query(Screening.status).distinct()\
                            .join(ScreeningType, Screening.screening_type == ScreeningType.name)\
                            .filter(ScreeningType.is_active == True).all() if row[0]]

    # Import variant manager for template
    from screening_variant_manager import variant_manager
    
    # Process screening types for consolidated display in filter dropdown
    consolidated_screening_types = []
    if tab == "screenings":
        processed_base_names = set()
        for screening_type in all_screening_types:
            base_name = variant_manager.extract_base_name(screening_type.name)
            if base_name not in processed_base_names:
                processed_base_names.add(base_name)
                
                # Find all variants for this base name
                variants = variant_manager.find_screening_variants(base_name)
                active_variants = [v for v in variants if hasattr(v, 'is_active') and v.is_active]
                
                if active_variants:
                    # Create consolidated entry
                    consolidated_entry = type('ConsolidatedScreeningType', (), {
                        'name': base_name,
                        'is_consolidated': len(active_variants) > 1,
                        'variants': active_variants
                    })()
                    consolidated_screening_types.append(consolidated_entry)
    
    try:
        return render_template(
            "screening_list.html",
            screenings=screenings,
            screening_types=screening_types,
            all_screening_types=consolidated_screening_types if tab == "screenings" else all_screening_types,
            add_form=add_form,
            edit_form=edit_form,
            search_query=search_query,
            active_tab=tab,
            cache_timestamp=cache_timestamp,
            now=now,
            today=today,
            patients=patients,
            settings=settings,
            active_screening_types=active_screening_types,
            distinct_statuses=distinct_statuses,
            status_filter=request.args.get('status', ''),
            screening_type_filter=request.args.get('screening_type', ''),
            cutoff_info=cutoff_info,
            total_screenings_before_cutoff=total_screenings_before_cutoff,
            screenings_hidden_by_cutoff=screenings_hidden_by_cutoff,
            admin_override=request.args.get('show_all') == 'true' and session.get('is_admin', False),
            variant_manager=variant_manager,  # Add missing variant_manager
            # ✅ PERFORMANCE OPTIMIZATION DATA FOR SCREENINGS TAB
            pagination=locals().get('pagination_info', {}),
            filters=locals().get('filters_info', {}),
            metadata=locals().get('metadata', {}),
            stats=locals().get('stats', {}),
            # URL parameters for maintaining state  
            current_page=int(request.args.get('page', 1)),
            page_size=int(request.args.get('page_size', 25)),
            # Template utility functions
            min=min,  # Add min function for template
            max=max,  # Add max function for template
        )
    except Exception as e:
        print(f"Error rendering screening_list.html: {str(e)}")
        # Add more detailed error information to help debug
        import traceback

        traceback.print_exc()
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for("index"))


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


@app.route("/debug/appointments", methods=["GET"])
def debug_appointments():
    """Debug endpoint to inspect appointments"""
    try:
        # Create an HTML response with proper formatting
        response_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Appointments Debugging</title>
            <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
            <style>
                body { padding: 20px; }
                pre { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
                .success { color: green; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Appointments Debug Page</h1>
                <h2>Current Appointments</h2>
        """

        # Fetch all appointments
        all_appointments = Appointment.query.all()
        appointment_count = len(all_appointments)

        response_html += f"<p>Total appointments in database: <strong>{appointment_count}</strong></p>"

        # Get dates of appointments
        dates = {}
        for appt in all_appointments:
            date_key = appt.appointment_date.strftime('%Y-%m-%d')
            if date_key not in dates:
                dates[date_key] = 0
            dates[date_key] += 1
            
        response_html += "</div></body></html>"
        return response_html
        
    except Exception as e:
        return f"Error: {str(e)}"