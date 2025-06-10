from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    session,
    abort,
    send_file,
    make_response,
)
from werkzeug.utils import secure_filename
from functools import wraps
from app import app, db
from models import (
    Patient,
    Appointment,
    Condition,
    Vital,
    MedicalDocument,
    LabResult,
    ImagingStudy,
    ConsultReport,
    HospitalSummary,
    Immunization,
    PatientAlert,
    Visit,
    User,
    AdminLog,
)
from forms import (
    PatientForm,
    AppointmentForm,
    ConditionForm,
    VitalForm,
    DocumentUploadForm,
    LabResultForm,
    ImagingStudyForm,
    ConsultReportForm,
    HospitalSummaryForm,
    ImmunizationForm,
    PatientAlertForm,
    VisitForm,
)
from comprehensive_logging import (
    log_patient_operation,
    log_admin_operation,
    log_data_modification,
    log_page_access,
)

# Import modular route files
from routes import patient_routes
from routes import appointment_routes

# Keep only unique routes that aren't in demo_routes.py or modular route files
# All duplicate routes have been removed to prevent conflicts


@app.route("/delete_condition/<int:id>", methods=["POST"])
@log_data_modification("condition")
def delete_condition(id):
    condition = Condition.query.get_or_404(id)
    patient_id = condition.patient_id
    db.session.delete(condition)
    db.session.commit()
    flash("Condition deleted successfully", "success")
    return redirect(url_for("patient_detail", id=patient_id))


def admin_required(f):
    """Decorator for admin-only routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id") or not session.get("is_admin"):
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route("/admin_dashboard")
@admin_required
@log_page_access("admin_dashboard")
def admin_dashboard():
    # Placeholder for admin dashboard logic
    return render_template("admin_dashboard.html")
