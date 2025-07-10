from flask import render_template, request, redirect, url_for, flash
from app import app, db
from models import ChecklistSettings, ScreeningType
from app import login_required
import json


@app.route('/screening-checklist-rebuilt')
@login_required
def screening_checklist_rebuilt():
    """Clean rebuild of checklist settings page"""
    # Get current settings
    settings = ChecklistSettings.query.first()
    if not settings:
        settings = ChecklistSettings()
        db.session.add(settings)
        db.session.commit()

    # Get active screening types
    active_screening_types = ScreeningType.query.filter_by(
        is_active=True, 
        status='active'
    ).order_by(ScreeningType.name).all()

    return render_template(
        'screening_checklist_rebuilt.html',
        settings=settings,
        active_screening_types=active_screening_types
    )


@app.route('/save-status-options-simple', methods=['POST'])
def save_status_options_simple():
    """Save status options with simple, reliable processing"""
    try:
        # Get current settings
        settings = ChecklistSettings.query.first()
        if not settings:
            settings = ChecklistSettings()
            db.session.add(settings)

        # Get selections from the single hidden input
        status_selections = request.form.get('status_selections', '')
        print(f"Received status selections: '{status_selections}'")

        # Get custom status options
        custom_status_options = request.form.getlist('custom_status_options')
        print(f"Received custom status options: {custom_status_options}")

        # Update settings - handle both regular and custom status options
        settings.status_options = status_selections if status_selections else ""
        
        # Update custom status options - filter out empty values
        filtered_custom_options = [opt for opt in custom_status_options if opt.strip()]
        if filtered_custom_options:
            settings.custom_status_options = ','.join(filtered_custom_options)
        else:
            settings.custom_status_options = ""

        # Commit to database
        db.session.commit()

        total_regular = len(status_selections.split(',')) if status_selections else 0
        total_custom = len(filtered_custom_options)
        total_options = total_regular + total_custom
        
        flash(f'Successfully saved {total_options} status options ({total_custom} custom)', 'success')
        print(f"Successfully saved status options: {status_selections}")
        print(f"Successfully saved custom status options: {filtered_custom_options}")
        print(f"Final custom_status_options in DB: {settings.custom_status_options}")

    except Exception as e:
        db.session.rollback()
        flash(f'Error saving status options: {str(e)}', 'danger')
        print(f"Error saving status options: {e}")

    return redirect(url_for('screening_list', tab='checklist'))


@app.route('/save-default-items-simple', methods=['POST'])
def save_default_items_simple():
    """Save default items with simple, reliable processing"""
    try:
        # Get current settings
        settings = ChecklistSettings.query.first()
        if not settings:
            settings = ChecklistSettings()
            db.session.add(settings)

        # Get selections from the single hidden input
        screening_selections = request.form.get('screening_selections', '')
        print(f"Received screening selections: '{screening_selections}'")

        # Convert comma-separated to newline-separated for storage
        if screening_selections:
            default_items = screening_selections.replace(',', '\n')
        else:
            default_items = ''

        # Update settings
        settings.default_items = default_items

        # Commit to database
        db.session.commit()

        flash(f'Successfully saved default items: {len(screening_selections.split(",") if screening_selections else [])} items', 'success')
        print(f"Successfully saved default items: {default_items}")

    except Exception as e:
        db.session.rollback()
        flash(f'Error saving default items: {str(e)}', 'danger')
        print(f"Error saving default items: {e}")

    return redirect(url_for('screening_list', tab='checklist'))

