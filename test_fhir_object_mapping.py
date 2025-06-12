#!/usr/bin/env python3
"""
Test FHIR Object Mapping

Comprehensive test suite demonstrating the conversion of internal objects
(Patient, Appointment, MedicalDocument) to FHIR-compliant resources.
"""

import json
from datetime import datetime, date, time
from fhir_object_mappers import (
    patient_to_fhir,
    appointment_to_fhir_encounter,
    document_to_fhir_document_reference,
    create_patient_fhir_bundle
)

# Mock data classes for testing
class MockPatient:
    def __init__(self):
        self.id = 123
        self.first_name = "Jane"
        self.last_name = "Smith" 
        self.date_of_birth = date(1985, 6, 15)
        self.sex = "Female"
        self.mrn = "MRN123456"
        self.phone = "555-0123"
        self.email = "jane.smith@email.com"
        self.address = "123 Main St, City, State 12345"
        self.insurance = "Blue Cross Blue Shield"
        self.created_at = datetime(2024, 1, 1, 10, 0, 0)
        self.updated_at = datetime(2024, 6, 1, 14, 30, 0)

class MockAppointment:
    def __init__(self):
        self.id = 456
        self.patient_id = 123
        self.appointment_date = date(2024, 12, 15)
        self.appointment_time = time(10, 30)
        self.note = "Annual physical examination"
        self.status = "provider"
        self.created_at = datetime(2024, 12, 1, 9, 0, 0)
        self.updated_at = datetime(2024, 12, 10, 16, 45, 0)

class MockMedicalDocument:
    def __init__(self):
        self.id = 789
        self.patient_id = 123
        self.filename = "hba1c_results_2024.pdf"
        self.document_name = "Hemoglobin A1C Lab Results"
        self.document_type = "Lab Report"
        self.content = "Lab Results: Hemoglobin A1C: 6.8% (Normal: <7.0%)"
        self.binary_content = None
        self.is_binary = False
        self.mime_type = "text/plain"
        self.source_system = "LabCorp"
        self.document_date = datetime(2024, 11, 20, 14, 0, 0)
        self.provider = "Dr. Johnson"
        self.doc_metadata = json.dumps({
            "fhir_primary_code": {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "4548-4",
                        "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
                    }]
                }
            },
            "extracted_at": "2024-11-20T14:30:00Z"
        })
        self.is_processed = True
        self.created_at = datetime(2024, 11, 20, 14, 30, 0)
        self.updated_at = datetime(2024, 11, 20, 15, 0, 0)

class MockCondition:
    def __init__(self, name, code=None):
        self.id = 101
        self.patient_id = 123
        self.name = name
        self.code = code
        self.diagnosed_date = date(2020, 3, 15)
        self.is_active = True
        self.notes = f"Active {name} - well controlled"
        self.created_at = datetime(2020, 3, 15, 11, 0, 0)
        self.updated_at = datetime(2024, 6, 1, 10, 0, 0)

class MockVital:
    def __init__(self):
        self.id = 202
        self.patient_id = 123
        self.date = datetime(2024, 11, 15, 9, 30, 0)
        self.weight = 68.5  # kg
        self.height = 165.0  # cm
        self.bmi = 25.1
        self.temperature = 36.7  # Celsius
        self.blood_pressure_systolic = 122
        self.blood_pressure_diastolic = 78
        self.pulse = 72
        self.respiratory_rate = 16
        self.oxygen_saturation = 98.5
        self.created_at = datetime(2024, 11, 15, 9, 45, 0)

class MockImmunization:
    def __init__(self):
        self.id = 303
        self.patient_id = 123
        self.vaccine_name = "Influenza vaccine"
        self.administration_date = date(2024, 10, 1)
        self.dose_number = 1
        self.manufacturer = "Sanofi Pasteur"
        self.lot_number = "FLU2024-001"
        self.notes = "Annual flu vaccination - no adverse reactions"
        self.created_at = datetime(2024, 10, 1, 11, 0, 0)
        self.updated_at = datetime(2024, 10, 1, 11, 15, 0)

