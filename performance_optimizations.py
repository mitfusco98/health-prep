from functools import lru_cache
from flask import request
import time
import hashlib


# Cache for expensive operations
class SimpleCache:
    def __init__(self, ttl=300):  # 5 minutes default TTL
        self.cache = {}
        self.ttl = ttl

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())

        # Simple cleanup: remove expired entries when cache gets large
        if len(self.cache) > 1000:
            current_time = time.time()
            expired_keys = [
                k
                for k, (_, timestamp) in self.cache.items()
                if current_time - timestamp >= self.ttl
            ]
            for k in expired_keys:
                del self.cache[k]


# Global cache instances
patient_cache = SimpleCache(ttl=300)  # 5 minutes
appointment_cache = SimpleCache(ttl=60)  # 1 minute
home_page_cache = SimpleCache(ttl=120)  # 2 minutes for home page data


def cache_key_from_request():
    """Generate cache key from request parameters"""
    key_parts = [
        request.endpoint or "unknown",
        request.method,
        str(sorted(request.args.items())),
        str(sorted(request.view_args.items()) if request.view_args else ""),
    ]
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


# Removed unused optimization suggestion functions - these are static data not used in runtime


# Optimized patient loading function
@lru_cache(maxsize=100)
def get_patient_summary(patient_id):
    """Cached patient summary to avoid repeated database calls"""
    from models import Patient

    patient = Patient.query.get(patient_id)
    if patient:
        return {
            "id": patient.id,
            "name": patient.full_name,
            "mrn": patient.mrn,
            "age": patient.age,
        }
    return None


# Optimized appointment loading
def get_today_appointments_optimized():
    """Optimized query for today's appointments"""
    from models import Appointment, Patient
    from sqlalchemy.orm import selectinload
    from datetime import date

    cache_key = f"appointments_today_{date.today().isoformat()}"
    cached_result = appointment_cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    # Use efficient query with selective loading
    appointments = (
        Appointment.query.options(selectinload(Appointment.patient))
        .filter(Appointment.appointment_date == date.today())
        .order_by(Appointment.appointment_time)
        .all()
    )

    result = [
        {
            "id": apt.id,
            "patient_name": apt.patient.full_name,
            "patient_mrn": apt.patient.mrn,
            "time": apt.appointment_time.strftime("%H:%M"),
            "note": apt.note,
        }
        for apt in appointments
    ]

    appointment_cache.set(cache_key, result)
    return result


async def get_home_page_data_async():
    """Async optimized data loading for home page"""
    from datetime import date, timedelta
    import asyncio

    cache_key = f"home_page_data_{date.today().isoformat()}"
    cached_result = home_page_cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    try:
        # Run all count queries concurrently
        tasks = [
            async_db.get_patient_count(),
            async_db.get_today_appointments_count(),
            async_db.get_recent_documents_count(7),
        ]

        patient_count, today_apt_count, recent_doc_count = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        # Handle any exceptions from concurrent queries
        patient_count = patient_count if not isinstance(patient_count, Exception) else 0
        today_apt_count = (
            today_apt_count if not isinstance(today_apt_count, Exception) else 0
        )
        recent_doc_count = min(
            recent_doc_count if not isinstance(recent_doc_count, Exception) else 0, 50
        )

        result = {
            "patient_count": patient_count,
            "today_appointments": today_apt_count,
            "recent_documents": recent_doc_count,
        }

        home_page_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Error in get_home_page_data_async: {str(e)}")
        return {"patient_count": 0, "today_appointments": 0, "recent_documents": 0}


def get_home_page_data_optimized():
    """Sync wrapper for backward compatibility"""
    return asyncio.run(get_home_page_data_async())


"""
Database and application performance optimizations
"""


def optimize_database_connection_pool():
    """Optimize database connection pool settings"""
    from app import app, db

    # Update SQLAlchemy engine options for better performance
    app.config["SQLALCHEMY_ENGINE_OPTIONS"].update(
        {
            "pool_size": 10,
            "pool_recycle": 300,
            "pool_pre_ping": False,  # Disable automatic pinging to reduce overhead
            "pool_timeout": 30,
            "max_overflow": 20,
            "connect_args": {
                "connect_timeout": 10,
                "application_name": "healthprep_app",
            },
        }
    )

    return "Database connection pool optimized"


def add_query_result_caching():
    """Add simple query result caching for frequently accessed data"""
    import time
    from functools import wraps

    # Simple in-memory cache
    _cache = {}
    _cache_timeout = 300  # 5 minutes

    def cache_query_result(cache_key, timeout=300):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()

                # Check if result is in cache and not expired
                if cache_key in _cache:
                    cached_data, cache_time = _cache[cache_key]
                    if current_time - cache_time < timeout:
                        return cached_data

                # Execute function and cache result
                result = func(*args, **kwargs)
                _cache[cache_key] = (result, current_time)

                # Clean up expired cache entries
                expired_keys = [
                    k for k, (_, t) in _cache.items() if current_time - t > timeout
                ]
                for k in expired_keys:
                    del _cache[k]

                return result

            return wrapper

        return decorator

    return cache_query_result
