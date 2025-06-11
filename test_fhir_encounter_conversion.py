"""
Standalone FHIR Encounter Conversion Test

This script demonstrates the FHIR encounter conversion functionality
using your actual Appointment model structure.
"""

import json
from datetime import date, time, datetime
import os
import sys

# Add the current directory to Python path
sys.path.append('.')

# Set up Flask app context for database access
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')
if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'

from fhir_mapping.encounter_mapper import EncounterMapper


class TestPatient:
    """Test patient class for appointment relationship"""
    def __init__(self, id, name):
        self.id = id
        self.full_name = name


class TestAppointment:
    """Test appointment class with your actual model structure"""
    def __init__(self):
        self.id = 67890
        self.patient_id = 12345
        self.appointment_date = date(2024, 6, 15)
        self.appointment_time = time(14, 30, 0)  # 2:30 PM
        self.note = "Follow-up visit for blood pressure monitoring"
        self.status = "waiting"  # OOO, waiting, provider, seen
        self.created_at = datetime(2024, 6, 1, 9, 0, 0)
        self.updated_at = datetime(2024, 6, 10, 15, 45, 0)
        
        # Mock patient relationship
        self.patient = TestPatient(12345, "John Doe")
    
    @property
    def date_time(self):
        """Return a datetime object combining the date and time"""
        return datetime.combine(self.appointment_date, self.appointment_time)


def main():
    """Test the FHIR encounter conversion functionality"""
    print("=== FHIR Encounter Conversion Test ===\n")
    
    # Create test appointment with your model structure
    appointment = TestAppointment()
    
    print("Original Appointment Data:")
    print(f"  ID: {appointment.id}")
    print(f"  Patient ID: {appointment.patient_id}")
    print(f"  Patient Name: {appointment.patient.full_name}")
    print(f"  Date: {appointment.appointment_date}")
    print(f"  Time: {appointment.appointment_time}")
    print(f"  DateTime: {appointment.date_time}")
    print(f"  Status: {appointment.status}")
    print(f"  Note: {appointment.note}")
    print(f"  Created: {appointment.created_at}")
    print(f"  Updated: {appointment.updated_at}")
    print()
    
    # Test conversion to FHIR Encounter
    try:
        mapper = EncounterMapper()
        fhir_encounter = mapper.to_fhir(appointment)
        
        print("✓ Successfully converted to FHIR Encounter resource")
        print("\nFHIR Encounter Resource:")
        print(json.dumps(fhir_encounter, indent=2))
        print()
        
        # Validate FHIR resource
        is_valid = mapper.validate_fhir_encounter(fhir_encounter)
        print(f"✓ FHIR validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test conversion back to internal format
        internal_data = mapper.from_fhir(fhir_encounter)
        print("\n✓ Successfully converted back to internal format")
        print("Converted Internal Data:")
        for key, value in internal_data.items():
            print(f"  {key}: {value}")
        
        # Summary of key FHIR fields
        print("\n=== FHIR Encounter Summary ===")
        print(f"Resource Type: {fhir_encounter.get('resourceType')}")
        print(f"Encounter ID: {fhir_encounter.get('id')}")
        print(f"Status: {fhir_encounter.get('status')}")
        
        # Class information
        encounter_class = fhir_encounter.get('class', {})
        print(f"Class: {encounter_class.get('display', encounter_class.get('code', 'Unknown'))}")
        
        # Type information
        types = fhir_encounter.get('type', [])
        if types:
            type_coding = types[0].get('coding', [{}])[0]
            print(f"Type: {type_coding.get('display', 'Unknown')}")
        
        # Subject (patient) reference
        subject = fhir_encounter.get('subject', {})
        print(f"Subject: {subject.get('reference')} ({subject.get('display', 'Unknown patient')})")
        
        # Period information
        period = fhir_encounter.get('period', {})
        print(f"Start Time: {period.get('start', 'Not specified')}")
        if period.get('end'):
            print(f"End Time: {period.get('end')}")
        
        # Reason/Note
        reason_codes = fhir_encounter.get('reasonCode', [])
        if reason_codes:
            print(f"Reason: {reason_codes[0].get('text', 'No reason specified')}")
        
        # Identifiers
        identifiers = fhir_encounter.get('identifier', [])
        for identifier in identifiers:
            print(f"Identifier: {identifier.get('value')} ({identifier.get('system', 'Unknown system')})")
        
        print("\n✓ FHIR encounter conversion test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ FHIR encounter conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_statuses():
    """Test conversion with different appointment statuses"""
    print("\n=== Different Status Tests ===\n")
    
    statuses = ['OOO', 'waiting', 'provider', 'seen']
    mapper = EncounterMapper()
    
    for status in statuses:
        print(f"Testing status: {status}")
        
        appointment = TestAppointment()
        appointment.status = status
        appointment.note = f"Test appointment with {status} status"
        
        try:
            fhir_encounter = mapper.to_fhir(appointment)
            fhir_status = fhir_encounter.get('status')
            print(f"  Internal '{status}' → FHIR '{fhir_status}'")
            
            # Test period end time for completed appointments
            period = fhir_encounter.get('period', {})
            if status == 'seen' and period.get('end'):
                print(f"  ✓ End time added for completed encounter")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        
        print()


def test_encounter_types():
    """Test encounter type detection based on notes"""
    print("\n=== Encounter Type Tests ===\n")
    
    test_cases = [
        ("Annual checkup appointment", "Encounter for check up"),
        ("Follow-up visit for medication review", "Follow-up encounter"),
        ("General consultation", "Consultation"),
        ("Regular appointment", "Consultation")  # Default
    ]
    
    mapper = EncounterMapper()
    
    for note, expected_type in test_cases:
        print(f"Testing note: '{note}'")
        
        appointment = TestAppointment()
        appointment.note = note
        
        try:
            fhir_encounter = mapper.to_fhir(appointment)
            types = fhir_encounter.get('type', [])
            if types:
                type_display = types[0].get('coding', [{}])[0].get('display', 'Unknown')
                print(f"  Expected: {expected_type}")
                print(f"  Detected: {type_display}")
                print(f"  ✓ {'Match' if expected_type == type_display else 'Different'}")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        
        print()


def test_minimal_appointment():
    """Test with minimal required fields only"""
    print("\n=== Minimal Appointment Test ===\n")
    
    class MinimalAppointment:
        def __init__(self):
            self.id = 98765
            self.patient_id = 54321
            self.appointment_date = date(2024, 7, 20)
            self.appointment_time = time(10, 0, 0)
            self.status = "OOO"
            self.note = None  # No note
    
    appointment = MinimalAppointment()
    
    try:
        mapper = EncounterMapper()
        fhir_encounter = mapper.to_fhir(appointment)
        
        print("✓ Minimal appointment converted successfully")
        print("FHIR Encounter (minimal):")
        print(json.dumps(fhir_encounter, indent=2))
        
        return True
        
    except Exception as e:
        print(f"✗ Minimal appointment conversion failed: {e}")
        return False


if __name__ == "__main__":
    success1 = main()
    test_different_statuses()
    test_encounter_types()
    success2 = test_minimal_appointment()
    
    if success1 and success2:
        print("\n✓ All FHIR encounter conversion tests passed!")
    else:
        print("\n✗ Some tests failed - check the output above")