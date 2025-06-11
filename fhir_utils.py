"""
FHIR Utilities for Healthcare Application

Ready-to-use utility functions for FHIR patient conversion in your Flask routes.
"""

from flask import jsonify
from fhir_mapping.patient_mapper import PatientMapper


def patient_to_fhir(patient):
    """
    Convert your Patient object to FHIR Patient resource
    
    Usage:
        from fhir_utils import patient_to_fhir
        
        patient = Patient.query.get(patient_id)
        fhir_resource = patient_to_fhir(patient)
    
    Args:
        patient: Your Patient model instance
        
    Returns:
        dict: Complete FHIR Patient resource
    """
    mapper = PatientMapper()
    return mapper.to_fhir(patient)


def fhir_to_patient_data(fhir_patient):
    """
    Convert FHIR Patient resource to internal patient data
    
    Args:
        fhir_patient: FHIR Patient resource dictionary
        
    Returns:
        dict: Patient data for your internal model
    """
    mapper = PatientMapper()
    return mapper.from_fhir(fhir_patient)


def create_fhir_bundle(patients):
    """
    Create FHIR Bundle from multiple patients
    
    Args:
        patients: List of Patient model instances
        
    Returns:
        dict: FHIR Bundle resource
    """
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "total": len(patients),
        "entry": []
    }
    
    for patient in patients:
        try:
            fhir_patient = patient_to_fhir(patient)
            bundle["entry"].append({
                "fullUrl": f"Patient/{patient.id}",
                "resource": fhir_patient
            })
        except ValueError:
            # Skip patients with incomplete data
            bundle["total"] -= 1
            continue
    
    return bundle


def add_fhir_routes(app):
    """
    Add FHIR API endpoints to your Flask application
    
    Usage:
        from fhir_utils import add_fhir_routes
        add_fhir_routes(app)
    
    This adds:
        GET /fhir/Patient/{id} - Get single patient as FHIR
        GET /fhir/Patient - Search/list patients as FHIR Bundle
    """
    from models import Patient
    
    @app.route('/fhir/Patient/<int:patient_id>')
    def get_fhir_patient(patient_id):
        """Get patient as FHIR Patient resource"""
        patient = Patient.query.get_or_404(patient_id)
        fhir_patient = patient_to_fhir(patient)
        return jsonify(fhir_patient)
    
    @app.route('/fhir/Patient')
    def get_fhir_patients():
        """Get patients as FHIR Bundle"""
        from flask import request
        
        # Handle search by MRN
        identifier = request.args.get('identifier')
        if identifier:
            patient = Patient.query.filter_by(mrn=identifier).first()
            if patient:
                fhir_patient = patient_to_fhir(patient)
                bundle = {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": 1,
                    "entry": [{
                        "fullUrl": f"Patient/{patient.id}",
                        "resource": fhir_patient
                    }]
                }
                return jsonify(bundle)
            else:
                return jsonify({
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": 0,
                    "entry": []
                })
        
        # Return all patients
        patients = Patient.query.all()
        bundle = create_fhir_bundle(patients)
        return jsonify(bundle)