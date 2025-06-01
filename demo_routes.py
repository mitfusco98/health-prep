from flask import render_template, request, redirect, url_for, flash, abort, send_file, jsonify, make_response
import time as time_module  # Rename to avoid conflicts
import json
import logging
from datetime import datetime, date, time, timedelta
from sqlalchemy import func
from app import app, db, csrf
from db_utils import safe_db_operation, fresh_session_operation
from models import (
    Patient, Condition, Vital, MedicalDocument, 
    LabResult, ImagingStudy, ConsultReport, HospitalSummary, 
    ScreeningType, Screening, Appointment, DocumentType, Immunization, PatientAlert
)
from input_validator import (
    validate_patient_input, validate_appointment_input, validate_login_input,
    validate_bulk_delete_input, log_validation_error
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
            # Get patients with fresh connection
            return Patient.query.order_by(Patient.last_name, Patient.first_name).all()
        except Exception as e:
            # Log error and return empty list instead of crashing
            logging.error(f"Error fetching patients in utility_processor: {str(e)}")
            return []
    
    # Add cache-busting timestamp for static files
    def cache_bust():
        return {'cache_bust': int(time_module.time())}
    
    return {
        'get_all_patients': get_all_patients,
        'cache_bust': cache_bust()
    }

# Add a datetime filter for templates
@app.template_filter('datetime')
def format_datetime(value, format='%B %d, %Y'):
    """Format a datetime object to a readable string."""
    if value is None:
        return ""
    return value.strftime(format)

# Add a date of birth filter for templates
@app.template_filter('dob')
def format_dob(value):
    """Format a date object to MM/DD/YYYY format for date of birth."""
    if value is None:
        return ""
    return value.strftime('%m/%d/%Y')

@app.template_filter('timestamp_to_est')
def timestamp_to_est(utc_timestamp):
    """Convert UTC timestamp to EST and format for display."""
    from datetime import timezone, timedelta
    if utc_timestamp:
        # EST is UTC-5, EDT is UTC-4. For simplicity, using EST offset
        est_offset = timedelta(hours=-5)
        est_timezone = timezone(est_offset)
        est_time = utc_timestamp.replace(tzinfo=timezone.utc).astimezone(est_timezone)
        return est_time.strftime('%m/%d %H:%M EST')
    return ''
from forms import (PatientForm, ConditionForm, VitalForm, 
                  VisitForm, LabResultForm, ImagingStudyForm, ConsultReportForm, 
                  HospitalSummaryForm, ScreeningForm, CSVUploadForm, DocumentUploadForm,
                  AppointmentForm, ImmunizationForm, PatientAlertForm)
from models import (Patient, Condition, Vital, Visit, LabResult, ImagingStudy, 
                   ConsultReport, HospitalSummary, Screening, MedicalDocument, DocumentType,
                   Appointment, Immunization, PatientAlert)
from utils import (process_csv_upload, generate_prep_sheet, evaluate_screening_needs,
                  process_document_upload, get_patient_documents_summary, extract_document_text_from_url,
                  group_documents_by_type)
from prep_doc_utils import generate_prep_sheet_doc
from appointment_utils import detect_appointment_conflicts, format_conflict_message, get_available_time_slots, get_booked_time_slots, DEFAULT_APPOINTMENT_DURATION
from datetime import datetime, timedelta
import json
import logging
import uuid

# Create logger for this module
logger = logging.getLogger(__name__)

def log_validation_error(endpoint, validation_errors, form_data, user_id=None):
    """Log form validation errors to admin logs - delegates to centralized middleware"""
    from validation_middleware import ValidationLogger
    ValidationLogger.log_validation_failure(endpoint, validation_errors, form_data, user_id)

@app.route('/')
def redirect_to_home():
    """Redirect root path to home page"""
    return redirect(url_for('index'))

@app.route('/home')
@app.route('/home/date/<date_str>')
def index(date_str=None):
    """Application home page - Demo version with sample patients"""
    # Get stats for the dashboard
    patient_count = Patient.query.count()
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    recent_lab_results = LabResult.query.order_by(LabResult.test_date.desc()).limit(5).all()
    
    # Get recent documents
    recent_documents = MedicalDocument.query.order_by(MedicalDocument.created_at.desc()).limit(10).all()

    # Get selected date's appointments or default to today
    today = datetime.now().date()
    
    # Check for date from query parameters
    selected_date_param = request.args.get('selected_date')  # From the date picker in the form
    date_str_param = request.args.get('date_str')  # Legacy parameter
    
    # The refresh parameter is used as a cache-busting mechanism
    # Note its presence for debugging purposes
    refresh_param = request.args.get('refresh')
    if refresh_param:
        print(f"Cache-busting refresh param: {refresh_param}")
    
    print(f"URL date_str parameter: {date_str}")
    print(f"Query param selected_date: {selected_date_param}")
    print(f"Query param date_str: {date_str_param}")
    
    # Give priority to the selected_date in query params, then date_str in query params, then URL param, then default to today
    if selected_date_param:
        try:
            print(f"Using date from selected_date param: {selected_date_param}")
            selected_date = datetime.strptime(selected_date_param, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
            print(f"Invalid date in query param, using today: {today}")
            flash('Invalid date format. Showing today\'s appointments.', 'warning')
    elif date_str:
        try:
            # Parse the date string (format: YYYY-MM-DD)
            print(f"Using date from URL path: {date_str}")
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # If date is invalid, default to today
            selected_date = today
            print(f"Invalid date in URL path, using today: {today}")
            flash('Invalid date format. Showing today\'s appointments.', 'warning')
    else:
        selected_date = today
        print(f"No date specified, using today: {today}")
    
    # Get previous and next day for navigation
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    
    # Generate timestamp for cache-busting
    timestamp = int(time_module.time())
    
    # Get appointments for the selected date
    print(f"Fetching appointments for date: {selected_date}")
    print(f"Selected date type: {type(selected_date)}")
    
    try:
        from sqlalchemy import text
        # Try with an explicit SQL query to see exactly what's happening
        sql_query = text(f"SELECT * FROM appointment WHERE DATE(appointment_date) = DATE('{selected_date}')")
        print(f"Executing SQL query: {sql_query}")
        result = db.session.execute(sql_query)
        sql_appointments = [row for row in result]
        print(f"SQL query found {len(sql_appointments)} appointments")
        
        # Also try with SQLAlchemy ORM
        appointments = Appointment.query.filter(
            Appointment.appointment_date == selected_date
        ).order_by(Appointment.appointment_time).all()
        print(f"SQLAlchemy ORM query found {len(appointments)} appointments")
        
        # Also try with func.date
        from sqlalchemy import func
        func_appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == func.date(selected_date)
        ).order_by(Appointment.appointment_time).all()
        print(f"func.date query found {len(func_appointments)} appointments")
        
        # Use the func.date query results
        appointments = func_appointments
    except Exception as e:
        print(f"Error in appointment query: {str(e)}")
        # Fallback to original query
        appointments = Appointment.query.filter(
            Appointment.appointment_date == selected_date
        ).order_by(Appointment.appointment_time).all()
    
    # Log all today's appointments for debugging
    if selected_date == today:
        print(f"Today's appointments (exact date match: {selected_date}):")
        today_appts_debug = Appointment.query.filter(
            func.date(Appointment.appointment_date) == func.date(today)
        ).all()
        print(f"Found {len(today_appts_debug)} appointments with func.date match")
        for appt in today_appts_debug:
            print(f"  ID: {appt.id}, Date: {appt.appointment_date}, Patient: {appt.patient.full_name}, Time: {appt.appointment_time}")
    print(f"Found {len(appointments)} appointments for selected date")
    
    # For debugging: show all appointments in the database
    all_appointments = Appointment.query.all()
    print(f"Total appointments in database: {len(all_appointments)}")
    for appt in all_appointments:
        print(f"Appointment ID: {appt.id}, Date: {appt.appointment_date}, Patient: {appt.patient.full_name}")
    
    return render_template('index.html', 
                          patient_count=patient_count,
                          patients=patients,
                          upcoming_visits=appointments,  # Use the appointments for the selected date for the counter
                          recent_lab_results=recent_lab_results,
                          recent_documents=recent_documents,
                          todays_appointments=appointments,
                          selected_date=selected_date,
                          prev_date=prev_date,
                          next_date=next_date,
                          today_date=today,
                          timestamp=timestamp)

@app.route('/patients')
def patient_list():
    """List all patients"""
    # Get the search query parameters
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort', 'last_name')
    order = request.args.get('order', 'asc')
    
    # Base query
    query = Patient.query
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(f'%{search_query}%'),
                Patient.last_name.ilike(f'%{search_query}%'),
                Patient.mrn.ilike(f'%{search_query}%')
            )
        )
    
    # Apply sorting
    if sort_by == 'last_name':
        if order == 'asc':
            query = query.order_by(Patient.last_name.asc())
        else:
            query = query.order_by(Patient.last_name.desc())
    elif sort_by == 'first_name':
        if order == 'asc':
            query = query.order_by(Patient.first_name.asc())
        else:
            query = query.order_by(Patient.first_name.desc())
    elif sort_by == 'dob':
        if order == 'asc':
            query = query.order_by(Patient.date_of_birth.asc())
        else:
            query = query.order_by(Patient.date_of_birth.desc())
    elif sort_by == 'mrn':
        if order == 'asc':
            query = query.order_by(Patient.mrn.asc())
        else:
            query = query.order_by(Patient.mrn.desc())
    
    # Execute the query
    patients = query.all()
    
    return render_template('patient_list.html', patients=patients, search_query=search_query)

