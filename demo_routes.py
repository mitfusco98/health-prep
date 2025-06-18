"""
Demo routes for PrepChecklist functionality
Simple interface to test the dynamic checklist system
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta
import json
from app import app, db
from models import (
    Patient, ScreeningType, LabResult, ImagingStudy, ConsultReport,
    PrepChecklistTemplate, PrepChecklistItem, PrepChecklistConfiguration,
    PrepChecklistSection, PrepChecklistItemType
)


@app.route("/demo/prep-checklist")
def demo_prep_checklist():
    """Demo page for PrepChecklist functionality"""
    # Get or create configuration
    config = PrepChecklistConfiguration.get_config()
    
    # Get templates
    templates = PrepChecklistTemplate.query.filter_by(is_active=True).all()
    
    # Get patients for testing
    patients = Patient.query.limit(10).all()
    
    return render_template("demo_prep_checklist.html", 
                         config=config, 
                         templates=templates, 
                         patients=patients)


@app.route("/demo/prep-checklist/create-demo", methods=["POST"])
def create_demo_prep_checklist():
    """Create demo PrepChecklist data"""
    try:
        # Create configuration
        config = PrepChecklistConfiguration.get_config()
        
        # Create demo template
        template = PrepChecklistTemplate(
            name="Demo Prep Checklist",
            description="Demonstration of intelligent keyword matching",
            is_default=True,
            is_active=True
        )
        db.session.add(template)
        db.session.flush()
        
        # Update config
        config.default_template_id = template.id
        
        # Create sample checklist items
        items_data = [
            {
                'title': 'Blood Pressure Monitoring',
                'section': PrepChecklistSection.VITAL_SIGNS,
                'item_type': PrepChecklistItemType.KEYWORD_MATCH,
                'description': 'Recent blood pressure measurements',
                'keywords': ['blood pressure', 'BP', 'hypertension', 'systolic', 'diastolic']
            },
            {
                'title': 'Diabetes Screening',
                'section': PrepChecklistSection.LABORATORY_RESULTS,
                'item_type': PrepChecklistItemType.KEYWORD_MATCH,
                'description': 'Diabetes monitoring and screening',
                'keywords': ['glucose', 'A1C', 'HbA1c', 'diabetes', 'blood sugar']
            },
            {
                'title': 'Cardiac Assessment',
                'section': PrepChecklistSection.IMAGING_STUDIES,
                'item_type': PrepChecklistItemType.KEYWORD_MATCH,
                'description': 'Heart and cardiovascular evaluation',
                'keywords': ['EKG', 'ECG', 'echocardiogram', 'cardiac', 'heart']
            }
        ]
        
        for i, item_data in enumerate(items_data):
            item = PrepChecklistItem(
                template_id=template.id,
                section=item_data['section'],
                item_type=item_data['item_type'],
                title=item_data['title'],
                description=item_data['description'],
                order_index=i + 1,
                primary_keywords=json.dumps(item_data['keywords']),
                is_required=False,
                is_active=True,
                show_in_summary=True,
                priority_level=2
            )
            db.session.add(item)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Created demo template with {len(items_data)} items",
            "template_id": template.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/demo/prep-checklist/evaluate/<int:patient_id>")
def demo_evaluate_checklist(patient_id):
    """Evaluate checklist for a patient (simple demo version)"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Get default template
        template = PrepChecklistTemplate.query.filter_by(is_default=True).first()
        if not template:
            return jsonify({
                "success": False,
                "error": "No default template found. Create demo data first."
            }), 404
        
        # Get checklist items
        items = PrepChecklistItem.query.filter_by(
            template_id=template.id, 
            is_active=True
        ).all()
        
        results = []
        
        for item in items:
            result = {
                "item_id": item.id,
                "title": item.title,
                "section": item.section.value,
                "type": item.item_type.value,
                "description": item.description,
                "status": "not_checked",
                "matches": [],
                "confidence": 0
            }
            
            if item.item_type == PrepChecklistItemType.KEYWORD_MATCH:
                keywords = item.get_primary_keywords()
                matches = []
                
                # Check lab results
                labs = LabResult.query.filter_by(patient_id=patient_id).all()
                for lab in labs:
                    search_text = f"{lab.test_name} {lab.result or ''}"
                    for keyword in keywords:
                        if keyword.lower() in search_text.lower():
                            matches.append({
                                "type": "lab",
                                "text": f"{lab.test_name}: {lab.result}",
                                "date": lab.test_date.strftime('%m/%d/%Y'),
                                "keyword": keyword
                            })
                            break
                
                # Check imaging studies
                imaging = ImagingStudy.query.filter_by(patient_id=patient_id).all()
                for study in imaging:
                    search_text = f"{study.study_type} {study.findings or ''}"
                    for keyword in keywords:
                        if keyword.lower() in search_text.lower():
                            matches.append({
                                "type": "imaging",
                                "text": f"{study.study_type}: {study.findings}",
                                "date": study.study_date.strftime('%m/%d/%Y'),
                                "keyword": keyword
                            })
                            break
                
                # Check consult reports
                consults = ConsultReport.query.filter_by(patient_id=patient_id).all()
                for consult in consults:
                    search_text = f"{consult.specialty} {consult.reason or ''}"
                    for keyword in keywords:
                        if keyword.lower() in search_text.lower():
                            matches.append({
                                "type": "consult",
                                "text": f"{consult.specialty}: {consult.reason}",
                                "date": consult.report_date.strftime('%m/%d/%Y'),
                                "keyword": keyword
                            })
                            break
                
                if matches:
                    result["status"] = "found"
                    result["matches"] = matches
                    result["confidence"] = min(100, len(matches) * 25)  # Simple confidence calculation
                else:
                    result["status"] = "not_found"
            
            results.append(result)
        
        # Calculate summary
        total_items = len(results)
        found_items = len([r for r in results if r["status"] == "found"])
        completion_percentage = (found_items / total_items * 100) if total_items > 0 else 0
        
        return jsonify({
            "success": True,
            "patient": {
                "id": patient.id,
                "name": f"{patient.first_name} {patient.last_name}",
                "age": patient.age,
                "sex": patient.sex
            },
            "template": {
                "id": template.id,
                "name": template.name
            },
            "summary": {
                "total_items": total_items,
                "found_items": found_items,
                "completion_percentage": completion_percentage
            },
            "results": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/demo/prep-checklist/create-sample-data/<int:patient_id>", methods=["POST"])
def create_sample_medical_data(patient_id):
    """Create sample medical data for testing"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Create test lab results
        lab1 = LabResult(
            patient_id=patient.id,
            test_name="Blood Pressure Check",
            result="142/88 mmHg",
            units="mmHg",
            reference_range="<120/80",
            test_date=datetime.now() - timedelta(days=15)
        )
        db.session.add(lab1)
        
        lab2 = LabResult(
            patient_id=patient.id,
            test_name="Hemoglobin A1C",
            result="6.8",
            units="%",
            reference_range="<7.0",
            test_date=datetime.now() - timedelta(days=30)
        )
        db.session.add(lab2)
        
        # Create test imaging
        imaging = ImagingStudy(
            patient_id=patient.id,
            study_type="Echocardiogram",
            description="Transthoracic echocardiogram",
            findings="Normal cardiac function, EF 58%",
            impression="Normal study",
            study_date=datetime.now() - timedelta(days=45)
        )
        db.session.add(imaging)
        
        # Create test consult
        consult = ConsultReport(
            patient_id=patient.id,
            provider="Dr. Smith",
            specialty="Cardiology",
            reason="Hypertension evaluation",
            recommendations="Continue current antihypertensive therapy",
            report_date=datetime.now() - timedelta(days=20)
        )
        db.session.add(consult)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Sample medical data created successfully",
            "data_created": {
                "lab_results": 2,
                "imaging_studies": 1,
                "consult_reports": 1
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500