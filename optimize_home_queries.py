
#!/usr/bin/env python3
"""
Optimize home page queries with caching
"""

from flask import request
from functools import lru_cache
import time
from app import app, db
from models import Patient, MedicalDocument

# Cache for 5 minutes (300 seconds)
CACHE_TIMEOUT = 300
_cache = {}

def get_cached_or_execute(cache_key, query_func, timeout=CACHE_TIMEOUT):
    """Get cached result or execute query if cache is expired"""
    current_time = time.time()
    
    if cache_key in _cache:
        cached_data, cached_time = _cache[cache_key]
        if current_time - cached_time < timeout:
            return cached_data
    
    # Execute query and cache result
    result = query_func()
    _cache[cache_key] = (result, current_time)
    return result

def get_dashboard_stats():
    """Get cached dashboard statistics"""
    def query_stats():
        return {
            'total_patients': Patient.query.count(),
            'recent_docs_count': MedicalDocument.query.count()
        }
    
    return get_cached_or_execute('dashboard_stats', query_stats)

def get_recent_documents_cached():
    """Get cached recent documents"""
    def query_recent_docs():
        return MedicalDocument.query.options(
            db.joinedload(MedicalDocument.patient)
        ).order_by(MedicalDocument.created_at.desc()).limit(5).all()
    
    return get_cached_or_execute('recent_documents', query_recent_docs)