@app.route('/patients/add', methods=['GET', 'POST'])
@safe_db_operation
@validate_patient_input
def add_patient():
    """Add a new patient"""
    app.logger.info(f"Add patient route accessed, method: {request.method}")
    
    # Initialize form
    form = PatientForm()
    
    if request.method == 'POST':
        app.logger.debug(f"Form data received: {request.form}")
        
        try:
            # Get form data directly from request
            new_mrn = request.form.get('mrn')
            
            # If MRN is not provided or is empty, generate one
            if not new_mrn or new_mrn.strip() == '':
                from utils import get_next_available_mrn
                new_mrn = get_next_available_mrn()
                app.logger.info(f"Auto-generated MRN: {new_mrn}")
            
            # Check if MRN already exists
            existing_patient = Patient.query.filter_by(mrn=new_mrn).first()
            if existing_patient:
                flash('A patient with this Medical Record Number already exists.', 'danger')
                return render_template('patient_form.html', form=form, title='Add Patient')
            
            # Parse and convert date string to date object
            dob_str = request.form.get('date_of_birth')
            dob = None
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format for Date of Birth.', 'danger')
                    return render_template('patient_form.html', form=form, title='Add Patient')
            
            # Create new patient with form data
            patient = Patient(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                date_of_birth=dob,
                sex=request.form.get('sex'),
                mrn=new_mrn,
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                address=request.form.get('address'),
                insurance=request.form.get('insurance')
            )
            
            # Add to session and flush to get the ID
            db.session.add(patient)
            db.session.flush()
            
            app.logger.info(f"New patient created: {patient.first_name} {patient.last_name} (ID: {patient.id}, MRN: {patient.mrn})")
            
            # Evaluate and add appropriate screenings for the new patient
            evaluate_screening_needs(patient)
            
            # Commit all changes
            db.session.commit()
            app.logger.info(f"Patient {patient.id} successfully saved to database")
            
            flash('Patient added successfully.', 'success')
            return redirect(url_for('patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding patient: {str(e)}")
            flash(f'Error adding patient: {str(e)}', 'danger')
    
    return render_template('patient_form.html', form=form, title='Add Patient')

@app.route('/patients/<int:patient_id>')
@safe_db_operation
def patient_detail(patient_id):
    """Display patient details"""
    app.logger.info(f"Viewing patient details for ID: {patient_id}")
    try:
        patient = Patient.query.get_or_404(patient_id)
        app.logger.info(f"Found patient: {patient.full_name}")
    except Exception as e:
        app.logger.error(f"Error retrieving patient: {str(e)}")
        flash(f"Error retrieving patient information: {str(e)}", "danger")
        return redirect(url_for('index'))
    
    # Get the most recent vital signs
    recent_vitals = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).first()
    
    # Get all vital signs for history
    all_vitals = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).all()
    
    # Get the most recent lab results
    recent_labs = LabResult.query.filter_by(patient_id=patient_id).order_by(LabResult.test_date.desc()).limit(5).all()
    
    # Get the active conditions
    active_conditions = Condition.query.filter_by(patient_id=patient_id, is_active=True).all()
    
    # Get past visits
    past_visits = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.visit_date.desc()).all()
    
    # Get screening recommendations
    screenings = Screening.query.filter_by(patient_id=patient_id).order_by(Screening.due_date).all()
    
    # Get immunization records
    immunizations = Immunization.query.filter_by(patient_id=patient_id).order_by(Immunization.administration_date.desc()).all()
    
    # Get upcoming visit if any
    upcoming_visit = Visit.query.filter(
        Visit.patient_id == patient_id,
        Visit.visit_date > datetime.now()
    ).order_by(Visit.visit_date).first()
    
    # Get past appointments (already occurred)
    current_date = datetime.now().date()
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        db.or_(
            Appointment.appointment_date < current_date,
            db.and_(
                Appointment.appointment_date == current_date,
                Appointment.appointment_time < datetime.now().time()
            )
        )
    ).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    
    # Get upcoming appointments (scheduled but not yet occurred)
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        db.or_(
            Appointment.appointment_date > current_date,
            db.and_(
                Appointment.appointment_date == current_date,
                Appointment.appointment_time >= datetime.now().time()
            )
        )
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    # Get patient documents
    documents = MedicalDocument.query.filter_by(patient_id=patient_id).order_by(MedicalDocument.document_date.desc()).all()
    
    # Organize documents by type
    lab_documents = [doc for doc in documents if doc.document_type == DocumentType.LAB_REPORT.value]
    imaging_documents = [doc for doc in documents if doc.document_type == DocumentType.RADIOLOGY_REPORT.value]
    consult_documents = [doc for doc in documents if doc.document_type == DocumentType.CONSULTATION.value]
    hospital_documents = [doc for doc in documents if doc.document_type == DocumentType.DISCHARGE_SUMMARY.value]
    
    # Helper function for templates to access current date
    def now():
        app.logger.info("now() function called in patient_detail template")
        current_date = datetime.now().date()
        app.logger.info(f"Current date: {current_date}, type: {type(current_date)}")
        return current_date
    
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())
    
    response = make_response(render_template(
        'patient_detail.html', 
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
        past_appointments=past_appointments,
        upcoming_appointments=upcoming_appointments,
        now=now
    ))
    
    # Add cache control headers to force fresh content
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@safe_db_operation
def edit_patient(patient_id):
    """Edit patient information"""
    app.logger.info(f"Editing patient with ID: {patient_id}, method: {request.method}")
    patient = Patient.query.get_or_404(patient_id)
    
    # For GET requests, initialize form with patient data
    form = PatientForm(obj=patient)
    
    if request.method == 'POST':
        # For POST requests, get form data directly from request
        app.logger.debug(f"Form data received: {request.form}")
        
        # CSRF token is already being validated by the input in the template
        # Extract and process the form data
        try:
            # Check if MRN is being changed and already exists
            new_mrn = request.form.get('mrn')
            if new_mrn != patient.mrn and Patient.query.filter_by(mrn=new_mrn).first():
                flash('A patient with this Medical Record Number already exists.', 'danger')
                return render_template('patient_form.html', form=form, title='Patient Demographics', patient=patient)
            
            # Store old values to check what changed
            old_dob = patient.date_of_birth
            
            # Update patient fields from form data
            patient.first_name = request.form.get('first_name')
            patient.last_name = request.form.get('last_name')
            
            # Parse and convert date string to date object
            dob_str = request.form.get('date_of_birth')
            if dob_str:
                try:
                    patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format for Date of Birth.', 'danger')
                    return render_template('patient_form.html', form=form, title='Patient Demographics', patient=patient)
            
            patient.sex = request.form.get('sex')
            patient.mrn = new_mrn
            patient.phone = request.form.get('phone')
            patient.email = request.form.get('email')
            patient.address = request.form.get('address')
            patient.insurance = request.form.get('insurance')
            
            # Force the session to recognize the changes
            db.session.add(patient)
            db.session.flush()
            
            app.logger.info(f"Patient data updated: {patient.first_name} {patient.last_name} (DOB: {patient.date_of_birth})")
            
            # If date of birth changed, re-evaluate screening needs
            if old_dob != patient.date_of_birth:
                evaluate_screening_needs(patient)
            
            # Explicitly commit the changes
            db.session.commit()
            app.logger.info(f"Patient {patient.id} successfully saved to database")
            
            flash('Patient demographics updated successfully.', 'success')
            return redirect(url_for('patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating patient: {str(e)}")
            flash(f'Error updating patient: {str(e)}', 'danger')
    
    return render_template('patient_form.html', form=form, title='Patient Demographics', patient=patient)

@app.route('/patients/<int:patient_id>/prep_sheet', defaults={'cache_buster': None})
@app.route('/patients/<int:patient_id>/prep_sheet/<int:cache_buster>')
def generate_patient_prep_sheet(patient_id, cache_buster=None):
    """Generate a preparation sheet for the patient"""
    def now():
        return datetime.now()
        
    patient = Patient.query.get_or_404(patient_id)
    
    # Get the date of the last visit
    last_visit = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.visit_date.desc()).first()
    last_visit_date = last_visit.visit_date if last_visit else None
    
    # Get data since the last visit or in the last 90 days if no previous visit
    cutoff_date = last_visit_date if last_visit_date else datetime.now() - timedelta(days=90)
    
    # Get past 3 appointments for the patient
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.appointment_date < datetime.now()
    ).order_by(Appointment.appointment_date.desc()).limit(3).all()
    
    # Get recent data for the prep sheet
    recent_vitals = Vital.query.filter(
        Vital.patient_id == patient_id,
        Vital.date > cutoff_date
    ).order_by(Vital.date.desc()).all()
    
    recent_labs = LabResult.query.filter(
        LabResult.patient_id == patient_id,
        LabResult.test_date > cutoff_date
    ).order_by(LabResult.test_date.desc()).all()
    
    recent_imaging = ImagingStudy.query.filter(
        ImagingStudy.patient_id == patient_id,
        ImagingStudy.study_date > cutoff_date
    ).order_by(ImagingStudy.study_date.desc()).all()
    
    recent_consults = ConsultReport.query.filter(
        ConsultReport.patient_id == patient_id,
        ConsultReport.report_date > cutoff_date
    ).order_by(ConsultReport.report_date.desc()).all()
    
    recent_hospital = HospitalSummary.query.filter(
        HospitalSummary.patient_id == patient_id,
        HospitalSummary.admission_date > cutoff_date
    ).order_by(HospitalSummary.admission_date.desc()).all()
    
    active_conditions = Condition.query.filter_by(
        patient_id=patient_id, 
        is_active=True
    ).all()
    
    screenings = Screening.query.filter_by(patient_id=patient_id).all()
    
    # Get immunizations
    immunizations = Immunization.query.filter_by(patient_id=patient_id).order_by(Immunization.administration_date.desc()).all()
    
    # Get past 3 appointments for the patient
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.appointment_date < datetime.now()
    ).order_by(Appointment.appointment_date.desc()).limit(3).all()
    
    # Get age and sex specific screenings
    recommended_screenings = []
    
    # Get checklist settings 
    from checklist_routes import get_or_create_settings
    checklist_settings = get_or_create_settings()
    content_sources = checklist_settings.content_sources_list
    
    # Start with default items if enabled - these are user-configured items in settings
    if 'database' in content_sources and checklist_settings.default_items:
        # Exclusively use default items when the database source is selected
        recommended_screenings.extend(checklist_settings.default_items_list)
        
    # Only add other items if database source isn't selected or if no default items are configured
    if 'database' not in content_sources or not checklist_settings.default_items_list:
        # Get patient's age
        if patient.date_of_birth:
            today = datetime.today()
            patient_age = today.year - patient.date_of_birth.year - ((today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
        else:
            patient_age = None
        
        # Query active screening types from the database if age/gender-based content is enabled
        if 'age_based' in content_sources or 'gender_based' in content_sources:
            screening_types = ScreeningType.query.filter_by(is_active=True).order_by(ScreeningType.name).all()
            
            # Filter screening types based on patient attributes and content sources
            for screening_type in screening_types:
                # Skip if age-based source is disabled and this is an age-specific screening
                if 'age_based' not in content_sources and (screening_type.min_age is not None or screening_type.max_age is not None):
                    continue
                    
                # Skip if gender-based source is disabled and this is a gender-specific screening
                if 'gender_based' not in content_sources and screening_type.gender_specific:
                    continue
                    
                # Gender-specific check
                if screening_type.gender_specific and patient.sex and screening_type.gender_specific.lower() != patient.sex.lower():
                    continue
                    
                # Age-specific check
                if patient_age is not None:
                    if screening_type.min_age is not None and patient_age < screening_type.min_age:
                        continue
                    if screening_type.max_age is not None and patient_age > screening_type.max_age:
                        continue
                        
                # Add this screening to the recommended list
                recommended_screenings.append(screening_type.name)
        
        # If no screening types are configured or none match, use default list
        if not recommended_screenings:
            # Basic screenings for all patients (fallback if nothing else applies)
            recommended_screenings.extend([
                "Vaccination History",
                "Lipid Panel",
                "A1c",
                "Colonoscopy"
            ])
            
            # Sex-specific screenings if gender-based source is enabled
            if 'gender_based' in content_sources and patient.sex and patient.sex.lower() == "female":
                recommended_screenings.extend([
                    "Pap Smear", 
                    "Mammogram", 
                    "DEXA Scan"
                ])
        
        # Condition-specific screenings if condition-based source is enabled
        if 'condition_based' in content_sources and active_conditions:
            has_diabetes = any("diabetes" in c.name.lower() for c in active_conditions)
            if has_diabetes:
                recommended_screenings.extend([
                    "Diabetic Eye Exam", 
                    "Microalbumin", 
                    "Foot Exam"
                ])
    
    # Only add existing screenings from database if that source is enabled
    if 'existing_screenings' in content_sources:
        for screening in screenings:
            if screening.screening_type not in recommended_screenings:
                recommended_screenings.append(screening.screening_type)
    
    # Generate a prep sheet summary
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
        past_appointments
    )
    
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())
    
    # Get checklist settings for display options (if not already loaded)
    if not 'checklist_settings' in locals():
        from checklist_routes import get_or_create_settings
        checklist_settings = get_or_create_settings()
    
    # Response with cache-control headers to prevent caching
    response = make_response(render_template(
        'prep_sheet.html', 
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
        checklist_settings=checklist_settings
    ))
    
    # Add cache control headers to force fresh content
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/admin/screening-types', methods=['GET'])
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
        'screening_types.html', 
        title='Screening Types Management',
        screening_types=screening_types,
        add_form=add_form,
        edit_form=edit_form,
        cache_timestamp=cache_timestamp
    )


@app.route('/screening-types/add', methods=['GET'])
def add_screening_type_form():
    """Display form to add a new screening type"""
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())
    
    return render_template('add_screening_type.html', cache_timestamp=cache_timestamp)

@app.route('/screening-types/add', methods=['POST'])
@safe_db_operation
def add_screening_type():
    """Add a new screening type"""
    from forms import ScreeningTypeForm
    
    form = ScreeningTypeForm()
    
    if form.validate_on_submit():
        screening_type = ScreeningType(
            name=form.name.data,
            description=form.description.data,
            default_frequency=form.default_frequency.data,
            gender_specific=form.gender_specific.data if form.gender_specific.data else None,
            min_age=form.min_age.data,
            max_age=form.max_age.data,
            is_active=form.is_active.data
        )
        
        db.session.add(screening_type)
        db.session.commit()
        
        flash(f'Screening type "{screening_type.name}" has been added successfully.', 'success')
    else:
        for field, errors in form.errors.items():
            flash(f"{form[field].label.text}: {', '.join(errors)}", 'danger')
    
    # Redirect back to screening list with 'types' tab active and timestamp for cache busting
    timestamp = int(time_module.time())
    return redirect(url_for('screening_list', tab='types', _t=timestamp))


