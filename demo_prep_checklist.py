#!/usr/bin/env python3
"""
Demo script for PrepChecklist system
Creates sample templates and demonstrates intelligent keyword matching
"""

import json
from datetime import datetime, timedelta
from app import app, db
from models import (
    Patient, ScreeningType, LabResult, ImagingStudy, ConsultReport,
    PrepChecklistTemplate, PrepChecklistItem, PrepChecklistResult,
    PrepChecklistConfiguration, PrepChecklistSection, PrepChecklistItemType,
    PrepChecklistMatchStatus
)


def create_sample_prep_checklist_data():
    """Create sample prep checklist templates and data"""
    print("Creating sample PrepChecklist data...")
    
    with app.app_context():
        # Create default configuration
        config = PrepChecklistConfiguration.get_config()
        
        # Create a sample template
        template = PrepChecklistTemplate(
            name="Comprehensive Prep Checklist",
            description="Standard preparation checklist with intelligent keyword matching",
            is_default=True,
            is_active=True
        )
        db.session.add(template)
        db.session.flush()  # Get the ID
        
        # Update config to use this template
        config.default_template_id = template.id
        
        # Create checklist items based on existing screening types
        screening_types = ScreeningType.query.filter_by(is_active=True).limit(5).all()
        
        order_index = 1
        for screening_type in screening_types:
            # Create screening type item
            item = PrepChecklistItem(
                template_id=template.id,
                section=PrepChecklistSection.SCREENING_CHECKLIST,
                item_type=PrepChecklistItemType.SCREENING_TYPE,
                title=screening_type.name,
                description=f"Check for {screening_type.name} in medical records",
                order_index=order_index,
                screening_type_id=screening_type.id,
                min_age=screening_type.min_age,
                max_age=screening_type.max_age,
                gender_specific=screening_type.gender_specific,
                is_required=True,
                show_in_summary=True,
                priority_level=1
            )
            db.session.add(item)
            order_index += 1
        
        # Add some keyword-based items
        keyword_items = [
            {
                'title': 'Blood Pressure Monitoring',
                'section': PrepChecklistSection.VITAL_SIGNS,
                'description': 'Recent blood pressure measurements',
                'primary_keywords': ['blood pressure', 'BP', 'hypertension', 'systolic', 'diastolic'],
                'min_age': 18
            },
            {
                'title': 'Vaccination History',
                'section': PrepChecklistSection.IMMUNIZATIONS,
                'description': 'Current vaccination status',
                'primary_keywords': ['vaccination', 'vaccine', 'immunization', 'flu shot', 'covid vaccine'],
                'secondary_keywords': ['booster', 'dose', 'series']
            },
            {
                'title': 'Cardiac Assessment',
                'section': PrepChecklistSection.LABORATORY_RESULTS,
                'description': 'Cardiac function tests and monitoring',
                'primary_keywords': ['EKG', 'ECG', 'echocardiogram', 'cardiac', 'heart'],
                'secondary_keywords': ['troponin', 'BNP', 'stress test'],
                'excluded_keywords': ['heart rate', 'pulse']
            },
            {
                'title': 'Diabetes Management',
                'section': PrepChecklistSection.LABORATORY_RESULTS,
                'description': 'Diabetes monitoring and control',
                'primary_keywords': ['glucose', 'A1C', 'HbA1c', 'diabetes', 'insulin'],
                'secondary_keywords': ['blood sugar', 'diabetic', 'metformin'],
                'trigger_conditions': ['diabetes', 'type 1 diabetes', 'type 2 diabetes']
            }
        ]
        
        for item_data in keyword_items:
            item = PrepChecklistItem(
                template_id=template.id,
                section=item_data['section'],
                item_type=PrepChecklistItemType.KEYWORD_MATCH,
                title=item_data['title'],
                description=item_data['description'],
                order_index=order_index,
                primary_keywords=json.dumps(item_data['primary_keywords']),
                secondary_keywords=json.dumps(item_data.get('secondary_keywords', [])),
                excluded_keywords=json.dumps(item_data.get('excluded_keywords', [])),
                trigger_conditions=json.dumps(item_data.get('trigger_conditions', [])),
                min_age=item_data.get('min_age'),
                max_age=item_data.get('max_age'),
                gender_specific=item_data.get('gender_specific'),
                is_required=False,
                show_in_summary=True,
                priority_level=2
            )
            db.session.add(item)
            order_index += 1
        
        # Add age/gender rule items
        rule_items = [
            {
                'title': 'Mammography Screening',
                'section': PrepChecklistSection.IMAGING_STUDIES,
                'description': 'Breast cancer screening for women 40+',
                'min_age': 40,
                'gender_specific': 'Female',
                'primary_keywords': ['mammogram', 'mammography', 'breast cancer screening']
            },
            {
                'title': 'Prostate Screening',
                'section': PrepChecklistSection.LABORATORY_RESULTS,
                'description': 'Prostate cancer screening for men 50+',
                'min_age': 50,
                'gender_specific': 'Male',
                'primary_keywords': ['PSA', 'prostate', 'prostate exam', 'DRE']
            }
        ]
        
        for item_data in rule_items:
            item = PrepChecklistItem(
                template_id=template.id,
                section=item_data['section'],
                item_type=PrepChecklistItemType.AGE_GENDER_RULE,
                title=item_data['title'],
                description=item_data['description'],
                order_index=order_index,
                primary_keywords=json.dumps(item_data.get('primary_keywords', [])),
                min_age=item_data.get('min_age'),
                max_age=item_data.get('max_age'),
                gender_specific=item_data.get('gender_specific'),
                is_required=True,
                show_in_summary=True,
                priority_level=1
            )
            db.session.add(item)
            order_index += 1
        
        db.session.commit()
        
        print(f"✓ Created PrepChecklist template '{template.name}' with {order_index-1} items")
        print(f"✓ Template includes:")
        print(f"  - {len(screening_types)} screening type items")
        print(f"  - {len(keyword_items)} keyword matching items")
        print(f"  - {len(rule_items)} age/gender rule items")
        
        return template


