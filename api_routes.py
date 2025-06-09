from flask import jsonify, request, g
from app import app, db, csrf
from models import Patient, Condition, Vital, LabResult, Visit, ImagingStudy, ConsultReport, HospitalSummary, Screening, MedicalDocument, Appointment, PatientAlert
from jwt_utils import jwt_required, optional_jwt, admin_required
from cache_manager import cache_route, invalidate_cache_pattern, cache_manager
from datetime import datetime, date, timedelta
import logging
from sqlalchemy import func, or_

logger = logging.getLogger(__name__)

@app.route('/api/patients', methods=['GET'])
@csrf.exempt
@jwt_required
@cache_route(timeout=300, vary_on=['page', 'per_page', 'search', 'sort', 'order'])
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
@cache_route(timeout=600, vary_on=['patient_id'])
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


        # Get query parameters for lazy loading
        include_vitals = request.args.get('include_vitals', 'false').lower() == 'true'
        include_visits = request.args.get('include_visits', 'false').lower() == 'true'
        include_screenings = request.args.get('include_screenings', 'false').lower() == 'true'
        include_alerts = request.args.get('include_alerts', 'false').lower() == 'true'
        
        # Always load basic conditions (lightweight)
        conditions = Condition.query.filter_by(patient_id=patient_id_int, is_active=True).limit(10).all()
        
        # Conditionally load heavy data
        recent_vitals = []
        recent_visits = []
        screenings = []
        alerts = []
        
        if include_vitals:
            recent_vitals = Vital.query.filter_by(patient_id=patient_id_int)\
                .order_by(Vital.date.desc()).limit(5).all()
        
        if include_visits:
            recent_visits = Visit.query.filter_by(patient_id=patient_id_int)\
                .order_by(Visit.visit_date.desc()).limit(5).all()
        
        if include_screenings:
            screenings = Screening.query.filter_by(patient_id=patient_id_int).limit(20).all()
        
        if include_alerts:
            alerts = PatientAlert.query.filter_by(patient_id=patient_id_int, is_active=True).limit(10).all()

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

@app.route('/api/patients/<patient_id>/vitals', methods=['GET'])
@csrf.exempt
@jwt_required
@cache_route(timeout=300, vary_on=['patient_id', 'limit'])
def api_patient_vitals(patient_id):
    """Get patient vitals separately for lazy loading"""
    try:
        patient_id_int = int(patient_id)
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 records
        
        vitals = Vital.query.filter_by(patient_id=patient_id_int)\
            .order_by(Vital.date.desc()).limit(limit).all()
        
        vitals_data = [{
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
        } for v in vitals]
        
        return jsonify({'vitals': vitals_data}), 200
        
    except Exception as e:
        logger.error(f"Error fetching patient vitals: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/patients/<patient_id>/visits', methods=['GET'])
@csrf.exempt
@jwt_required
@cache_route(timeout=300, vary_on=['patient_id', 'limit', 'page'])
def api_patient_visits(patient_id):
    """Get patient visits with pagination"""
    try:
        patient_id_int = int(patient_id)
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 25)  # Max 25 per page
        
        pagination = Visit.query.filter_by(patient_id=patient_id_int)\
            .order_by(Visit.visit_date.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        visits_data = [{
            'id': v.id,
            'visit_date': v.visit_date.isoformat() if v.visit_date else None,
            'visit_type': v.visit_type,
            'provider': v.provider,
            'reason': v.reason,
            'notes': v.notes[:200] + '...' if v.notes and len(v.notes) > 200 else v.notes  # Truncate long notes
        } for v in pagination.items]
        
        return jsonify({
            'visits': visits_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching patient visits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/patients/<patient_id>/documents/summary', methods=['GET'])
@csrf.exempt
@jwt_required
@cache_route(timeout=600, vary_on=['patient_id'])
def api_patient_documents_summary(patient_id):
    """Get lightweight document summary without full content"""
    try:
        patient_id_int = int(patient_id)
        
        documents = MedicalDocument.query.filter_by(patient_id=patient_id_int)\
            .with_entities(
                MedicalDocument.id,
                MedicalDocument.filename,
                MedicalDocument.document_type,
                MedicalDocument.document_date,
                MedicalDocument.provider,
                MedicalDocument.source_system
            ).order_by(MedicalDocument.document_date.desc()).limit(50).all()
        
        documents_data = [{
            'id': doc.id,
            'filename': doc.filename,
            'document_type': doc.document_type,
            'document_date': doc.document_date.isoformat() if doc.document_date else None,
            'provider': doc.provider,
            'source_system': doc.source_system
        } for doc in documents]
        
        return jsonify({'documents': documents_data}), 200
        
    except Exception as e:
        logger.error(f"Error fetching patient documents summary: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
        # Check content length before parsing JSON
        content_length = request.content_length
        if content_length and content_length > 1024 * 1024:  # 1MB limit
            return jsonify({'error': 'Request too large. Maximum size is 1MB.'}), 413

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Check for extremely large field values that would indicate a potential attack
        total_size = sum(len(str(value)) for value in data.values() if value is not None)
        if total_size > 100000:  # 100KB total data
            return jsonify({'error': 'Request too large. Total data exceeds maximum size.'}), 413
            
        for field, value in data.items():
            if isinstance(value, str) and len(value) > 50000:  # 50KB per field
                return jsonify({'error': 'Request too large. Field values exceed maximum length.'}), 413

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

        # Invalidate patient-related caches
        invalidate_cache_pattern('api_patients*')
        invalidate_cache_pattern('patients*')

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
@cache_route(timeout=180, vary_on=['date'])
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
                # Validate reasonable date range (1950 to 2050 for medical appointments)
                if selected_date.year < 1950 or selected_date.year > 2050:
                    return jsonify({'error': 'Date must be within reasonable range (1950-2050)'}), 400
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


@app.route('/api/cache/stats', methods=['GET'])
@csrf.exempt
@jwt_required
@admin_required
def api_cache_stats():
    """Get cache statistics (admin only)"""
    try:
        stats = cache_manager.get_stats()
        
        return jsonify({
            'cache_type': 'redis' if cache_manager.redis_client else 'memory',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cache/clear', methods=['POST'])
@csrf.exempt
@jwt_required
@admin_required
def api_cache_clear():
    """Clear cache (admin only)"""
    try:
        pattern = request.json.get('pattern', '*') if request.json else '*'
        
        if pattern == '*':
            cache_manager.clear_all()
            message = 'All cache cleared'
        else:
            invalidate_cache_pattern(pattern)
            message = f'Cache cleared for pattern: {pattern}'
        
        logger.info(f"Cache cleared by admin {g.current_user.username}: {pattern}")
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/config', methods=['GET'])
@csrf.exempt
@cache_route(timeout=3600)  # Cache for 1 hour since config rarely changes
def api_config():
    """Get frontend configuration"""
    try:
        from config import get_config
        
        config = get_config()
        frontend_config = config.get_frontend_config()
        
        return jsonify(frontend_config), 200
        
    except Exception as e:
        logger.error(f"Error getting frontend config: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
