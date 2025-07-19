from flask import render_template, request, redirect, url_for, flash, jsonify
import time as time_module
from datetime import datetime, timedelta
from app import app, db
from models import ChecklistSettings, Appointment
from db_utils import safe_db_operation
from screening_variant_manager import variant_manager


def get_or_create_settings():
    """Get or create checklist settings"""
    settings = ChecklistSettings.query.first()
    if not settings:
        settings = ChecklistSettings()
        db.session.add(settings)
        db.session.commit()
    return settings


@app.route("/checklist-settings", methods=["GET"])
def checklist_settings():
    """Display and manage prep sheet quality checklist settings"""
    # Generate timestamp for cache busting
    cache_timestamp = int(time_module.time())

    # Get current settings
    settings = get_or_create_settings()

    # Default items as string with newlines
    default_items_text = (
        "\n".join(settings.default_items_list) if settings.default_items else ""
    )

    return render_template(
        "checklist_settings_updated.html",
        settings=settings,
        default_items_text=default_items_text,
        cache_timestamp=cache_timestamp,
    )


@app.route("/checklist-settings/display", methods=["POST"])
def update_checklist_settings():
    """Update display settings for the prep sheet quality checklist"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    layout_style = request.form.get("layout_style", "list")
    status_options = request.form.getlist("status_options")
    show_notes = "show_notes" in request.form

    # Update settings - DEBUG THE WORKING STATUS OPTIONS
    print(f"DEBUG STATUS OPTIONS: Received {len(status_options)} items: {status_options}")
    settings.layout_style = layout_style
    settings.status_options = (
        ",".join(status_options) if status_options else "due,due_soon"
    )
    settings.custom_status_options = ""  # Custom status options no longer supported
    settings.show_notes = show_notes

    # Save settings
    db.session.commit()

    flash("Prep sheet display settings updated successfully!", "success")

    # Redirect back to the screening list page with the checklist tab active
    return redirect(url_for("screening_list", tab="checklist"))


@app.route("/checklist-settings/cutoff", methods=["POST"])
@safe_db_operation
def update_checklist_cutoff_settings():
    """Update time-based cutoff settings for medical data filtering"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    labs_cutoff = request.form.get("labs_cutoff_months", type=int)
    imaging_cutoff = request.form.get("imaging_cutoff_months", type=int)
    consults_cutoff = request.form.get("consults_cutoff_months", type=int)
    hospital_cutoff = request.form.get("hospital_cutoff_months", type=int)

    # Validate and update settings (0 means use last appointment date)
    if labs_cutoff is not None:
        settings.labs_cutoff_months = labs_cutoff
    if imaging_cutoff is not None:
        settings.imaging_cutoff_months = imaging_cutoff
    if consults_cutoff is not None:
        settings.consults_cutoff_months = consults_cutoff
    if hospital_cutoff is not None:
        settings.hospital_cutoff_months = hospital_cutoff

    # Save settings
    db.session.commit()

    flash("Data cutoff settings updated successfully!", "success")

    # ✅ EDGE CASE HANDLER: Trigger auto-refresh when cutoff settings change
    try:
        from automated_edge_case_handler import trigger_global_auto_refresh
        refresh_result = trigger_global_auto_refresh("checklist_cutoff_settings_updated")
        if refresh_result.get("status") == "success":
            import logging
            logging.info(f"Auto-refreshed all screenings after checklist cutoff settings update")
    except Exception as e:
        import logging
        logging.error(f"Auto-refresh failed after checklist cutoff settings update: {e}")
        # Don't fail the settings update if auto-refresh fails

    # Redirect back to the screening list page with the checklist tab active
    return redirect(url_for("screening_list", tab="checklist"))


