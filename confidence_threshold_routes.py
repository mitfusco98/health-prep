#!/usr/bin/env python3
"""
Confidence Threshold Configuration Routes
Handles saving and managing confidence threshold settings
"""

from flask import request, redirect, url_for, flash
from app import app, db

@app.route("/save-confidence-thresholds", methods=["POST"])
def save_confidence_thresholds():
    """Save confidence threshold settings from checklist tab"""
    try:
        # Get form data
        high_threshold = float(request.form.get('confidence_high_threshold', 0.8))
        medium_threshold = float(request.form.get('confidence_medium_threshold', 0.5))
        
        # Validate thresholds
        if high_threshold <= medium_threshold:
            flash("High confidence threshold must be greater than medium threshold", "danger")
            return redirect(url_for('screening_list', tab='checklist'))
        
        if not (0.1 <= high_threshold <= 1.0) or not (0.1 <= medium_threshold <= 1.0):
            flash("Confidence thresholds must be between 0.1 and 1.0", "danger")
            return redirect(url_for('screening_list', tab='checklist'))
        
        # Import here to avoid circular import
        from models import ChecklistSettings
        
        # Get or create settings
        settings = ChecklistSettings.query.first()
        if not settings:
            settings = ChecklistSettings()
            db.session.add(settings)
        
        # Update confidence thresholds
        settings.confidence_high_threshold = high_threshold
        settings.confidence_medium_threshold = medium_threshold
        
        # Save to database
        db.session.commit()
        
        flash(f"Confidence thresholds updated: High {high_threshold:.2f}, Medium {medium_threshold:.2f}", "success")
        
    except ValueError:
        flash("Invalid threshold values. Please enter numbers between 0.1 and 1.0", "danger")
    except Exception as e:
        flash(f"Error saving confidence thresholds: {str(e)}", "danger")
        db.session.rollback()
    
    return redirect(url_for('screening_list', tab='checklist'))