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

    # Get form data
    content_sources = request.form.getlist("content_sources")
    selected_screening_types = request.form.getlist("selected_screening_types")
    
    # Check for serialized fallback if normal checkboxes failed
    serialized_data = request.form.get("selected_screening_types_serialized")
    backup_data = request.form.get("selected_screening_types_backup")
    
    if (not selected_screening_types or len(selected_screening_types) <= 1):
        if serialized_data:
            try:
                import json
                selected_screening_types = json.loads(serialized_data)
                print(f"DEBUG: Using JSON serialized data: {selected_screening_types}")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"DEBUG: Error parsing JSON serialized data: {e}")
                # Try backup method
                if backup_data:
                    selected_screening_types = backup_data.split('|||')
                    print(f"DEBUG: Using backup string data: {selected_screening_types}")
        elif backup_data:
            selected_screening_types = backup_data.split('|||')
            print(f"DEBUG: Using backup string data: {selected_screening_types}")
    
    print(f"DEBUG: ===== FORM SUBMISSION DEBUG =====")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Content type: {request.content_type}")
    print(f"DEBUG: Raw form data: {request.form}")
    print(f"DEBUG: Form data as dict: {dict(request.form)}")
    
    print(f"DEBUG: content_sources (getlist): {content_sources}")
    print(f"DEBUG: selected_screening_types (final): {selected_screening_types}")
    print(f"DEBUG: Number of selected items: {len(selected_screening_types)}")
    print(f"DEBUG: Serialized fallback used: {serialized_data is not None}")
    
    # Filter out empty values
    selected_screening_types = [item for item in selected_screening_types if item and item.strip()]
    print(f"DEBUG: Filtered selected_screening_types: {selected_screening_types}")
    print(f"DEBUG: Number of filtered items: {len(selected_screening_types)}")
    
    print(f"DEBUG: ===== END FORM DEBUG =====")
    
    # Update settings
    settings.content_sources = (
        ",".join(content_sources) if content_sources else "database"
    )
    
    # Update default items with selected screening types
    if selected_screening_types and len(selected_screening_types) > 0:
        # Filter out any empty strings and join with newlines
        filtered_types = [item.strip() for item in selected_screening_types if item.strip()]
        settings.default_items = '\n'.join(filtered_types)
        print(f"DEBUG: Updated default_items to: '{settings.default_items}'")
        print(f"DEBUG: Length of default_items string: {len(settings.default_items)}")
        print(f"DEBUG: Number of items stored: {len(filtered_types)}")
    else:
        # Clear default items if no screening types selected
        settings.default_items = ''
        print(f"DEBUG: Cleared default_items (no selections)")

    try:
        db.session.commit()
        print(f"DEBUG: Successfully committed to database")

        # Verify the data was saved
        db.session.refresh(settings)
        print(f"DEBUG: After refresh, default_items: '{settings.default_items}'")
        print(f"DEBUG: default_items_list: {settings.default_items_list}")
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'danger')
        return redirect(url_for("screening_list", tab="checklist"))

    flash("Prep sheet generation settings updated successfully!", "success")

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


@app.route("/test-checkboxes", methods=["POST"])
def test_checkboxes():
    """Test route to debug multiple checkbox submission"""
    print("=== CHECKBOX TEST ROUTE ===")
    print(f"Request method: {request.method}")
    print(f"Content type: {request.content_type}")
    print(f"Form data: {dict(request.form)}")
    
    # Test different ways to get the data
    test_items_getlist = request.form.getlist('test_items')
    test_items_get = request.form.get('test_items')
    
    print(f"request.form.getlist('test_items'): {test_items_getlist}")
    print(f"request.form.get('test_items'): {test_items_get}")
    print(f"Length of getlist result: {len(test_items_getlist)}")
    
    return jsonify({
        "success": True,
        "getlist_result": test_items_getlist,
        "get_result": test_items_get,
        "count": len(test_items_getlist)
    })
