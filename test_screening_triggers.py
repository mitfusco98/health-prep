"""
Test FHIR Condition-Triggered Screening System
Validates condition-based screening triggers using existing database structure
"""

import json
from datetime import datetime, date
from app import app, db
from models import Patient, ScreeningType, Condition


def test_screening_trigger_system():
    """Test the complete condition-triggered screening system"""
    
    print("TESTING CONDITION-TRIGGERED SCREENING SYSTEM")
    print("=" * 50)
    
    with app.app_context():
        # Step 1: Setup screening types with trigger conditions
        setup_trigger_conditions()
        
        # Step 2: Test with existing patient
        test_patient = Patient.query.first()
        if not test_patient:
            print("No patients found - creating test patient")
            return
        
        print(f"\nTesting with Patient: {test_patient.first_name} {test_patient.last_name}")
        print(f"Patient ID: {test_patient.id}, MRN: {test_patient.mrn}")
        
        # Step 3: Add test conditions
        add_test_conditions(test_patient.id)
        
        # Step 4: Test screening type matching
        test_screening_matching(test_patient.id)
        
        print("\n" + "=" * 50)
        print("SCREENING TRIGGER TEST COMPLETE")


def setup_trigger_conditions():
    """Setup screening types with FHIR trigger conditions"""
    
    print("\nSetting up screening types with trigger conditions...")
    
    # Define screening configurations with trigger conditions
    configs = [
        {
            "name": "Diabetes Management",
            "description": "HbA1c monitoring and diabetic complications screening",
            "frequency": "Every 3 months",
            "trigger_conditions": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "73211009",
                    "display": "Diabetes mellitus"
                },
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "E11.9",
                    "display": "Type 2 diabetes mellitus"
                }
            ]
        },
        {
            "name": "Hypertension Monitoring", 
            "description": "Blood pressure monitoring and cardiovascular assessment",
            "frequency": "Monthly",
            "trigger_conditions": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "38341003",
                    "display": "Hypertensive disorder"
                },
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "I10",
                    "display": "Essential hypertension"
                }
            ]
        }
    ]
    
    for config in configs:
        # Check if screening type exists
        screening_type = ScreeningType.query.filter_by(name=config["name"]).first()
        
        if not screening_type:
            # Create new screening type
            screening_type = ScreeningType(
                name=config["name"],
                description=config["description"],
                default_frequency=config["frequency"],
                is_active=True
            )
            db.session.add(screening_type)
            db.session.flush()  # Get the ID
        
        # Set trigger conditions
        screening_type.set_trigger_conditions(config["trigger_conditions"])
        print(f"Configured: {config['name']}")
    
    db.session.commit()
    print("Screening types configured successfully")


def add_test_conditions(patient_id):
    """Add test conditions with FHIR-compatible codes"""
    
    print(f"\nAdding test conditions for patient {patient_id}...")
    
    test_conditions = [
        {
            "name": "Type 2 Diabetes Mellitus",
            "code": "E11.9",
            "notes": json.dumps({
                "fhir_codes": {
                    "icd10": "E11.9",
                    "snomed": "73211009"
                }
            })
        },
        {
            "name": "Essential Hypertension",
            "code": "I10", 
            "notes": json.dumps({
                "fhir_codes": {
                    "icd10": "I10",
                    "snomed": "38341003"
                }
            })
        }
    ]
    
    for condition_data in test_conditions:
        # Check if condition already exists
        existing = Condition.query.filter_by(
            patient_id=patient_id,
            name=condition_data["name"]
        ).first()
        
        if not existing:
            new_condition = Condition(
                patient_id=patient_id,
                name=condition_data["name"],
                code=condition_data["code"],
                diagnosed_date=date.today(),
                is_active=True,
                notes=condition_data["notes"]
            )
            db.session.add(new_condition)
            print(f"Added: {condition_data['name']} ({condition_data['code']})")
        else:
            print(f"Exists: {condition_data['name']}")
    
    db.session.commit()


def test_screening_matching(patient_id):
    """Test screening type trigger condition matching"""
    
    print(f"\nTesting screening trigger matching for patient {patient_id}...")
    
    # Get patient conditions
    conditions = Condition.query.filter_by(patient_id=patient_id).all()
    print(f"Patient has {len(conditions)} conditions:")
    
    for condition in conditions:
        print(f"  - {condition.name} ({condition.code})")
    
    # Get screening types with trigger conditions
    screening_types = ScreeningType.query.filter_by(is_active=True).all()
    
    matches_found = 0
    
    print(f"\nChecking {len(screening_types)} screening types for triggers...")
    
    for screening_type in screening_types:
        trigger_conditions = screening_type.get_trigger_conditions()
        
        if not trigger_conditions:
            continue
            
        print(f"\nScreening: {screening_type.name}")
        print(f"  Trigger conditions: {len(trigger_conditions)}")
        
        # Check each patient condition against trigger conditions
        for condition in conditions:
            condition_matched = False
            
            for trigger in trigger_conditions:
                # Check direct code match
                if condition.code == trigger.get('code'):
                    matches_found += 1
                    condition_matched = True
                    print(f"  ✓ MATCHED: {condition.name} ({condition.code}) triggers {screening_type.name}")
                    print(f"    Trigger: {trigger.get('display')} ({trigger.get('code')})")
                    break
            
            if not condition_matched:
                # Check if condition has FHIR codes in notes
                if condition.notes:
                    try:
                        condition_fhir = json.loads(condition.notes)
                        fhir_codes = condition_fhir.get('fhir_codes', {})
                        
                        for trigger in trigger_conditions:
                            if (fhir_codes.get('icd10') == trigger.get('code') or 
                                fhir_codes.get('snomed') == trigger.get('code')):
                                matches_found += 1
                                print(f"  ✓ FHIR MATCHED: {condition.name} triggers {screening_type.name}")
                                print(f"    Via FHIR code: {trigger.get('code')}")
                                break
                    except json.JSONDecodeError:
                        pass
    
    print(f"\nSummary:")
    print(f"  Total screening-condition matches: {matches_found}")
    print(f"  Unique triggered screenings found")
    
    # Test the screening type methods directly
    print(f"\nTesting ScreeningType methods:")
    
    diabetes_screening = ScreeningType.query.filter_by(name="Diabetes Management").first()
    if diabetes_screening:
        # Test matches_condition_code method
        matches_diabetes_icd = diabetes_screening.matches_condition_code("E11.9")
        matches_diabetes_snomed = diabetes_screening.matches_condition_code("73211009")
        
        print(f"  Diabetes screening matches E11.9: {matches_diabetes_icd}")
        print(f"  Diabetes screening matches 73211009: {matches_diabetes_snomed}")
        
        # Show trigger conditions
        triggers = diabetes_screening.get_trigger_conditions()
        print(f"  Diabetes trigger conditions: {len(triggers)}")
        for trigger in triggers:
            print(f"    - {trigger.get('display')} ({trigger.get('code')})")
    
    return matches_found


if __name__ == "__main__":
    test_screening_trigger_system()