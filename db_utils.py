# Applying the provided changes to implement a robust retry mechanism with connection recovery for PostgreSQL SSL timeout issues.
from functools import wraps
from flask import flash, redirect, url_for
import logging

logger = logging.getLogger(__name__)


def with_db_retry(max_retries=2):
    """Decorator to retry database operations with connection recovery"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app import db

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    is_db_error = any(
                        term in error_str
                        for term in [
                            "ssl connection has been closed",
                            "connection closed",
                            "server closed the connection",
                            "operationalerror",
                            "connection pool",
                            "database connection",
                        ]
                    )

                    if is_db_error and attempt < max_retries:
                        logger.warning(
                            f"Database connection error on attempt {attempt + 1}, retrying: {str(e)}"
                        )
                        try:
                            # Try to recover the connection
                            db.session.rollback()
                            db.session.remove()
                            db.engine.dispose()
                        except:
                            pass
                        continue
                    else:
                        # Re-raise the exception if it's not a DB error or we've exhausted retries
                        raise e

            return func(*args, **kwargs)

        return wrapper

    return decorator


import functools
import logging
from app import sanitize_input


def sanitize_db_inputs(func):
    """Decorator to sanitize all inputs before database operations"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Sanitize string arguments
        sanitized_args = []
        for arg in args:
            if isinstance(arg, str):
                sanitized_args.append(sanitize_input(arg, max_length=5000))
            else:
                sanitized_args.append(arg)

        # Sanitize string keyword arguments
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                sanitized_kwargs[key] = sanitize_input(value, max_length=5000)
            else:
                sanitized_kwargs[key] = value

        return func(*sanitized_args, **sanitized_kwargs)

    return wrapper


"""
Database utility functions for the healthcare application
"""

from functools import wraps
from flask import flash
from app import db


def safe_db_operation(max_retries=5, retry_delay=2):
    """
    Decorator to handle database operations with retries and proper error handling
    Enhanced with PostgreSQL connection recovery for Replit environment

    Args:
        max_retries: Maximum number of retry attempts (increased for SSL timeouts)
        retry_delay: Delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app import db
            from sqlalchemy.exc import OperationalError, DisconnectionError
            import time
            import psycopg2

            for attempt in range(max_retries):
                try:
                    # Check connection health before operation
                    _ensure_db_connection(db)

                    # Execute the function
                    result = func(*args, **kwargs)

                    # Commit the transaction with retry on SSL errors
                    _safe_commit(db, attempt)

                    return result

                except (OperationalError, DisconnectionError, psycopg2.OperationalError) as e:
                    error_msg = str(e).lower()

                    # Handle SSL connection issues specifically
                    if "ssl connection has been closed" in error_msg or "connection closed" in error_msg:
                        logger.warning(f"PostgreSQL SSL connection lost (attempt {attempt + 1}/{max_retries})")

                        # Force connection cleanup and recreation
                        _recover_db_connection(db)

                        if attempt == max_retries - 1:
                            logger.error(f"Failed to recover database connection after {max_retries} attempts")
                            raise

                        # Exponential backoff for connection recovery
                        wait_time = retry_delay * (2 ** attempt)
                        logger.info(f"Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Other database errors
                        _safe_rollback(db)
                        if attempt == max_retries - 1:
                            logger.error(f"Database operation failed after {max_retries} attempts: {str(e)}")
                            raise
                        time.sleep(retry_delay)
                        continue

                except Exception as e:
                    # Non-database errors
                    _safe_rollback(db)

                    if attempt == max_retries - 1:
                        logger.error(f"Operation failed after {max_retries} attempts: {str(e)}")
                        raise

                    logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)

            # This should never be reached, but just in case
            raise Exception("Unexpected end of retry loop")

        return wrapper
    return decorator


def _ensure_db_connection(db):
    """Ensure database connection is healthy"""
    try:
        # Simple query to test connection
        db.session.execute(db.text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Database connection test failed: {e}")
        _recover_db_connection(db)


def _safe_commit(db, attempt):
    """Safely commit with SSL error handling"""
    try:
        db.session.commit()
    except Exception as e:
        error_msg = str(e).lower()
        if "ssl connection has been closed" in error_msg:
            # Don't rollback on SSL errors - the connection is already lost
            logger.warning(f"SSL connection lost during commit (attempt {attempt + 1})")
            raise
        else:
            # For other commit errors, try to rollback
            _safe_rollback(db)
            raise


def _safe_rollback(db):
    """Safely rollback transaction"""
    try:
        db.session.rollback()
    except Exception as rollback_error:
        logger.warning(f"Error during rollback (connection may be lost): {rollback_error}")
        # Force session cleanup on rollback failure
        try:
            db.session.remove()
        except:
            pass


def _recover_db_connection(db):
    """Recover from lost database connection"""
    try:
        # Clean up the current session
        db.session.remove()

        # Dispose of the engine's connection pool to force new connections
        db.engine.dispose()

        logger.info("Database connection pool refreshed")

    except Exception as e:
        logger.error(f"Error during connection recovery: {e}")
        # Continue anyway - new connections will be created as needed


def fresh_session_operation(func):
    """
    Decorator that ensures a fresh database session is used for the operation.
    This can help resolve issues with stale session states.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Close any existing session
        db.session.close()

        try:
            # Call the original function
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # Roll back the session if there's an error
            db.session.rollback()
            print(f"Database error in {func.__name__}: {str(e)}")
            flash(f"Database error: {str(e)}", "danger")
            # Re-raise the exception or handle it as needed
            raise
        finally:
            # Always ensure the session is closed properly
            db.session.close()

    return wrapper