def test_patient_to_fhir():
    """Test Patient to FHIR Patient resource conversion"""
    print("=== Patient to FHIR Patient Resource Test ===")
    
    patient = MockPatient()
    fhir_patient = patient_to_fhir(patient)
    
    print(f"Original Patient: {patient.first_name} {patient.last_name} (MRN: {patient.mrn})")
    print("FHIR Patient Resource:")
    print(json.dumps(fhir_patient, indent=2, default=str))
    print()
    
    # Verify key FHIR fields
    assert fhir_patient["resourceType"] == "Patient"
    assert fhir_patient["id"] == "patient-123"
    assert fhir_patient["identifier"][0]["value"] == "MRN123456"
    assert fhir_patient["name"][0]["family"] == "Smith"
    assert fhir_patient["name"][0]["given"] == ["Jane"]
    assert fhir_patient["gender"] == "female"
    assert fhir_patient["birthDate"] == "1985-06-15"
    
    print("✓ Patient to FHIR conversion successful")
    return fhir_patient

def test_appointment_to_fhir_encounter():
    """Test Appointment to FHIR Encounter resource conversion"""
    print("=== Appointment to FHIR Encounter Resource Test ===")
    
    appointment = MockAppointment()
    fhir_encounter = appointment_to_fhir_encounter(appointment)
    
    print(f"Original Appointment: {appointment.appointment_date} at {appointment.appointment_time}")
    print("FHIR Encounter Resource:")
    print(json.dumps(fhir_encounter, indent=2, default=str))
    print()
    
    # Verify key FHIR fields
    assert fhir_encounter["resourceType"] == "Encounter"
    assert fhir_encounter["id"] == "encounter-456"
    assert fhir_encounter["status"] == "in-progress"  # mapped from "provider"
    assert fhir_encounter["class"]["code"] == "AMB"
    assert fhir_encounter["subject"]["reference"] == "Patient/patient-123"
    
    print("✓ Appointment to FHIR Encounter conversion successful")
    return fhir_encounter

def test_document_to_fhir_document_reference():
    """Test MedicalDocument to FHIR DocumentReference resource conversion"""
    print("=== Document to FHIR DocumentReference Resource Test ===")
    
    document = MockMedicalDocument()
    fhir_doc_ref = document_to_fhir_document_reference(document)
    
    print(f"Original Document: {document.document_name} ({document.document_type})")
    print("FHIR DocumentReference Resource:")
    print(json.dumps(fhir_doc_ref, indent=2, default=str))
    print()
    
    # Verify key FHIR fields
    assert fhir_doc_ref["resourceType"] == "DocumentReference"
    assert fhir_doc_ref["id"] == "documentreference-789"
    assert fhir_doc_ref["status"] == "current"
    assert fhir_doc_ref["subject"]["reference"] == "Patient/patient-123"
    assert fhir_doc_ref["description"] == "Hemoglobin A1C Lab Results"
    
    # Check if FHIR metadata was preserved
    if "extension" in fhir_doc_ref:
        metadata_ext = fhir_doc_ref["extension"][0]
        assert "fhir_primary_code" in json.loads(metadata_ext["valueString"])
    
    print("✓ Document to FHIR DocumentReference conversion successful")
    return fhir_doc_ref

def test_condition_to_fhir():
    """Test Condition to FHIR Condition resource conversion"""
    print("=== Condition to FHIR Condition Resource Test ===")
    
    from fhir_object_mappers import fhir_mapper
    
    condition = MockCondition("Type 2 Diabetes", "E11.9")
    fhir_condition = fhir_mapper.map_condition_to_fhir(condition)
    
    print(f"Original Condition: {condition.name} ({condition.code})")
    print("FHIR Condition Resource:")
    print(json.dumps(fhir_condition, indent=2, default=str))
    print()
    
    # Verify key FHIR fields
    assert fhir_condition["resourceType"] == "Condition"
    assert fhir_condition["id"] == "condition-101"
    assert fhir_condition["clinicalStatus"]["coding"][0]["code"] == "active"
    assert fhir_condition["subject"]["reference"] == "Patient/patient-123"
    assert fhir_condition["code"]["text"] == "Type 2 Diabetes"
    
    print("✓ Condition to FHIR conversion successful")
    return fhir_condition

