"""
Comprehensive Test: FHIR Condition-Triggered Screening System
Tests the complete workflow from patient conditions to screening recommendations
"""

import json
from datetime import datetime, date
from app import app, db
from models import Patient, ScreeningType, MedicalCondition
from fhir_condition_screening_matcher import ConditionScreeningMatcher
from fhir_object_mappers import FHIRObjectMapper


def test_condition_triggered_screening_system():
    """Test the complete condition-triggered screening system"""
    
    print("CONDITION-TRIGGERED SCREENING SYSTEM TEST")
    print("=" * 60)
    
    with app.app_context():
        # Step 1: Set up screening types with trigger conditions
        setup_screening_types_with_triggers()
        
        # Step 2: Test with existing patient
        test_patient = Patient.query.first()
        if not test_patient:
            print("❌ No patients found in database")
            return
            
        print(f"\n📋 Testing with patient: {test_patient.first_name} {test_patient.last_name}")
        print(f"   Patient ID: {test_patient.id}")
        print(f"   MRN: {test_patient.mrn}")
        
        # Step 3: Add test medical conditions
        add_test_conditions(test_patient.id)
        
        # Step 4: Test condition-screening matching
        test_condition_matching(test_patient.id)
        
        # Step 5: Test FHIR conversion and Epic compatibility
        test_fhir_integration(test_patient.id)
        
        print("\n" + "=" * 60)
        print("CONDITION-TRIGGERED SCREENING TEST COMPLETE")


def setup_screening_types_with_triggers():
    """Set up screening types with FHIR trigger conditions"""
    
    print("\n🔧 Setting up screening types with trigger conditions...")
    
    screening_configs = [
        {
            "name": "Diabetes Management Screening",
            "description": "Comprehensive diabetes monitoring including HbA1c, eye exam, and foot exam",
            "frequency": "Every 6 months",
            "trigger_conditions": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "73211009",
                    "display": "Diabetes mellitus"
                },
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "E11.9",
                    "display": "Type 2 diabetes mellitus without complications"
                }
            ]
        },
        {
            "name": "Hypertension Monitoring",
            "description": "Blood pressure monitoring and cardiovascular risk assessment",
            "frequency": "Every 3 months",
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
        },
        {
            "name": "Cancer Risk Screening",
            "description": "Enhanced cancer screening for high-risk patients",
            "frequency": "Annual",
            "trigger_conditions": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "395557000",
                    "display": "Family history of malignant neoplasm"
                },
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "Z80.9",
                    "display": "Family history of malignant neoplasm, unspecified"
                }
            ]
        }
    ]
    
    for config in screening_configs:
        # Check if screening type already exists
        existing = ScreeningType.query.filter_by(name=config["name"]).first()
        
        if existing:
            # Update existing with trigger conditions
            existing.set_trigger_conditions(config["trigger_conditions"])
            existing.description = config["description"]
            existing.default_frequency = config["frequency"]
            print(f"   ✓ Updated: {config['name']}")
        else:
            # Create new screening type
            new_screening = ScreeningType(
                name=config["name"],
                description=config["description"],
                default_frequency=config["frequency"],
                is_active=True
            )
            new_screening.set_trigger_conditions(config["trigger_conditions"])
            db.session.add(new_screening)
            print(f"   ✓ Created: {config['name']}")
    
    db.session.commit()
    print(f"   📊 Setup complete: {len(screening_configs)} screening types configured")


def add_test_conditions(patient_id):
    """Add test medical conditions with FHIR codes"""
    
    print(f"\n🏥 Adding test medical conditions for patient {patient_id}...")
    
    test_conditions = [
        {
            "condition_name": "Type 2 Diabetes Mellitus",
            "icd10_code": "E11.9",
            "snomed_code": "73211009",
            "status": "Active"
        },
        {
            "condition_name": "Essential Hypertension", 
            "icd10_code": "I10",
            "snomed_code": "38341003",
            "status": "Active"
        },
        {
            "condition_name": "Family History of Breast Cancer",
            "icd10_code": "Z80.3",
            "snomed_code": "395557000", 
            "status": "Active"
        }
    ]
    
    added_conditions = []
    
    for condition_data in test_conditions:
        # Check if condition already exists
        existing = MedicalCondition.query.filter_by(
            patient_id=patient_id,
            condition_name=condition_data["condition_name"]
        ).first()
        
        if not existing:
            # Create condition with FHIR-compatible metadata
            fhir_metadata = {
                "fhir_condition_code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": condition_data["icd10_code"],
                            "display": condition_data["condition_name"]
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": condition_data["snomed_code"],
                            "display": condition_data["condition_name"]
                        }
                    ]
                }
            }
            
            new_condition = MedicalCondition(
                patient_id=patient_id,
                condition_name=condition_data["condition_name"],
                diagnosis_date=date.today(),
                status=condition_data["status"],
                notes=json.dumps(fhir_metadata)
            )
            
            db.session.add(new_condition)
            added_conditions.append(condition_data["condition_name"])
            print(f"   ✓ Added: {condition_data['condition_name']} ({condition_data['icd10_code']})")
    
    db.session.commit()
    
    if added_conditions:
        print(f"   📋 Added {len(added_conditions)} new conditions")
    else:
        print(f"   📋 Conditions already exist, using existing data")