def create_sample_medical_data():
    """Create sample medical data for testing checklist matching"""
    print("\nCreating sample medical data for checklist testing...")
    
    with app.app_context():
        # Get first patient
        patient = Patient.query.first()
        if not patient:
            print("No patients found. Create some patients first.")
            return
        
        # Create sample lab results
        lab_results = [
            {
                'test_name': 'Blood Pressure Check',
                'result': '140/90 mmHg',
                'units': 'mmHg',
                'reference_range': '<120/80',
                'test_date': datetime.now() - timedelta(days=30)
            },
            {
                'test_name': 'Hemoglobin A1C',
                'result': '7.2',
                'units': '%',
                'reference_range': '<7.0',
                'test_date': datetime.now() - timedelta(days=45)
            },
            {
                'test_name': 'PSA Total',
                'result': '2.8',
                'units': 'ng/mL',
                'reference_range': '<4.0',
                'test_date': datetime.now() - timedelta(days=60)
            }
        ]
        
        for lab_data in lab_results:
            lab = LabResult(
                patient_id=patient.id,
                test_name=lab_data['test_name'],
                result=lab_data['result'],
                units=lab_data['units'],
                reference_range=lab_data['reference_range'],
                test_date=lab_data['test_date']
            )
            db.session.add(lab)
        
        # Create sample imaging studies
        imaging_studies = [
            {
                'study_type': 'Mammography',
                'description': 'Bilateral mammography screening',
                'findings': 'No suspicious lesions identified',
                'impression': 'BI-RADS Category 1 - Negative',
                'study_date': datetime.now() - timedelta(days=90)
            },
            {
                'study_type': 'Echocardiogram',
                'description': 'Transthoracic echocardiogram',
                'findings': 'Normal left ventricular function, EF 60%',
                'impression': 'Normal cardiac function',
                'study_date': datetime.now() - timedelta(days=120)
            }
        ]
        
        for imaging_data in imaging_studies:
            imaging = ImagingStudy(
                patient_id=patient.id,
                study_type=imaging_data['study_type'],
                description=imaging_data['description'],
                findings=imaging_data['findings'],
                impression=imaging_data['impression'],
                study_date=imaging_data['study_date']
            )
            db.session.add(imaging)
        
        # Create sample consult reports
        consult_reports = [
            {
                'provider': 'Dr. Smith',
                'specialty': 'Cardiology',
                'reason': 'Hypertension management',
                'recommendations': 'Continue current medications, follow-up in 3 months',
                'report_date': datetime.now() - timedelta(days=75)
            },
            {
                'provider': 'Dr. Johnson',
                'specialty': 'Endocrinology',
                'reason': 'Diabetes management',
                'recommendations': 'Adjust insulin dosing, increase glucose monitoring',
                'report_date': datetime.now() - timedelta(days=45)
            }
        ]
        
        for consult_data in consult_reports:
            consult = ConsultReport(
                patient_id=patient.id,
                provider=consult_data['provider'],
                specialty=consult_data['specialty'],
                reason=consult_data['reason'],
                recommendations=consult_data['recommendations'],
                report_date=consult_data['report_date']
            )
            db.session.add(consult)
        
        db.session.commit()
        
        print(f"✓ Created sample medical data for patient {patient.id}:")
        print(f"  - {len(lab_results)} lab results")
        print(f"  - {len(imaging_studies)} imaging studies")
        print(f"  - {len(consult_reports)} consult reports")


