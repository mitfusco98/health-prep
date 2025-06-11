"""
FHIR Patient Mapper Usage Example

This module demonstrates how to use the PatientMapper to convert
internal Patient objects to FHIR Patient resources.
"""

import json
from datetime import date, datetime
from fhir_mapping import PatientMapper


# Mock Patient class for demonstration
class MockPatient:
    """Mock Patient class that mimics your internal Patient model"""
    
    def __init__(self, id=None, first_name="", last_name="", date_of_birth=None, 
                 sex="", mrn="", phone="", email="", address="", insurance="",
                 created_at=None, updated_at=None):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.sex = sex
        self.mrn = mrn
        self.phone = phone
        self.email = email
        self.address = address
        self.insurance = insurance
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


def convert_patient_to_fhir(patient):
    """
    Main function to convert your internal patient object to FHIR Patient resource
    
    Args:
        patient: Your internal Patient model object with fields:
                - id, first_name, last_name, dob, sex, mrn (required)
                - phone, email, address, insurance (optional)
                
    Returns:
        Dict containing FHIR Patient resource
        
    Raises:
        ValueError: If patient is missing required fields
    """
    mapper = PatientMapper()
    return mapper.to_fhir(patient)


def convert_fhir_to_patient_data(fhir_patient):
    """
    Convert FHIR Patient resource back to internal patient data format
    
    Args:
        fhir_patient: FHIR Patient resource dictionary
        
    Returns:
        Dict containing internal patient data fields
    """
    mapper = PatientMapper()
    return mapper.from_fhir(fhir_patient)


def example_usage():
    """Demonstrate the FHIR patient conversion functionality"""
    
    print("=== FHIR Patient Mapper Example ===\n")
    
    # Create a sample patient
    sample_patient = MockPatient(
        id=12345,
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1985, 3, 15),
        sex="Male",
        mrn="MRN123456",
        phone="555-123-4567",
        email="john.doe@example.com",
        address="123 Main St, Anytown, NY, 12345",
        insurance="Blue Cross Blue Shield",
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=datetime(2024, 6, 1, 14, 45, 0)
    )
    
    print("Original Patient Data:")
    print(f"  ID: {sample_patient.id}")
    print(f"  Name: {sample_patient.first_name} {sample_patient.last_name}")
    print(f"  Date of Birth: {sample_patient.date_of_birth}")
    print(f"  Sex: {sample_patient.sex}")
    print(f"  MRN: {sample_patient.mrn}")
    print(f"  Phone: {sample_patient.phone}")
    print(f"  Email: {sample_patient.email}")
    print(f"  Address: {sample_patient.address}")
    print(f"  Insurance: {sample_patient.insurance}")
    print()
    
    try:
        # Convert to FHIR
        fhir_patient = convert_patient_to_fhir(sample_patient)
        
        print("FHIR Patient Resource:")
        print(json.dumps(fhir_patient, indent=2))
        print()
        
        # Convert back to internal format
        internal_data = convert_fhir_to_patient_data(fhir_patient)
        
        print("Converted Back to Internal Format:")
        for key, value in internal_data.items():
            print(f"  {key}: {value}")
        print()
        
        # Validate the FHIR resource
        mapper = PatientMapper()
        is_valid = mapper.validate_fhir_patient(fhir_patient)
        print(f"FHIR Resource Valid: {is_valid}")
        
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def minimal_patient_example():
    """Example with only required fields"""
    
    print("\n=== Minimal Patient Example (Required Fields Only) ===\n")
    
    minimal_patient = MockPatient(
        id=67890,
        first_name="Jane",
        last_name="Smith",
        date_of_birth=date(1990, 7, 22),
        sex="Female",
        mrn="MRN789012"
    )
    
    try:
        fhir_patient = convert_patient_to_fhir(minimal_patient)
        print("Minimal FHIR Patient Resource:")
        print(json.dumps(fhir_patient, indent=2))
        
    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    example_usage()
    minimal_patient_example()