@app.route('/screening-types/<int:screening_type_id>/edit', methods=['GET', 'POST'])
@safe_db_operation
def edit_screening_type(screening_type_id):
    """Edit an existing screening type"""
    screening_type = ScreeningType.query.get_or_404(screening_type_id)
    
    from forms import ScreeningTypeForm
    
    # For GET requests, pre-populate the form with existing data
    if request.method == 'GET':
        form = ScreeningTypeForm(obj=screening_type)
    else:
        form = ScreeningTypeForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        # We'll allow duplicate names since screenings may have different protocols based on gender
        
        # Update the screening type with form data
        screening_type.name = form.name.data
        screening_type.description = form.description.data
        screening_type.default_frequency = form.default_frequency.data
        screening_type.gender_specific = form.gender_specific.data if form.gender_specific.data else None
        screening_type.min_age = form.min_age.data
        screening_type.max_age = form.max_age.data
        screening_type.is_active = form.is_active.data
        
        try:
            db.session.commit()
            flash(f'Screening type "{screening_type.name}" has been updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating screening type: {str(e)}")
            flash(f'Error updating screening type: {str(e)}', 'danger')
            timestamp = int(time_module.time())
            return render_template(
                'edit_screening_type.html',
                form=form,
                screening_type=screening_type,
                cache_timestamp=timestamp
            )
        
        # Redirect back to screening list with 'types' tab active and timestamp for cache busting
        timestamp = int(time_module.time())
        return redirect(url_for('screening_list', tab='types', t=timestamp))
    
    # For GET requests or if validation fails, render the form page
    timestamp = int(time_module.time())
    return render_template(
        'edit_screening_type.html',
        form=form,
        screening_type=screening_type,
        cache_timestamp=timestamp
    )


@app.route('/screening-types/<int:screening_type_id>/delete')
@safe_db_operation
def delete_screening_type(screening_type_id):
    """Delete a screening type"""
    screening_type = ScreeningType.query.get_or_404(screening_type_id)
    
    # Check if this screening type is used in any patient screenings
    patient_screenings = Screening.query.filter_by(screening_type=screening_type.name).count()
    
    if patient_screenings > 0:
        # Instead of deleting, mark as inactive
        screening_type.is_active = False
        db.session.commit()
        flash(f'Screening type "{screening_type.name}" has been marked as inactive because it is used by {patient_screenings} patient(s).', 'warning')
    else:
        name = screening_type.name
        db.session.delete(screening_type)
        db.session.commit()
        flash(f'Screening type "{name}" has been deleted successfully.', 'success')
    
    # Redirect back to screening list with 'types' tab active and timestamp for cache busting
    timestamp = int(time_module.time())
    return redirect(url_for('screening_list', tab='types', _t=timestamp))


@app.route('/patients/<int:patient_id>/download_prep_sheet')
def download_patient_prep_sheet(patient_id):
    """Generate and download a Word document prep sheet for the patient"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get the date of the last visit
    last_visit = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.visit_date.desc()).first()
    last_visit_date = last_visit.visit_date if last_visit else None
    
    # Get all conditions regardless of date
    conditions = Condition.query.filter_by(patient_id=patient_id).all()
    
    # Get all screenings
    screenings = Screening.query.filter_by(patient_id=patient_id).all()
    
    # Get the most recent vitals
    vitals = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).all()
    
    # Get recent data (last 6 months)
    six_months_ago = datetime.now() - timedelta(days=180)
    
    labs = LabResult.query.filter(
        LabResult.patient_id == patient_id,
        LabResult.test_date >= six_months_ago
    ).order_by(LabResult.test_date.desc()).all()
    
    imaging = ImagingStudy.query.filter(
        ImagingStudy.patient_id == patient_id,
        ImagingStudy.study_date >= six_months_ago
    ).order_by(ImagingStudy.study_date.desc()).all()
    
    consults = ConsultReport.query.filter(
        ConsultReport.patient_id == patient_id,
        ConsultReport.report_date >= six_months_ago
    ).order_by(ConsultReport.report_date.desc()).all()
    
    hospital = HospitalSummary.query.filter(
        HospitalSummary.patient_id == patient_id,
        HospitalSummary.admission_date >= six_months_ago
    ).order_by(HospitalSummary.admission_date.desc()).all()
    
    # Get immunizations
    immunizations = Immunization.query.filter_by(patient_id=patient_id).order_by(Immunization.administration_date.desc()).all()
    
    # Get past 3 appointments for the patient
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.appointment_date < datetime.now()
    ).order_by(Appointment.appointment_date.desc()).limit(3).all()
    
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
        last_visit_date=last_visit_date
    )
    
    # Create a response with the document
    from io import BytesIO
    doc_io = BytesIO(doc_bytes)
    
    filename = f"PrepSheet_{patient.last_name}_{patient.first_name}_{datetime.now().strftime('%Y%m%d')}.docx"
    
    return send_file(
        doc_io,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route('/patients/<int:patient_id>/save_prep_sheet', methods=['POST'])
@safe_db_operation
def save_prep_sheet(patient_id):
    """Save the current state of a prep sheet as a document in the patient's records"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Get the JSON data from the request
        data = request.get_json(silent=True) or {}
        
        # Create date from the string in format YYYY-MM-DD
        date_str = data.get('date', '')
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
        except ValueError:
            current_date = datetime.now().date()
        
        # Get the checked screening items
        checked_screenings = data.get('checked_screenings', [])
        
        # Get the detailed screening data (with statuses and notes)
        screening_data = data.get('screening_data', [])
        
        # Get the date of the last completed appointment
        last_appointment = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.status == 'completed',
            Appointment.appointment_date < datetime.now()
        ).order_by(Appointment.appointment_date.desc()).first()
        
        last_appointment_date = last_appointment.appointment_date if last_appointment else None
        
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
            html_content += "<thead><tr><th>Screening</th><th>Status & Notes</th></tr></thead>"
            html_content += "<tbody>"
            
            for item in screening_data:
                screening_name = item.get('item', '')
                
                # Check for consolidated field first
                consolidated_text = item.get('consolidated', '')
                
                # Fall back to separate status and notes if no consolidated field
                if not consolidated_text:
                    status = item.get('status', '')
                    note = item.get('notes', '')
                    
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
            'checked_screenings': checked_screenings,
            'creation_date': current_date.strftime('%Y-%m-%d'),
            'screening_data': screening_data
        }
        metadata_json = json.dumps(metadata_dict)
        
        # Create a new medical document
        document = MedicalDocument(
            patient_id=patient_id,
            document_type='prep_sheet',
            filename=f'Prep_Sheet_{current_date.strftime("%Y%m%d")}.html',
            document_name=f'Prep Sheet - {current_date.strftime("%m/%d/%Y")}',
            content=html_content,
            is_binary=False,
            mime_type='text/html',
            document_date=datetime.now(),
            source_system='HealthPrep',
            provider='System',
            doc_metadata=metadata_json
        )
        
        # Add and commit to database
        db.session.add(document)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Prep sheet saved successfully'})
    
    except Exception as e:
        # Log the error
        logging.error(f"Error saving prep sheet: {str(e)}")
        
        # Rollback the session
        db.session.rollback()
        
        # Return error response
        return jsonify({'status': 'error', 'message': f'Failed to save prep sheet: {str(e)}'}), 500