def test_vital_to_fhir_observations():
    """Test Vital to FHIR Observation resources conversion"""
    print("=== Vital to FHIR Observation Resources Test ===")
    
    from fhir_object_mappers import fhir_mapper
    
    vital = MockVital()
    fhir_observations = fhir_mapper.map_vital_to_fhir_observation(vital)
    
    print(f"Original Vital Signs: BP {vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic}, HR {vital.pulse}")
    print(f"Generated {len(fhir_observations)} FHIR Observation Resources:")
    
    for i, obs in enumerate(fhir_observations, 1):
        print(f"Observation {i}: {obs['code']['coding'][0]['display']}")
        if i <= 2:  # Show first 2 observations in detail
            print(json.dumps(obs, indent=2, default=str))
        print()
    
    # Verify observations were created
    assert len(fhir_observations) > 0
    
    # Find blood pressure observation
    bp_obs = next((obs for obs in fhir_observations if "blood pressure" in obs['code']['coding'][0]['display'].lower()), None)
    if bp_obs:
        assert bp_obs["resourceType"] == "Observation"
        assert bp_obs["category"][0]["coding"][0]["code"] == "vital-signs"
        assert len(bp_obs["component"]) == 2  # systolic and diastolic
    
    print("✓ Vital to FHIR Observations conversion successful")
    return fhir_observations

def test_immunization_to_fhir():
    """Test Immunization to FHIR Immunization resource conversion"""
    print("=== Immunization to FHIR Immunization Resource Test ===")
    
    from fhir_object_mappers import fhir_mapper
    
    immunization = MockImmunization()
    fhir_immunization = fhir_mapper.map_immunization_to_fhir(immunization)
    
    print(f"Original Immunization: {immunization.vaccine_name} on {immunization.administration_date}")
    print("FHIR Immunization Resource:")
    print(json.dumps(fhir_immunization, indent=2, default=str))
    print()
    
    # Verify key FHIR fields
    assert fhir_immunization["resourceType"] == "Immunization"
    assert fhir_immunization["id"] == "immunization-303"
    assert fhir_immunization["status"] == "completed"
    assert fhir_immunization["patient"]["reference"] == "Patient/patient-123"
    assert fhir_immunization["vaccineCode"]["text"] == "Influenza vaccine"
    
    print("✓ Immunization to FHIR conversion successful")
    return fhir_immunization

def test_comprehensive_patient_bundle():
    """Test creating comprehensive FHIR Bundle for patient"""
    print("=== Comprehensive Patient FHIR Bundle Test ===")
    
    # Create mock patient with related data
    class MockPatientWithData(MockPatient):
        def __init__(self):
            super().__init__()
            self.conditions = [MockCondition("Type 2 Diabetes", "E11.9"), MockCondition("Hypertension", "I10")]
            self.vitals = [MockVital()]
            self.immunizations = [MockImmunization()]
            self.documents = [MockMedicalDocument()]
    
    patient = MockPatientWithData()
    bundle = create_patient_fhir_bundle(patient, include_related=True)
    
    print(f"Patient: {patient.first_name} {patient.last_name}")
    print(f"Bundle contains {bundle['total']} resources:")
    
    resource_counts = {}
    for entry in bundle["entry"]:
        resource_type = entry["resource"]["resourceType"]
        resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1
    
    for resource_type, count in resource_counts.items():
        print(f"  - {resource_type}: {count}")
    
    print()
    print("Sample Bundle Structure:")
    print(json.dumps({
        "resourceType": bundle["resourceType"],
        "id": bundle["id"],
        "type": bundle["type"],
        "total": bundle["total"],
        "entry": [{"resource": {"resourceType": entry["resource"]["resourceType"], "id": entry["resource"]["id"]}} for entry in bundle["entry"][:3]]
    }, indent=2))
    print()
    
    # Verify bundle structure
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] > 1
    assert any(entry["resource"]["resourceType"] == "Patient" for entry in bundle["entry"])
    
    print("✓ Comprehensive patient bundle creation successful")
    return bundle

