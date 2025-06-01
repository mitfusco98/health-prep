from flask import jsonify, request, g
from app import app, db, csrf
from models import Patient, Condition, Vital, LabResult, Visit, ImagingStudy, ConsultReport, HospitalSummary, Screening, MedicalDocument, Appointment, PatientAlert
from jwt_utils import jwt_required, optional_jwt, admin_required
from datetime import datetime, date, timedelta
import logging
from sqlalchemy import func, or_

logger = logging.getLogger(__name__)

@app.route('/api/patients', methods=['GET'])
@csrf.exempt
@jwt_required
def api_patients():
    """
    Get paginated list of patients (JWT protected)

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - search: Search term for name or MRN
    - sort: Sort field (name, mrn, age, created_at)
    - order: Sort order (asc, desc)
    """
    try:
        # Get and validate query parameters
        try:
            page = int(request.args.get('page', 1))
            if page < 1:
                return jsonify({'error': 'page must be a positive integer'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'page must be a valid integer'}), 400

        try:
            per_page = int(request.args.get('per_page', 20))
            if per_page < 1 or per_page > 100:
                return jsonify({'error': 'per_page must be between 1 and 100'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'per_page must be a valid integer'}), 400

        search_term = request.args.get('search', '').strip()
        if len(search_term) > 100:
            return jsonify({'error': 'search term must be maximum 100 characters'}), 400

        sort_field = request.args.get('sort', 'created_at')
        valid_sort_fields = ['name', 'mrn', 'age', 'created_at']
        if sort_field not in valid_sort_fields:
            return jsonify({'error': f'sort field must be one of: {", ".join(valid_sort_fields)}'}), 400

        sort_order = request.args.get('order', 'desc')
        if sort_order not in ['asc', 'desc']:
            return jsonify({'error': 'order must be either "asc" or "desc"'}), 400

        # Build query
        query = Patient.query

        # Apply search filter
        if search_term:
            search_filter = or_(
                Patient.first_name.ilike(f'%{search_term}%'),
                Patient.last_name.ilike(f'%{search_term}%'),
                Patient.mrn.ilike(f'%{search_term}%'),
                func.concat(Patient.first_name, ' ', Patient.last_name).ilike(f'%{search_term}%')
            )
            query = query.filter(search_filter)

        # Apply sorting
        if sort_field == 'name':
            sort_column = Patient.first_name
        elif sort_field == 'mrn':
            sort_column = Patient.mrn
        elif sort_field == 'age':
            sort_column = Patient.date_of_birth
            # For age, reverse the order since older birth dates = older age
            sort_order = 'asc' if sort_order == 'desc' else 'desc'
        else:
            sort_column = Patient.created_at

        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Serialize patients
        patients_data = []
        for patient in pagination.items:
            patients_data.append({
                'id': patient.id,
                'mrn': patient.mrn,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'full_name': patient.full_name,
                'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                'age': patient.age,
                'sex': patient.sex,
                'phone': patient.phone,
                'email': patient.email,
                'address': patient.address,
                'insurance': patient.insurance,
                'created_at': patient.created_at.isoformat() if patient.created_at else None,
                'updated_at': patient.updated_at.isoformat() if patient.updated_at else None
            })

        return jsonify({
            'patients': patients_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_num': pagination.next_num,
                'prev_num': pagination.prev_num
            },
            'search': search_term,
            'sort': {
                'field': sort_field,
                'order': sort_order
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in API patients endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/patients/<patient_id>', methods=['GET'])
@csrf.exempt
@jwt_required
def api_patient_detail(patient_id):
    """
    Get detailed information for a specific patient (JWT protected)
    """
    try:
        # Validate patient ID format
        try:
            patient_id_int = int(patient_id)
            if patient_id_int <= 0:
                return jsonify({'error': 'Patient ID must be a positive integer'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Patient ID must be a valid integer'}), 400

        patient = Patient.query.get(patient_id_int)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404


        # Get related data
        conditions = Condition.query.filter_by(patient_id=patient_id_int, is_active=True).all()
        recent_vitals = Vital.query.filter_by(patient_id=patient_id_int)\
            .order_by(Vital.date.desc()).limit(5).all()
        recent_visits = Visit.query.filter_by(patient_id=patient_id_int)\
            .order_by(Visit.visit_date.desc()).limit(5).all()
        screenings = Screening.query.filter_by(patient_id=patient_id_int).all()
        alerts = PatientAlert.query.filter_by(patient_id=patient_id_int, is_active=True).all()

        # Serialize patient data
        patient_data = {
            'id': patient.id,
            'mrn': patient.mrn,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'full_name': patient.full_name,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'age': patient.age,
            'sex': patient.sex,
            'phone': patient.phone,
            'email': patient.email,
            'address': patient.address,
            'insurance': patient.insurance,
            'created_at': patient.created_at.isoformat() if patient.created_at else None,
            'updated_at': patient.updated_at.isoformat() if patient.updated_at else None,
            'conditions': [{
                'id': c.id,
                'name': c.name,
                'code': c.code,
                'diagnosed_date': c.diagnosed_date.isoformat() if c.diagnosed_date else None,
                'notes': c.notes
            } for c in conditions],
            'recent_vitals': [{
                'id': v.id,
                'date': v.date.isoformat() if v.date else None,
                'weight': v.weight,
                'height': v.height,
                'bmi': v.bmi,
                'temperature': v.temperature,
                'blood_pressure_systolic': v.blood_pressure_systolic,
                'blood_pressure_diastolic': v.blood_pressure_diastolic,
                'pulse': v.pulse,
                'respiratory_rate': v.respiratory_rate,
                'oxygen_saturation': v.oxygen_saturation
            } for v in recent_vitals],
            'recent_visits': [{
                'id': v.id,
                'visit_date': v.visit_date.isoformat() if v.visit_date else None,
                'visit_type': v.visit_type,
                'provider': v.provider,
                'reason': v.reason,
                'notes': v.notes
            } for v in recent_visits],
            'screenings': [{
                'id': s.id,
                'screening_type': s.screening_type,
                'due_date': s.due_date.isoformat() if s.due_date else None,
                'last_completed': s.last_completed.isoformat() if s.last_completed else None,
                'frequency': s.frequency,
                'priority': s.priority,
                'notes': s.notes
            } for s in screenings],
            'alerts': [{
                'id': a.id,
                'alert_type': a.alert_type,
                'description': a.description,
                'details': a.details,
                'severity': a.severity,
                'start_date': a.start_date.isoformat() if a.start_date else None,
                'end_date': a.end_date.isoformat() if a.end_date else None
            } for a in alerts]
        }

        return jsonify(patient_data), 200

    except Exception as e:
        logger.error(f"Error in API patient detail endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def validate_patient_fields(data):
    """Validate patient data fields"""
    errors = []

    # Required fields validation
    required_fields = ['first_name', 'last_name', 'date_of_birth', 'sex']
    for field in required_fields:
        if not data.get(field) or not str(data.get(field)).strip():
            errors.append(f'{field} is required')

    # Field type and format validation
    if 'first_name' in data:
        if not isinstance(data['first_name'], str) or len(data['first_name'].strip()) > 100:
            errors.append('first_name must be a string with maximum 100 characters')
        elif not data['first_name'].strip().replace(' ', '').replace('-', '').replace("'", '').replace('.', '').isalpha():
            errors.append('first_name contains invalid characters')

    if 'last_name' in data:
        if not isinstance(data['last_name'], str) or len(data['last_name'].strip()) > 100:
            errors.append('last_name must be a string with maximum 100 characters')
        elif not data['last_name'].strip().replace(' ', '').replace('-', '').replace("'", '').replace('.', '').isalpha():
            errors.append('last_name contains invalid characters')

    if 'sex' in data:
        valid_sex_values = ['Male', 'Female', 'Other', 'Unknown']
        if data['sex'] not in valid_sex_values:
            errors.append(f'sex must be one of: {", ".join(valid_sex_values)}')

    if 'email' in data and data['email']:
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']) or len(data['email']) > 254:
            errors.append('email format is invalid')

    if 'phone' in data and data['phone']:
        import re
        phone_digits = re.sub(r'\D', '', data['phone'])
        if len(phone_digits) < 10 or len(phone_digits) > 15:
            errors.append('phone number must contain 10-15 digits')

    if 'mrn' in data and data['mrn']:
        import re
        if not re.match(r'^[A-Za-z0-9\-]+$', data['mrn']) or len(data['mrn']) < 3 or len(data['mrn']) > 20:
            errors.append('mrn must be alphanumeric with optional hyphens, 3-20 characters')

    if 'address' in data and data['address'] and len(data['address']) > 500:
        errors.append('address must be maximum 500 characters')

    if 'insurance' in data and data['insurance'] and len(data['insurance']) > 200:
        errors.append('insurance must be maximum 200 characters')

    return errors

@app.route('/api/patients', methods=['POST'])
@csrf.exempt
@jwt_required
def api_create_patient():
    """Create a new patient via API"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate data size limits first
        errors = []
        field_limits = {
            'first_name': 100,
            'last_name': 100,
            'email': 254,
            'phone': 20,
            'address': 500,
            'mrn': 20
        }

        for field, max_length in field_limits.items():
            if field in data and data[field] and len(str(data[field])) > max_length:
                errors.append(f"{field} must be {max_length} characters or less")

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'sex']

        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f'{field} is required')
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f'{field} cannot be empty or contain only whitespace')

        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400

        # Parse date of birth
        try:
            dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Generate MRN if not provided
        mrn = data.get('mrn')
        if not mrn:
            from utils import get_next_available_mrn
            mrn = get_next_available_mrn()

        # Check if MRN already exists
        existing_patient = Patient.query.filter_by(mrn=mrn).first()
        if existing_patient:
            return jsonify({'error': 'MRN already exists'}), 409

        # Create new patient
        patient = Patient(
            first_name=data['first_name'],
            last_name=data['last_name'],
            date_of_birth=dob,
            sex=data['sex'],
            mrn=mrn,
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            address=data.get('address', ''),
            insurance=data.get('insurance', '')
        )

        db.session.add(patient)
        db.session.commit()

        # Evaluate screening needs
        from utils import evaluate_screening_needs
        evaluate_screening_needs(patient)

        logger.info(f"Created new patient: {patient.full_name} (MRN: {patient.mrn}) by user {g.current_user.username}")

        return jsonify({
            'id': patient.id,
            'mrn': patient.mrn,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'full_name': patient.full_name,
            'date_of_birth': patient.date_of_birth.isoformat(),
            'age': patient.age,
            'sex': patient.sex,
            'phone': patient.phone,
            'email': patient.email,
            'address': patient.address,
            'insurance': patient.insurance,
            'created_at': patient.created_at.isoformat()
        }), 201

    except Exception as e:
        logger.error(f"Error creating patient via API: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/appointments', methods=['GET'])
@csrf.exempt
@jwt_required
def api_appointments():
    """
    Get appointments for a specific date (JWT protected)

    Query parameters:
    - date: Date in YYYY-MM-DD format (default: today)
    """
    try:
        # Get and validate date parameter
        date_str = request.args.get('date')
        if date_str:
            if len(date_str) != 10:
                return jsonify({'error': 'Date must be in YYYY-MM-DD format'}), 400
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                # Validate reasonable date range (not too far in past or future)
                # Validate reasonable date range (1900 to 2100)
                if selected_date.year < 1900 or selected_date.year > 2100:
                    return jsonify({'error': 'Date must be within reasonable range'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            selected_date = date.today()

        # Get appointments for the selected date
        appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == selected_date
        ).order_by(Appointment.appointment_time).all()

        # Serialize appointments
        appointments_data = []
        for apt in appointments:
            appointments_data.append({
                'id': apt.id,
                'patient_id': apt.patient_id,
                'patient_name': apt.patient.full_name,
                'patient_mrn': apt.patient.mrn,
                'appointment_date': apt.appointment_date.isoformat(),
                'appointment_time': apt.appointment_time.strftime('%H:%M'),
                'note': apt.note,
                'status': apt.status
            })

        return jsonify({
            'date': selected_date.isoformat(),
            'appointments': appointments_data,
            'total': len(appointments_data)
        }), 200

    except Exception as e:
        logger.error(f"Error in API appointments endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500