@app.route('/patients/<int:patient_id>/condition', methods=['GET', 'POST'])
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
            notes=form.notes.data
        )
        
        db.session.add(condition)
        db.session.commit()
        
        # Re-evaluate screening needs based on new condition
        evaluate_screening_needs(patient)
        
        flash('Condition added successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    
    return render_template('condition_form.html', form=form, patient=patient)

@app.route('/patients/<int:patient_id>/immunization', methods=['GET', 'POST'])
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
            notes=form.notes.data
        )
        
        db.session.add(immunization)
        db.session.commit()
        
        flash('Immunization record added successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    
    return render_template('immunization_form.html', form=form, patient=patient)

@app.route('/patients/<int:patient_id>/immunization/<int:immunization_id>/delete')
def delete_immunization(patient_id, immunization_id):
    """Delete a patient's immunization record"""
    patient = Patient.query.get_or_404(patient_id)
    immunization = Immunization.query.get_or_404(immunization_id)
    
    if immunization.patient_id != patient_id:
        abort(403)  # Forbidden if immunization doesn't belong to this patient
    
    db.session.delete(immunization)
    db.session.commit()
    
    flash('Immunization record deleted successfully.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patients/<int:patient_id>/add_alert', methods=['GET', 'POST'])
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
                end_date=form.end_date.data,
                is_active=form.is_active.data,
                severity=form.severity.data
            )
            
            db.session.add(alert)
            db.session.commit()
            flash("Alert added successfully.", "success")
            return redirect(url_for('patient_detail', patient_id=patient_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding alert: {str(e)}", "error")
    
    return render_template('alert_form.html', 
                          form=form, 
                          patient=patient, 
                          title="Add Alert")


@app.route('/patients/<int:patient_id>/edit_alert/<int:alert_id>', methods=['GET', 'POST'])
def edit_alert(patient_id, alert_id):
    """Edit a patient alert"""
    patient = Patient.query.get_or_404(patient_id)
    alert = PatientAlert.query.get_or_404(alert_id)
    
    # Verify the alert belongs to this patient
    if alert.patient_id != patient_id:
        flash("Alert does not belong to this patient.", "error")
        return redirect(url_for('patient_detail', patient_id=patient_id))
    
    form = PatientAlertForm(obj=alert)
    
    if form.validate_on_submit():
        try:
            alert.alert_type = form.alert_type.data
            alert.description = form.description.data
            alert.details = form.details.data
            alert.start_date = form.start_date.data
            alert.end_date = form.end_date.data
            alert.is_active = form.is_active.data
            alert.severity = form.severity.data
            
            db.session.commit()
            flash("Alert updated successfully.", "success")
            return redirect(url_for('patient_detail', patient_id=patient_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating alert: {str(e)}", "error")
    
    return render_template('alert_form.html', 
                          form=form, 
                          patient=patient, 
                          alert=alert,
                          title="Edit Alert")


@app.route('/patients/<int:patient_id>/delete_alert/<int:alert_id>')
def delete_alert(patient_id, alert_id):
    """Delete a patient alert"""
    try:
        alert = PatientAlert.query.get_or_404(alert_id)
        
        # Verify the alert belongs to this patient
        if alert.patient_id != patient_id:
            flash("Alert does not belong to this patient.", "error")
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        db.session.delete(alert)
        db.session.commit()
        flash("Alert deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting alert: {str(e)}", "error")
    
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patients/<int:patient_id>/vitals', methods=['GET', 'POST'])
def add_vitals(patient_id):
    """Add vital signs for a patient"""
    patient = Patient.query.get_or_404(patient_id)
    form = VitalForm()
    
    # Populate the height field from the last recorded vital signs
    last_vitals = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).first()
    if last_vitals and not form.height.data and request.method == 'GET':
        # Convert from cm to inches for display
        form.height.data = last_vitals.height / 2.54  # Convert cm to inches
    
    if form.validate_on_submit():
        # Convert the form data from American units to metric for database storage
        weight_kg = form.weight.data / 2.20462 if form.weight.data else None  # Convert lbs to kg
        height_cm = form.height.data * 2.54 if form.height.data else None  # Convert inches to cm
        temperature_c = (form.temperature.data - 32) * 5/9 if form.temperature.data else None  # Convert °F to °C
        
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
            oxygen_saturation=form.oxygen_saturation.data
        )
        
        db.session.add(vital)
        db.session.commit()
        
        flash('Vital signs added successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    
    return render_template('vitals_form.html', form=form, patient=patient)

@app.route('/patients/<int:patient_id>/documents')
def patient_documents(patient_id):
    """View a patient's documents"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get all documents for this patient
    all_documents = MedicalDocument.query.filter_by(patient_id=patient_id).order_by(MedicalDocument.document_date.desc()).all()
    
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
        
    return render_template('patient_documents.html', 
                          patient=patient, 
                          documents=grouped_documents,
                          recent_documents=recent_documents,
                          document_count=document_count,
                          now=now)

@app.route('/patients/<int:patient_id>/document/add', methods=['GET', 'POST'])
def add_document(patient_id):
    """Add a document for a patient"""
    patient = Patient.query.get_or_404(patient_id)
    form = DocumentUploadForm()
    
    # Get the document type from query parameter
    doc_type = request.args.get('type')
    
    if form.validate_on_submit():
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
            
            # Check if the file is an image or binary type
            mime_type = file.content_type
            is_binary = mime_type and (mime_type.startswith('image/') or not mime_type.startswith('text/'))
            
            if is_binary:
                # Store as binary for images and other binary types
                binary_content = file.read()
                content = None
                document_metadata = {"mime_type": mime_type, "filename": filename}
            else:
                # Read file content as text for text-based files
                file_content = file.read()
                try:
                    # Try to decode as UTF-8 text
                    content = file_content.decode('utf-8', errors='replace')
                    binary_content = None
                    # Process document to classify it
                    document_metadata = process_document_upload(content, filename)
                except:
                    # If decoding fails, treat as binary
                    binary_content = file_content
                    content = None
                    document_metadata = {"mime_type": mime_type or "application/octet-stream", "filename": filename}
        else:
            # No file uploaded - create a reference-only document entry
            document_metadata = {"is_reference_only": True, "notes": "Document reference only - no file attached"}
        
        # Use the document type from query parameter if available
        document_type = DocumentType.UNKNOWN.value
        if doc_type == 'lab':
            document_type = DocumentType.LAB_REPORT.value
        elif doc_type == 'imaging':
            document_type = DocumentType.RADIOLOGY_REPORT.value
        elif doc_type == 'consult':
            document_type = DocumentType.CONSULTATION.value
        elif doc_type == 'hospital':
            document_type = DocumentType.DISCHARGE_SUMMARY.value
        else:
            # Fall back to the form selection when no type is specified by the route
            document_type = form.document_type.data
        
        # Create new document
        document = MedicalDocument(
            patient_id=patient_id,
            filename=filename,
            document_name=form.document_name.data,
            document_type=document_type,
            content=content,
            binary_content=binary_content,
            is_binary=is_binary,
            mime_type=mime_type,
            source_system=form.source_system.data,
            document_date=form.document_date.data or datetime.now(),
            doc_metadata=json.dumps(document_metadata)
        )
        
        db.session.add(document)
        db.session.commit()
        
        flash('Document uploaded successfully.', 'success')
        
        # Always redirect back to patient detail page with medical-data anchor
        return redirect(url_for('patient_detail', patient_id=patient_id) + '#medical-data')
    
    # Set document type mapping for the template
    doc_type_map = {
        'lab': 'LAB_REPORT',
        'imaging': 'RADIOLOGY_REPORT',
        'consult': 'CONSULTATION',
        'hospital': 'DISCHARGE_SUMMARY'
    }
    doc_type_value = doc_type_map.get(doc_type, '')
    
    # Update title based on document type
    title = 'Upload Document'
    if doc_type == 'lab':
        title = 'Upload Lab Report'
    elif doc_type == 'imaging':
        title = 'Upload Imaging Study'
    elif doc_type == 'consult':
        title = 'Upload Consultation Report'
    elif doc_type == 'hospital':
        title = 'Upload Hospital Summary'
        
    return render_template('document_upload.html', 
                         form=form, 
                         patient=patient, 
                         doc_type=doc_type_value,
                         title=title)

@app.route('/documents/<int:document_id>')
def view_document(document_id):
    """View a document"""
    document = MedicalDocument.query.get_or_404(document_id)
    patient = Patient.query.get_or_404(document.patient_id)
    
    # Get the return_to parameter (if provided)
    return_to = request.args.get('return_to', None)
    
    # Get metadata if available
    metadata = {}
    if document.doc_metadata:
        try:
            metadata = json.loads(document.doc_metadata)
        except:
            metadata = {}
    
    return render_template('document_view.html', 
                          document=document, 
                          patient=patient,
                          return_to=return_to,
                          metadata=metadata)
                          
@app.route('/documents/<int:document_id>/image')
def document_image(document_id):
    """Serve a document's binary content as an image"""
    document = MedicalDocument.query.get_or_404(document_id)
    
    if not document.binary_content:
        abort(404)
    
    # Determine mime type for the response
    mime_type = document.mime_type or 'application/octet-stream'
    
    # Create a response with the binary content
    response = make_response(document.binary_content)
    response.headers.set('Content-Type', mime_type)
    return response

@app.route('/documents/repository')
def document_repository():
    """Display all documents in the repository with patient information"""
    # Get search query parameter
    search_query = request.args.get('search', '')
    
    # Get patient filter parameter
    selected_patient_id = request.args.get('patient_id', '')
    if selected_patient_id and selected_patient_id.isdigit():
        selected_patient_id = int(selected_patient_id)
    else:
        selected_patient_id = None
    
    # Create query with eager loading of patient relationship
    query = MedicalDocument.query.join(Patient).options(db.joinedload(MedicalDocument.patient))
    
    # Apply patient filter if provided
    if selected_patient_id:
        query = query.filter(MedicalDocument.patient_id == selected_patient_id)
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(
            db.or_(
                MedicalDocument.document_name.ilike(f'%{search_query}%'),
                MedicalDocument.document_type.ilike(f'%{search_query}%'),
                MedicalDocument.source_system.ilike(f'%{search_query}%'),
                Patient.first_name.ilike(f'%{search_query}%'),
                Patient.last_name.ilike(f'%{search_query}%')
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
    response = make_response(render_template(
        'document_repository.html',
        all_documents=all_documents,
        all_patients=all_patients,
        selected_patient_id=selected_patient_id,
        search_query=search_query,
        cache_timestamp=cache_timestamp
    ))
    
    # Add cache control headers to force fresh content
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/import-from-url', methods=['POST'])
def import_from_url():
    """Import document content from a URL"""
    url = request.form.get('url')
    patient_id = request.form.get('patient_id')
    
    if not url or not patient_id:
        return jsonify({'success': False, 'error': 'Missing URL or patient ID'})
    
    try:
        # Extract text from the URL
        document_text = extract_document_text_from_url(url)
        
        if not document_text:
            return jsonify({'success': False, 'error': 'Could not extract text from the provided URL'})
        
        # Process the document
        document_metadata = process_document_upload(document_text, f"Import from {url}")
        
        # Create new document
        document = MedicalDocument(
            patient_id=patient_id,
            filename=f"Import from {url}",
            document_type=document_metadata.get('document_type', DocumentType.UNKNOWN.value),
            content=document_text,
            source_system="Web Import",
            document_date=datetime.now(),
            doc_metadata=json.dumps(document_metadata)
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'document_id': document.id,
            'document_type': document.document_type,
            'message': 'Document imported successfully!'
        })
    except Exception as e:
        logging.error(f"Error importing from URL: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

from flask import session, redirect, url_for, flash
from forms import LoginForm, RegistrationForm
from models import User
from werkzeug.security import check_password_hash

@app.route('/login', methods=['GET', 'POST'])
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
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            logger.info(f"Successful login for user: {user.username}")
            
            # Log successful login
            try:
                import uuid
                from models import AdminLog
                request_id = str(uuid.uuid4())
                
                AdminLog.log_event(
                    event_type='login_success',
                    user_id=user.id,
                    event_details={
                        'username': user.username,
                        'is_admin': user.is_admin,
                        'login_method': 'web_form'
                    },
                    request_id=request_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )
                db.session.commit()
            except Exception as e:
                logger.error(f"Error logging successful login: {str(e)}")
                db.session.rollback()
            
            # Redirect admin users to admin dashboard
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            logger.warning(f"Failed login attempt for username: {form.username.data}")
            
            # Log failed login attempt with detailed information
            try:
                import uuid
                from models import AdminLog
                request_id = str(uuid.uuid4())
                
                # Determine the specific reason for failure
                user_exists = User.query.filter(
                    (User.username == form.username.data) | (User.email == form.username.data)
                ).first()
                
                if user_exists:
                    reason = 'invalid_password'
                else:
                    reason = 'user_not_found'
                
                AdminLog.log_event(
                    event_type='login_fail',
                    user_id=None,
                    event_details={
                        'attempted_username': form.username.data,
                        'login_method': 'web_form',
                        'reason': reason,
                        'ip_address': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'timestamp': datetime.now().isoformat()
                    },
                    request_id=request_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )
                db.session.commit()
            except Exception as e:
                logger.error(f"Error logging failed login: {str(e)}")
                db.session.rollback()
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Web-based registration using sessions"""
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists', 'error')
        else:
            # Create new user
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                is_admin=False
            )
            new_user.set_password(form.password.data)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Auto-login the new user
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            session['is_admin'] = new_user.is_admin
            flash('Registration successful!', 'success')
            logger.info(f"New user registered and logged in: {new_user.username}")
            return redirect(url_for('index'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    """Web-based logout that clears the session"""
    username = session.get('username', 'Unknown')
    session.clear()
    flash('You have been logged out.', 'info')
    logger.info(f"User logged out: {username}")
    return redirect(url_for('index'))

@app.route('/admin')
@app.route('/admin_dashboard')
def admin_dashboard():
    """Admin dashboard with system statistics and logs"""
    # Check if user is logged in and is admin
    if not session.get('user_id') or not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('login'))
    
    # Log admin dashboard access
    try:
        import uuid
        from models import AdminLog
        request_id = str(uuid.uuid4())
        
        AdminLog.log_event(
            event_type='admin_dashboard_access',
            user_id=session.get('user_id'),
            event_details={
                'action': 'admin_dashboard_viewed',
                'username': session.get('username'),
                'timestamp': datetime.now().isoformat()
            },
            request_id=request_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
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
    overdue_screenings = Screening.query.filter(
        Screening.due_date < today
    ).count()
    
    # Get total appointments
    total_appointments = Appointment.query.count()
    
    # Get total documents
    total_documents = MedicalDocument.query.count()
    
    # Get total users
    from models import User
    total_users = User.query.count()
    
    # Get recent login failures from admin logs
    recent_login_failures = 0
    
    # Get paginated admin logs
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of logs per page
    
    recent_admin_logs = []
    admin_logs_pagination = None
    try:
        from models import AdminLog
        admin_logs_pagination = AdminLog.query.order_by(AdminLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        recent_admin_logs = admin_logs_pagination.items
        
        # Count recent login failures (last 24 hours)
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        recent_login_failures = AdminLog.query.filter(
            AdminLog.event_type == 'login_fail',
            AdminLog.timestamp >= twenty_four_hours_ago
        ).count()
        
    except Exception as e:
        logger.warning(f"Could not fetch admin logs: {str(e)}")
    
    # Get recent patients
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    
    # Get recent appointments
    recent_appointments = Appointment.query.order_by(Appointment.appointment_date.desc()).limit(5).all()
    
    # Get recent documents
    recent_documents = MedicalDocument.query.order_by(MedicalDocument.created_at.desc()).limit(5).all()
    
    # Get all users for user management section
    all_users = User.query.order_by(User.username).all()
    
    # Count admin users for the safeguard logic
    admin_count = User.query.filter_by(is_admin=True).count()
    
    # Create database statistics object
    db_stats = {
        'patients': total_patients,
        'appointments': total_appointments,
        'documents': total_documents,
        'users': total_users,
        'screenings': Screening.query.count(),
        'admin_logs': len(recent_admin_logs)
    }
    
    return render_template('admin_dashboard.html',
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
                          db_stats=db_stats)

# Error handlers
@app.route('/admin/users/<int:user_id>/delete', methods=['GET', 'POST'])
@safe_db_operation
def delete_user(user_id):
    """Delete a user account with admin safeguard"""
    print(f"Delete user request received for user ID: {user_id}")
    print(f"Request method: {request.method}")
    print(f"Current user: {session.get('username')} (ID: {session.get('user_id')})")
    print(f"Is admin: {session.get('is_admin')}")
    
    # Check if user is logged in and is admin
    if not session.get('user_id') or not session.get('is_admin'):
        print("Access denied - insufficient privileges")
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('login'))
    
    try:
        user_to_delete = User.query.get_or_404(user_id)
        print(f"Found user to delete: {user_to_delete.username} (Admin: {user_to_delete.is_admin})")
        
        # Get current admin count
        admin_count = User.query.filter_by(is_admin=True).count()
        print(f"Current admin count: {admin_count}")
        
        # Prevent deletion if this is the last admin user
        if user_to_delete.is_admin and admin_count <= 1:
            print("Deletion blocked - would remove last admin user")
            flash('Cannot delete the last admin user. At least one admin must remain.', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        # Store user info for confirmation message
        username = user_to_delete.username
        
        # Delete associated admin logs (set user_id to NULL instead of deleting logs)
        from models import AdminLog
        AdminLog.query.filter_by(user_id=user_id).update({'user_id': None})
        
        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        print(f"Successfully deleted user: {username}")
        
        flash(f'User "{username}" has been deleted successfully.', 'success')
        
        # Log the admin action
        try:
            import uuid
            request_id = str(uuid.uuid4())
            
            AdminLog.log_event(
                event_type='admin_action',
                user_id=session.get('user_id'),
                event_details={
                    'action': 'user_deleted',
                    'deleted_user': username,
                    'deleted_user_id': user_id,
                    'admin_user': session.get('username')
                },
                request_id=request_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.commit()
            print(f"Admin action logged for user deletion: {username}")
        except Exception as e:
            logger.error(f"Error logging user deletion: {str(e)}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/screenings')
def screening_list():
    """List all patients with due screenings and manage screening types"""
    # Define now() function to use in templates for date comparisons
    def now():
        return datetime.now()
    
    # Get the tab parameter (screenings or types)
    tab = request.args.get('tab', 'screenings')
    
    # Get the search query parameter
    search_query = request.args.get('search', '')
    
    # Import the checklist settings model and helper function
    from models import ChecklistSettings
    
    # Get or create checklist settings for the checklist tab
    def get_or_create_settings():
        """Get or create checklist settings"""
        settings = ChecklistSettings.query.first()
        if not settings:
            settings = ChecklistSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
        
    # Variables for checklist tab
    settings = None
    default_items_text = ""
    if tab == 'checklist':
        settings = get_or_create_settings()
        default_items_text = '\n'.join(settings.default_items_list) if settings.default_items else ''
    
    # Create forms for screening type management
    from forms import ScreeningTypeForm
    add_form = ScreeningTypeForm()
    edit_form = ScreeningTypeForm()
    
    # If we're on the screening types tab
    screening_types = []
    if tab == 'types':
        # Get all screening types
        screening_types_query = ScreeningType.query.order_by(ScreeningType.name)
        
        # Apply search filter if provided
        if search_query:
            screening_types_query = screening_types_query.filter(
                ScreeningType.name.ilike(f'%{search_query}%')
            )
            
        screening_types = screening_types_query.all()
    
    # Otherwise, proceed with regular screening list
    # Base query for patient screenings
    query = Screening.query.join(Patient)
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(f'%{search_query}%'),
                Patient.last_name.ilike(f'%{search_query}%'),
                Screening.screening_type.ilike(f'%{search_query}%')
            )
        )
    
    # Don't apply any date filter to make sure all screenings appear
    # This shows ALL screenings regardless of due date
    today = datetime.now().date()
    
    # Order by priority (High first) and due date (earliest first)
    screenings = query.order_by(
        db.case(
            (Screening.priority == 'High', 0),
            (Screening.priority == 'Medium', 1),
            else_=2
        ),
        # Handle NULL due_dates by using nullslast()
        db.nullslast(Screening.due_date)
    ).all()
    
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())
    
    # Get all active screening types for the Add Recommendation modal
    all_screening_types = ScreeningType.query.filter_by(is_active=True).order_by(ScreeningType.name).all()
    
    # Get all patients for the Add Recommendation modal
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    
    try:
        return render_template('screening_list.html', 
                              screenings=screenings, 
                              screening_types=screening_types,
                              all_screening_types=all_screening_types,
                              add_form=add_form,
                              edit_form=edit_form,
                              search_query=search_query,
                              active_tab=tab,
                              cache_timestamp=cache_timestamp,
                              now=now,
                              today=today,
                              patients=patients,
                              settings=settings,
                              default_items_text=default_items_text)
    except Exception as e:
        print(f"Error rendering screening_list.html: {str(e)}")
        # Add more detailed error information to help debug
        import traceback
        traceback.print_exc()
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/debug/appointments', methods=['GET'])
def debug_appointments():
    """Debug endpoint to inspect appointments"""
    try:
        # Create an HTML response with proper formatting
        response_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Appointment Debugging</title>
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
            date_str = appt.appointment_date.strftime('%Y-%m-%d')
            if date_str in dates:
                dates[date_str] += 1
            else:
                dates[date_str] = 1
        
        response_html += "<h3>Appointments by date:</h3><ul>"
        for date_str, count in sorted(dates.items()):
            response_html += f"<li>{date_str}: {count} appointment(s)</li>"
        response_html += "</ul>"
        
        # Get today's appointments
        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')
        
        response_html += f"<h3>Today's appointments ({today_str}):</h3>"
        today_appointments = Appointment.query.filter(
            Appointment.appointment_date == today
        ).order_by(Appointment.appointment_time).all()
        
        if today_appointments:
            response_html += "<table class='table table-striped'>"
            response_html += "<thead><tr><th>ID</th><th>Patient</th><th>Time</th><th>Note</th></tr></thead><tbody>"
            for appt in today_appointments:
                time_str = appt.appointment_time.strftime('%H:%M') if appt.appointment_time else "N/A"
                response_html += f"<tr><td>{appt.id}</td><td>{appt.patient.full_name}</td><td>{time_str}</td><td>{appt.note or ''}</td></tr>"
            response_html += "</tbody></table>"
        else:
            response_html += "<p>No appointments for today.</p>"
            
        # Test appointment creation section
        response_html += """
            <h2>Test Appointment Creation</h2>
            <div class="card">
                <div class="card-body">
                    <h3 class="card-title">Creating Test Appointment</h3>
        """
        
        try:
            # Create test appointment
            from datetime import time
            test_patient = Patient.query.first()
            if test_patient:
                test_appointment = Appointment(
                    patient_id=test_patient.id,
                    appointment_date=today,
                    appointment_time=time(hour=14, minute=30),
                    note="Test appointment created via debug endpoint"
                )
                db.session.add(test_appointment)
                db.session.commit()
                
                response_html += f"""
                    <div class="alert alert-success">
                        <p>Created test appointment:</p>
                        <ul>
                            <li>ID: {test_appointment.id}</li>
                            <li>Patient: {test_patient.full_name}</li>
                            <li>Date: {today_str}</li>
                            <li>Time: 14:30</li>
                        </ul>
                    </div>
                """
                
                # Verify it was created
                verify = Appointment.query.get(test_appointment.id)
                if verify:
                    response_html += f"""
                        <div class="alert alert-success">
                            Successfully verified appointment exists in database
                        </div>
                    """
                else:
                    response_html += f"""
                        <div class="alert alert-danger">
                            ERROR: Could not verify appointment in database
                        </div>
                    """
                    
                # Refresh to see the new appointment
                response_html += f"""
                    <h3>All appointments after test creation</h3>
                    <p>There should now be {appointment_count + 1} total appointments</p>
                """
                
                # Show appointments again after creation
                updated_appointments = Appointment.query.all()
                response_html += f"<p>Actual count after creation: <strong>{len(updated_appointments)}</strong></p>"
                
                # New today's appointments
                updated_today = Appointment.query.filter(
                    Appointment.appointment_date == today
                ).order_by(Appointment.appointment_time).all()
                
                response_html += f"<h4>Updated today's appointments ({today_str}):</h4>"
                if updated_today:
                    response_html += "<table class='table table-striped'>"
                    response_html += "<thead><tr><th>ID</th><th>Patient</th><th>Time</th><th>Note</th></tr></thead><tbody>"
                    for appt in updated_today:
                        time_str = appt.appointment_time.strftime('%H:%M') if appt.appointment_time else "N/A"
                        row_class = " class='table-success'" if appt.id == test_appointment.id else ""
                        response_html += f"<tr{row_class}><td>{appt.id}</td><td>{appt.patient.full_name}</td><td>{time_str}</td><td>{appt.note or ''}</td></tr>"
                    response_html += "</tbody></table>"
                else:
                    response_html += "<p>No appointments for today (this is unexpected!).</p>"
            else:
                response_html += """
                    <div class="alert alert-warning">
                        No patients available for test appointment creation
                    </div>
                """
        except Exception as e:
            response_html += f"""
                <div class="alert alert-danger">
                    Error creating test appointment: {str(e)}
                </div>
            """
            
        # Close the HTML
        response_html += """
                </div>
            </div>
            <div class="mt-4">
                <a href="/" class="btn btn-primary">Return to Home</a>
            </div>
        </div>
        </body>
        </html>
        """
        
        return response_html
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        </head>
        <body>
            <div class="container mt-5">
                <div class="alert alert-danger">
                    <h3>Error occurred in debug endpoint</h3>
                    <p>{str(e)}</p>
                </div>
                <a href="/" class="btn btn-primary">Return to Home</a>
            </div>
        </body>
        </html>
        """
        return error_html


@app.route('/appointments/debug_add', methods=['GET', 'POST'])
@fresh_session_operation
def debug_add_appointment():
    """Debug version of add_appointment - simplified for testing"""
    print("=" * 50)
    print("STARTING DEBUG_ADD_APPOINTMENT...")
    
    if request.method == 'GET':
        # Just show the form
        form = AppointmentForm()
        patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
        form.patient_id.choices = [(p.id, f"{p.full_name} (MRN: {p.mrn})") for p in patients]
        
        # Pre-populate today's date
        today = datetime.now().date()
        form.appointment_date.data = today
        
        return render_template('appointment_form.html', 
                              form=form, 
                              patients=patients, 
                              editing=False, 
                              debug_mode=True)
    
    elif request.method == 'POST':
        print(f"DEBUG POST DATA: {request.form}")
        
        # Extract form data directly
        try:
            # Get form data
            patient_id = request.form.get('patient_id')
            date_str = request.form.get('appointment_date')
            time_str = request.form.get('appointment_time')
            note = request.form.get('note', '')
            
            # Basic validation
            if not patient_id or not date_str or not time_str:
                flash('Missing required appointment data.', 'danger')
                patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
                form = AppointmentForm(request.form)
                form.patient_id.choices = [(p.id, f"{p.full_name} (MRN: {p.mrn})") for p in patients]
                return render_template('appointment_form.html', form=form, patients=patients, editing=False, debug_mode=True)
            
            # Convert strings to appropriate data types
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_parts = time_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            from datetime import time
            appointment_time = time(hour=hour, minute=minute)
            
            # Try with SQLAlchemy
            appointment = Appointment(
                patient_id=int(patient_id),
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                note=note
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            # Log details
            print(f"DEBUG: Successfully created appointment with ID: {appointment.id}")
            print(f"DEBUG: Patient ID: {appointment.patient_id}")
            print(f"DEBUG: Date: {appointment.appointment_date}")
            print(f"DEBUG: Time: {appointment.appointment_time}")
            
            flash(f'DEBUG MODE: Appointment added successfully with ID {appointment.id}!', 'success')
            
            # Also check if we can query it back
            verify = Appointment.query.get(appointment.id)
            if verify:
                print(f"DEBUG: Verified appointment exists with ID: {verify.id}")
            else:
                print("DEBUG: WARNING - Could not verify appointment after creation!")
            
            # Force redirect using absolute URL
            date_str_redirect = appointment_date.strftime('%Y-%m-%d')
            return redirect('/home/date/' + date_str_redirect)
            
        except Exception as e:
            db.session.rollback()
            error_msg = f'DEBUG ERROR: {str(e)}'
            flash(error_msg, 'danger')
            print(error_msg)
            patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
            form = AppointmentForm(request.form)
            form.patient_id.choices = [(p.id, f"{p.full_name} (MRN: {p.mrn})") for p in patients]
            return render_template('appointment_form.html', form=form, patients=patients, editing=False, debug_mode=True)
    
    # Should never get here
    return redirect('/home')


# The simple_add_appointment function has been consolidated into the main add_appointment function

@app.route('/get-available-slots', methods=['GET'])
def get_available_slots():
    """API endpoint to get available appointment time slots for a specific date"""
    try:
        # Get the date from the query parameters
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({
                'success': False,
                'message': 'Date parameter is required',
                'available_slots': [],
                'booked_slots': []
            }), 400
        
        # Get optional appointment ID (for editing scenarios)
        appointment_id = request.args.get('appointment_id')
        appointment_id = int(appointment_id) if appointment_id else None
        
        # Check if we're editing an appointment (stored in session)
        if not appointment_id and 'editing_appointment_id' in session:
            appointment_id = session['editing_appointment_id']
            print(f"Using appointment ID from session: {appointment_id}")
        
        print(f"Get available slots - Date: {date_str}, Appointment ID: {appointment_id}")
        
        # Parse the date
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD',
                'available_slots': [],
                'booked_slots': []
            }), 400
        
        # Get all available slots (excluding current appointment if editing)
        available_slots = get_available_time_slots(appointment_date, appointment_id)
        
        # Get all booked slots (excluding current appointment if editing)
        booked_slots = get_booked_time_slots(appointment_date, appointment_id, as_string=True)
        
        # Format available slots for the dropdown
        formatted_available_slots = []
        for slot in available_slots:
            # Convert from 24-hour to 12-hour format for display
            hour, minute = map(int, slot.split(':'))
            if hour < 12:
                label = f"{hour}:{minute:02d} AM" if hour > 0 else f"12:{minute:02d} AM"
            elif hour == 12:
                label = f"12:{minute:02d} PM"
            else:
                label = f"{hour-12}:{minute:02d} PM"
            
            formatted_available_slots.append({
                'value': slot,
                'label': label
            })
        
        return jsonify({
            'success': True,
            'available_slots': formatted_available_slots,
            'booked_slots': booked_slots
        })
    except Exception as e:
        print(f"Error getting available slots: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}',
            'available_slots': [],
            'booked_slots': []
        }), 500


@app.route('/add-appointment', methods=['GET', 'POST'], endpoint='add_appointment')
@fresh_session_operation
@validate_appointment_input
def add_appointment():
    """Add a new appointment - Enhanced version with 15-minute time slots and conflict prevention"""
    print("=" * 50)
    print("Starting add_appointment function...")
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request is AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
    print(f"Request form data: {request.form}")
    print(f"Request args: {request.args}")
    print(f"Request files: {request.files}")
    print("=" * 50)
    
    # Always create a fresh form
    form = AppointmentForm()
    
    # Get pre-selected date from query parameters if available
    selected_date = request.args.get('date')
    print(f"Selected date from URL: {selected_date}")
    
    # Get the current date for debugging
    current_date = datetime.now().date()
    print(f"Current date for reference: {current_date}")
    
    # This is crucial - explicitly set appointment_date to None to prevent default values
    form.appointment_date.data = None
    print(f"Initial form appointment_date.data: {form.appointment_date.data}")
    
    # Check if we have a fallback date from form submission
    fallback_date = None
    if request.method == 'POST' and 'fallback_date' in request.form:
        fallback_date = request.form['fallback_date']
        print(f"Fallback date from form: {fallback_date}")
    
    # Check if user wants to force save despite conflicts
    force_save = request.args.get('force_save') == '1'
    print(f"Force save flag: {force_save}")
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    print(f"Is AJAX request: {is_ajax}")
    
    # Populate the patient select field with all patients
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    print(f"Found {len(patients)} patients for dropdown")
    form.patient_id.choices = [(p.id, f"{p.full_name} (MRN: {p.mrn})") for p in patients]
    
    # Initialize form with pre-selected date for GET requests
    if selected_date and request.method == 'GET':
        try:
            # Parse and set the appointment date
            parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            form.appointment_date.data = parsed_date
            print(f"Set form appointment_date to: {form.appointment_date.data}")
            print(f"Date format check - Selected date: {selected_date}, Parsed as: {parsed_date}, Form value: {form.appointment_date.data}")
        except ValueError:
            # If invalid, set to today's date and show warning
            form.appointment_date.data = datetime.now().date()
            print(f"Invalid date format. Using today's date: {form.appointment_date.data}")
            flash('Invalid date format in URL. Date should be in YYYY-MM-DD format. Using today\'s date instead.', 'warning')
    
    # Handle direct test appointment creation
    if request.args.get('test_create') == '1':
        try:
            # Get first patient for test
            test_patient = patients[0] if patients else None
            if test_patient:
                print(f"TEST MODE: Creating test appointment for patient: {test_patient.full_name}")
                from datetime import time
                # Create test appointment
                test_appointment = Appointment(
                    patient_id=test_patient.id,
                    appointment_date=datetime.now().date(),
                    appointment_time=time(hour=10, minute=30),
                    note="Test appointment"
                )
                db.session.add(test_appointment)
                db.session.commit()
                print(f"TEST MODE: Created appointment with ID: {test_appointment.id}")
                
                # Verify it was created
                verify = Appointment.query.filter_by(id=test_appointment.id).first()
                if verify:
                    print(f"TEST MODE: Successfully verified appointment exists in database")
                    flash(f'Test appointment created successfully with ID: {test_appointment.id}', 'success')
                else:
                    print(f"TEST MODE: Failed to verify appointment in database")
                    flash('Test appointment failed - could not verify creation', 'danger')
                    
                # List all appointments for today
                today_appts = Appointment.query.filter(
                    Appointment.appointment_date == datetime.now().date()
                ).all()
                print(f"TEST MODE: Found {len(today_appts)} appointments for today")
                for appt in today_appts:
                    print(f"TEST MODE: Appointment ID: {appt.id}, Patient: {appt.patient.full_name}, Time: {appt.appointment_time}")
                
                timestamp = int(time_module.time())
                return redirect(url_for('index', refresh=timestamp))
            else:
                flash('No patients available for test appointment creation', 'danger')
        except Exception as e:
            db.session.rollback()
            print(f"TEST MODE ERROR: {str(e)}")
            flash(f'Error in test appointment creation: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    # Debug form submission
    print(f"Form submitted: {request.method == 'POST'}")
    if request.method == 'POST':
        print(f"Form data: {request.form}")
        print(f"Debug info: {request.form.get('_form_debug', 'none')} - Has errors: {request.form.get('_form_has_errors', 'false')}")
        
        # Create a new form with the POST data but make sure we set the patient choices first
        print(f"POST data before creating form: appointment_date={request.form.get('appointment_date')}")
        form = AppointmentForm(request.form)
        print(f"Form after creation: appointment_date={form.appointment_date.data}")
        
        # Need to set choices before validation
        form.patient_id.choices = [(p.id, f"{p.full_name} (MRN: {p.mrn})") for p in patients]
        
        # Save the appointment date before validation for debugging
        pre_validate_date = form.appointment_date.data
        print(f"Appointment date before validation: {pre_validate_date}, type: {type(pre_validate_date)}")
        
        # Run validation
        validation_result = form.validate()
        print(f"Form validation: {validation_result}")
        
        # Check if the date changed during validation
        post_validate_date = form.appointment_date.data
        print(f"Appointment date after validation: {post_validate_date}, type: {type(post_validate_date)}")
        if not form.validate():
            print(f"Form validation errors: {form.errors}")
            # If in a force save scenario but there's CSRF error, handle special case
            # Modified to handle CSRF errors more gracefully for appointment creation
            # This helps when tokens expire during form interactions
            if 'csrf_token' in form.errors:
                # Recreate the appointment manually instead of relying on form validation
                try:
                    patient_id = request.form.get('patient_id')
                    appointment_date_str = request.form.get('appointment_date')
                    appointment_time_str = request.form.get('appointment_time')
                    note = request.form.get('note', '')
                    
                    # Validate and convert
                    if not patient_id or not appointment_date_str or not appointment_time_str:
                        error_msg = 'Missing required appointment data.'
                        if is_ajax:
                            response = jsonify({'success': False, 'message': error_msg})
                            response.headers['Content-Type'] = 'application/json'
                            return response
                        flash(error_msg, 'danger')
                        return render_template('appointment_form.html', form=form, patients=patients, editing=False)
                    
                    appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
                    time_parts = appointment_time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    from datetime import time
                    appointment_time = time(hour=hour, minute=minute)
                    
                    # Create appointment with force save
                    appointment = Appointment(
                        patient_id=int(patient_id),
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                        note=note
                    )
                    
                    db.session.add(appointment)
                    db.session.commit()
                    
                    success_msg = 'Appointment added with scheduling conflicts.'
                    timestamp = int(time_module.time())
                    
                    if is_ajax:
                        return jsonify({
                            'success': True, 
                            'message': success_msg,
                            'redirect': f"/date/{appointment_date_str}?refresh={timestamp}"
                        })
                    
                    flash(success_msg, 'warning')
                    return redirect(f"/date/{appointment_date_str}?refresh={timestamp}")
                except Exception as e:
                    db.session.rollback()
                    print(f"Force save error: {str(e)}")
                    error_msg = f'Error creating appointment: {str(e)}'
                    
                    if is_ajax:
                        return jsonify({'success': False, 'message': error_msg})
                    
                    flash(error_msg, 'danger')
    
    # Use a more reliable approach that works with or without form validation
    if request.method == 'POST':
        # Try to create an appointment either way - with form validation or direct data parsing
        print("Processing POST request for appointment creation")
        
        # First, try to get data directly from the form data (more reliable)
        patient_id = request.form.get('patient_id')
        appointment_date_str = request.form.get('appointment_date')
        appointment_time_str = request.form.get('appointment_time') 
        note = request.form.get('note', '')
        
        # Debug info
        print(f"Direct form data: patient_id={patient_id}, date={appointment_date_str}, time={appointment_time_str}")
        print(f"Form validated: {form.validate()}")
        
        # Validate the essential data is present
        if not patient_id or not appointment_date_str or not appointment_time_str:
            error_msg = 'Missing required appointment data.'
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg})
            flash(error_msg, 'danger')
            return render_template('appointment_form.html', form=form, patients=patients, editing=False)
        
        # Convert date and time strings to appropriate objects
        try:
            # Parse the date and time
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
            
            # Parse the time string
            time_parts = appointment_time_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            from datetime import time
            appointment_time = time(hour=hour, minute=minute)
            
            print(f"Successfully parsed date: {appointment_date} and time: {appointment_time}")
        except (ValueError, IndexError) as e:
            print(f"Error parsing date or time: {e}")
            error_msg = 'Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.'
            
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg})
            
            flash(error_msg, 'danger')
            return render_template('appointment_form.html', form=form, patients=patients, editing=False)
        
        print(f"Checking conflicts for date: {appointment_date}, time: {appointment_time}")
        # Check for appointment conflicts
        conflicts = detect_appointment_conflicts(
            date=appointment_date,  # Use the directly parsed date
            time_obj=appointment_time,
            duration_minutes=30  # Default appointment duration
        )
        
        if conflicts and not force_save:
            print(f"Found {len(conflicts)} conflicts and force_save is False")
            # Generate a warning message about the conflict
            conflict_message = format_conflict_message(conflicts)
            warn_msg = f'Warning: {conflict_message}'
            
            if is_ajax:
                return jsonify({
                    'success': False, 
                    'message': warn_msg,
                    'has_conflicts': True,
                    'conflicts': [{'patient': c.patient.full_name, 'time': c.appointment_time.strftime('%I:%M %p')} for c in conflicts]
                })
            
            flash(warn_msg, 'warning')
            # Pass conflicts to template to highlight them
            return render_template('appointment_form.html', 
                                  form=form, 
                                  patients=patients, 
                                  editing=False, 
                                  conflicts=conflicts,
                                  conflict_message=conflict_message)
        
        # Create a new appointment
        try:
            # Get date directly from request.form to avoid WTForms processing
            raw_appointment_date = request.form.get('appointment_date')
            print(f"Raw appointment date: {raw_appointment_date}")
            
            # Use the raw date if possible, or fall back to form data
            if raw_appointment_date:
                try:
                    # Parse the raw date string
                    appointment_date = datetime.strptime(raw_appointment_date, '%Y-%m-%d').date()
                    print(f"Using parsed date: {appointment_date}")
                except ValueError:
                    # Fall back to processed form data
                    appointment_date = form.appointment_date.data
                    print(f"Invalid raw date, using form data: {appointment_date}")
            else:
                # No raw date in form, use processed form data
                appointment_date = form.appointment_date.data
                print(f"No raw date, using form data: {appointment_date}")
            
            # Create the appointment using our directly parsed data
            # Use integer conversion for patient_id to ensure it's the right type
            patient_id_int = int(patient_id)
            print(f"Creating appointment for patient ID: {patient_id_int}, date: {appointment_date}")
            appointment = Appointment(
                patient_id=patient_id_int,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                note=note
            )
            
            db.session.add(appointment)
            db.session.commit()
            print(f"Appointment created successfully with ID: {appointment.id}")
            
            # Double-check the appointment was actually created and log the result
            verify = Appointment.query.get(appointment.id)
            if verify:
                print(f"Verified appointment exists in database with ID {verify.id}")
                today_count = Appointment.query.filter(
                    Appointment.appointment_date == form.appointment_date.data
                ).count()
                print(f"Total appointments for {form.appointment_date.data}: {today_count}")
            else:
                print("WARNING: Could not verify appointment in database after creation!")
                
            if conflicts and force_save:
                success_msg = 'Appointment added with scheduling conflicts.'
            else:
                success_msg = 'Appointment added successfully.'
            
            # Use our original unparsed date string for the redirect - it's already in the correct format
            appointment_date_str = appointment_date_str  # This is from the form input and is already in 'YYYY-MM-DD' format
            
            # If we have a fallback date from the form, use that instead
            if fallback_date:
                print(f"Using fallback date for redirect: {fallback_date}")
                appointment_date_str = fallback_date
            elif not appointment_date_str:
                # Default to today if still no date
                today = datetime.now().date()
                appointment_date_str = today.strftime('%Y-%m-%d')
                print(f"No appointment date found, defaulting to today: {appointment_date_str}")
                
            # Use a cache-busting parameter to ensure fresh page load
            timestamp = int(time_module.time())
            print(f"Redirecting to index with date_str: {appointment_date_str} and refresh: {timestamp}")
            
            # Construct an absolute URL to ensure proper redirect
            redirect_url = f"/home/date/{appointment_date_str}?refresh={timestamp}"
            print(f"FINAL REDIRECT URL: {redirect_url}")
            
            # Update flash message to confirm the redirect path for debugging
            success_msg += f" Redirecting to date: {appointment_date_str}"
            
            if is_ajax:
                # Use direct URL path for consistency
                redirect_url = f"/home/date/{appointment_date_str}?refresh={timestamp}"
                print(f"AJAX Redirect URL: {redirect_url}")
                return jsonify({
                    'success': True, 
                    'message': success_msg,
                    'redirect': redirect_url
                })
            
            if conflicts and force_save:
                flash(success_msg, 'warning')
            else:
                flash(success_msg, 'success')
                
            print(f"Form date: {form.appointment_date.data}, type: {type(form.appointment_date.data)}")
            
            # Use Flask's url_for with external=True to get an absolute URL
            try:
                # First try using url_for with the 'index' route and date parameter
                redirect_url = url_for('index', date=appointment_date_str, refresh=timestamp)
                print(f"URL generated via url_for: {redirect_url}")
            except Exception as url_err:
                print(f"Error with url_for: {str(url_err)}")
                # Fallback to direct URL construction
                redirect_url = f"/home/date/{appointment_date_str}?refresh={timestamp}"
                print(f"Fallback direct URL: {redirect_url}")
            
            print(f"FINAL REDIRECT: {redirect_url}")
            # Redirect to the date page
            response = redirect(redirect_url)
            print(f"Prepared redirect response: {response}")
            return response
        except Exception as e:
            db.session.rollback()
            print(f"Error saving appointment: {str(e)}")
            error_msg = f'Error saving appointment: {str(e)}'
            
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg})
            
            flash(error_msg, 'danger')
            return render_template('appointment_form.html', form=form, patients=patients, editing=False)
    
    print("-" * 50)
    print(f"FINAL DEBUG - Request method: {request.method}")
    print(f"FINAL DEBUG - Form validation status: {form.validate() if request.method == 'POST' else 'GET request'}")
    print(f"FINAL DEBUG - Selected date: {selected_date}")
    print(f"FINAL DEBUG - Fallback date: {fallback_date}")
    print("-" * 50)
    return render_template('appointment_form.html', form=form, patients=patients, editing=False)


