#!/usr/bin/env python3
"""
Create a simple PrepChecklist demonstration
Creates templates and shows keyword matching functionality
"""

import json
from datetime import datetime, timedelta
from app import app, db
from models import (
    Patient, ScreeningType, LabResult, ImagingStudy, ConsultReport,
    PrepChecklistTemplate, PrepChecklistItem, PrepChecklistConfiguration,
    PrepChecklistSection, PrepChecklistItemType
)


def create_prep_checklist_demo():
    """Create demo prep checklist system"""
    
    with app.app_context():
        print("Creating PrepChecklist demonstration...")
        
        # Create configuration
        config = PrepChecklistConfiguration.get_config()
        print("✓ Configuration created")
        
        # Create demo template
        template = PrepChecklistTemplate()
        template.name = "Demo Prep Checklist"
        template.description = "Demonstration of intelligent keyword matching"
        template.is_default = True
        template.is_active = True
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
            item = PrepChecklistItem()
            item.template_id = template.id
            item.section = item_data['section']
            item.item_type = item_data['item_type']
            item.title = item_data['title']
            item.description = item_data['description']
            item.order_index = i + 1
            item.primary_keywords = json.dumps(item_data['keywords'])
            item.is_required = False
            item.is_active = True
            item.show_in_summary = True
            item.priority_level = 2
            db.session.add(item)
        
        db.session.commit()
        
        print(f"✓ Created template '{template.name}' with {len(items_data)} items")
        return template.id


def create_sample_data():
    """Create sample medical data for testing"""
    
    with app.app_context():
        # Get first patient
        patient = Patient.query.first()
        if not patient:
            print("No patients found - creating demo patient")
            patient = Patient()
            patient.first_name = "John"
            patient.last_name = "Demo"
            patient.date_of_birth = datetime(1975, 5, 15).date()
            patient.sex = "Male"
            patient.mrn = "DEMO001"
            patient.phone = "555-0123"
            patient.email = "john.demo@example.com"
            db.session.add(patient)
            db.session.flush()
        
        # Create test lab results
        lab1 = LabResult()
        lab1.patient_id = patient.id
        lab1.test_name = "Blood Pressure Check"
        lab1.result = "142/88 mmHg"
        lab1.units = "mmHg"
        lab1.reference_range = "<120/80"
        lab1.test_date = datetime.now() - timedelta(days=15)
        db.session.add(lab1)
        
        lab2 = LabResult()
        lab2.patient_id = patient.id
        lab2.test_name = "Hemoglobin A1C"
        lab2.result = "6.8"
        lab2.units = "%"
        lab2.reference_range = "<7.0"
        lab2.test_date = datetime.now() - timedelta(days=30)
        db.session.add(lab2)
        
        # Create test imaging
        imaging = ImagingStudy()
        imaging.patient_id = patient.id
        imaging.study_type = "Echocardiogram"
        imaging.description = "Transthoracic echocardiogram"
        imaging.findings = "Normal cardiac function, EF 58%"
        imaging.impression = "Normal study"
        imaging.study_date = datetime.now() - timedelta(days=45)
        db.session.add(imaging)
        
        # Create test consult
        consult = ConsultReport()
        consult.patient_id = patient.id
        consult.provider = "Dr. Smith"
        consult.specialty = "Cardiology"
        consult.reason = "Hypertension evaluation"
        consult.recommendations = "Continue current antihypertensive therapy"
        consult.report_date = datetime.now() - timedelta(days=20)
        db.session.add(consult)
        
        db.session.commit()
        print(f"✓ Created sample medical data for patient {patient.id}")
        return patient.id


def test_keyword_matching(patient_id, template_id):
    """Test keyword matching functionality"""
    
    with app.app_context():
        print(f"\nTesting keyword matching for patient {patient_id}...")
        
        # Get template and items
        template = PrepChecklistTemplate.query.get(template_id)
        items = PrepChecklistItem.query.filter_by(template_id=template_id, is_active=True).all()
        
        patient = Patient.query.get(patient_id)
        
        for item in items:
            print(f"\n--- {item.title} ---")
            keywords = item.get_primary_keywords()
            print(f"Keywords: {', '.join(keywords)}")
            
            matches = []
            
            # Check labs
            labs = LabResult.query.filter_by(patient_id=patient_id).all()
            for lab in labs:
                text = f"{lab.test_name} {lab.result or ''}"
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        matches.append(f"Lab: {lab.test_name} ({lab.test_date.strftime('%m/%d/%Y')})")
                        break
            
            # Check imaging
            imaging = ImagingStudy.query.filter_by(patient_id=patient_id).all()
            for study in imaging:
                text = f"{study.study_type} {study.findings or ''}"
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        matches.append(f"Imaging: {study.study_type} ({study.study_date.strftime('%m/%d/%Y')})")
                        break
            
            # Check consults
            consults = ConsultReport.query.filter_by(patient_id=patient_id).all()
            for consult in consults:
                text = f"{consult.specialty} {consult.reason or ''}"
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        matches.append(f"Consult: {consult.specialty} ({consult.report_date.strftime('%m/%d/%Y')})")
                        break
            
            if matches:
                print("✓ FOUND:")
                for match in matches:
                    print(f"  • {match}")
            else:
                print("✗ No matches found")


if __name__ == "__main__":
    print("=== PrepChecklist Demo Creation ===")
    
    template_id = create_prep_checklist_demo()
    patient_id = create_sample_data()
    test_keyword_matching(patient_id, template_id)
    
    print("\n=== Demo Complete ===")
    print("PrepChecklist system created and tested successfully!")
    print("The system demonstrates:")
    print("• Dynamic template creation")
    print("• Keyword-based matching across medical data")
    print("• Integration with labs, imaging, and consults")
    print("• Intelligent data discovery for prep sheets")