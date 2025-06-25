from flask import render_template, request, redirect, url_for, flash, jsonify
import time as time_module
from app import app, db
from models import ChecklistSettings
from db_utils import safe_db_operation


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
        "checklist_settings.html",
        settings=settings,
        default_items_text=default_items_text,
        cache_timestamp=cache_timestamp,
    )


@app.route("/checklist-settings/display", methods=["POST"])
@safe_db_operation
def update_checklist_settings():
    """Update display settings for the prep sheet quality checklist"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    layout_style = request.form.get("layout_style", "list")
    status_options = request.form.getlist("status_options")
    custom_status_options = request.form.getlist("custom_status_options")
    show_notes = "show_notes" in request.form

    # Update settings
    settings.layout_style = layout_style
    settings.status_options = (
        ",".join(status_options) if status_options else "due,due_soon"
    )
    settings.custom_status_options = (
        ",".join(custom_status_options) if custom_status_options else ""
    )
    settings.show_notes = show_notes

    # Save settings
    db.session.commit()

    flash("Prep sheet display settings updated successfully!", "success")

    # Redirect back to the screening list page with the checklist tab active
    return redirect(url_for("screening_list", tab="checklist"))


@app.route("/checklist-settings/generation", methods=["POST"])
@safe_db_operation
def update_checklist_generation():
    """Update content generation settings for the prep sheet quality checklist"""
    
    # Debug: Print comprehensive form debugging info
    print(f"DEBUG: Raw request.form: {request.form}")
    print(f"DEBUG: Raw request.form type: {type(request.form)}")
    print(f"DEBUG: All form keys: {list(request.form.keys())}")
    print(f"DEBUG: Form as dict: {dict(request.form)}")
    
    # Check for multiple values specifically
    print(f"DEBUG: request.form.getlist('selected_screening_types'): {request.form.getlist('selected_screening_types')}")
    
    # Check raw form data
    for key in request.form.keys():
        if 'screening' in key.lower():
            values = request.form.getlist(key)
            print(f"DEBUG: Key '{key}' has {len(values)} values: {values}")
    
    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    content_sources = request.form.getlist("content_sources")
    selected_screening_types = request.form.getlist("selected_screening_types")
    
    print(f"DEBUG: Content sources: {content_sources}")
    print(f"DEBUG: Selected screening types: {selected_screening_types}")
    print(f"DEBUG: Selected screening types count: {len(selected_screening_types)}")

    # Update settings
    settings.content_sources = (
        ",".join(content_sources) if content_sources else "database"
    )
    
    # Use the selected screening types as default items
    settings.default_items = ",".join(selected_screening_types) if selected_screening_types else ""
    
    print(f"DEBUG: Saving default_items as: '{settings.default_items}'")

    # Save settings
    db.session.commit()

    flash(f"Prep sheet generation settings updated successfully! Saved {len(selected_screening_types)} screening types.", "success")

    # Redirect back to the screening list page with the checklist tab active
    return redirect(url_for("screening_list", tab="checklist"))


@app.route("/checklist-settings/remove-custom-status", methods=["POST"])
@safe_db_operation
def remove_custom_status():
    """Remove a specific custom status option from the prep sheet quality checklist settings"""
    # Get the current settings
    settings = get_or_create_settings()

    # Get the status to remove
    status_to_remove = request.form.get("status")

    if not status_to_remove:
        return jsonify({"success": False, "error": "No status specified"}), 400

    # Get current custom statuses
    custom_statuses = settings.custom_status_list

    # Remove the specified status if it exists
    if status_to_remove in custom_statuses:
        custom_statuses.remove(status_to_remove)
        settings.custom_status_options = (
            ",".join(custom_statuses) if custom_statuses else ""
        )
        db.session.commit()
        return jsonify({"success": True})

    return jsonify({"success": False, "error": "Status not found"}), 404