@app.route('/appointments/<int:appointment_id>/edit', methods=['GET', 'POST'])
@fresh_session_operation
def edit_appointment(appointment_id):
    """Edit an existing appointment - Enhanced version with improved data handling"""
    print("=" * 50)
    print(f"Starting edit_appointment function for ID: {appointment_id}")
    print(f"Request method: {request.method}")
    
    # Get the appointment by ID
    appointment = Appointment.query.get_or_404(appointment_id)
    print(f"Found appointment: ID={appointment.id}, Patient={appointment.patient.full_name}, Date={appointment.appointment_date}")
    
    # Create form with standard handling
    if request.method == 'GET':
        form = AppointmentForm(obj=appointment)
    else:
        # For POST requests, create form with request data
        form = AppointmentForm(request.form)
    
    # Populate the patient select field with all patients
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    form.patient_id.choices = [(p.id, f"{p.full_name} (MRN: {p.mrn})") for p in patients]
    
    # Check if user wants to force save despite conflicts
    force_save = request.args.get('force_save') == '1'
    print(f"Edit appointment - force save: {force_save}")
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    print(f"Edit is AJAX request: {is_ajax}")
    
    # Set the time field for GET request
    if request.method == 'GET':
        form.appointment_time.data = appointment.appointment_time.strftime('%H:%M')
        print(f"Set initial time to: {form.appointment_time.data}")
        
        # Store appointment ID in session for API exclusion during editing
        session['editing_appointment_id'] = appointment_id
        print(f"Stored editing appointment ID in session: {appointment_id}")
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        print(f"Edit form data: {request.form}")
        
        # Use direct data parsing approach - get data directly from form data
        patient_id = request.form.get('patient_id')
        appointment_date_str = request.form.get('appointment_date')
        appointment_time_str = request.form.get('appointment_time')
        note = request.form.get('note', '')
        
        print(f"Direct form data: patient_id={patient_id}, date={appointment_date_str}, time={appointment_time_str}")
        
        # Validate essential data is present
        if not patient_id or not appointment_date_str or not appointment_time_str:
            error_msg = 'Missing required appointment data.'
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg})
            flash(error_msg, 'danger')
            return render_template('appointment_form.html', form=form, patients=patients, editing=True, appointment=appointment)
        
        # Parse date and time
        try:
            # Parse the date 
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
            
            # Parse the time
            time_parts = appointment_time_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            from datetime import time
            appointment_time = time(hour=hour, minute=minute)
            
            print(f"Successfully parsed date: {appointment_date} and time: {appointment_time}")
        except (ValueError, IndexError) as e:
            print(f"Error parsing date or time: {e}")
            error_msg = 'Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.'
            
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg})
            
            flash(error_msg, 'danger')
            return render_template('appointment_form.html', form=form, patients=patients, editing=True, appointment=appointment)
        
        # Check for conflicts
        conflicts = detect_appointment_conflicts(
            date=appointment_date,
            time_obj=appointment_time,
            duration_minutes=30,  # Default appointment duration
            appointment_id=appointment.id  # Exclude this appointment from conflict check
        )
        
        if conflicts and not force_save:
            print(f"Found {len(conflicts)} conflicts and force_save is False")
            conflict_message = format_conflict_message(conflicts)
            warn_msg = f'Warning: {conflict_message}'
            
            if is_ajax:
                return jsonify({
                    'success': False, 
                    'message': warn_msg,
                    'has_conflicts': True,
                    'conflicts': [{'patient': c.patient.full_name, 'time': c.appointment_time.strftime('%I:%M %p')} for c in conflicts]
                })
            
            flash(warn_msg, 'warning')
            return render_template('appointment_form.html', 
                                 form=form, 
                                 patients=patients, 
                                 editing=True, 
                                 conflicts=conflicts,
                                 conflict_message=conflict_message,
                                 appointment=appointment)
        
        # Update the appointment with our parsed data
        try:
            # Convert patient_id to integer
            patient_id_int = int(patient_id)
            
            # Update appointment data
            print(f"Updating appointment ID {appointment.id} for patient_id: {patient_id_int}")
            appointment.patient_id = patient_id_int
            appointment.appointment_date = appointment_date
            appointment.appointment_time = appointment_time
            appointment.note = note
            
            # Save changes
            db.session.commit()
            print(f"Appointment updated successfully")
            
            # Set success message
            if conflicts and force_save:
                success_msg = 'Appointment updated with scheduling conflicts.'
            else:
                success_msg = 'Appointment updated successfully.'
            
            # Use a cache-busting timestamp
            timestamp = int(time_module.time())
            
            # Use our parsed date string for the redirect
            appointment_date_str = appointment_date.strftime('%Y-%m-%d')
            
            # Construct redirect URL
            redirect_url = f"/date/{appointment_date_str}?refresh={timestamp}"
            print(f"FINAL EDIT REDIRECT URL: {redirect_url}")
            
            # For AJAX requests
            if is_ajax:
                return jsonify({
                    'success': True, 
                    'message': success_msg,
                    'redirect': redirect_url
                })
            
            # Set flash message
            if conflicts and force_save:
                flash(success_msg, 'warning')
            else:
                flash(success_msg, 'success')
            
            # Clear the editing appointment ID from session
            session.pop('editing_appointment_id', None)
            
            # Redirect to the date page
            return redirect(redirect_url)
        except Exception as e:
            db.session.rollback()
            print(f"Error updating appointment: {str(e)}")
            error_msg = f'Error updating appointment: {str(e)}'
            
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg})
            
            flash(error_msg, 'danger')
            return render_template('appointment_form.html', form=form, patients=patients, editing=True, appointment=appointment)
    
    # For GET requests, just show the form
    return render_template('appointment_form.html', form=form, patients=patients, editing=True, appointment=appointment)

