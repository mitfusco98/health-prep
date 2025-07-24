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





@app.route("/save-status-options-simple", methods=["POST"])
@safe_db_operation
def save_status_options_simple():
    """Save status options for prep sheet checklists"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get status options from form
    status_options = request.form.getlist("status_options")

    # Update settings
    settings.custom_status_options = (
        ",".join(status_options) if status_options else ""
    )

    # Save settings
    db.session.commit()

    flash("Status options updated successfully!", "success")

    # Redirect back to checklist settings
    return redirect(url_for("checklist_settings"))


@app.route("/checklist-settings/generation", methods=["POST"])
@safe_db_operation
def update_checklist_generation():
    """Update default items for the prep sheet quality checklist"""
    # Get or create settings
    settings = get_or_create_settings()

    # Get manual default items from textarea
    manual_default_items = request.form.get("default_items", "")

    # Update settings
    settings.default_items = manual_default_items

    try:
        # Save settings
        db.session.commit()
        flash("Default checklist items updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'danger')

    # Redirect back to checklist settings
    return redirect(url_for("checklist_settings"))


# Custom status routes removed - using standard status options only
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

        # Handle screening-specific cutoffs with improved processing
        screening_cutoffs_processed = 0
        
        # Get all active screening types to validate against
        from models import ScreeningType
        active_screening_names = [st.name for st in ScreeningType.query.filter_by(is_active=True).all()]
        print(f"DEBUG: Active screening types: {active_screening_names}")
        
        for key, value in request.form.items():
            if key.startswith("screening_cutoff_"):
                # Extract screening name from field name (screening_cutoff_ScreeningName)
                screening_name = key.replace("screening_cutoff_", "")
                
                # Validate that this is a known active screening type
                if screening_name not in active_screening_names:
                    print(f"WARNING: Unknown screening type '{screening_name}' in form data")
                    continue
                    
                try:
                    # Convert empty string to 0. Preserve all numeric values including 0
                    if value == '' or value is None:
                        months = 0
                    else:
                        months = int(value)
                    
                    # Validate the range
                    if months < 0 or months > 120:
                        print(f"WARNING: Invalid cutoff value {months} for '{screening_name}', skipping")
                        continue
                    
                    # Set the cutoff value exactly as provided by user
                    old_value = settings.get_screening_cutoff(screening_name)
                    settings.set_screening_cutoff(screening_name, months)
                    screening_cutoffs_processed += 1
                    print(f"DEBUG: Successfully updated cutoff for '{screening_name}': {old_value} -> {months} months (form value: '{value}')")
                except (ValueError, TypeError) as e:
                    print(f"ERROR: Error processing cutoff for '{screening_name}' with value '{value}': {e}")
                    # Skip this field if there's an error, don't modify existing value
                    continue
                
        print(f"DEBUG: Processed {screening_cutoffs_processed} screening cutoffs out of {len(active_screening_names)} active screening types")
        
        # Debug: Print all form data to help identify issues
        print("DEBUG: All form data received:")
        for key, value in request.form.items():
            print(f"  {key}: {repr(value)}")
            
        # Debug: Check if problematic fields are in form data
        bone_density_field = request.form.get("screening_cutoff_Bone Density Screening")
        hba1c_field = request.form.get("screening_cutoff_HbA1c Testing")
        print(f"DEBUG: Bone Density form field: {repr(bone_density_field)}")
        print(f"DEBUG: HbA1c form field: {repr(hba1c_field)}")
            
        # Debug: Print current screening cutoffs after processing
        print("DEBUG: Current screening cutoffs after processing:")
        if hasattr(settings, 'screening_cutoffs_dict') and settings.screening_cutoffs_dict:
            for screening, cutoff in settings.screening_cutoffs_dict.items():
                print(f"  {screening}: {cutoff} months")
        else:
            print("  No screening_cutoffs_dict found or empty")
            
        # Debug: Print the raw screening_cutoffs value
        print(f"DEBUG: Raw screening_cutoffs value: {repr(settings.screening_cutoffs)}")
        
        # Specific debug for problematic screening types
        bone_density_cutoff = settings.get_screening_cutoff("Bone Density Screening")
        hba1c_cutoff = settings.get_screening_cutoff("HbA1c Testing")
        print(f"DEBUG: Bone Density Screening cutoff: {bone_density_cutoff}")
        print(f"DEBUG: HbA1c Testing cutoff: {hba1c_cutoff}")
        
        # Debug: Check if these values are being overridden somewhere
        print("DEBUG: Final verification before commit:")
        print(f"  Bone Density final value: {settings.get_screening_cutoff('Bone Density Screening')}")
        print(f"  HbA1c final value: {settings.get_screening_cutoff('HbA1c Testing')}")

        # Verify settings before commit
        print("DEBUG: Verifying settings before commit:")
        for screening_name in active_screening_names:
            current_cutoff = settings.get_screening_cutoff(screening_name)
            print(f"  {screening_name}: {current_cutoff} months")
        
        db.session.commit()
        
        # Verify settings after commit
        print("DEBUG: Verifying settings after commit:")
        settings_after = get_or_create_settings()
        for screening_name in active_screening_names:
            current_cutoff = settings_after.get_screening_cutoff(screening_name)
            print(f"  {screening_name}: {current_cutoff} months")
        
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
        print(f"ERROR: Exception in save_cutoff_settings: {e}")
        flash("Invalid cutoff values provided. Please enter valid numbers.", "error")
    except Exception as e:
        print(f"ERROR: Unexpected exception in save_cutoff_settings: {e}")
        db.session.rollback()
        flash(f"Error updating cutoff settings: {str(e)}", "error")

    return redirect(url_for("screening_list", tab="checklist"))