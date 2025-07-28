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
    """Save standard status options for prep sheet checklists"""
    # Get or create settings
    settings = ChecklistSettings.query.first()
    if not settings:
        settings = ChecklistSettings()
        db.session.add(settings)

    # Status options are now permanently fixed and cannot be modified
    # Always use: due, due_soon, incomplete, completed
    flash('Status options are now permanently fixed and cannot be modified.', 'info')

    try:
        db.session.commit()
        flash('Status options updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status options: {str(e)}', 'danger')

    # Redirect back to checklist tab
    return redirect(url_for('screening_list', tab='checklist'))


@app.route('/save-default-items-simple', methods=['POST'])
def save_default_items_simple():
    """Legacy route - default items no longer used"""
    flash('Prep sheet content is now controlled by the screening engine. Use the Screenings tab to manage content.', 'info')
    return redirect(url_for('screening_list', tab='checklist'))