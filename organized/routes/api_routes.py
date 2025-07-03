from flask import jsonify, request, g
from app import app, db, csrf
from models import (
    Patient,
    Condition,
    Vital,
    LabResult,
    Visit,
    ImagingStudy,
    ConsultReport,
    HospitalSummary,
    Screening,
    MedicalDocument,
    Appointment,
    PatientAlert,
)
from jwt_utils import jwt_required, optional_jwt, admin_required
from cache_manager import cache_route, invalidate_cache_pattern, cache_manager
from db_utils import (
    get_patient_by_id_or_404,
    search_patients,
    get_appointments_for_date,
    get_patient_recent_vitals,
    get_patient_recent_visits,
    get_patient_screenings,
    serialize_patient_basic,
    serialize_appointment,
)
from datetime import datetime, date, timedelta
import logging
from sqlalchemy import func, or_
from comprehensive_logging import log_patient_operation, log_data_modification

logger = logging.getLogger(__name__)


@app.route("/api/patients", methods=["GET"])
@csrf.exempt
@jwt_required
@cache_route(timeout=300, vary_on=["page", "per_page", "search", "sort", "order"])
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
            page = int(request.args.get("page", 1))
            if page < 1:
                return jsonify({"error": "page must be a positive integer"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "page must be a valid integer"}), 400

        try:
            per_page = int(request.args.get("per_page", 20))
            if per_page < 1 or per_page > 100:
                return jsonify({"error": "per_page must be between 1 and 100"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "per_page must be a valid integer"}), 400

        search_term = request.args.get("search", "").strip()
        if len(search_term) > 100:
            return jsonify({"error": "search term must be maximum 100 characters"}), 400

        sort_field = request.args.get("sort", "created_at")
        valid_sort_fields = ["name", "mrn", "age", "created_at"]
        if sort_field not in valid_sort_fields:
            return (
                jsonify(
                    {
                        "error": f'sort field must be one of: {", ".join(valid_sort_fields)}'
                    }
                ),
                400,
            )

        sort_order = request.args.get("order", "desc")
        if sort_order not in ["asc", "desc"]:
            return jsonify({"error": 'order must be either "asc" or "desc"'}), 400

        # Use shared search function
        pagination = search_patients(
            search_term, page, per_page, sort_field, sort_order
        )

        # Serialize patients with minimal fields for list view
        patients_data = [
            {
                "id": patient.id,
                "mrn": patient.mrn,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "age": patient.age,
                "sex": patient.sex,
                "phone": (
                    patient.phone[:12] + "..."
                    if patient.phone and len(patient.phone) > 12
                    else patient.phone
                ),  # Truncate long phone numbers
                "created_at": (
                    patient.created_at.strftime("%Y-%m-%d")
                    if patient.created_at
                    else None
                ),  # Date only, not full timestamp
            }
            for patient in pagination.items
        ]

        return (
            jsonify(
                {
                    "patients": patients_data,
                    "pagination": {
                        "page": pagination.page,
                        "per_page": pagination.per_page,
                        "total": pagination.total,
                        "pages": pagination.pages,
                        "has_next": pagination.has_next,
                        "has_prev": pagination.has_prev,
                        "next_num": pagination.next_num,
                        "prev_num": pagination.prev_num,
                    },
                    "search": search_term,
                    "sort": {"field": sort_field, "order": sort_order},
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in API patients endpoint: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<patient_id>", methods=["GET"])
@csrf.exempt
@jwt_required
@cache_route(timeout=600, vary_on=["patient_id"])
def api_patient_detail(patient_id):
    """
    Get detailed information for a specific patient (JWT protected)
    """
    try:
        patient = get_patient_by_id_or_404(patient_id)
        if not patient:
            return jsonify({"error": "Patient not found"}), 404

        # Get query parameters for lazy loading
        include_vitals = request.args.get("include_vitals", "false").lower() == "true"
        include_visits = request.args.get("include_visits", "false").lower() == "true"
        include_screenings = (
            request.args.get("include_screenings", "false").lower() == "true"
        )
        include_alerts = request.args.get("include_alerts", "false").lower() == "true"

        # Load only essential condition data
        conditions = (
            Condition.query.filter_by(patient_id=patient.id, is_active=True)
            .with_entities(Condition.id, Condition.name, Condition.code)
            .limit(5)
            .all()
        )

        # Conditionally load heavy data with minimal fields
        recent_vitals = []
        if include_vitals:
            vitals = (
                Vital.query.filter_by(patient_id=patient.id)
                .with_entities(
                    Vital.id,
                    Vital.date,
                    Vital.weight,
                    Vital.height,
                    Vital.blood_pressure_systolic,
                    Vital.blood_pressure_diastolic,
                )
                .order_by(Vital.date.desc())
                .limit(3)
                .all()
            )
            recent_vitals = vitals

        recent_visits = []
        if include_visits:
            visits = (
                Visit.query.filter_by(patient_id=patient.id)
                .with_entities(
                    Visit.id, Visit.visit_date, Visit.visit_type, Visit.provider
                )
                .order_by(Visit.visit_date.desc())
                .limit(3)
                .all()
            )
            recent_visits = visits

        screenings = get_patient_screenings(patient.id) if include_screenings else []
        alerts = (
            PatientAlert.query.filter_by(patient_id=patient.id, is_active=True)
            .with_entities(
                PatientAlert.id,
                PatientAlert.alert_type,
                PatientAlert.description,
                PatientAlert.severity,
            )
            .limit(5)
            .all()
            if include_alerts
            else []
        )

        # Serialize patient data with essential fields only
        patient_data = {
            "id": patient.id,
            "mrn": patient.mrn,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "age": patient.age,
            "sex": patient.sex,
            "phone": patient.phone,
            "email": patient.email,
            # Remove address and insurance from API response for privacy
            "created_at": (
                patient.created_at.strftime("%Y-%m-%d") if patient.created_at else None
            ),
            "conditions": [
                {"id": c.id, "name": c.name, "code": c.code} for c in conditions
            ],
            "recent_vitals": [
                {
                    "id": v.id,
                    "date": v.date.strftime("%Y-%m-%d") if v.date else None,
                    "weight": v.weight,
                    "height": v.height,
                    "bp": (
                        f"{v.blood_pressure_systolic}/{v.blood_pressure_diastolic}"
                        if v.blood_pressure_systolic and v.blood_pressure_diastolic
                        else None
                    ),
                }
                for v in recent_vitals
            ],
            "recent_visits": [
                {
                    "id": v.id,
                    "visit_date": (
                        v.visit_date.strftime("%Y-%m-%d") if v.visit_date else None
                    ),
                    "visit_type": v.visit_type,
                    "provider": v.provider,
                }
                for v in recent_visits
            ],
            "screenings": [
                {
                    "id": s.id,
                    "screening_type": s.screening_type,
                    "due_date": s.due_date.isoformat() if s.due_date else None,
                    "last_completed": (
                        s.last_completed.isoformat() if s.last_completed else None
                    ),
                    "frequency": s.frequency,
                    "priority": s.priority,
                    "notes": s.notes,
                }
                for s in screenings
            ],
            "alerts": [
                {
                    "id": a.id,
                    "alert_type": a.alert_type,
                    "description": a.description,
                    "details": a.details,
                    "severity": a.severity,
                    "start_date": a.start_date.isoformat() if a.start_date else None,
                    "end_date": a.end_date.isoformat() if a.end_date else None,
                }
                for a in alerts
            ],
        }

        return jsonify(patient_data), 200

    except Exception as e:
        logger.error(f"Error in API patient detail endpoint: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def validate_patient_fields(data):
    """Validate patient data fields"""
    errors = []

    # Required fields validation
    required_fields = ["first_name", "last_name", "date_of_birth", "sex"]
    for field in required_fields:
        if not data.get(field) or not str(data.get(field)).strip():
            errors.append(f"{field} is required")

    # Field type and format validation
    if "first_name" in data:
        if (
            not isinstance(data["first_name"], str)
            or len(data["first_name"].strip()) > 100
        ):
            errors.append("first_name must be a string with maximum 100 characters")
        elif (
            not data["first_name"]
            .strip()
            .replace(" ", "")
            .replace("-", "")
            .replace("'", "")
            .replace(".", "")
            .isalpha()
        ):
            errors.append("first_name contains invalid characters")

    if "last_name" in data:
        if (
            not isinstance(data["last_name"], str)
            or len(data["last_name"].strip()) > 100
        ):
            errors.append("last_name must be a string with maximum 100 characters")
        elif (
            not data["last_name"]
            .strip()
            .replace(" ", "")
            .replace("-", "")
            .replace("'", "")
            .replace(".", "")
            .isalpha()
        ):
            errors.append("last_name contains invalid characters")

    if "sex" in data:
        valid_sex_values = ["Male", "Female", "Other", "Unknown"]
        if data["sex"] not in valid_sex_values:
            errors.append(f'sex must be one of: {", ".join(valid_sex_values)}')

    if "email" in data and data["email"]:
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, data["email"]) or len(data["email"]) > 254:
            errors.append("email format is invalid")

    if "phone" in data and data["phone"]:
        import re

        phone_digits = re.sub(r"\D", "", data["phone"])
        if len(phone_digits) < 10 or len(phone_digits) > 15:
            errors.append("phone number must contain 10-15 digits")

    if "mrn" in data and data["mrn"]:
        import re

        if (
            not re.match(r"^[A-Za-z0-9\-]+$", data["mrn"])
            or len(data["mrn"]) < 3
            or len(data["mrn"]) > 20
        ):
            errors.append(
                "mrn must be alphanumeric with optional hyphens, 3-20 characters"
            )

    if "address" in data and data["address"] and len(data["address"]) > 500:
        errors.append("address must be maximum 500 characters")

    if "insurance" in data and data["insurance"] and len(data["insurance"]) > 200:
        errors.append("insurance must be maximum 200 characters")

    return errors


@app.route("/api/patients/<patient_id>/vitals", methods=["GET"])
@csrf.exempt
@jwt_required
@cache_route(timeout=300, vary_on=["patient_id", "limit"])
def api_patient_vitals(patient_id):
    """Get patient vitals separately for lazy loading"""
    try:
        patient_id_int = int(patient_id)
        limit = min(int(request.args.get("limit", 10)), 50)  # Max 50 records

        vitals = (
            Vital.query.filter_by(patient_id=patient_id_int)
            .order_by(Vital.date.desc())
            .limit(limit)
            .all()
        )

        vitals_data = [
            {
                "id": v.id,
                "date": v.date.isoformat() if v.date else None,
                "weight": v.weight,
                "height": v.height,
                "bmi": v.bmi,
                "temperature": v.temperature,
                "blood_pressure_systolic": v.blood_pressure_systolic,
                "blood_pressure_diastolic": v.blood_pressure_diastolic,
                "pulse": v.pulse,
                "respiratory_rate": v.respiratory_rate,
                "oxygen_saturation": v.oxygen_saturation,
            }
            for v in vitals
        ]

        return jsonify({"vitals": vitals_data}), 200

    except Exception as e:
        logger.error(f"Error fetching patient vitals: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<patient_id>/visits", methods=["GET"])
@csrf.exempt
@jwt_required
@cache_route(timeout=300, vary_on=["patient_id", "limit", "page"])
def api_patient_visits(patient_id):
    """Get patient visits with pagination"""
    try:
        patient_id_int = int(patient_id)
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 10)), 25)  # Max 25 per page

        pagination = (
            Visit.query.filter_by(patient_id=patient_id_int)
            .order_by(Visit.visit_date.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        visits_data = [
            {
                "id": v.id,
                "visit_date": v.visit_date.isoformat() if v.visit_date else None,
                "visit_type": v.visit_type,
                "provider": v.provider,
                "reason": v.reason,
                "notes": (
                    v.notes[:200] + "..." if v.notes and len(v.notes) > 200 else v.notes
                ),  # Truncate long notes
            }
            for v in pagination.items
        ]

        return (
            jsonify(
                {
                    "visits": visits_data,
                    "pagination": {
                        "page": pagination.page,
                        "per_page": pagination.per_page,
                        "total": pagination.total,
                        "pages": pagination.pages,
                        "has_next": pagination.has_next,
                        "has_prev": pagination.has_prev,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error fetching patient visits: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<patient_id>/documents/summary", methods=["GET"])
@csrf.exempt
@jwt_required
@cache_route(timeout=600, vary_on=["patient_id"])
def api_patient_documents_summary(patient_id):
    """Get lightweight document summary without full content"""
    try:
        patient_id_int = int(patient_id)

        documents = (
            MedicalDocument.query.filter_by(patient_id=patient_id_int)
            .with_entities(
                MedicalDocument.id,
                MedicalDocument.filename,
                MedicalDocument.document_type,
                MedicalDocument.document_date,
                MedicalDocument.provider,
                MedicalDocument.source_system,
            )
            .order_by(MedicalDocument.document_date.desc())
            .limit(50)
            .all()
        )

        documents_data = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "document_date": (
                    doc.document_date.isoformat() if doc.document_date else None
                ),
                "provider": doc.provider,
                "source_system": doc.source_system,
            }
            for doc in documents
        ]

        return jsonify({"documents": documents_data}), 200

    except Exception as e:
        logger.error(f"Error fetching patient documents summary: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients", methods=["POST"])
@csrf.exempt
@jwt_required
def api_create_patient():
    """Create a new patient via API"""
    try:
        # Check content length before parsing JSON
        content_length = request.content_length
        if content_length and content_length > 1024 * 1024:  # 1MB limit
            return jsonify({"error": "Request too large. Maximum size is 1MB."}), 413

        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Check for extremely large field values that would indicate a potential attack
        total_size = sum(
            len(str(value)) for value in data.values() if value is not None
        )
        if total_size > 100000:  # 100KB total data
            return (
                jsonify(
                    {"error": "Request too large. Total data exceeds maximum size."}
                ),
                413,
            )

        for field, value in data.items():
            if isinstance(value, str) and len(value) > 50000:  # 50KB per field
                return (
                    jsonify(
                        {
                            "error": "Request too large. Field values exceed maximum length."
                        }
                    ),
                    413,
                )

        # Validate data size limits first
        errors = []
        field_limits = {
            "first_name": 100,
            "last_name": 100,
            "email": 254,
            "phone": 20,
            "address": 500,
            "mrn": 20,
        }

        for field, max_length in field_limits.items():
            if field in data and data[field] and len(str(data[field])) > max_length:
                errors.append(f"{field} must be {max_length} characters or less")

        # Validate required fields
        required_fields = ["first_name", "last_name", "date_of_birth", "sex"]

        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"{field} is required")
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f"{field} cannot be empty or contain only whitespace")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        # Parse date of birth
        try:
            dob = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Generate MRN if not provided
        mrn = data.get("mrn")
        if not mrn:
            from utils import get_next_available_mrn

            mrn = get_next_available_mrn()

        # Check if MRN already exists
        existing_patient = Patient.query.filter_by(mrn=mrn).first()
        if existing_patient:
            return jsonify({"error": "MRN already exists"}), 409

        # Create new patient
        patient = Patient(
            first_name=data["first_name"],
            last_name=data["last_name"],
            date_of_birth=dob,
            sex=data["sex"],
            mrn=mrn,
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
            insurance=data.get("insurance", ""),
        )

        db.session.add(patient)
        db.session.commit()

        # Invalidate patient-related caches
        invalidate_cache_pattern("api_patients*")
        invalidate_cache_pattern("patients*")

        # Evaluate screening needs
        from utils import evaluate_screening_needs

        evaluate_screening_needs(patient)

        logger.info(
            f"Created new patient: {patient.full_name} (MRN: {patient.mrn}) by user {g.current_user.username}"
        )

        return (
            jsonify(
                {
                    "id": patient.id,
                    "mrn": patient.mrn,
                    "first_name": patient.first_name,
                    "last_name": patient.last_name,
                    "full_name": patient.full_name,
                    "date_of_birth": patient.date_of_birth.isoformat(),
                    "age": patient.age,
                    "sex": patient.sex,
                    "phone": patient.phone,
                    "email": patient.email,
                    "address": patient.address,
                    "insurance": patient.insurance,
                    "created_at": patient.created_at.isoformat(),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating patient via API: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/appointments", methods=["GET"])
@csrf.exempt
@jwt_required
@cache_route(timeout=180, vary_on=["date"])
def api_appointments():
    """
    Get appointments for a specific date (JWT protected)

    Query parameters:
    - date: Date in YYYY-MM-DD format (default: today)
    """
    try:
        # Get and validate date parameter
        date_str = request.args.get("date")
        if date_str:
            if len(date_str) != 10:
                return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400
            try:
                selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                # Validate reasonable date range (1950 to 2050 for medical appointments)
                if selected_date.year < 1950 or selected_date.year > 2050:
                    return (
                        jsonify(
                            {
                                "error": "Date must be within reasonable range (1950-2050)"
                            }
                        ),
                        400,
                    )
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            selected_date = date.today()

        # Get appointments for the selected date using shared function
        appointments = get_appointments_for_date(selected_date)

        # Serialize appointments with minimal fields
        appointments_data = [
            {
                "id": apt.id,
                "patient_name": apt.patient.first_name + " " + apt.patient.last_name,
                "patient_mrn": apt.patient.mrn,
                "appointment_time": apt.appointment_time.strftime("%H:%M"),
                "status": apt.status,
                "note": (
                    apt.note[:50] + "..."
                    if apt.note and len(apt.note) > 50
                    else apt.note
                ),
            }
            for apt in appointments
        ]

        return (
            jsonify(
                {
                    "date": selected_date.isoformat(),
                    "appointments": appointments_data,
                    "total": len(appointments_data),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in API appointments endpoint: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/cache/stats", methods=["GET"])
@csrf.exempt
@jwt_required
@admin_required
def api_cache_stats():
    """Get cache statistics (admin only)"""
    try:
        stats = cache_manager.get_stats()

        return (
            jsonify(
                {
                    "cache_type": "redis" if cache_manager.redis_client else "memory",
                    "stats": stats,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/cache/clear", methods=["POST"])
@csrf.exempt
@jwt_required
@admin_required
def api_cache_clear():
    """Clear cache (admin only)"""
    try:
        pattern = request.json.get("pattern", "*") if request.json else "*"

        if pattern == "*":
            cache_manager.clear_all()
            message = "All cache cleared"
        else:
            invalidate_cache_pattern(pattern)
            message = f"Cache cleared for pattern: {pattern}"

        logger.info(f"Cache cleared by admin {g.current_user.username}: {pattern}")

        return jsonify({"success": True, "message": message}), 200

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/config", methods=["GET"])
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
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/vitals", methods=["POST"])
@csrf.exempt
@log_data_modification("vital")
def add_vitals_api(patient_id):
    """Add vitals for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "weight" not in data or not isinstance(data["weight"], (int, float)):
            errors.append("weight is required and must be a number")

        if "height" not in data or not isinstance(data["height"], (int, float)):
            errors.append("height is required and must be a number")

        if "date" not in data or not isinstance(data["date"], str):
            errors.append("date is required and must be a string")
        else:
            try:
                datetime.strptime(data["date"], "%Y-%m-%d")
            except ValueError:
                errors.append("date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        vital = Vital(
            patient_id=patient_id,
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            weight=data["weight"],
            height=data["height"],
            bmi=data.get("bmi"),
            temperature=data.get("temperature"),
            blood_pressure_systolic=data.get("blood_pressure_systolic"),
            blood_pressure_diastolic=data.get("blood_pressure_diastolic"),
            pulse=data.get("pulse"),
            respiratory_rate=data.get("respiratory_rate"),
            oxygen_saturation=data.get("oxygen_saturation"),
        )

        db.session.add(vital)
        db.session.commit()

        # Invalidate cache for patient vitals
        invalidate_cache_pattern(f"api_patient_vitals?patient_id={patient_id}*")

        return (
            jsonify(
                {
                    "id": vital.id,
                    "patient_id": vital.patient_id,
                    "date": vital.date.isoformat(),
                    "weight": vital.weight,
                    "height": vital.height,
                    "bmi": vital.bmi,
                    "temperature": vital.temperature,
                    "blood_pressure_systolic": vital.blood_pressure_systolic,
                    "blood_pressure_diastolic": vital.blood_pressure_diastolic,
                    "pulse": vital.pulse,
                    "respiratory_rate": vital.respiratory_rate,
                    "oxygen_saturation": vital.oxygen_saturation,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding vitals: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/conditions", methods=["POST"])
@csrf.exempt
@log_data_modification("condition")
def add_condition_api(patient_id):
    """Add conditions for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "name" not in data or not isinstance(data["name"], str):
            errors.append("name is required and must be a string")

        if "code" not in data or not isinstance(data["code"], str):
            errors.append("code is required and must be a string")

        if "diagnosed_date" not in data or not isinstance(data["diagnosed_date"], str):
            errors.append("diagnosed_date is required and must be a string")
        else:
            try:
                datetime.strptime(data["diagnosed_date"], "%Y-%m-%d")
            except ValueError:
                errors.append("diagnosed_date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        condition = Condition(
            patient_id=patient_id,
            name=data["name"],
            code=data["code"],
            diagnosed_date=datetime.strptime(data["diagnosed_date"], "%Y-%m-%d").date(),
            notes=data.get("notes"),
        )

        db.session.add(condition)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": condition.id,
                    "patient_id": condition.patient_id,
                    "name": condition.name,
                    "code": condition.code,
                    "diagnosed_date": condition.diagnosed_date.isoformat(),
                    "notes": condition.notes,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding condition: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/lab_results", methods=["POST"])
@csrf.exempt
@log_data_modification("lab")
def add_lab_result_api(patient_id):
    """Add lab results for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "test_name" not in data or not isinstance(data["test_name"], str):
            errors.append("test_name is required and must be a string")

        if "result" not in data or not isinstance(data["result"], str):
            errors.append("result is required and must be a string")

        if "date" not in data or not isinstance(data["date"], str):
            errors.append("date is required and must be a string")
        else:
            try:
                datetime.strptime(data["date"], "%Y-%m-%d")
            except ValueError:
                errors.append("date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        lab_result = LabResult(
            patient_id=patient_id,
            test_name=data["test_name"],
            result=data["result"],
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            unit=data.get("unit"),
            reference_range=data.get("reference_range"),
            notes=data.get("notes"),
        )

        db.session.add(lab_result)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": lab_result.id,
                    "patient_id": lab_result.patient_id,
                    "test_name": lab_result.test_name,
                    "result": lab_result.result,
                    "date": lab_result.date.isoformat(),
                    "unit": lab_result.unit,
                    "reference_range": lab_result.reference_range,
                    "notes": lab_result.notes,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding lab result: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/immunizations", methods=["POST"])
@csrf.exempt
@log_data_modification("immunization")
def add_immunization_api(patient_id):
    """Add immunization for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "vaccine_name" not in data or not isinstance(data["vaccine_name"], str):
            errors.append("vaccine_name is required and must be a string")

        if "date" not in data or not isinstance(data["date"], str):
            errors.append("date is required and must be a string")
        else:
            try:
                datetime.strptime(data["date"], "%Y-%m-%d")
            except ValueError:
                errors.append("date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        immunization = Immunization(
            patient_id=patient_id,
            vaccine_name=data["vaccine_name"],
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            provider=data.get("provider"),
            notes=data.get("notes"),
        )

        db.session.add(immunization)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": immunization.id,
                    "patient_id": immunization.patient_id,
                    "vaccine_name": immunization.vaccine_name,
                    "date": immunization.date.isoformat(),
                    "provider": immunization.provider,
                    "notes": immunization.notes,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding immunization: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/imaging", methods=["POST"])
@csrf.exempt
@log_data_modification("imaging")
def add_imaging_api(patient_id):
    """Add imaging study for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "study_type" not in data or not isinstance(data["study_type"], str):
            errors.append("study_type is required and must be a string")

        if "date" not in data or not isinstance(data["date"], str):
            errors.append("date is required and must be a string")
        else:
            try:
                datetime.strptime(data["date"], "%Y-%m-%d")
            except ValueError:
                errors.append("date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        imaging_study = ImagingStudy(
            patient_id=patient_id,
            study_type=data["study_type"],
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            radiologist=data.get("radiologist"),
            notes=data.get("notes"),
        )

        db.session.add(imaging_study)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": imaging_study.id,
                    "patient_id": imaging_study.patient_id,
                    "study_type": imaging_study.study_type,
                    "date": imaging_study.date.isoformat(),
                    "radiologist": imaging_study.radiologist,
                    "notes": imaging_study.notes,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding imaging study: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/consults", methods=["POST"])
@csrf.exempt
@log_data_modification("consult")
def add_consult_api(patient_id):
    """Add consult report for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "specialty" not in data or not isinstance(data["specialty"], str):
            errors.append("specialty is required and must be a string")

        if "date" not in data or not isinstance(data["date"], str):
            errors.append("date is required and must be a string")
        else:
            try:
                datetime.strptime(data["date"], "%Y-%m-%d")
            except ValueError:
                errors.append("date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        consult_report = ConsultReport(
            patient_id=patient_id,
            specialty=data["specialty"],
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            consulting_provider=data.get("consulting_provider"),
            reason_for_consult=data.get("reason_for_consult"),
            findings=data.get("findings"),
            recommendations=data.get("recommendations"),
        )

        db.session.add(consult_report)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": consult_report.id,
                    "patient_id": consult_report.patient_id,
                    "specialty": consult_report.specialty,
                    "date": consult_report.date.isoformat(),
                    "consulting_provider": consult_report.consulting_provider,
                    "reason_for_consult": consult_report.reason_for_consult,
                    "findings": consult_report.findings,
                    "recommendations": consult_report.recommendations,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding consult report: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/hospital_summaries", methods=["POST"])
@csrf.exempt
@log_data_modification("hospital")
def add_hospital_summary_api(patient_id):
    """Add hospital summary for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "hospital_name" not in data or not isinstance(data["hospital_name"], str):
            errors.append("hospital_name is required and must be a string")

        if "admission_date" not in data or not isinstance(data["admission_date"], str):
            errors.append("admission_date is required and must be a string")
        else:
            try:
                datetime.strptime(data["admission_date"], "%Y-%m-%d")
            except ValueError:
                errors.append("admission_date must be in YYYY-MM-DD format")

        if "discharge_date" not in data or not isinstance(data["discharge_date"], str):
            errors.append("discharge_date is required and must be a string")
        else:
            try:
                datetime.strptime(data["discharge_date"], "%Y-%m-%d")
            except ValueError:
                errors.append("discharge_date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        hospital_summary = HospitalSummary(
            patient_id=patient_id,
            hospital_name=data["hospital_name"],
            admission_date=datetime.strptime(data["admission_date"], "%Y-%m-%d").date(),
            discharge_date=datetime.strptime(data["discharge_date"], "%Y-%m-%d").date(),
            reason_for_admission=data.get("reason_for_admission"),
            summary=data.get("summary"),
        )

        db.session.add(hospital_summary)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": hospital_summary.id,
                    "patient_id": hospital_summary.patient_id,
                    "hospital_name": hospital_summary.hospital_name,
                    "admission_date": hospital_summary.admission_date.isoformat(),
                    "discharge_date": hospital_summary.discharge_date.isoformat(),
                    "reason_for_admission": hospital_summary.reason_for_admission,
                    "summary": hospital_summary.summary,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding hospital summary: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/documents", methods=["POST"])
@csrf.exempt
@log_data_modification("document")
def add_document_api(patient_id):
    """Add medical document for a specific patient"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data
        errors = []
        if "filename" not in data or not isinstance(data["filename"], str):
            errors.append("filename is required and must be a string")

        if "document_type" not in data or not isinstance(data["document_type"], str):
            errors.append("document_type is required and must be a string")

        if "document_date" not in data or not isinstance(data["document_date"], str):
            errors.append("document_date is required and must be a string")
        else:
            try:
                datetime.strptime(data["document_date"], "%Y-%m-%d")
            except ValueError:
                errors.append("document_date must be in YYYY-MM-DD format")

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        document = MedicalDocument(
            patient_id=patient_id,
            filename=data["filename"],
            document_type=data["document_type"],
            document_date=datetime.strptime(data["document_date"], "%Y-%m-%d").date(),
            provider=data.get("provider"),
            source_system=data.get("source_system"),
            content=data.get("content"),
        )

        db.session.add(document)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": document.id,
                    "patient_id": document.patient_id,
                    "filename": document.filename,
                    "document_type": document.document_type,
                    "document_date": document.document_date.isoformat(),
                    "provider": document.provider,
                    "source_system": document.source_system,
                    "content": document.content,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding medical document: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/patients/<int:patient_id>/last_appointment", methods=["GET"])
@csrf.exempt
@jwt_required
@cache_route(timeout=300, vary_on=["patient_id"])
def api_patient_last_appointment(patient_id):
    """Get the last appointment date for a specific patient"""
    try:
        patient = get_patient_by_id_or_404(patient_id)
        if not patient:
            return jsonify({"error": "Patient not found"}), 404

        # Get the most recent appointment for this patient
        last_appointment = (
            Appointment.query.filter(
                Appointment.patient_id == patient_id,
                Appointment.appointment_date < date.today()
            )
            .order_by(Appointment.appointment_date.desc())
            .first()
        )

        if last_appointment:
            return jsonify({
                "success": True,
                "patient_id": patient_id,
                "patient_name": patient.full_name,
                "last_appointment_date": last_appointment.appointment_date.isoformat(),
                "formatted_date": last_appointment.appointment_date.strftime("%m/%d/%Y"),
                "appointment_time": last_appointment.appointment_time.strftime("%I:%M %p") if last_appointment.appointment_time else None
            }), 200
        else:
            return jsonify({
                "success": False,
                "patient_id": patient_id,
                "patient_name": patient.full_name,
                "message": "No previous appointments found for this patient",
                "last_appointment_date": None
            }), 200

    except Exception as e:
        logger.error(f"Error fetching last appointment for patient {patient_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