from models import (
    Patient,
    Appointment,
    Vital,
    Visit,
    Condition,
    Screening,
    PatientAlert,
)
from app import db
from sqlalchemy import func, or_
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


def get_patient_by_id_or_404(patient_id):
    """Get patient by ID with validation, raise 404 if not found"""
    try:
        patient_id_int = int(patient_id)
        if patient_id_int <= 0:
            return None
    except (ValueError, TypeError):
        return None

    return Patient.query.get_or_404(patient_id_int)


def get_patient_with_basic_data(patient_id):
    """Get patient with commonly needed related data"""
    patient = get_patient_by_id_or_404(patient_id)
    if not patient:
        return None

    # Pre-load commonly accessed relationships
    conditions = (
        Condition.query.filter_by(patient_id=patient_id, is_active=True).limit(10).all()
    )
    alerts = (
        PatientAlert.query.filter_by(patient_id=patient_id, is_active=True)
        .limit(10)
        .all()
    )

    return {"patient": patient, "conditions": conditions, "alerts": alerts}


def search_patients(
    search_term, page=1, per_page=20, sort_field="created_at", sort_order="desc"
):
    """Shared patient search functionality"""
    query = Patient.query

    if search_term:
        search_filter = or_(
            Patient.first_name.ilike(f"%{search_term}%"),
            Patient.last_name.ilike(f"%{search_term}%"),
            Patient.mrn.ilike(f"%{search_term}%"),
            func.concat(Patient.first_name, " ", Patient.last_name).ilike(
                f"%{search_term}%"
            ),
        )
        query = query.filter(search_filter)

    # Apply sorting
    if sort_field == "name":
        sort_column = Patient.first_name
    elif sort_field == "mrn":
        sort_column = Patient.mrn
    elif sort_field == "age":
        sort_column = Patient.date_of_birth
        sort_order = "asc" if sort_order == "desc" else "desc"
    else:
        sort_column = Patient.created_at

    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_appointments_for_date(target_date):
    """Get all appointments for a specific date"""
    return (
        Appointment.query.filter(func.date(Appointment.appointment_date) == target_date)
        .order_by(Appointment.appointment_time)
        .all()
    )


def get_patient_recent_vitals(patient_id, limit=5):
    """Get recent vitals for a patient"""
    return (
        Vital.query.filter_by(patient_id=patient_id)
        .order_by(Vital.date.desc())
        .limit(limit)
        .all()
    )


def get_patient_recent_visits(patient_id, limit=5):
    """Get recent visits for a patient"""
    return (
        Visit.query.filter_by(patient_id=patient_id)
        .order_by(Visit.visit_date.desc())
        .limit(limit)
        .all()
    )


def get_patient_screenings(patient_id, limit=20):
    """Get patient screenings"""
    return Screening.query.filter_by(patient_id=patient_id).limit(limit).all()


def serialize_patient_basic(patient):
    """Serialize patient data for list views with minimal fields"""
    return {
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
        ),
        "created_at": (
            patient.created_at.strftime("%Y-%m-%d") if patient.created_at else None
        ),
    }


def get_patient_summary_lightweight(patient_id):
    """Get lightweight patient summary with essential data only"""
    from models import Patient, Condition

    patient = Patient.query.get(patient_id)
    if not patient:
        return None

    # Get only active conditions, limited fields
    conditions = (
        Condition.query.filter_by(patient_id=patient_id, is_active=True)
        .with_entities(Condition.name, Condition.code)
        .limit(3)
        .all()
    )

    return {
        "id": patient.id,
        "name": patient.first_name + " " + patient.last_name,
        "mrn": patient.mrn,
        "age": patient.age,
        "conditions": [{"name": c.name, "code": c.code} for c in conditions],
    }


def serialize_appointment(appointment):
    """Standard appointment serialization"""
    return {
        "id": appointment.id,
        "patient_id": appointment.patient_id,
        "patient_name": appointment.patient.full_name,
        "patient_mrn": appointment.patient.mrn,
        "appointment_date": appointment.appointment_date.isoformat(),
        "appointment_time": appointment.appointment_time.strftime("%H:%M"),
        "note": appointment.note,
        "status": appointment.status,
    }