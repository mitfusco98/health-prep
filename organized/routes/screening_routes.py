"""
Screening-related routes extracted from demo_routes.py
Handles screening types and patient screening recommendations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import ScreeningType, Screening, Patient
from app import db
from datetime import datetime, date
import json

# Create screening blueprint
screening_bp = Blueprint("screening", __name__, url_prefix="/screenings")


@screening_bp.route("/")
def screening_list():
    """List all patients with due screenings and manage screening types"""
    tab = request.args.get("tab", "patients")

    if tab == "types":
        # Show screening types management
        screening_types = ScreeningType.query.order_by(ScreeningType.name).all()
        return render_template(
            "screening_list.html", screening_types=screening_types, active_tab="types"
        )
    else:
        # Show patient screenings
        screenings = (
            Screening.query.join(Patient).order_by(Screening.due_date.asc()).all()
        )

        # Get all patients and screening types for the form
        patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
        screening_types = (
            ScreeningType.query.filter_by(is_active=True)
            .order_by(ScreeningType.name)
            .all()
        )

        return render_template(
            "screening_list.html",
            screenings=screenings,
            patients=patients,
            screening_types=screening_types,
            active_tab="patients",
        )


@screening_bp.route("/types/add", methods=["GET", "POST"])
def add_screening_type():
    """Add a new screening type"""
    if request.method == "POST":
        screening_type = ScreeningType(
            name=request.form.get("name"),
            default_frequency=request.form.get("default_frequency"),
            gender_specific=(
                request.form.get("gender_specific")
                if request.form.get("gender_specific")
                else None
            ),
            min_age=request.form.get("min_age", type=int),
            max_age=request.form.get("max_age", type=int),
            is_active=bool(request.form.get("is_active")),
        )

        try:
            db.session.add(screening_type)
            db.session.flush()  # Get the ID without committing
            
            # Handle keywords if provided
            keywords_json = request.form.get("keywords_json")
            if keywords_json:
                try:
                    from screening_keyword_manager import ScreeningKeywordManager
                    keywords = json.loads(keywords_json)
                    manager = ScreeningKeywordManager()
                    
                    for keyword_data in keywords:
                        manager.add_keyword_rule(
                            screening_type_id=screening_type.id,
                            keyword=keyword_data.get('keyword', ''),
                            section=keyword_data.get('section', 'general'),
                            weight=keyword_data.get('weight', 1.0),
                            case_sensitive=keyword_data.get('case_sensitive', False),
                            exact_match=keyword_data.get('exact_match', False),
                            description=keyword_data.get('description', '')
                        )
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Error processing keywords: {str(e)}")
            
            db.session.commit()
            flash(
                f'Screening type "{screening_type.name}" has been added successfully.',
                "success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding screening type: {str(e)}", "danger")

    return redirect(url_for("screening.screening_list", tab="types"))


@screening_bp.route("/types/<int:screening_type_id>/edit", methods=["GET", "POST"])
def edit_screening_type(screening_type_id):
    """Edit an existing screening type"""
    screening_type = ScreeningType.query.get_or_404(screening_type_id)

    if request.method == "POST":
        screening_type.name = request.form.get("name")
        screening_type.default_frequency = request.form.get("default_frequency")
        screening_type.gender_specific = (
            request.form.get("gender_specific")
            if request.form.get("gender_specific")
            else None
        )
        screening_type.min_age = request.form.get("min_age", type=int)
        screening_type.max_age = request.form.get("max_age", type=int)
        screening_type.is_active = bool(request.form.get("is_active"))

        try:
            # Handle keywords if provided
            keywords_json = request.form.get("keywords_json")
            if keywords_json:
                try:
                    from screening_keyword_manager import ScreeningKeywordManager
                    keywords = json.loads(keywords_json)
                    manager = ScreeningKeywordManager()
                    
                    # Clear existing keywords and add new ones
                    config = manager.get_keyword_config(screening_type_id)
                    if config:
                        config.keyword_rules = []
                        manager._save_keyword_config(config)
                    
                    for keyword_data in keywords:
                        manager.add_keyword_rule(
                            screening_type_id=screening_type_id,
                            keyword=keyword_data.get('keyword', ''),
                            section=keyword_data.get('section', 'general'),
                            weight=keyword_data.get('weight', 1.0),
                            case_sensitive=keyword_data.get('case_sensitive', False),
                            exact_match=keyword_data.get('exact_match', False),
                            description=keyword_data.get('description', '')
                        )
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Error processing keywords: {str(e)}")
            
            db.session.commit()
            flash(
                f'Screening type "{screening_type.name}" has been updated successfully.',
                "success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating screening type: {str(e)}", "danger")

    return redirect(url_for("screening.screening_list", tab="types"))


@screening_bp.route("/types/<int:screening_type_id>/delete")
def delete_screening_type(screening_type_id):
    """Delete a screening type or mark as inactive if in use"""
    screening_type = ScreeningType.query.get_or_404(screening_type_id)

    # Check if this screening type is used in any patient screenings
    patient_screenings = Screening.query.filter_by(
        screening_type=screening_type.name
    ).count()

    if patient_screenings > 0:
        # Mark as inactive instead of deleting
        screening_type.is_active = False
        db.session.commit()
        flash(
            f'Screening type "{screening_type.name}" has been marked as inactive because it is used by {patient_screenings} patient(s).',
            "warning",
        )
    else:
        # Safe to delete
        name = screening_type.name
        db.session.delete(screening_type)
        db.session.commit()
        flash(f'Screening type "{name}" has been deleted successfully.', "success")

    return redirect(url_for("screening.screening_list", tab="types"))


@screening_bp.route("/add", methods=["POST"])
def add_screening():
    """Add a new screening recommendation"""
    patient_id = request.form.get("patient_id")
    screening_type = request.form.get("screening_type")
    due_date_str = request.form.get("due_date")
    last_completed_str = request.form.get("last_completed")
    priority = request.form.get("priority", "Medium")
    notes = request.form.get("notes", "")

    if not patient_id or not screening_type:
        flash("Patient and screening type are required.", "danger")
        return redirect(url_for("screening.screening_list"))

    try:
        due_date = (
            datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None
        )
        last_completed = (
            datetime.strptime(last_completed_str, "%Y-%m-%d").date()
            if last_completed_str
            else None
        )

        screening = Screening(
            patient_id=int(patient_id),
            screening_type=screening_type,
            due_date=due_date,
            last_completed=last_completed,
            priority=priority,
            notes=notes,
        )

        db.session.add(screening)
        db.session.commit()
        flash("Screening recommendation added successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error adding screening: {str(e)}", "danger")

    return redirect(url_for("screening.screening_list"))


@screening_bp.route("/<int:patient_id>/<int:screening_id>/edit", methods=["POST"])
def edit_screening(patient_id, screening_id):
    """Edit a screening record"""
    screening = Screening.query.get_or_404(screening_id)

    if screening.patient_id != patient_id:
        flash("Invalid request: Screening does not belong to this patient.", "danger")
        return redirect(url_for("screening.screening_list"))

    try:
        screening.screening_type = request.form.get(
            "screening_type", screening.screening_type
        )

        due_date = request.form.get("due_date")
        if due_date:
            screening.due_date = datetime.strptime(due_date, "%Y-%m-%d").date()

        last_completed = request.form.get("last_completed")
        if last_completed:
            screening.last_completed = datetime.strptime(
                last_completed, "%Y-%m-%d"
            ).date()
        else:
            screening.last_completed = None

        screening.priority = request.form.get("priority", screening.priority)
        screening.notes = request.form.get("notes", "")

        db.session.commit()
        flash("Screening record updated successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error updating screening: {str(e)}", "danger")

    return redirect(url_for("screening.screening_list"))


@screening_bp.route(
    "/<int:patient_id>/<int:screening_id>/delete", methods=["GET", "POST"]
)
def delete_screening(patient_id, screening_id):
    """Delete a screening record"""
    try:
        screening = Screening.query.get_or_404(screening_id)

        if screening.patient_id != patient_id:
            flash(
                "Invalid request: screening does not belong to this patient.", "danger"
            )
            return redirect(url_for("screening.screening_list"))

        db.session.delete(screening)
        db.session.commit()
        flash("Screening record deleted successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting screening record: {str(e)}", "danger")

    return redirect(url_for("screening.screening_list"))
