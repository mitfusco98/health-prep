from cache_manager import cache_manager
from db_utils import *
from datetime import datetime, timedelta
import json


def get_cached_patient_summary(patient_id, include_heavy_data=False):
    """Get patient summary with caching"""
    cache_key = f"patient_summary_{patient_id}_heavy_{include_heavy_data}"

    cached_data = cache_manager.get(cache_key)
    if cached_data:
        return cached_data

    # Get fresh data
    patient_data = get_patient_with_basic_data(patient_id)
    if not patient_data:
        return None

    result = {
        "patient": serialize_patient_basic(patient_data["patient"]),
        "conditions": [
            {
                "id": c.id,
                "name": c.name,
                "code": c.code,
                "diagnosed_date": (
                    c.diagnosed_date.isoformat() if c.diagnosed_date else None
                ),
                "notes": c.notes,
            }
            for c in patient_data["conditions"]
        ],
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "description": a.description,
                "severity": a.severity,
            }
            for a in patient_data["alerts"]
        ],
    }

    if include_heavy_data:
        vitals = get_patient_recent_vitals(patient_id)
        visits = get_patient_recent_visits(patient_id)
        screenings = get_patient_screenings(patient_id)

        result.update(
            {
                "recent_vitals": [
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
                ],
                "recent_visits": [
                    {
                        "id": v.id,
                        "visit_date": (
                            v.visit_date.isoformat() if v.visit_date else None
                        ),
                        "visit_type": v.visit_type,
                        "provider": v.provider,
                        "reason": v.reason,
                        "notes": v.notes,
                    }
                    for v in visits
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
            }
        )

    # Cache for 10 minutes (basic data) or 5 minutes (heavy data)
    timeout = 300 if include_heavy_data else 600
    cache_manager.set(cache_key, result, timeout)

    return result


def get_cached_daily_appointments(target_date):
    """Get daily appointments with caching"""
    cache_key = f"daily_appointments_{target_date.isoformat()}"

    cached_data = cache_manager.get(cache_key)
    if cached_data:
        return cached_data

    appointments = get_appointments_for_date(target_date)
    result = [serialize_appointment(apt) for apt in appointments]

    # Cache for 3 minutes (appointments change frequently)
    cache_manager.set(cache_key, result, 180)

    return result


def invalidate_patient_caches(patient_id):
    """Invalidate all caches related to a specific patient"""
    patterns = [
        f"patient_summary_{patient_id}_*",
        f"patient_detail_{patient_id}*",
        f"api_patients_{patient_id}*",
    ]

    for pattern in patterns:
        cache_manager.clear_pattern(pattern)


def invalidate_appointment_caches(appointment_date=None):
    """Invalidate appointment-related caches"""
    if appointment_date:
        cache_manager.delete(f"daily_appointments_{appointment_date.isoformat()}")
    else:
        cache_manager.clear_pattern("daily_appointments_*")
