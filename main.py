import os

# Set default FLASK_ENV if not provided
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'

from app import app, db  # noqa: F401

# Import all route modules
import demo_routes  # noqa: F401
import ehr_routes  # noqa: F401
import checklist_routes  # noqa: F401
import api_routes  # noqa: F401
import performance_routes  # noqa: F401

# Import modular route files
from routes import patient_routes  # noqa: F401
from routes import appointment_routes  # noqa: F401

# Import service layers for dependency injection
from services import patient_service, appointment_service  # noqa: F401
import logging

# Defer expensive operations to avoid startup bloat
# These will be handled by lazy loading on first request instead
pass