def demo_checklist_evaluation():
    """Demonstrate checklist evaluation functionality"""
    print("\nDemonstrating PrepChecklist evaluation...")
    
    with app.app_context():
        # Get first patient
        patient = Patient.query.first()
        if not patient:
            print("No patients found.")
            return
        
        # Get default template
        template = PrepChecklistTemplate.query.filter_by(is_default=True).first()
        if not template:
            print("No default template found.")
            return
        
        print(f"Evaluating checklist for Patient {patient.id} using template '{template.name}'")
        
        # Get all checklist items
        items = PrepChecklistItem.query.filter_by(template_id=template.id, is_active=True).all()
        
        print(f"\nFound {len(items)} checklist items:")
        
        for item in items:
            print(f"\n--- {item.title} ---")
            print(f"Type: {item.item_type.value}")
            print(f"Section: {item.section.value}")
            
            if item.item_type == PrepChecklistItemType.KEYWORD_MATCH:
                keywords = item.get_primary_keywords()
                if keywords:
                    print(f"Primary Keywords: {', '.join(keywords)}")
                
                # Simple keyword matching demo
                found_matches = []
                
                # Check lab results
                labs = LabResult.query.filter_by(patient_id=patient.id).all()
                for lab in labs:
                    search_text = f"{lab.test_name} {lab.result or ''}"
                    for keyword in keywords:
                        if keyword.lower() in search_text.lower():
                            found_matches.append(f"Lab: {lab.test_name}")
                            break
                
                # Check imaging studies
                imaging = ImagingStudy.query.filter_by(patient_id=patient.id).all()
                for study in imaging:
                    search_text = f"{study.study_type} {study.description or ''} {study.findings or ''}"
                    for keyword in keywords:
                        if keyword.lower() in search_text.lower():
                            found_matches.append(f"Imaging: {study.study_type}")
                            break
                
                # Check consults
                consults = ConsultReport.query.filter_by(patient_id=patient.id).all()
                for consult in consults:
                    search_text = f"{consult.specialty} {consult.reason or ''} {consult.recommendations or ''}"
                    for keyword in keywords:
                        if keyword.lower() in search_text.lower():
                            found_matches.append(f"Consult: {consult.specialty}")
                            break
                
                if found_matches:
                    print(f"✓ FOUND: {', '.join(found_matches)}")
                else:
                    print("✗ NOT FOUND in medical data")
            
            elif item.item_type == PrepChecklistItemType.AGE_GENDER_RULE:
                applies = item.applies_to_patient(patient)
                if applies:
                    print(f"✓ APPLIES: Patient meets age/gender criteria")
                else:
                    print(f"✗ NOT APPLICABLE: Patient doesn't meet criteria")
            
            elif item.item_type == PrepChecklistItemType.SCREENING_TYPE:
                if item.screening_type:
                    print(f"Linked to screening type: {item.screening_type.name}")
                    print("✓ CONFIGURED: Ready for evaluation")
                else:
                    print("✗ ERROR: No screening type linked")


if __name__ == "__main__":
    print("=== PrepChecklist Demo ===")
    
    # Create sample data
    template = create_sample_prep_checklist_data()
    create_sample_medical_data()
    
    # Demonstrate evaluation
    demo_checklist_evaluation()
    
    print("\n=== Demo Complete ===")
    print("✓ PrepChecklist system is ready for use")
    print("✓ Access via /prep-checklist routes")
    print("✓ Templates and items created successfully")