@app.route("/checklist-settings/generation", methods=["POST"])
@safe_db_operation
def update_checklist_generation():
    """Update content generation settings for the prep sheet quality checklist"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get content sources
    content_sources = request.form.getlist('content_sources')
    settings.content_sources = ','.join(content_sources) if content_sources else ''

    # Get selected screening types from the checkboxes
    selected_screening_types = request.form.getlist('selected_screening_types')
    print(f"DEBUG: Received selected_screening_types: {selected_screening_types}")
    
    # Clean up inactive screening types from default items (automatic maintenance)
    from models import ScreeningType
    active_screening_names = {st.name for st in ScreeningType.query.filter_by(is_active=True).all()}
    
    # Consolidate to base names to handle variants
    consolidated_base_names = set()
    for screening_name in selected_screening_types:
        base_name = variant_manager.extract_base_name(screening_name)
        consolidated_base_names.add(base_name)
    
    consolidated_list = list(consolidated_base_names)
    print(f"DEBUG: Consolidated to base names: {consolidated_list}")

    # Update default items with consolidated base names  
    if consolidated_list:
        # Filter out inactive screening types during update (maintenance)
        active_consolidated_list = [item for item in consolidated_list if item in active_screening_names]
        if len(active_consolidated_list) != len(consolidated_list):
            print(f"🧹 Filtered out {len(consolidated_list) - len(active_consolidated_list)} inactive screening types")
        
        # Join the active consolidated screening base names with newlines
        settings.default_items = '\n'.join(active_consolidated_list)
        print(f"DEBUG: Updated default_items to active consolidated: '{settings.default_items}'")
    else:
        # Fall back to manual default items input if no screening types selected
        default_items = request.form.get('default_items', '')
        # Filter manual items too
        if default_items:
            manual_items = default_items.split('\n')
            active_manual_items = [item.strip() for item in manual_items if item.strip() in active_screening_names]
            settings.default_items = '\n'.join(active_manual_items)
        else:
            settings.default_items = default_items
        print(f"DEBUG: Using filtered manual default_items: '{settings.default_items}'")

    try:
        db.session.commit()
        print(f"INFO: Successfully saved {len(selected_screening_types) if selected_screening_types else 0} default items to database")
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'danger')

    return redirect(url_for('screening_list', tab='checklist'))





@app.route("/save-cutoff-settings", methods=["POST"])
@safe_db_operation
def save_cutoff_settings():
    """Update data cutoff settings for medical data parsing"""
    settings = get_or_create_settings()
    
    # Get cutoff values from form (default to 0 for "last appointment" logic)
    try:
        settings.labs_cutoff_months = int(request.form.get("labs_cutoff_months", 0))
        settings.imaging_cutoff_months = int(request.form.get("imaging_cutoff_months", 0))
        settings.consults_cutoff_months = int(request.form.get("consults_cutoff_months", 0))
        settings.hospital_cutoff_months = int(request.form.get("hospital_cutoff_months", 0))
        
        # Handle screening-specific cutoffs (default to 0 for "last appointment" logic)
        # Get all active screening types to match against
        from models import ScreeningType
        active_screening_types = ScreeningType.query.filter_by(
            is_active=True, 
            status='active'
        ).all()
        
        for screening in active_screening_types:
            # Convert screening name to field name format (spaces to underscores, lowercase)
            field_name = f"screening_cutoff_{screening.name.replace(' ', '_').lower()}"
            
            # Get the cutoff value from form
            cutoff_value = request.form.get(field_name)
            
            if cutoff_value is not None:
                try:
                    cutoff_months = int(cutoff_value)
                    settings.set_screening_cutoff(screening.name, cutoff_months)
                    print(f"Saved cutoff for '{screening.name}': {cutoff_months} months (field: {field_name})")
                except (ValueError, TypeError):
                    print(f"Invalid cutoff value for '{screening.name}': {cutoff_value}")
                    # Set default to 0 if invalid
                    settings.set_screening_cutoff(screening.name, 0)
            else:
                print(f"No cutoff value found for '{screening.name}' (field: {field_name})")
                # Keep existing value or set to 0 if none exists
                existing_cutoff = settings.get_screening_cutoff(screening.name, 0)
                if existing_cutoff == 12:  # Default value, set to 0
                    settings.set_screening_cutoff(screening.name, 0)
        
        db.session.commit()
        flash("Data cutoff settings updated successfully!", "success")
        
        # ✅ EDGE CASE HANDLER: Trigger auto-refresh when screening-specific cutoff settings change
        try:
            from automated_edge_case_handler import trigger_global_auto_refresh
            refresh_result = trigger_global_auto_refresh("screening_specific_cutoff_settings_updated")
            if refresh_result.get("status") == "success":
                import logging
                logging.info(f"Auto-refreshed all screenings after screening-specific cutoff settings update")
        except Exception as e:
            import logging
            logging.error(f"Auto-refresh failed after screening-specific cutoff settings update: {e}")
            # Don't fail the settings update if auto-refresh fails
        
    except (ValueError, TypeError) as e:
        flash("Invalid cutoff values provided. Please enter valid numbers.", "error")
        
    return redirect(url_for("screening_list", tab="checklist"))


@app.route("/api/recent-appointments")
def get_recent_appointments():
    """Get recent appointment dates for cutoff configuration"""
    try:
        # Get the last 5 appointment dates across all patients
        recent_appointments = db.session.query(Appointment)\
            .filter(Appointment.appointment_date.isnot(None))\
            .order_by(Appointment.appointment_date.desc())\
            .limit(5)\
            .all()
        
        # Convert to list of date strings
        appointment_dates = []
        for apt in recent_appointments:
            if apt.appointment_date:
                appointment_dates.append({
                    'date': apt.appointment_date.strftime('%Y-%m-%d'),
                    'formatted_date': apt.appointment_date.strftime('%B %d, %Y')
                })
        
        return jsonify({
            'success': True,
            'appointments': appointment_dates
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/update-cutoff-settings", methods=["POST"])
@safe_db_operation
def update_cutoff_settings():
    """Update general cutoff settings for prep sheet data"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    cutoff_months = request.form.get("cutoff_months")
    
    # Update general cutoff setting
    if cutoff_months and cutoff_months.strip():
        try:
            settings.cutoff_months = int(cutoff_months)
        except ValueError:
            flash("Invalid cutoff months value", "danger")
            return redirect(url_for("checklist_settings"))
    else:
        # If empty, set to None to use last appointment date fallback
        settings.cutoff_months = None

    # Save settings
    db.session.commit()

    if settings.cutoff_months:
        flash(f"General cutoff period set to {settings.cutoff_months} months!", "success")
    else:
        flash("Cutoff period reset to use last appointment date for each patient", "success")

    # ✅ EDGE CASE HANDLER: Trigger auto-refresh when general cutoff settings change
    try:
        from automated_edge_case_handler import trigger_global_auto_refresh
        refresh_result = trigger_global_auto_refresh("general_cutoff_settings_updated")
        if refresh_result.get("status") == "success":
            import logging
            logging.info(f"Auto-refreshed all screenings after general cutoff settings update")
    except Exception as e:
        import logging
        logging.error(f"Auto-refresh failed after general cutoff settings update: {e}")
        # Don't fail the settings update if auto-refresh fails

    # Redirect back to checklist settings
    return redirect(url_for("checklist_settings"))