def test_condition_matching(patient_id):
    """Test the condition-screening matching logic"""
    
    print(f"\n🔍 Testing condition-screening matching for patient {patient_id}...")
    
    matcher = ConditionScreeningMatcher()
    
    # Get patient condition codes
    condition_codes = matcher.get_patient_condition_codes(patient_id)
    print(f"   📊 Found {len(condition_codes)} condition codes:")
    
    for condition in condition_codes:
        print(f"      • {condition['condition_name']}: {condition['code']} ({condition['system']})")
    
    # Find triggered screenings
    triggered_screenings = matcher.find_triggered_screenings(patient_id)
    print(f"\n   🎯 Found {len(triggered_screenings)} triggered screenings:")
    
    for screening in triggered_screenings:
        print(f"\n      📋 {screening['screening_type']['name']}")
        print(f"         Description: {screening['screening_type']['description']}")
        print(f"         Priority: {screening['priority']}")
        print(f"         Status: {screening['recommendation_status']}")
        print(f"         Triggered by:")
        
        for match in screening['triggered_by']:
            patient_condition = match['patient_condition']
            trigger_condition = match['trigger_condition']
            print(f"           - {patient_condition['condition_name']} matches {trigger_condition['display']}")
    
    # Generate comprehensive recommendations
    recommendations = matcher.generate_condition_triggered_recommendations(patient_id)
    
    print(f"\n   📈 Screening Recommendations Summary:")
    print(f"      Total triggered: {recommendations['total_triggered']}")
    print(f"      Due: {recommendations['summary']['due_count']}")
    print(f"      Overdue: {recommendations['summary']['overdue_count']}")
    print(f"      Scheduled: {recommendations['summary']['scheduled_count']}")
    print(f"      Completed: {recommendations['summary']['completed_count']}")
    
    return recommendations


def test_fhir_integration(patient_id):
    """Test FHIR integration and Epic compatibility"""
    
    print(f"\n🔗 Testing FHIR integration for patient {patient_id}...")
    
    fhir_mapper = FHIRObjectMapper()
    
    # Get patient and convert to FHIR
    patient = Patient.query.get(patient_id)
    fhir_patient = fhir_mapper.map_patient_to_fhir(patient)
    
    print(f"   👤 FHIR Patient Resource:")
    print(f"      ID: {fhir_patient['id']}")
    print(f"      Name: {fhir_patient['name'][0]['given'][0]} {fhir_patient['name'][0]['family']}")
    print(f"      MRN: {fhir_patient['identifier'][0]['value']}")
    
    # Get conditions and convert to FHIR
    conditions = MedicalCondition.query.filter_by(patient_id=patient_id).all()
    fhir_conditions = []
    
    print(f"\n   🏥 FHIR Condition Resources:")
    for condition in conditions:
        fhir_condition = fhir_mapper.map_condition_to_fhir(condition)
        fhir_conditions.append(fhir_condition)
        
        condition_code = fhir_condition['code']['coding'][0]
        print(f"      • {condition_code['display']} ({condition_code['code']})")
    
    # Create Epic-compatible bundle
    epic_bundle = {
        "resourceType": "Bundle",
        "id": f"patient-{patient_id}-conditions-screenings",
        "type": "collection",
        "timestamp": datetime.now().isoformat(),
        "entry": [
            {"resource": fhir_patient}
        ] + [{"resource": condition} for condition in fhir_conditions]
    }
    
    print(f"\n   📦 Epic-Compatible Bundle:")
    print(f"      Bundle ID: {epic_bundle['id']}")
    print(f"      Total Resources: {len(epic_bundle['entry'])}")
    print(f"      Resources: 1 Patient, {len(fhir_conditions)} Conditions")
    
    # Test screening type trigger matching
    print(f"\n   🎯 Testing Trigger Condition Matching:")
    
    screening_types = ScreeningType.query.filter_by(is_active=True).all()
    matches_found = 0
    
    for screening_type in screening_types:
        trigger_conditions = screening_type.get_trigger_conditions()
        if not trigger_conditions:
            continue
            
        for condition in conditions:
            # Extract condition codes from FHIR condition
            fhir_condition = fhir_mapper.map_condition_to_fhir(condition)
            
            for coding in fhir_condition['code']['coding']:
                condition_code = coding['code']
                condition_system = coding['system']
                
                if screening_type.matches_condition_code(condition_code, condition_system):
                    matches_found += 1
                    print(f"      ✓ {screening_type.name} triggered by {coding['display']} ({condition_code})")
    
    print(f"\n   📊 Matching Results: {matches_found} screening-condition matches found")
    
    return epic_bundle


if __name__ == "__main__":
    test_condition_triggered_screening_system()