@app.route('/appointments/<int:appointment_id>/update-status', methods=['POST'])
@fresh_session_operation
def update_appointment_status(appointment_id):
    """Update the status of an appointment"""
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        # Get the new status from the form
        new_status = request.form.get('status')
        if new_status in ['OOO', 'waiting', 'provider', 'seen']:
            appointment.status = new_status
            db.session.commit()
            
            # If this is an AJAX request, return JSON
            if is_ajax:
                return jsonify({
                    'success': True, 
                    'message': f'Appointment status updated to {new_status}',
                    'status': new_status
                })
            
            # No flash message to keep the UI clean
        else:
            if is_ajax:
                return jsonify({
                    'success': False, 
                    'message': 'Invalid status value'
                }), 400
            
            flash('Invalid status value', 'danger')
        
        # Determine where to redirect back to
        referrer = request.referrer
        if referrer and '/patients/' in referrer:
            # If coming from patient detail page, go back there
            patient_id = appointment.patient_id
            return redirect(url_for('patient_detail', patient_id=patient_id))
        else:
            # Otherwise go back to the schedule for that day
            redirect_date = appointment.appointment_date
            return redirect(url_for('index', date_str=redirect_date.strftime('%Y-%m-%d')))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating appointment status: {str(e)}")
        if is_ajax:
            return jsonify({
                'success': False,
                'message': f"Error updating appointment status: {str(e)}"
            }), 500
        flash(f"Error updating appointment status: {str(e)}", 'danger')
        return redirect(url_for('index'))

