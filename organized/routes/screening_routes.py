"""
Screening-related routes extracted from demo_routes.py
Handles screening types and patient screening recommendations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import ScreeningType, Screening, Patient
from app import db
from datetime import datetime, date
import json
from screening_variant_manager import variant_manager

# Create screening blueprint
screening_bp = Blueprint("screening", __name__, url_prefix="/screenings")


def _has_valid_frequency(screening_type):
    """Check if screening type has valid frequency defined"""
    has_structured_frequency = (
        screening_type.frequency_number and 
        screening_type.frequency_unit and
        screening_type.frequency_number > 0
    )
    
    has_default_frequency = (
        screening_type.default_frequency and 
        screening_type.default_frequency.strip() and
        screening_type.default_frequency.lower() not in ['', 'none', 'null']
    )
    
    return has_structured_frequency or has_default_frequency


@screening_bp.route("/")
def screening_list():
    """List all patients with due screenings and manage screening types"""
    tab = request.args.get("tab", "patients")

    if tab == "types":
        # Show screening types management with variant grouping
        screening_types = ScreeningType.query.order_by(ScreeningType.name).all()
        
        # Group by base names for variant management
        variant_groups = variant_manager.get_consolidated_screening_groups()
        
        return render_template(
            "screening_list.html", 
            screening_types=screening_types, 
            variant_groups=variant_groups,
            variant_manager=variant_manager,
            active_tab="types"
        )
    else:
        # Show patient screenings with high-performance optimized query
        try:
            from screening_performance_optimizer import screening_optimizer
            
            # Get pagination parameters
            page = int(request.args.get('page', 1))
            page_size = min(int(request.args.get('page_size', 50)), 100)
            status_filter = request.args.get('status', '')
            screening_type_filter = request.args.get('screening_type', '')
            search_query = request.args.get('search', '')
            
            # Use optimized query with caching and pagination
            query_result = screening_optimizer.get_optimized_screenings(
                page=page,
                page_size=page_size,
                status_filter=status_filter,
                screening_type_filter=screening_type_filter,
                search_query=search_query
            )
            
            screenings = query_result['screenings']
            pagination_info = query_result['pagination']
            filters_info = query_result['filters']
            metadata = query_result['metadata']
            
            # Quick validation without additional database queries
            validation_errors = []
            frequency_errors = []
            
            # Process screenings efficiently
            for screening in screenings:
                # Validate documents vs status (using already loaded data)
                if screening.status == "Incomplete":
                    documents = list(screening.documents) if hasattr(screening, 'documents') else []
                    if documents and len(documents) > 0:
                        validation_errors.append(f"Screening {screening.id} ({screening.screening_type.name if screening.screening_type else 'Unknown'}) is Incomplete but has {len(documents)} documents")
                
                # Use already loaded screening_type data
                if screening.screening_type and not _has_valid_frequency(screening.screening_type):
                    frequency_errors.append(f"Screening type '{screening.screening_type.name}' is missing frequency definition")
            
            # Show validation messages
            if validation_errors:
                flash(f"⚠️ Data integrity issue: {len(validation_errors)} incomplete screenings have documents. Please contact admin.", "warning")
                
            if frequency_errors:
                flash(f"⚠️ Frequency missing: {len(frequency_errors)} screening types need frequency defined in Types tab.", "warning")
                
        except Exception as e:
            # Fallback to basic query if optimized version fails
            print(f"Performance optimization failed: {e}")
            screenings = Screening.query.join(Patient).filter(Screening.is_visible == True).order_by(Screening.due_date.asc()).limit(50).all()
            flash("Using simplified view due to performance optimization issue", "info")
            
            # Create basic pagination info for fallback
            pagination_info = {
                'current_page': 1,
                'total_pages': 1,
                'total_count': len(screenings),
                'page_size': 50,
                'has_next': False,
                'has_prev': False
            }
            filters_info = {}
            metadata = {'optimized': False, 'fallback': True}

        # Get all patients and screening types for the form
        patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
        screening_types = (
            ScreeningType.query.filter_by(is_active=True)
            .order_by(ScreeningType.name)
            .all()
        )

        # Get screening statistics for dashboard
        try:
            from screening_performance_optimizer import screening_optimizer
            stats = screening_optimizer.get_screening_stats()
        except Exception:
            stats = {'by_status': {}, 'by_type': {}, 'total_count': len(screenings)}

        return render_template(
            "screening_list.html",
            screenings=screenings,
            patients=patients,
            screening_types=screening_types,
            active_tab="patients",
            variant_manager=variant_manager,
            # Performance optimization data
            pagination=pagination_info if 'pagination_info' in locals() else {},
            filters=filters_info if 'filters_info' in locals() else {},
            metadata=metadata if 'metadata' in locals() else {},
            stats=stats,
            # URL parameters for maintaining state
            current_page=int(request.args.get('page', 1)),
            page_size=int(request.args.get('page_size', 50)),
            status_filter=request.args.get('status', ''),
            screening_type_filter=request.args.get('screening_type', ''),
            search_query=request.args.get('search', '')
        )


@screening_bp.route("/types/add", methods=["GET", "POST"])
def add_screening_type():
    """Add a new screening type"""
    if request.method == "POST":
        # Get frequency data
        frequency_number = request.form.get("frequency_number")
        frequency_unit = request.form.get("frequency_unit")
        
        # Convert frequency_number to int if provided
        if frequency_number:
            try:
                frequency_number = int(frequency_number)
            except (ValueError, TypeError):
                frequency_number = None
        
        screening_type = ScreeningType(
            name=request.form.get("name"),
            description=request.form.get("description"),
            frequency_number=frequency_number,
            frequency_unit=frequency_unit if frequency_unit else None,
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
        # Get frequency data
        frequency_number = request.form.get("frequency_number")
        frequency_unit = request.form.get("frequency_unit")
        
        # Convert frequency_number to int if provided
        if frequency_number:
            try:
                frequency_number = int(frequency_number)
            except (ValueError, TypeError):
                frequency_number = None
        
        screening_type.name = request.form.get("name")
        screening_type.description = request.form.get("description")
        screening_type.frequency_number = frequency_number
        screening_type.frequency_unit = frequency_unit if frequency_unit else None
        screening_type.gender_specific = (
            request.form.get("gender_specific")
            if request.form.get("gender_specific")
            else None
        )
        screening_type.min_age = request.form.get("min_age", type=int)
        screening_type.max_age = request.form.get("max_age", type=int)
        screening_type.is_active = bool(request.form.get("is_active"))

        try:
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
    base_name = variant_manager.extract_base_name(screening_type.name)

    # Check if this screening type is used in any patient screenings
    patient_screenings = Screening.query.filter_by(
        screening_type=screening_type.name
    ).count()

    if patient_screenings > 0:
        # Use unified variant status management to sync all variants
        variant_manager.sync_single_variant_status(screening_type_id, False)
        
        flash(
            f'Screening type "{screening_type.name}" and all its variants have been marked as inactive because it is used by {patient_screenings} patient(s). This affects the unified "{base_name}" status.',
            "warning",
        )
    else:
        # Safe to delete
        name = screening_type.name
        db.session.delete(screening_type)
        db.session.commit()
        
        # Check remaining variants
        remaining_variants = variant_manager.find_screening_variants(base_name)
        if remaining_variants:
            flash(f'Screening type "{name}" has been deleted successfully. Other variants of "{base_name}" remain active.', "success")
        else:
            flash(f'Screening type "{name}" has been deleted successfully. No other variants remain.', "success")

    return redirect(url_for("screening.screening_list", tab="types"))


@screening_bp.route("/types/<int:screening_type_id>/toggle_status")
def toggle_screening_type_status(screening_type_id):
    """Toggle screening type status and sync all variants with unified status"""
    screening_type = ScreeningType.query.get_or_404(screening_type_id)
    base_name = variant_manager.extract_base_name(screening_type.name)
    
    # Toggle status
    new_status = not screening_type.is_active
    
    # Use unified variant status management to sync all variants
    success = variant_manager.sync_single_variant_status(screening_type_id, new_status)
    
    if success:
        status_text = "activated" if new_status else "deactivated"
        flash(f'Screening type "{screening_type.name}" and all its variants have been {status_text}. This affects the unified "{base_name}" status across all tabs.', "success")
        
        # Additional check: Trigger edge case handler for proper cleanup
        if not new_status:
            try:
                from automated_edge_case_handler import handle_screening_type_change
                handle_screening_type_change(screening_type_id, new_status)
            except Exception as e:
                print(f"Warning: Edge case handler failed: {e}")
    else:
        flash(f'Error updating screening type status for "{screening_type.name}".', "error")
    
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
