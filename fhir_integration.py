"""
FHIR Integration for Healthcare Application

This module provides ready-to-use functions for converting your Patient objects
to FHIR Patient resources in your Flask application.
"""

import json
from flask import jsonify
from fhir_mapping.patient_mapper import PatientMapper
from models import Patient


def convert_patient_to_fhir(patient):
    """
    Convert your internal Patient object to FHIR Patient resource
    
    Args:
        patient: Patient model instance with fields (id, first_name, last_name, dob, sex, mrn)
                
    Returns:
        dict: FHIR Patient resource
        
    Raises:
        ValueError: If patient is missing required fields
    """
    mapper = PatientMapper()
    return mapper.to_fhir(patient)


def convert_fhir_to_patient_data(fhir_patient_dict):
    """
    Convert FHIR Patient resource to internal patient data format
    
    Args:
        fhir_patient_dict: FHIR Patient resource as dictionary
        
    Returns:
        dict: Patient data compatible with your Patient model
    """
    mapper = PatientMapper()
    return mapper.from_fhir(fhir_patient_dict)


def get_patient_fhir_by_id(patient_id):
    """
    Get a patient as FHIR resource by ID
    
    Args:
        patient_id: Patient ID
        
    Returns:
        dict: FHIR Patient resource or None if not found
    """
    patient = Patient.query.get(patient_id)
    if not patient:
        return None
    
    return convert_patient_to_fhir(patient)


def get_patient_fhir_by_mrn(mrn):
    """
    Get a patient as FHIR resource by MRN
    
    Args:
        mrn: Medical Record Number
        
    Returns:
        dict: FHIR Patient resource or None if not found
    """
    patient = Patient.query.filter_by(mrn=mrn).first()
    if not patient:
        return None
    
    return convert_patient_to_fhir(patient)


def export_all_patients_to_fhir():
    """
    Export all patients as FHIR Bundle
    
    Returns:
        dict: FHIR Bundle containing all patients
    """
    patients = Patient.query.all()
    mapper = PatientMapper()
    
    bundle = {
        "resourceType": "Bundle",
        "id": "patient-export",
        "type": "collection",
        "timestamp": mapper.format_datetime(mapper.constants.datetime.utcnow()) if hasattr(mapper.constants, 'datetime') else None,
        "total": len(patients),
        "entry": []
    }
    
    for patient in patients:
        try:
            fhir_patient = convert_patient_to_fhir(patient)
            bundle["entry"].append({
                "fullUrl": f"Patient/{patient.id}",
                "resource": fhir_patient
            })
        except ValueError as e:
            # Skip patients with incomplete data and log the issue
            print(f"Skipping patient ID {patient.id}: {e}")
            continue
    
    return bundle


def validate_patient_for_fhir(patient):
    """
    Validate that a patient has all required fields for FHIR conversion
    
    Args:
        patient: Patient model instance
        
    Returns:
        tuple: (is_valid: bool, missing_fields: list)
    """
    required_fields = ['first_name', 'last_name', 'date_of_birth', 'sex', 'mrn']
    missing_fields = []
    
    for field in required_fields:
        if not hasattr(patient, field) or getattr(patient, field) is None:
            missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields


# Flask route examples for API integration
def register_fhir_routes(app):
    """
    Register FHIR API routes with your Flask app
    
    Usage:
        from fhir_integration import register_fhir_routes
        register_fhir_routes(app)
    """
    
    @app.route('/api/fhir/Patient/<int:patient_id>', methods=['GET'])
    def get_fhir_patient(patient_id):
        """Get patient as FHIR resource"""
        fhir_patient = get_patient_fhir_by_id(patient_id)
        if not fhir_patient:
            return jsonify({"error": "Patient not found"}), 404
        
        return jsonify(fhir_patient)
    
    @app.route('/api/fhir/Patient', methods=['GET'])
    def search_fhir_patients():
        """Search patients and return as FHIR Bundle"""
        from flask import request
        
        # Handle search by MRN
        identifier = request.args.get('identifier')
        if identifier:
            fhir_patient = get_patient_fhir_by_mrn(identifier)
            if fhir_patient:
                bundle = {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": 1,
                    "entry": [{
                        "fullUrl": f"Patient/{fhir_patient['id']}",
                        "resource": fhir_patient
                    }]
                }
                return jsonify(bundle)
        
        # Return all patients if no specific search
        bundle = export_all_patients_to_fhir()
        return jsonify(bundle)
    
    @app.route('/api/fhir/export/patients', methods=['GET'])
    def export_fhir_patients():
        """Export all patients as FHIR Bundle"""
        bundle = export_all_patients_to_fhir()
        return jsonify(bundle)


def test_fhir_conversion():
    """
    Test FHIR conversion with actual patient data from your database
    """
    print("Testing FHIR Patient Conversion...")
    
    # Get a sample patient from your database
    patient = Patient.query.first()
    if not patient:
        print("No patients found in database")
        return
    
    print(f"Testing with patient: {patient.full_name} (MRN: {patient.mrn})")
    
    # Validate patient data
    is_valid, missing_fields = validate_patient_for_fhir(patient)
    if not is_valid:
        print(f"Patient missing required fields: {missing_fields}")
        return
    
    try:
        # Convert to FHIR
        fhir_patient = convert_patient_to_fhir(patient)
        print("✓ Successfully converted to FHIR")
        
        # Validate FHIR structure
        mapper = PatientMapper()
        is_fhir_valid = mapper.validate_fhir_patient(fhir_patient)
        print(f"✓ FHIR validation: {'passed' if is_fhir_valid else 'failed'}")
        
        # Convert back to internal format
        internal_data = convert_fhir_to_patient_data(fhir_patient)
        print("✓ Successfully converted back to internal format")
        
        # Display key fields
        print("\nFHIR Resource Summary:")
        print(f"  Resource Type: {fhir_patient.get('resourceType')}")
        print(f"  Patient ID: {fhir_patient.get('id')}")
        print(f"  Name: {fhir_patient['name'][0]['given'][0]} {fhir_patient['name'][0]['family']}")
        print(f"  Birth Date: {fhir_patient.get('birthDate')}")
        print(f"  Gender: {fhir_patient.get('gender')}")
        print(f"  MRN: {fhir_patient['identifier'][0]['value']}")
        
        return fhir_patient
        
    except Exception as e:
        print(f"✗ Conversion failed: {e}")
        return None