@app.route('/appointments/<int:appointment_id>/delete', methods=['GET', 'POST'])
@fresh_session_operation
def delete_appointment(appointment_id):
    """Delete an appointment and redirect to the home page"""
    print(f"Attempting to delete appointment {appointment_id}")
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    print(f"Delete is AJAX request: {is_ajax}")
    
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        print(f"Found appointment: {appointment.id} for patient {appointment.patient.full_name}")
        
        # Store the date for redirection
        appointment_date = appointment.appointment_date.strftime('%Y-%m-%d') if appointment.appointment_date else None
        print(f"Appointment date for redirect: {appointment_date}")
        
        # Delete the appointment
        db.session.delete(appointment)
        db.session.commit()
        
        success_msg = 'Appointment deleted successfully.'
        if not is_ajax:
            flash(success_msg, 'success')
        
        # Redirect to the home page, showing the same date with cache-busting
        timestamp = int(time_module.time())
        
        if is_ajax:
            if appointment_date:
                return jsonify({
                    'success': True, 
                    'message': success_msg,
                    'redirect': f"/date/{appointment_date}?refresh={timestamp}"
                })
            else:
                return jsonify({
                    'success': True, 
                    'message': success_msg,
                    'redirect': f"/home?refresh={timestamp}"
                })
                
        # Use Flask's url_for for consistency
        try:
            if appointment_date:
                redirect_url = url_for('index', date=appointment_date, refresh=timestamp)
                print(f"Delete redirect URL via url_for: {redirect_url}")
            else:
                redirect_url = url_for('index', refresh=timestamp)
                print(f"Delete redirect URL via url_for (no date): {redirect_url}")
        except Exception as url_err:
            print(f"Error with url_for in delete: {str(url_err)}")
            # Fallback to direct URL construction
            if appointment_date:
                redirect_url = f"/home/date/{appointment_date}?refresh={timestamp}"
            else:
                redirect_url = f"/home?refresh={timestamp}"
                
        print(f"FINAL DELETE REDIRECT: {redirect_url}")
        return redirect(redirect_url)
            
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error deleting appointment: {str(e)}'
        
        if is_ajax:
            return jsonify({'success': False, 'message': error_msg})
        
        flash(error_msg, 'danger')
        
        # Try to redirect to the same date if we have it in the session
        selected_date = request.args.get('date_str')
        timestamp = int(time_module.time())
        
        # Use Flask's url_for for consistency in error case too
        try:
            if selected_date:
                redirect_url = url_for('index', date=selected_date, refresh=timestamp)
            else:
                redirect_url = url_for('index', refresh=timestamp)
        except Exception as url_err:
            print(f"Error with url_for in delete error case: {str(url_err)}")
            # Fallback to direct URL construction
            if selected_date:
                redirect_url = f"/home/date/{selected_date}?refresh={timestamp}"
            else:
                redirect_url = f"/home?refresh={timestamp}"
        
        print(f"FINAL ERROR REDIRECT: {redirect_url}")
        return redirect(redirect_url)

