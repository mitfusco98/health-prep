"""
Centralized blueprint registration for organized route modules
"""
from .patient_routes import patient_bp
from .appointment_routes import appointment_bp
from .screening_routes import screening_bp
from .medical_routes import medical_bp
from .document_routes import document_bp
from .admin_routes import admin_bp

def register_organized_blueprints(app):
    """Register all organized blueprints with the Flask app"""
    
    # Register blueprints with organized URL prefixes
    app.register_blueprint(patient_bp, url_prefix='/organized/patients')
    app.register_blueprint(appointment_bp, url_prefix='/organized/appointments')
    app.register_blueprint(screening_bp, url_prefix='/organized/screenings')
    app.register_blueprint(medical_bp, url_prefix='/organized/medical')
    app.register_blueprint(document_bp, url_prefix='/organized/documents')
    app.register_blueprint(admin_bp, url_prefix='/organized/admin')
    
    print("✅ Organized blueprints registered successfully")
    print("   Available routes:")
    print("   • /organized/patients/* - Patient management")
    print("   • /organized/appointments/* - Appointment scheduling")
    print("   • /organized/screenings/* - Screening operations")
    print("   • /organized/medical/* - Medical data management")
    print("   • /organized/documents/* - Document handling")
    print("   • /organized/admin/* - Administrative functions")