"""
FHIR API Routes

Flask routes that expose FHIR-compliant resources for external API compatibility
and enhanced prep sheet functionality using standardized healthcare data formats.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, date
import json
from fhir_object_mappers import (
    patient_to_fhir,
    appointment_to_fhir_encounter,
    document_to_fhir_document_reference,
    create_patient_fhir_bundle
)
from fhir_prep_sheet_integration import (
    generate_fhir_prep_sheet,
    export_patient_as_fhir_bundle,
    search_patients_as_fhir
)
from models import Patient, Appointment, MedicalDocument
from app import db

# Create FHIR API blueprint
fhir_api = Blueprint('fhir_api', __name__, url_prefix='/fhir')

@fhir_api.route('/Patient/<int:patient_id>', methods=['GET'])
def get_patient_fhir(patient_id):
    """
    Get patient as FHIR Patient resource
    
    Returns:
        FHIR Patient resource in JSON format
    """
    try:
        patient = Patient.query.get_or_404(patient_id)
        fhir_patient = patient_to_fhir(patient)
        
        return jsonify(fhir_patient), 200
    except Exception as e:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "details": {"text": str(e)}
            }]
        }), 500

@fhir_api.route('/Patient/<int:patient_id>/$everything', methods=['GET'])
def get_patient_everything(patient_id):
    """
    Get comprehensive patient data as FHIR Bundle (implements $everything operation)
    
    Query Parameters:
        include_documents: Include document content (default: false)
    
    Returns:
        FHIR Bundle with all patient-related resources
    """
    try:
        include_docs = request.args.get('include_documents', 'false').lower() == 'true'
        bundle = export_patient_as_fhir_bundle(patient_id, include_documents=include_docs)
        
        if 'error' in bundle:
            return jsonify({
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "not-found",
                    "details": {"text": bundle['error']}
                }]
            }), 404
        
        return jsonify(bundle), 200
    except Exception as e:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "details": {"text": str(e)}
            }]
        }), 500

@fhir_api.route('/Patient', methods=['GET'])
def search_patients_fhir():
    """
    Search patients using FHIR search parameters
    
    Query Parameters:
        name: Patient name (partial match)
        birthdate: Birth date (YYYY-MM-DD)
        identifier: Medical Record Number
        _count: Maximum results (default: 20)
    
    Returns:
        FHIR Bundle with search results
    """
    try:
        search_params = {
            'name': request.args.get('name'),
            'birthdate': request.args.get('birthdate'),
            'identifier': request.args.get('identifier')
        }
        
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        if not search_params:
            return jsonify({
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "required",
                    "details": {"text": "At least one search parameter is required"}
                }]
            }), 400
        
        bundle = search_patients_as_fhir(search_params)
        
        if 'error' in bundle:
            return jsonify({
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "exception",
                    "details": {"text": bundle['error']}
                }]
            }), 500
        
        return jsonify(bundle), 200
    except Exception as e:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "details": {"text": str(e)}
            }]
        }), 500

@fhir_api.route('/Encounter/<int:appointment_id>', methods=['GET'])
def get_appointment_fhir_encounter(appointment_id):
    """
    Get appointment as FHIR Encounter resource
    
    Returns:
        FHIR Encounter resource in JSON format
    """
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        fhir_encounter = appointment_to_fhir_encounter(appointment)
        
        return jsonify(fhir_encounter), 200
    except Exception as e:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "details": {"text": str(e)}
            }]
        }), 500

@fhir_api.route('/DocumentReference/<int:document_id>', methods=['GET'])
def get_document_fhir_reference(document_id):
    """
    Get document as FHIR DocumentReference resource
    
    Query Parameters:
        include_content: Include document content (default: false)
    
    Returns:
        FHIR DocumentReference resource in JSON format
    """
    try:
        document = MedicalDocument.query.get_or_404(document_id)
        fhir_doc_ref = document_to_fhir_document_reference(document)
        
        # Remove content if not requested
        include_content = request.args.get('include_content', 'false').lower() == 'true'
        if not include_content and "content" in fhir_doc_ref:
            for content in fhir_doc_ref["content"]:
                if "attachment" in content and "data" in content["attachment"]:
                    del content["attachment"]["data"]
        
        return jsonify(fhir_doc_ref), 200
    except Exception as e:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "details": {"text": str(e)}
            }]
        }), 500

@fhir_api.route('/Patient/<int:patient_id>/prep-sheet', methods=['GET'])
def generate_patient_prep_sheet_fhir(patient_id):
    """
    Generate FHIR-compliant prep sheet for patient
    
    Query Parameters:
        appointment_date: Date of appointment (YYYY-MM-DD, default: today)
    
    Returns:
        FHIR Bundle containing comprehensive prep sheet data
    """
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Parse appointment date
        appointment_date_str = request.args.get('appointment_date')
        if appointment_date_str:
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
        else:
            appointment_date = date.today()
        
        prep_sheet_bundle = generate_fhir_prep_sheet(patient, appointment_date)
        
        return jsonify(prep_sheet_bundle), 200
    except ValueError as e:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "invalid",
                "details": {"text": f"Invalid date format: {str(e)}"}
            }]
        }), 400
    except Exception as e:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "details": {"text": str(e)}
            }]
        }), 500

@fhir_api.route('/metadata', methods=['GET'])
def get_capability_statement():
    """
    Return FHIR CapabilityStatement describing supported operations
    
    Returns:
        FHIR CapabilityStatement resource
    """
    capability_statement = {
        "resourceType": "CapabilityStatement",
        "id": "healthcare-app-capability",
        "url": "https://your-system.com/fhir/metadata",
        "version": "1.0.0",
        "name": "HealthcareAppCapabilityStatement",
        "title": "Healthcare App FHIR Capability Statement",
        "status": "active",
        "date": datetime.utcnow().isoformat() + 'Z',
        "publisher": "Healthcare App System",
        "description": "FHIR capability statement for healthcare application",
        "kind": "instance",
        "software": {
            "name": "Healthcare Management System",
            "version": "1.0.0"
        },
        "implementation": {
            "description": "Healthcare App FHIR Server",
            "url": "https://your-system.com/fhir"
        },
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "documentation": "Healthcare App FHIR API",
            "security": {
                "description": "OAuth2 Bearer Token or API Key authentication"
            },
            "resource": [
                {
                    "type": "Patient",
                    "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"}
                    ],
                    "searchParam": [
                        {"name": "name", "type": "string"},
                        {"name": "birthdate", "type": "date"},
                        {"name": "identifier", "type": "token"}
                    ],
                    "operation": [
                        {"name": "everything", "definition": "Patient/$everything"}
                    ]
                },
                {
                    "type": "Encounter",
                    "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter",
                    "interaction": [
                        {"code": "read"}
                    ]
                },
                {
                    "type": "DocumentReference",
                    "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-documentreference",
                    "interaction": [
                        {"code": "read"}
                    ]
                },
                {
                    "type": "Condition",
                    "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition",
                    "interaction": [
                        {"code": "read"}
                    ]
                },
                {
                    "type": "Observation",
                    "profile": "http://hl7.org/fhir/StructureDefinition/vitalsigns",
                    "interaction": [
                        {"code": "read"}
                    ]
                },
                {
                    "type": "Immunization",
                    "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-immunization",
                    "interaction": [
                        {"code": "read"}
                    ]
                }
            ]
        }]
    }
    
    return jsonify(capability_statement), 200

# Register blueprint with main app
def register_fhir_routes(app):
    """Register FHIR API routes with Flask app"""
    app.register_blueprint(fhir_api)

# Additional utility routes for internal use
@fhir_api.route('/internal/convert/patient/<int:patient_id>', methods=['GET'])
def convert_patient_to_fhir(patient_id):
    """
    Internal utility: Convert single patient to FHIR format
    For testing and development purposes
    """
    try:
        patient = Patient.query.get_or_404(patient_id)
        fhir_patient = patient_to_fhir(patient)
        
        return jsonify({
            "conversion": "success",
            "original_id": patient_id,
            "fhir_resource": fhir_patient
        }), 200
    except Exception as e:
        return jsonify({
            "conversion": "failed",
            "error": str(e)
        }), 500

@fhir_api.route('/internal/convert/appointment/<int:appointment_id>', methods=['GET'])
def convert_appointment_to_fhir(appointment_id):
    """
    Internal utility: Convert single appointment to FHIR Encounter
    For testing and development purposes
    """
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        fhir_encounter = appointment_to_fhir_encounter(appointment)
        
        return jsonify({
            "conversion": "success",
            "original_id": appointment_id,
            "fhir_resource": fhir_encounter
        }), 200
    except Exception as e:
        return jsonify({
            "conversion": "failed",
            "error": str(e)
        }), 500

@fhir_api.route('/internal/convert/document/<int:document_id>', methods=['GET'])
def convert_document_to_fhir(document_id):
    """
    Internal utility: Convert single document to FHIR DocumentReference
    For testing and development purposes
    """
    try:
        document = MedicalDocument.query.get_or_404(document_id)
        fhir_doc_ref = document_to_fhir_document_reference(document)
        
        return jsonify({
            "conversion": "success",
            "original_id": document_id,
            "fhir_resource": fhir_doc_ref
        }), 200
    except Exception as e:
        return jsonify({
            "conversion": "failed",
            "error": str(e)
        }), 500