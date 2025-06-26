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
    # Get or create settings
    settings = get_or_create_settings()

    # Get content sources
    content_sources = request.form.getlist('content_sources')
    settings.content_sources = ','.join(content_sources) if content_sources else ''

    # Get selected screening types from the multiselect dropdown
    selected_screening_types = request.form.getlist('selected_screening_types')
    print(f"INFO: Multiselect received {len(selected_screening_types)} screening types: {selected_screening_types}")

    # Update default items with selected screening types
    if selected_screening_types:
        # Join the selected screening types with newlines
        settings.default_items = '\n'.join(selected_screening_types)
        flash(f'Successfully updated checklist with {len(selected_screening_types)} screening types', 'success')
        print(f"SUCCESS: Saved screening types: {selected_screening_types}")
    else:
        # Clear default items if none selected
        settings.default_items = ''
        flash('Cleared default checklist items - no screening types selected', 'info')
        print("INFO: Cleared default items - no selections made")

    try:
        db.session.commit()
        print(f"DATABASE: Successfully committed {len(selected_screening_types)} screening types to database")
        
        # Verify the save
        db.session.refresh(settings)
        saved_items = settings.default_items_list
        print(f"VERIFIED: Saved items in database: {saved_items}")
        
        if len(saved_items) != len(selected_screening_types):
            print(f"WARNING: Mismatch - sent {len(selected_screening_types)} but saved {len(saved_items)}")
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'danger')
        print(f"ERROR: Database save failed: {e}")

    return redirect(url_for('screening_list', tab='checklist'))


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