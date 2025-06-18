"""
PrepChecklist Routes - Dynamic checklist management interface
Provides routes for managing intelligent prep checklists with keyword matching
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from datetime import datetime, date
import json
from app import app, db
from models import Patient, ScreeningType
from prep_checklist_service import PrepChecklistEvaluator, PrepChecklistManager
from models import (
    PrepChecklistTemplate, PrepChecklistItem, PrepChecklistResult, 
    PrepChecklistConfiguration, PrepChecklistSection, PrepChecklistItemType,
    PrepChecklistMatchStatus
)
from admin_middleware import admin_required


@app.route("/prep-checklist")
def prep_checklist_dashboard():
    """Main dashboard for prep checklist management"""
    config = PrepChecklistConfiguration.get_config()
    templates = PrepChecklistTemplate.query.filter_by(is_active=True).all()
    
    # Get recent evaluations
    recent_evaluations = PrepChecklistResult.query.order_by(
        PrepChecklistResult.evaluated_at.desc()
    ).limit(10).all()
    
    # Calculate statistics
    total_templates = len(templates)
    total_items = PrepChecklistItem.query.filter_by(is_active=True).count()
    recent_matches = PrepChecklistResult.query.filter(
        PrepChecklistResult.match_status == PrepChecklistMatchStatus.FOUND,
        PrepChecklistResult.evaluated_at >= datetime.now().replace(hour=0, minute=0, second=0)
    ).count()
    
    return render_template(
        "prep_checklist/dashboard.html",
        config=config,
        templates=templates,
        recent_evaluations=recent_evaluations,
        stats={
            'total_templates': total_templates,
            'total_items': total_items,
            'recent_matches': recent_matches
        }
    )


@app.route("/prep-checklist/templates")
def prep_checklist_templates():
    """Manage prep checklist templates"""
    templates = PrepChecklistTemplate.query.all()
    return render_template("prep_checklist/templates.html", templates=templates)


@app.route("/prep-checklist/templates/create", methods=["GET", "POST"])
@admin_required
def create_prep_checklist_template():
    """Create a new prep checklist template"""
    if request.method == "POST":
        template = PrepChecklistTemplate(
            name=request.form["name"],
            description=request.form.get("description", ""),
            is_active=True,
            is_default=request.form.get("is_default") == "on"
        )
        
        # If this is set as default, unset other defaults
        if template.is_default:
            PrepChecklistTemplate.query.filter_by(is_default=True).update({"is_default": False})
        
        db.session.add(template)
        db.session.commit()
        
        flash("Prep checklist template created successfully.", "success")
        return redirect(url_for("prep_checklist_templates"))
    
    return render_template("prep_checklist/create_template.html")


@app.route("/prep-checklist/templates/<int:template_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_prep_checklist_template(template_id):
    """Edit a prep checklist template"""
    template = PrepChecklistTemplate.query.get_or_404(template_id)
    
    if request.method == "POST":
        template.name = request.form["name"]
        template.description = request.form.get("description", "")
        template.is_active = request.form.get("is_active") == "on"
        
        # Handle default template setting
        is_default = request.form.get("is_default") == "on"
        if is_default and not template.is_default:
            PrepChecklistTemplate.query.filter_by(is_default=True).update({"is_default": False})
            template.is_default = True
        elif not is_default and template.is_default:
            template.is_default = False
        
        db.session.commit()
        flash("Template updated successfully.", "success")
        return redirect(url_for("prep_checklist_templates"))
    
    return render_template("prep_checklist/edit_template.html", template=template)


@app.route("/prep-checklist/templates/<int:template_id>/items")
def prep_checklist_template_items(template_id):
    """Manage items in a prep checklist template"""
    template = PrepChecklistTemplate.query.get_or_404(template_id)
    items = PrepChecklistItem.query.filter_by(template_id=template_id).order_by(
        PrepChecklistItem.section, PrepChecklistItem.order_index
    ).all()
    
    # Group items by section
    grouped_items = {}
    for item in items:
        section = item.section.value
        if section not in grouped_items:
            grouped_items[section] = []
        grouped_items[section].append(item)
    
    # Get available screening types for linking
    screening_types = ScreeningType.query.filter_by(is_active=True).all()
    
    return render_template(
        "prep_checklist/template_items.html",
        template=template,
        grouped_items=grouped_items,
        screening_types=screening_types,
        sections=PrepChecklistSection,
        item_types=PrepChecklistItemType
    )


@app.route("/prep-checklist/templates/<int:template_id>/items/create", methods=["GET", "POST"])
@admin_required
def create_prep_checklist_item(template_id):
    """Create a new checklist item"""
    template = PrepChecklistTemplate.query.get_or_404(template_id)
    
    if request.method == "POST":
        # Get form data
        section = PrepChecklistSection(request.form["section"])
        item_type = PrepChecklistItemType(request.form["item_type"])
        
        # Create the item
        item = PrepChecklistItem(
            template_id=template_id,
            section=section,
            item_type=item_type,
            title=request.form["title"],
            description=request.form.get("description", ""),
            order_index=int(request.form.get("order_index", 0)),
            is_required=request.form.get("is_required") == "on",
            is_active=True
        )
        
        # Handle screening type reference
        if item_type == PrepChecklistItemType.SCREENING_TYPE:
            screening_type_id = request.form.get("screening_type_id")
            if screening_type_id:
                item.screening_type_id = int(screening_type_id)
        
        # Handle keywords
        primary_keywords = request.form.get("primary_keywords", "").strip()
        if primary_keywords:
            keywords = [k.strip() for k in primary_keywords.split(",") if k.strip()]
            item.primary_keywords = json.dumps(keywords)
        
        secondary_keywords = request.form.get("secondary_keywords", "").strip()
        if secondary_keywords:
            keywords = [k.strip() for k in secondary_keywords.split(",") if k.strip()]
            item.secondary_keywords = json.dumps(keywords)
        
        excluded_keywords = request.form.get("excluded_keywords", "").strip()
        if excluded_keywords:
            keywords = [k.strip() for k in excluded_keywords.split(",") if k.strip()]
            item.excluded_keywords = json.dumps(keywords)
        
        # Handle age/gender rules
        min_age = request.form.get("min_age")
        if min_age:
            item.min_age = int(min_age)
        
        max_age = request.form.get("max_age")
        if max_age:
            item.max_age = int(max_age)
        
        gender_specific = request.form.get("gender_specific")
        if gender_specific and gender_specific != "all":
            item.gender_specific = gender_specific
        
        # Handle condition triggers
        trigger_conditions = request.form.get("trigger_conditions", "").strip()
        if trigger_conditions:
            conditions = [c.strip() for c in trigger_conditions.split(",") if c.strip()]
            item.trigger_conditions = json.dumps(conditions)
        
        # Handle matching configuration
        item.match_confidence_threshold = int(request.form.get("match_confidence_threshold", 70))
        item.require_recent_data = request.form.get("require_recent_data") == "on"
        item.recent_data_days = int(request.form.get("recent_data_days", 365))
        
        # Handle display configuration
        item.show_in_summary = request.form.get("show_in_summary") == "on"
        item.priority_level = int(request.form.get("priority_level", 1))
        
        db.session.add(item)
        db.session.commit()
        
        flash("Checklist item created successfully.", "success")
        return redirect(url_for("prep_checklist_template_items", template_id=template_id))
    
    # GET request - show form
    screening_types = ScreeningType.query.filter_by(is_active=True).all()
    return render_template(
        "prep_checklist/create_item.html",
        template=template,
        screening_types=screening_types,
        sections=PrepChecklistSection,
        item_types=PrepChecklistItemType
    )


@app.route("/prep-checklist/items/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_prep_checklist_item(item_id):
    """Edit a checklist item"""
    item = PrepChecklistItem.query.get_or_404(item_id)
    
    if request.method == "POST":
        # Update basic fields
        item.title = request.form["title"]
        item.description = request.form.get("description", "")
        item.section = PrepChecklistSection(request.form["section"])
        item.item_type = PrepChecklistItemType(request.form["item_type"])
        item.order_index = int(request.form.get("order_index", 0))
        item.is_required = request.form.get("is_required") == "on"
        item.is_active = request.form.get("is_active") == "on"
        
        # Handle screening type reference
        if item.item_type == PrepChecklistItemType.SCREENING_TYPE:
            screening_type_id = request.form.get("screening_type_id")
            item.screening_type_id = int(screening_type_id) if screening_type_id else None
        else:
            item.screening_type_id = None
        
        # Update keywords
        primary_keywords = request.form.get("primary_keywords", "").strip()
        item.primary_keywords = json.dumps([k.strip() for k in primary_keywords.split(",") if k.strip()]) if primary_keywords else None
        
        secondary_keywords = request.form.get("secondary_keywords", "").strip()
        item.secondary_keywords = json.dumps([k.strip() for k in secondary_keywords.split(",") if k.strip()]) if secondary_keywords else None
        
        excluded_keywords = request.form.get("excluded_keywords", "").strip()
        item.excluded_keywords = json.dumps([k.strip() for k in excluded_keywords.split(",") if k.strip()]) if excluded_keywords else None
        
        # Update age/gender rules
        min_age = request.form.get("min_age")
        item.min_age = int(min_age) if min_age else None
        
        max_age = request.form.get("max_age")
        item.max_age = int(max_age) if max_age else None
        
        gender_specific = request.form.get("gender_specific")
        item.gender_specific = gender_specific if gender_specific and gender_specific != "all" else None
        
        # Update condition triggers
        trigger_conditions = request.form.get("trigger_conditions", "").strip()
        item.trigger_conditions = json.dumps([c.strip() for c in trigger_conditions.split(",") if c.strip()]) if trigger_conditions else None
        
        # Update matching configuration
        item.match_confidence_threshold = int(request.form.get("match_confidence_threshold", 70))
        item.require_recent_data = request.form.get("require_recent_data") == "on"
        item.recent_data_days = int(request.form.get("recent_data_days", 365))
        
        # Update display configuration
        item.show_in_summary = request.form.get("show_in_summary") == "on"
        item.priority_level = int(request.form.get("priority_level", 1))
        
        db.session.commit()
        flash("Checklist item updated successfully.", "success")
        return redirect(url_for("prep_checklist_template_items", template_id=item.template_id))
    
    # GET request - show form with current values
    screening_types = ScreeningType.query.filter_by(is_active=True).all()
    return render_template(
        "prep_checklist/edit_item.html",
        item=item,
        screening_types=screening_types,
        sections=PrepChecklistSection,
        item_types=PrepChecklistItemType
    )


@app.route("/prep-checklist/patients/<int:patient_id>/evaluate")
def evaluate_patient_checklist(patient_id):
    """Evaluate prep checklist for a specific patient"""
    patient = Patient.query.get_or_404(patient_id)
    evaluator = PrepChecklistEvaluator()
    
    # Get template ID from query params
    template_id = request.args.get("template_id", type=int)
    
    # Perform evaluation
    evaluation_result = evaluator.evaluate_patient_checklist(patient_id, template_id)
    
    return render_template(
        "prep_checklist/patient_evaluation.html",
        patient=patient,
        evaluation_result=evaluation_result,
        match_statuses=PrepChecklistMatchStatus
    )


@app.route("/prep-checklist/patients/<int:patient_id>/prep-sheet")
def patient_prep_sheet_with_checklist(patient_id):
    """Generate prep sheet with intelligent checklist integration"""
    patient = Patient.query.get_or_404(patient_id)
    evaluator = PrepChecklistEvaluator()
    
    # Evaluate checklist
    evaluation_result = evaluator.evaluate_patient_checklist(patient_id)
    
    # Get traditional prep sheet data
    from utils import generate_prep_sheet
    from datetime import datetime, timedelta
    
    # Get recent medical data (last 6 months for prep sheet)
    six_months_ago = datetime.now() - timedelta(days=180)
    
    # Get medical data for prep sheet
    recent_vitals = patient.vitals.filter(
        patient.vitals.property.mapper.class_.date >= six_months_ago
    ).order_by(patient.vitals.property.mapper.class_.date.desc()).limit(5).all()
    
    recent_labs = patient.lab_results.filter(
        patient.lab_results.property.mapper.class_.test_date >= six_months_ago
    ).order_by(patient.lab_results.property.mapper.class_.test_date.desc()).limit(10).all()
    
    recent_imaging = patient.imaging_studies.filter(
        patient.imaging_studies.property.mapper.class_.study_date >= six_months_ago
    ).order_by(patient.imaging_studies.property.mapper.class_.study_date.desc()).limit(5).all()
    
    recent_consults = patient.consult_reports.filter(
        patient.consult_reports.property.mapper.class_.report_date >= six_months_ago
    ).order_by(patient.consult_reports.property.mapper.class_.report_date.desc()).limit(5).all()
    
    recent_hospital = patient.hospital_summaries.filter(
        patient.hospital_summaries.property.mapper.class_.admission_date >= six_months_ago
    ).order_by(patient.hospital_summaries.property.mapper.class_.admission_date.desc()).limit(3).all()
    
    active_conditions = patient.conditions.filter_by(is_active=True).all()
    screenings = patient.screenings.all()
    
    # Generate traditional prep sheet
    prep_sheet_data = generate_prep_sheet(
        patient,
        recent_vitals,
        recent_labs,
        recent_imaging,
        recent_consults,
        recent_hospital,
        active_conditions,
        screenings,
        None,  # last_visit_date
        []     # past_appointments
    )
    
    return render_template(
        "prep_checklist/integrated_prep_sheet.html",
        patient=patient,
        evaluation_result=evaluation_result,
        prep_sheet_data=prep_sheet_data,
        match_statuses=PrepChecklistMatchStatus
    )


@app.route("/api/prep-checklist/sync-screening-types", methods=["POST"])
@admin_required
def api_sync_screening_types():
    """API endpoint to sync checklist with screening types"""
    try:
        manager = PrepChecklistManager()
        manager.sync_with_screening_types()
        
        return jsonify({
            "success": True,
            "message": "Screening types synchronized successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/prep-checklist/evaluate/<int:patient_id>", methods=["POST"])
def api_evaluate_patient_checklist(patient_id):
    """API endpoint to evaluate patient checklist"""
    try:
        evaluator = PrepChecklistEvaluator()
        template_id = request.json.get("template_id") if request.json else None
        
        evaluation_result = evaluator.evaluate_patient_checklist(patient_id, template_id)
        
        # Convert result to JSON-serializable format
        json_result = {
            "patient_id": evaluation_result["patient_id"],
            "template_id": evaluation_result["template"].id,
            "template_name": evaluation_result["template"].name,
            "summary": evaluation_result["summary"],
            "evaluation_date": evaluation_result["evaluation_date"].isoformat(),
            "results": []
        }
        
        for result in evaluation_result["results"]:
            json_result["results"].append({
                "item_id": result.checklist_item_id,
                "item_title": result.checklist_item.title,
                "section": result.checklist_item.section.value,
                "match_status": result.match_status.value,
                "confidence_score": result.confidence_score,
                "matched_data_type": result.matched_data_type,
                "matched_keywords": result.matched_keywords_list,
                "text_snippet": result.matched_text_snippet
            })
        
        return jsonify({
            "success": True,
            "data": json_result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/prep-checklist/configuration", methods=["GET", "POST"])
@admin_required
def prep_checklist_configuration():
    """Manage prep checklist global configuration"""
    config = PrepChecklistConfiguration.get_config()
    
    if request.method == "POST":
        # Update configuration
        config.auto_evaluate_on_data_add = request.form.get("auto_evaluate_on_data_add") == "on"
        config.require_manual_review = request.form.get("require_manual_review") == "on"
        config.confidence_threshold = int(request.form.get("confidence_threshold", 70))
        
        config.max_lab_age_days = int(request.form.get("max_lab_age_days", 365))
        config.max_imaging_age_days = int(request.form.get("max_imaging_age_days", 730))
        config.max_consult_age_days = int(request.form.get("max_consult_age_days", 365))
        config.max_hospital_age_days = int(request.form.get("max_hospital_age_days", 1095))
        
        config.show_confidence_scores = request.form.get("show_confidence_scores") == "on"
        config.group_by_section = request.form.get("group_by_section") == "on"
        config.highlight_missing_items = request.form.get("highlight_missing_items") == "on"
        
        config.sync_with_screening_types = request.form.get("sync_with_screening_types") == "on"
        config.auto_create_screening_items = request.form.get("auto_create_screening_items") == "on"
        
        # Handle default template
        default_template_id = request.form.get("default_template_id")
        if default_template_id:
            config.default_template_id = int(default_template_id)
        
        db.session.commit()
        flash("Configuration updated successfully.", "success")
        return redirect(url_for("prep_checklist_configuration"))
    
    # Get available templates for default selection
    templates = PrepChecklistTemplate.query.filter_by(is_active=True).all()
    
    return render_template(
        "prep_checklist/configuration.html",
        config=config,
        templates=templates
    )