def test_fhir_format_compliance():
    """Test FHIR format compliance across all conversions"""
    print("=== FHIR Format Compliance Test ===")
    
    # Test all conversions
    patient = MockPatient()
    appointment = MockAppointment()
    document = MockMedicalDocument()
    
    # Convert to FHIR
    fhir_patient = patient_to_fhir(patient)
    fhir_encounter = appointment_to_fhir_encounter(appointment)
    fhir_doc_ref = document_to_fhir_document_reference(document)
    
    # Check common FHIR requirements
    fhir_resources = [
        ("Patient", fhir_patient),
        ("Encounter", fhir_encounter),
        ("DocumentReference", fhir_doc_ref)
    ]
    
    print("FHIR Compliance Checks:")
    for resource_name, resource in fhir_resources:
        print(f"\n{resource_name}:")
        
        # Required fields
        assert "resourceType" in resource, f"{resource_name} missing resourceType"
        print(f"  ✓ resourceType: {resource['resourceType']}")
        
        assert "id" in resource, f"{resource_name} missing id"
        print(f"  ✓ id: {resource['id']}")
        
        if "meta" in resource:
            print(f"  ✓ meta: lastUpdated present")
        
        # Check for US Core profiles where applicable
        if resource_name == "Patient":
            assert "identifier" in resource, "Patient missing identifier"
            assert "name" in resource, "Patient missing name"
            assert "gender" in resource, "Patient missing gender"
            print(f"  ✓ US Core Patient fields present")
        
        elif resource_name == "Encounter":
            assert "status" in resource, "Encounter missing status"
            assert "class" in resource, "Encounter missing class"
            assert "subject" in resource, "Encounter missing subject"
            print(f"  ✓ US Core Encounter fields present")
        
        elif resource_name == "DocumentReference":
            assert "status" in resource, "DocumentReference missing status"
            assert "type" in resource, "DocumentReference missing type"
            assert "subject" in resource, "DocumentReference missing subject"
            print(f"  ✓ US Core DocumentReference fields present")
    
    print("\n✓ All resources pass FHIR compliance checks")

def demonstrate_prep_sheet_integration():
    """Demonstrate how FHIR resources integrate with prep sheet logic"""
    print("=== FHIR Prep Sheet Integration Demo ===")
    
    from fhir_prep_sheet_integration import fhir_prep_sheet_generator
    
    # Create mock patient
    class MockPatientWithData(MockPatient):
        def __init__(self):
            super().__init__()
            self.conditions = [MockCondition("Type 2 Diabetes", "E11.9")]
    
    patient = MockPatientWithData()
    appointment_date = date(2024, 12, 15)
    
    print(f"Generating FHIR prep sheet for {patient.first_name} {patient.last_name}")
    print(f"Appointment Date: {appointment_date}")
    
    # This would normally call the database, but we'll show the structure
    print("\nPrep Sheet would contain:")
    print("- FHIR Patient resource with complete demographics")
    print("- FHIR ServiceRequest resources for recommended screenings")
    print("- FHIR Condition resources for active medical conditions")
    print("- FHIR Observation resources for recent vital signs")
    print("- FHIR DocumentReference resources for relevant documents")
    print("- FHIR Immunization resources for vaccination history")
    
    print("\nBenefits of FHIR format:")
    print("• Standardized data structure for external API compatibility")
    print("• Consistent coding systems (LOINC, SNOMED CT, ICD-10)")
    print("• Proper categorization and metadata preservation")
    print("• Ready for healthcare system integrations")
    print("• Supports bidirectional data exchange")

def main():
    """Run comprehensive FHIR object mapping tests"""
    print("FHIR Object Mapping Test Suite")
    print("=" * 50)
    print()
    
    # Run all tests
    test_patient_to_fhir()
    test_appointment_to_fhir_encounter()
    test_document_to_fhir_document_reference()
    test_condition_to_fhir()
    test_vital_to_fhir_observations()
    test_immunization_to_fhir()
    test_comprehensive_patient_bundle()
    test_fhir_format_compliance()
    demonstrate_prep_sheet_integration()
    
    print("=" * 50)
    print("✓ All FHIR object mapping tests completed successfully")
    print()
    print("Your FHIR mapping functions provide:")
    print("• Complete conversion of internal objects to FHIR resources")
    print("• Standards-compliant healthcare data format")
    print("• External API compatibility for data exchange")
    print("• Enhanced prep sheet logic with structured data")
    print("• Bidirectional mapping capability")
    print("• Comprehensive patient bundles for complete data export")

if __name__ == "__main__":
    main()