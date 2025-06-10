
"""
Response optimization utilities for reducing API payload sizes
"""

from flask import request, jsonify
import gzip
import json
from functools import wraps

def compress_response(data):
    """Compress JSON response data"""
    json_str = json.dumps(data, separators=(',', ':'))  # Compact JSON
    return gzip.compress(json_str.encode('utf-8'))

def filter_fields(data, allowed_fields):
    """Filter response data to only include specified fields"""
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in allowed_fields}
    elif isinstance(data, list):
        return [filter_fields(item, allowed_fields) for item in data]
    return data

def optimize_response(allowed_fields=None):
    """Decorator to optimize API responses"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            # If response is a tuple (data, status_code)
            if isinstance(response, tuple):
                data, status_code = response
            else:
                data = response
                status_code = 200
            
            # Filter fields if specified
            if allowed_fields and isinstance(data, (dict, list)):
                data = filter_fields(data, allowed_fields)
            
            # Check if client accepts gzip
            if 'gzip' in request.headers.get('Accept-Encoding', ''):
                compressed_data = compress_response(data)
                response = compressed_data, status_code
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Type'] = 'application/json'
            
            return response
        return decorated_function
    return decorator

# Field definitions for different endpoints
PATIENT_LIST_FIELDS = ['id', 'mrn', 'first_name', 'last_name', 'age', 'sex', 'phone', 'created_at']
PATIENT_DETAIL_FIELDS = ['id', 'mrn', 'first_name', 'last_name', 'age', 'sex', 'phone', 'email', 'conditions', 'recent_vitals']
APPOINTMENT_FIELDS = ['id', 'patient_name', 'patient_mrn', 'appointment_time', 'status', 'note']