@app.route("/update-individual-cutoffs", methods=["POST"])
@safe_db_operation
def update_individual_cutoffs():
    """Update individual cutoff settings for different medical data types"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    labs_cutoff = request.form.get("labs_cutoff_months", type=int)
    imaging_cutoff = request.form.get("imaging_cutoff_months", type=int)
    consults_cutoff = request.form.get("consults_cutoff_months", type=int)
    hospital_cutoff = request.form.get("hospital_cutoff_months", type=int)

    # Update individual cutoff settings (0 means use last appointment date)
    if labs_cutoff is not None:
        settings.labs_cutoff_months = labs_cutoff
    if imaging_cutoff is not None:
        settings.imaging_cutoff_months = imaging_cutoff
    if consults_cutoff is not None:
        settings.consults_cutoff_months = consults_cutoff
    if hospital_cutoff is not None:
        settings.hospital_cutoff_months = hospital_cutoff

    # Save settings
    db.session.commit()

    flash("Individual data type cutoffs updated successfully!", "success")

    # ✅ EDGE CASE HANDLER: Trigger auto-refresh when cutoff settings change
    try:
        from automated_edge_case_handler import trigger_global_auto_refresh
        refresh_result = trigger_global_auto_refresh("cutoff_settings_updated")
        if refresh_result.get("status") == "success":
            import logging
            logging.info(f"Auto-refreshed all screenings after cutoff settings update")
    except Exception as e:
        import logging
        logging.error(f"Auto-refresh failed after cutoff settings update: {e}")
        # Don't fail the settings update if auto-refresh fails

    # Redirect back to checklist settings
    return redirect(url_for("checklist_settings"))