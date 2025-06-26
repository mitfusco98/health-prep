import os
import logging

# Set default FLASK_ENV if not provided
if not os.environ.get("FLASK_ENV"):
    os.environ["FLASK_ENV"] = "development"

from app import app, db  # noqa: F401

# Defer route imports for faster startup - routes will be loaded on first request
def load_all_routes():
    """Load all route modules on demand"""
    try:
        import demo_routes  # noqa: F401
        import ehr_routes  # noqa: F401
        import checklist_routes  # noqa: F401
        import api_routes  # noqa: F401
        import performance_routes  # noqa: F401
        import screening_keyword_routes  # noqa: F401

        # Import modular route files
        from routes import patient_routes  # noqa: F401
        from routes import appointment_routes  # noqa: F401

        # Import service layers for dependency injection
        from services import patient_service, appointment_service  # noqa: F401
        
        logging.info("All route modules loaded successfully")
    except Exception as e:
        logging.warning(f"Some route modules failed to load: {e}")

# Load essential routes only at startup
try:
    # Only load core auth routes for immediate functionality
    import auth_routes  # noqa: F401
    logging.info("Essential routes loaded")
except Exception as e:
    logging.warning(f"Essential routes failed to load: {e}")
import logging

# Skip EHR and sample data initialization during startup for faster boot
# These will be loaded on-demand when needed
