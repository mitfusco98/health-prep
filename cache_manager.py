import redis
import json
import time
import logging
from flask import request
from functools import wraps


def invalidate_appointment_cache(patient_id=None, date=None):
    """Invalidate appointment-related cache entries"""
    patterns = [
        'appointments*',
        'todays_appointments*',
        'home_dashboard*',
        'api_appointments*'
    ]

    if patient_id:
        patterns.append(f'patient_detail_{patient_id}*')
        patterns.append(f'patient_appointments_{patient_id}*')
        patterns.append(f'api_patients_{patient_id}*')

    if date:
        patterns.append(f'appointments_{date}*')
        patterns.append(f'api_appointments*date={date}*')

    for pattern in patterns:
        invalidate_cache_pattern(pattern)

def invalidate_api_cache():
    """Invalidate all API cache entries"""
    patterns = [
        'api_patients*',
        'api_appointments*'
    ]

    for pattern in patterns:
        invalidate_cache_pattern(pattern)