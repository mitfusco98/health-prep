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
    # DEBUG: Print all form data
    print("DEBUG: Display settings form data:")
    for key, value in request.form.items():
        print(f"  {key}: {value}")

    print("DEBUG: Checkbox lists:")
    for key in request.form.keys():
        values = request.form.getlist(key)
        if len(values) > 1:
            print(f"  {key}: {values}")

    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    layout_style = request.form.get("layout_style", "list")
    status_options = request.form.getlist("status_options")
    custom_status_options = request.form.getlist("custom_status_options")
    show_notes = "show_notes" in request.form

    # DEBUG: Print parsed values
    print(f"DEBUG: layout_style = {layout_style}")
    print(f"DEBUG: status_options = {status_options}")
    print(f"DEBUG: custom_status_options = {custom_status_options}")
    print(f"DEBUG: show_notes = {show_notes}")

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
    # DEBUG: Print all form data
    print("DEBUG: All form data received:")
    for key, value in request.form.items():
        print(f"  {key}: {value}")

    print("DEBUG: All form lists:")
    for key in request.form.keys():
        values = request.form.getlist(key)
        if len(values) > 1:
            print(f"  {key}: {values}")

    print("DEBUG: Raw form data:", dict(request.form))

    # Get or create settings
    settings = get_or_create_settings()

    # Get form data
    content_sources = request.form.getlist("content_sources")

    # Get selected screening types from hidden inputs (button selections)
    selected_screening_types = request.form.getlist("selected_screening_types")
    print(f"DEBUG: Received selected_screening_types: {selected_screening_types}")
    print(f"DEBUG: Number of selected items: {len(selected_screening_types)}")

    # Get manual default items from textarea (fallback)
    manual_default_items = request.form.get("default_items", "")
    print(f"DEBUG: Manual default_items from textarea: '{manual_default_items}'")

    # Update settings
    settings.content_sources = (
        ",".join(content_sources) if content_sources else "database"
    )

    # Priority logic: Button selections override manual textarea input
    if selected_screening_types:
        # Use button selections - join with newlines to preserve multiple selections
        settings.default_items = '\n'.join(selected_screening_types)
        print(f"DEBUG: Using button selections: '{settings.default_items}'")
        print(f"DEBUG: Saved {len(selected_screening_types)} screening types")
    else:
        # Fall back to manual textarea input only if no buttons selected
        settings.default_items = manual_default_items
        print(f"DEBUG: Using manual textarea input: '{manual_default_items}'")

    try:
        # Save settings
        db.session.commit()
        print(f"INFO: Successfully saved {len(selected_screening_types) if selected_screening_types else 0} default items to database")
        flash("Prep sheet generation settings updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Database error: {str(e)}")
        flash(f'Error updating settings: {str(e)}', 'danger')

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


@app.route("/debug-form", methods=["GET", "POST"])
def debug_form():
    """Debug route to inspect form data from checkboxes"""
    if request.method == "GET":
        # Return a simple test form
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug Form</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        </head>
        <body>
            <div class="container mt-5">
                <h2>Debug Form for Multiple Checkboxes</h2>
                <form method="POST">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

                    <h4>Test Checkboxes:</h4>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="test_options" value="option1" id="opt1">
                        <label class="form-check-label" for="opt1">Option 1</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="test_options" value="option2" id="opt2">
                        <label class="form-check-label" for="opt2">Option 2</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="test_options" value="option3" id="opt3">
                        <label class="form-check-label" for="opt3">Option 3</label>
                    </div>

                    <h4 class="mt-4">Single Checkbox:</h4>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="single_check" value="yes" id="single">
                        <label class="form-check-label" for="single">Single Option</label>
                    </div>

                    <h4 class="mt-4">Text Input:</h4>
                    <input type="text" name="text_input" class="form-control" placeholder="Enter some text">

                    <button type="submit" class="btn btn-primary mt-3">Submit for Debug</button>
                </form>
            </div>
        </body>
        </html>
        '''

    else:  # POST
        print("\n" + "="*50)
        print("FORM DEBUG OUTPUT")
        print("="*50)

        # Print all form data
        print("ALL FORM DATA:")
        for key, value in request.form.items():
            print(f"  {key}: {repr(value)}")

        print("\nFORM LISTS (for checkboxes):")
        for key in request.form.keys():
            values = request.form.getlist(key)
            print(f"  {key}: {values} (count: {len(values)})")

        print("\nRAW FORM DICT:")
        print(f"  {dict(request.form)}")

        print("\nMULTI DICT TO DICT:")
        print(f"  {request.form.to_dict(flat=False)}")

        print("\nCHECKING SPECIFIC FIELDS:")
        test_options = request.form.getlist("test_options")
        single_check = request.form.get("single_check")
        text_input = request.form.get("text_input")

        print(f"  test_options: {test_options}")
        print(f"  single_check: {repr(single_check)} (exists: {'single_check' in request.form})")
        print(f"  text_input: {repr(text_input)}")

        print("="*50 + "\n")

        return f'''
        <div class="container mt-5">
            <h2>Debug Results</h2>
            <h4>Check the console/logs for detailed output</h4>
            <p>test_options: {test_options}</p>
            <p>single_check: {single_check}</p>
            <p>text_input: {text_input}</p>
            <a href="/debug-form" class="btn btn-secondary">Try Again</a>
        </div>
        '''