"""
Standalone FHIR Conversion Test

This script demonstrates the FHIR patient conversion functionality
using your actual Patient model structure.
"""

import json
from datetime import date, datetime
import os
import sys

# Add the current directory to Python path
sys.path.append('.')

# Set up Flask app context for database access
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')
if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'

from fhir_mapping.patient_mapper import PatientMapper


class TestPatient:
    """Test patient class with your actual model structure"""
    def __init__(self):
        self.id = 12345
        self.first_name = "John"
        self.last_name = "Doe"
        self.date_of_birth = date(1985, 3, 15)
        self.sex = "Male"
        self.mrn = "MRN123456"
        self.phone = "555-123-4567"
        self.email = "john.doe@example.com"
        self.address = "123 Main St, Anytown, NY, 12345"
        self.insurance = "Blue Cross Blue Shield"
        self.created_at = datetime(2024, 1, 15, 10, 30, 0)
        self.updated_at = datetime(2024, 6, 1, 14, 45, 0)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


def main():
    """Test the FHIR conversion functionality"""
    print("=== FHIR Patient Conversion Test ===\n")
    
    # Create test patient with your model structure
    patient = TestPatient()
    
    print("Original Patient Data:")
    print(f"  ID: {patient.id}")
    print(f"  Name: {patient.full_name}")
    print(f"  Date of Birth: {patient.date_of_birth}")
    print(f"  Sex: {patient.sex}")
    print(f"  MRN: {patient.mrn}")
    print(f"  Phone: {patient.phone}")
    print(f"  Email: {patient.email}")
    print(f"  Address: {patient.address}")
    print(f"  Insurance: {patient.insurance}")
    print()
    
    # Test conversion to FHIR
    try:
        mapper = PatientMapper()
        fhir_patient = mapper.to_fhir(patient)
        
        print("✓ Successfully converted to FHIR Patient resource")
        print("\nFHIR Patient Resource:")
        print(json.dumps(fhir_patient, indent=2))
        print()
        
        # Validate FHIR resource
        is_valid = mapper.validate_fhir_patient(fhir_patient)
        print(f"✓ FHIR validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test conversion back to internal format
        internal_data = mapper.from_fhir(fhir_patient)
        print("\n✓ Successfully converted back to internal format")
        print("Converted Internal Data:")
        for key, value in internal_data.items():
            print(f"  {key}: {value}")
        
        # Summary of key FHIR fields
        print("\n=== FHIR Resource Summary ===")
        print(f"Resource Type: {fhir_patient.get('resourceType')}")
        print(f"Patient ID: {fhir_patient.get('id')}")
        print(f"Active Status: {fhir_patient.get('active')}")
        
        # Name information
        names = fhir_patient.get('name', [])
        if names:
            name = names[0]
            given_names = name.get('given', [])
            family_name = name.get('family', '')
            print(f"Name: {' '.join(given_names)} {family_name}")
        
        # Identifiers
        identifiers = fhir_patient.get('identifier', [])
        for identifier in identifiers:
            type_info = identifier.get('type', {})
            coding = type_info.get('coding', [{}])[0] if type_info.get('coding') else {}
            type_display = coding.get('display', 'Unknown')
            print(f"Identifier ({type_display}): {identifier.get('value')}")
        
        # Contact information
        telecom = fhir_patient.get('telecom', [])
        for contact in telecom:
            system = contact.get('system', '').title()
            value = contact.get('value', '')
            use = contact.get('use', '').title()
            print(f"{system} ({use}): {value}")
        
        print(f"Gender: {fhir_patient.get('gender')}")
        print(f"Birth Date: {fhir_patient.get('birthDate')}")
        
        # Address
        addresses = fhir_patient.get('address', [])
        if addresses:
            addr = addresses[0]
            address_line = ', '.join(addr.get('line', []))
            city = addr.get('city', '')
            state = addr.get('state', '')
            postal = addr.get('postalCode', '')
            full_address = f"{address_line}, {city}, {state}, {postal}".strip(', ')
            print(f"Address: {full_address}")
        
        # Extensions
        extensions = fhir_patient.get('extension', [])
        for ext in extensions:
            url = ext.get('url', '')
            if 'insurance' in url:
                print(f"Insurance: {ext.get('valueString', '')}")
        
        print("\n✓ FHIR conversion test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ FHIR conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_minimal_patient():
    """Test with minimal required fields only"""
    print("\n=== Minimal Patient Test ===\n")
    
    class MinimalPatient:
        def __init__(self):
            self.id = 67890
            self.first_name = "Jane"
            self.last_name = "Smith"
            self.date_of_birth = date(1990, 7, 22)
            self.sex = "Female"
            self.mrn = "MRN789012"
    
    patient = MinimalPatient()
    
    try:
        mapper = PatientMapper()
        fhir_patient = mapper.to_fhir(patient)
        
        print("✓ Minimal patient converted successfully")
        print("FHIR Resource (minimal):")
        print(json.dumps(fhir_patient, indent=2))
        
        return True
        
    except Exception as e:
        print(f"✗ Minimal patient conversion failed: {e}")
        return False


if __name__ == "__main__":
    success1 = main()
    success2 = test_minimal_patient()
    
    if success1 and success2:
        print("\n🎉 All FHIR conversion tests passed!")
    else:
        print("\n❌ Some tests failed - check the output above")