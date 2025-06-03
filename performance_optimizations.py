
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
                k for k, (_, timestamp) in self.cache.items()
                if current_time - timestamp >= self.ttl
            ]
            for k in expired_keys:
                del self.cache[k]

# Global cache instances
patient_cache = SimpleCache(ttl=300)  # 5 minutes
appointment_cache = SimpleCache(ttl=60)  # 1 minute

def cache_key_from_request():
    """Generate cache key from request parameters"""
    key_parts = [
        request.endpoint or 'unknown',
        request.method,
        str(sorted(request.args.items())),
        str(sorted(request.view_args.items()) if request.view_args else '')
    ]
    key_string = '|'.join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def optimize_patient_queries():
    """Optimization suggestions for patient-related queries"""
    return [
        {
            'optimization': 'Use pagination for patient lists',
            'before': 'Patient.query.all()',
            'after': 'Patient.query.paginate(page=1, per_page=20)',
            'benefit': 'Reduces memory usage and improves response time for large datasets'
        },
        {
            'optimization': 'Add selective loading for patient details',
            'before': 'Patient.query.get(id) with all relationships loaded',
            'after': 'Patient.query.options(selectinload(Patient.conditions)).get(id)',
            'benefit': 'Only loads needed relationships, reducing database queries'
        },
        {
            'optimization': 'Use database-level filtering',
            'before': '[p for p in patients if p.age > 65]',
            'after': 'Patient.query.filter(Patient.date_of_birth < cutoff_date)',
            'benefit': 'Filters at database level instead of in Python'
        }
    ]

def optimize_middleware_stack():
    """Suggestions for optimizing middleware"""
    return [
        {
            'optimization': 'Reduce middleware for API routes',
            'suggestion': 'Skip CSRF, session validation for JWT-protected API endpoints',
            'implementation': 'Add early returns in middleware for /api/ routes'
        },
        {
            'optimization': 'Optimize security headers',
            'suggestion': 'Set security headers only once per response type',
            'implementation': 'Cache headers based on response type'
        },
        {
            'optimization': 'Lazy load validation',
            'suggestion': 'Only validate inputs that are actually used',
            'implementation': 'Move validation closer to where data is used'
        }
    ]

def get_performance_recommendations():
    """Get comprehensive performance recommendations"""
    return {
        'database_optimizations': [
            'Add database indexes on frequently queried columns',
            'Use database-level pagination instead of loading all records',
            'Implement query result caching for expensive operations',
            'Use selective loading (selectinload) for relationships',
            'Consider database connection pooling optimization'
        ],
        'application_optimizations': [
            'Implement response caching for static content',
            'Reduce middleware overhead for API routes',
            'Use lazy loading for heavy operations',
            'Optimize JSON serialization with pre-computed fields',
            'Implement async processing for non-critical operations'
        ],
        'code_optimizations': [
            'Replace list comprehensions with database filters',
            'Use generator expressions instead of lists where possible',
            'Cache expensive calculations (age, formatted dates)',
            'Minimize database queries in loops',
            'Use bulk operations for multiple database changes'
        ],
        'infrastructure_optimizations': [
            'Enable gzip compression for responses',
            'Use CDN for static assets',
            'Implement database read replicas for read-heavy operations',
            'Consider Redis for session storage and caching',
            'Enable HTTP/2 for better connection efficiency'
        ]
    }

# Optimized patient loading function
@lru_cache(maxsize=100)
def get_patient_summary(patient_id):
    """Cached patient summary to avoid repeated database calls"""
    from models import Patient
    patient = Patient.query.get(patient_id)
    if patient:
        return {
            'id': patient.id,
            'name': patient.full_name,
            'mrn': patient.mrn,
            'age': patient.age
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
    appointments = (Appointment.query
                   .options(selectinload(Appointment.patient))
                   .filter(Appointment.appointment_date == date.today())
                   .order_by(Appointment.appointment_time)
                   .all())
    
    result = [{
        'id': apt.id,
        'patient_name': apt.patient.full_name,
        'patient_mrn': apt.patient.mrn,
        'time': apt.appointment_time.strftime('%H:%M'),
        'note': apt.note
    } for apt in appointments]
    
    appointment_cache.set(cache_key, result)
    return result
<line_number>1</line_number>
"""
Database and application performance optimizations
"""

def optimize_database_connection_pool():
    """Optimize database connection pool settings"""
    from app import app, db
    
    # Update SQLAlchemy engine options for better performance
    app.config["SQLALCHEMY_ENGINE_OPTIONS"].update({
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": False,  # Disable automatic pinging to reduce overhead
        "pool_timeout": 30,
        "max_overflow": 20,
        "connect_args": {
            "connect_timeout": 10,
            "application_name": "healthprep_app"
        }
    })
    
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
                expired_keys = [k for k, (_, t) in _cache.items() 
                              if current_time - t > timeout]
                for k in expired_keys:
                    del _cache[k]
                
                return result
            return wrapper
        return decorator
    
    return cache_query_result