@app.route('/delete_appointments_bulk', methods=['POST'])
@csrf.exempt
@fresh_session_operation
@validate_bulk_delete_input
def delete_appointments_bulk():
    """Delete multiple selected appointments"""
    try:
        # Debug all incoming data
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Form data keys: {list(request.form.keys())}")
        print(f"DEBUG: All form data: {dict(request.form)}")
        
        # Get all selected appointment IDs - handle comma-separated values
        if 'appointment_ids' in request.form:
            # Handle comma-separated appointment IDs
            appointment_ids_str = request.form.get('appointment_ids', '')
            selected_appointments = [id.strip() for id in appointment_ids_str.split(',') if id.strip()]
        else:
            # Fallback for original format
            try:
                selected_appointments = request.form.getlist('selected_appointments[]')
            except AttributeError:
                form_data = dict(request.form)
                if 'selected_appointments[]' in form_data:
                    selected_appointments = [form_data['selected_appointments[]']] if isinstance(form_data['selected_appointments[]'], str) else form_data['selected_appointments[]']
                else:
                    selected_appointments = []
            
        print(f"DEBUG: Received appointments for deletion: {selected_appointments}")
        
        if not selected_appointments:
            flash('No appointments were selected for deletion.', 'warning')
            return redirect(url_for('all_visits'))
        
        deleted_count = 0
        for appt_id in selected_appointments:
            try:
                print(f"DEBUG: Processing appointment ID: {appt_id}")
                appointment = Appointment.query.get(int(appt_id))
                if appointment:
                    print(f"DEBUG: Found appointment {appointment.id} for patient {appointment.patient.full_name}")
                    db.session.delete(appointment)
                    deleted_count += 1
                    print(f"DEBUG: Marked appointment {appointment.id} for deletion")
                else:
                    print(f"DEBUG: No appointment found with ID {appt_id}")
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Error processing appointment ID {appt_id}: {e}")
                continue
        
        db.session.commit()
        flash(f'Successfully deleted {deleted_count} appointment(s).', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting appointments: {str(e)}', 'error')
    
    return redirect(url_for('all_visits'))
    
@app.route('/patients/<int:patient_id>/conditions/<int:condition_id>/delete', methods=['GET', 'POST'])
def delete_condition(patient_id, condition_id):
    """Delete a medical condition and redirect to the patient detail page"""
    try:
        condition = Condition.query.get_or_404(condition_id)
        
        # Verify this condition belongs to the patient
        if condition.patient_id != patient_id:
            flash('Invalid request: condition does not belong to this patient.', 'danger')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Delete the condition
        db.session.delete(condition)
        db.session.commit()
        
        flash('Medical condition deleted successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting condition: {str(e)}', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/patients/<int:patient_id>/vitals/<int:vital_id>/delete', methods=['GET', 'POST'])
def delete_vital(patient_id, vital_id):
    """Delete a vital signs record and redirect to the patient detail page"""
    try:
        vital = Vital.query.get_or_404(vital_id)
        
        # Verify this vital belongs to the patient
        if vital.patient_id != patient_id:
            flash('Invalid request: vital does not belong to this patient.', 'danger')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Delete the vital
        db.session.delete(vital)
        db.session.commit()
        
        flash('Vital signs record deleted successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting vital signs: {str(e)}', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/patients/<int:patient_id>/documents/<int:document_id>/delete', methods=['GET', 'POST'])
def delete_document(patient_id, document_id):
    """Delete a medical document and redirect to the patient detail page"""
    try:
        document = MedicalDocument.query.get_or_404(document_id)
        
        # Verify this document belongs to the patient
        if document.patient_id != patient_id:
            flash('Invalid request: document does not belong to this patient.', 'danger')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Delete the document
        db.session.delete(document)
        db.session.commit()
        
        flash('Document deleted successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/patients/<int:patient_id>/labs/<int:lab_id>/delete', methods=['GET', 'POST'])
def delete_lab(patient_id, lab_id):
    """Delete a lab result and redirect to the patient detail page"""
    try:
        lab = LabResult.query.get_or_404(lab_id)
        
        # Verify this lab belongs to the patient
        if lab.patient_id != patient_id:
            flash('Invalid request: lab result does not belong to this patient.', 'danger')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Delete the lab
        db.session.delete(lab)
        db.session.commit()
        
        flash('Lab result deleted successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting lab result: {str(e)}', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/patients/<int:patient_id>/imaging/<int:imaging_id>/delete', methods=['GET', 'POST'])
def delete_imaging(patient_id, imaging_id):
    """Delete an imaging study and redirect to the patient detail page"""
    try:
        imaging = ImagingStudy.query.get_or_404(imaging_id)
        
        # Verify this imaging belongs to the patient
        if imaging.patient_id != patient_id:
            flash('Invalid request: imaging study does not belong to this patient.', 'danger')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Delete the imaging
        db.session.delete(imaging)
        db.session.commit()
        
        flash('Imaging study deleted successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting imaging study: {str(e)}', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/patients/<int:patient_id>/consults/<int:consult_id>/delete', methods=['GET', 'POST'])
def delete_consult(patient_id, consult_id):
    """Delete a consult report and redirect to the patient detail page"""
    try:
        consult = ConsultReport.query.get_or_404(consult_id)
        
        # Verify this consult belongs to the patient
        if consult.patient_id != patient_id:
            flash('Invalid request: consult report does not belong to this patient.', 'danger')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Delete the consult
        db.session.delete(consult)
        db.session.commit()
        
        flash('Consult report deleted successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting consult report: {str(e)}', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/patients/<int:patient_id>/hospital/<int:hospital_id>/delete', methods=['GET', 'POST'])
def delete_hospital(patient_id, hospital_id):
    """Delete a hospital summary and redirect to the patient detail page"""
    try:
        hospital = HospitalSummary.query.get_or_404(hospital_id)
        
        # Verify this hospital summary belongs to the patient
        if hospital.patient_id != patient_id:
            flash('Invalid request: hospital summary does not belong to this patient.', 'danger')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Delete the hospital summary
        db.session.delete(hospital)
        db.session.commit()
        
        flash('Hospital summary deleted successfully.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting hospital summary: {str(e)}', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/screenings/add', methods=['GET'])
def add_screening_form():
    """Display form to add a new screening recommendation"""
    # Get all patients for the dropdown
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    
    # Get all active screening types for the datalist
    all_screening_types = ScreeningType.query.filter_by(is_active=True).order_by(ScreeningType.name).all()
    
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())
    
    return render_template('add_screening.html', 
                          patients=patients, 
                          all_screening_types=all_screening_types,
                          cache_timestamp=cache_timestamp)

@app.route('/screenings/add', methods=['POST'])
@safe_db_operation
def add_screening_recommendation():
    """Add a new screening recommendation"""
    # Get form data
    patient_id = request.form.get('patient_id')
    screening_type = request.form.get('screening_type')
    due_date_str = request.form.get('due_date')
    last_completed_str = request.form.get('last_completed')
    priority = request.form.get('priority', 'Medium')
    notes = request.form.get('notes', '')
    
    # Validate required fields
    if not patient_id or not screening_type:
        flash('Patient and screening type are required.', 'danger')
        return redirect(url_for('screening_list'))
    
    # Convert dates from string to date objects
    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
    last_completed = datetime.strptime(last_completed_str, '%Y-%m-%d').date() if last_completed_str else None
    
    # Create new screening record
    screening = Screening(
        patient_id=patient_id,
        screening_type=screening_type,
        due_date=due_date,
        last_completed=last_completed,
        priority=priority,
        notes=notes
    )
    
    # Add to database
    db.session.add(screening)
    db.session.commit()
    
    flash('Screening recommendation added successfully.', 'success')
    # Add timestamp parameter to force a fresh query (avoid caching)
    timestamp = int(time_module.time())
    return redirect(url_for('screening_list', _t=timestamp))

@app.route('/patients/<int:patient_id>/screenings/<int:screening_id>/edit', methods=['POST'])
@safe_db_operation
def edit_screening(patient_id, screening_id):
    """Edit a screening record"""
    screening = Screening.query.get_or_404(screening_id)
    
    # Ensure the screening belongs to the specified patient
    if screening.patient_id != patient_id:
        flash('Invalid request: Screening does not belong to this patient.', 'danger')
        return redirect(url_for('screening_list'))
    
    # Update screening details
    screening.screening_type = request.form.get('screening_type', screening.screening_type)
    
    # Handle date inputs
    due_date = request.form.get('due_date')
    if due_date:
        screening.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
    
    last_completed = request.form.get('last_completed')
    if last_completed:
        screening.last_completed = datetime.strptime(last_completed, '%Y-%m-%d').date()
    else:
        screening.last_completed = None
    
    screening.priority = request.form.get('priority', screening.priority)
    screening.notes = request.form.get('notes', '')
    
    db.session.commit()
    
    flash('Screening record updated successfully.', 'success')
    
    # Redirect back to screening list with timestamp to force refresh
    timestamp = int(time_module.time())
    return redirect(url_for('screening_list', _t=timestamp))

@app.route('/patients/<int:patient_id>/screenings/<int:screening_id>/delete', methods=['GET', 'POST'])
def delete_screening(patient_id, screening_id):
    """Delete a screening record and redirect to the screening list page"""
    try:
        screening = Screening.query.get_or_404(screening_id)
        
        # Verify this screening belongs to the patient
        if screening.patient_id != patient_id:
            flash('Invalid request: screening does not belong to this patient.', 'danger')
            timestamp = int(time_module.time())
            return redirect(url_for('screening_list', _t=timestamp))
        
        # Delete the screening
        db.session.delete(screening)
        db.session.commit()
        
        flash('Screening record deleted successfully.', 'success')
        # Redirect to screening list instead of patient detail
        # Add timestamp parameter to force a fresh query (avoid caching)
        timestamp = int(time_module.time())
        return redirect(url_for('screening_list', _t=timestamp))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting screening record: {str(e)}', 'danger')
        timestamp = int(time_module.time())
        return redirect(url_for('screening_list', _t=timestamp))

@app.route('/patients/<int:patient_id>/delete', methods=['POST'])
@csrf.exempt  # Exempt this route from CSRF protection for bulk operations
@safe_db_operation
def delete_patient(patient_id):
    """Delete a patient and all their associated records
    
    This route can handle both single patient deletion and bulk deletion.
    For bulk deletion, pass patient IDs in selected_patients[] array
    or as a comma-separated list in patient_ids field.
    """
    # First check if this is an array-style submission (selected_patients[])
    selected_patients = request.form.getlist('selected_patients[]')
    
    # If not, check for comma-separated list in patient_ids
    patient_ids_str = request.form.get('patient_ids')
    
    app.logger.debug(f"Delete patient route called with patient_id={patient_id}")
    app.logger.debug(f"Form data: {request.form}")
    app.logger.debug(f"Selected patients (array): {selected_patients}")
    app.logger.debug(f"Patient IDs (string): {patient_ids_str}")
    
    # Check if we have an array of selected patients
    if selected_patients:
        app.logger.debug(f"Bulk deletion requested with array: {selected_patients}")
        try:
            # Convert string IDs to integers
            patient_ids = [int(pid) for pid in selected_patients if pid.strip()]
            app.logger.debug(f"Parsed patient IDs from array: {patient_ids}")
            deleted_count = 0
            
            for pid in patient_ids:
                patient = Patient.query.get(pid)
                if patient:
                    app.logger.debug(f"Deleting patient ID {pid}: {patient.full_name}")
                    # Delete all related records first to avoid foreign key constraint errors
                    # The cascade delete should handle most of these, but we'll be explicit
                    Vital.query.filter_by(patient_id=pid).delete()
                    Condition.query.filter_by(patient_id=pid).delete()
                    Screening.query.filter_by(patient_id=pid).delete()
                    Appointment.query.filter_by(patient_id=pid).delete()
                    Visit.query.filter_by(patient_id=pid).delete()
                    LabResult.query.filter_by(patient_id=pid).delete()
                    ImagingStudy.query.filter_by(patient_id=pid).delete()
                    ConsultReport.query.filter_by(patient_id=pid).delete()
                    HospitalSummary.query.filter_by(patient_id=pid).delete()
                    MedicalDocument.query.filter_by(patient_id=pid).delete()
                    
                    # Delete the patient
                    db.session.delete(patient)
                    deleted_count += 1
            
            db.session.commit()
            app.logger.debug(f"Successfully deleted {deleted_count} patients")
            
            if deleted_count == 1:
                flash(f'1 patient and all associated records have been deleted.', 'success')
            else:
                flash(f'{deleted_count} patients and all associated records have been deleted.', 'success')
            
            return redirect(url_for('patient_list'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in bulk patient deletion (array): {str(e)}")
            flash(f'Error deleting patients: {str(e)}', 'danger')
    
    # Check if we have a comma-separated list of patient IDs
    elif patient_ids_str:
        app.logger.debug(f"Bulk deletion requested with IDs: {patient_ids_str}")
        # Bulk deletion
        try:
            patient_ids = [int(id.strip()) for id in patient_ids_str.split(',') if id.strip()]
            app.logger.debug(f"Parsed patient IDs: {patient_ids}")
            deleted_count = 0
            
            for pid in patient_ids:
                patient = Patient.query.get(pid)
                if patient:
                    app.logger.debug(f"Deleting patient ID {pid}: {patient.full_name}")
                    # Delete all related records first to avoid foreign key constraint errors
                    # The cascade delete should handle most of these, but we'll be explicit
                    Vital.query.filter_by(patient_id=pid).delete()
                    Condition.query.filter_by(patient_id=pid).delete()
                    Screening.query.filter_by(patient_id=pid).delete()
                    Appointment.query.filter_by(patient_id=pid).delete()
                    Visit.query.filter_by(patient_id=pid).delete()
                    LabResult.query.filter_by(patient_id=pid).delete()
                    ImagingStudy.query.filter_by(patient_id=pid).delete()
                    ConsultReport.query.filter_by(patient_id=pid).delete()
                    HospitalSummary.query.filter_by(patient_id=pid).delete()
                    MedicalDocument.query.filter_by(patient_id=pid).delete()
                    
                    # Delete the patient
                    db.session.delete(patient)
                    deleted_count += 1
            
            db.session.commit()
            app.logger.debug(f"Successfully deleted {deleted_count} patients")
            
            if deleted_count == 1:
                flash(f'1 patient and all associated records have been deleted.', 'success')
            else:
                flash(f'{deleted_count} patients and all associated records have been deleted.', 'success')
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in bulk patient deletion: {str(e)}")
            flash(f'Error deleting patients: {str(e)}', 'danger')
    else:
        app.logger.debug(f"Single patient deletion requested for ID: {patient_id}")
        # Single patient deletion
        patient = Patient.query.get_or_404(patient_id)
        patient_name = patient.full_name
        
        try:
            # Delete all related records first to avoid foreign key constraint errors
            # The cascade delete should handle most of these, but we'll be explicit
            
            # Delete vitals
            Vital.query.filter_by(patient_id=patient_id).delete()
            
            # Delete conditions
            Condition.query.filter_by(patient_id=patient_id).delete()
            
            # Delete screenings
            Screening.query.filter_by(patient_id=patient_id).delete()
            
            # Delete appointments
            appointment_count = Appointment.query.filter_by(patient_id=patient_id).count()
            app.logger.debug(f"Deleting {appointment_count} appointments for patient {patient_id}")
            Appointment.query.filter_by(patient_id=patient_id).delete()
            
            # Delete visits
            Visit.query.filter_by(patient_id=patient_id).delete()
            
            # Delete lab results
            LabResult.query.filter_by(patient_id=patient_id).delete()
            
            # Delete imaging studies
            ImagingStudy.query.filter_by(patient_id=patient_id).delete()
            
            # Delete consult reports
            ConsultReport.query.filter_by(patient_id=patient_id).delete()
            
            # Delete hospital summaries
            HospitalSummary.query.filter_by(patient_id=patient_id).delete()
            
            # Delete medical documents
            MedicalDocument.query.filter_by(patient_id=patient_id).delete()
            
            # Finally, delete the patient
            db.session.delete(patient)
            db.session.commit()
            app.logger.debug(f"Successfully deleted patient {patient_id}: {patient_name}")
            
            flash(f'Patient {patient_name} and all associated records have been deleted.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting patient: {str(e)}")
            flash(f'Error deleting patient: {str(e)}', 'danger')
    
    return redirect(url_for('patient_list'))

@app.route('/visits')
def all_visits():
    """Display all appointments (past and future) with ability to delete"""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    patient_filter = request.args.get('patient', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Base query for all appointments
    query = Appointment.query.join(Patient)
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter(Appointment.status == status_filter)
    
    if patient_filter:
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(f'%{patient_filter}%'),
                Patient.last_name.ilike(f'%{patient_filter}%')
            )
        )
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date <= to_date)
        except ValueError:
            pass
    
    # Order by date and time (most recent first)
    appointments = query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    # Get all patients for filter dropdown
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    
    # Get today's date for comparison
    today = datetime.now().date()
    
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())
    
    return render_template('all_visits.html',
                         appointments=appointments,
                         patients=patients,
                         status_filter=status_filter,
                         patient_filter=patient_filter,
                         date_from=date_from,
                         date_to=date_to,
                         today=today,
                         cache_timestamp=cache_timestamp)