"""
FHIR Utilities for Healthcare Application

Ready-to-use utility functions for FHIR patient and encounter conversion in your Flask routes.
"""

from flask import jsonify
from fhir_mapping.patient_mapper import PatientMapper
from fhir_mapping.encounter_mapper import EncounterMapper
from fhir_mapping.document_reference_mapper import DocumentReferenceMapper


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


def appointment_to_fhir(appointment):
    """
    Convert your Appointment object to FHIR Encounter resource
    
    Usage:
        from fhir_utils import appointment_to_fhir
        
        appointment = Appointment.query.get(appointment_id)
        fhir_encounter = appointment_to_fhir(appointment)
    
    Args:
        appointment: Your Appointment model instance
        
    Returns:
        dict: Complete FHIR Encounter resource
    """
    mapper = EncounterMapper()
    return mapper.to_fhir(appointment)


def fhir_to_appointment_data(fhir_encounter):
    """
    Convert FHIR Encounter resource to internal appointment data
    
    Args:
        fhir_encounter: FHIR Encounter resource dictionary
        
    Returns:
        dict: Appointment data for your internal model
    """
    mapper = EncounterMapper()
    return mapper.from_fhir(fhir_encounter)


def create_encounter_bundle(appointments):
    """
    Create FHIR Bundle from multiple appointments
    
    Args:
        appointments: List of Appointment model instances
        
    Returns:
        dict: FHIR Bundle resource containing Encounters
    """
    mapper = EncounterMapper()
    return mapper.create_encounter_bundle(appointments)


def document_to_fhir(document):
    """
    Convert your MedicalDocument object to FHIR DocumentReference resource
    
    Usage:
        from fhir_utils import document_to_fhir
        
        document = MedicalDocument.query.get(document_id)
        fhir_document_ref = document_to_fhir(document)
    
    Args:
        document: Your MedicalDocument model instance
        
    Returns:
        dict: Complete FHIR DocumentReference resource
    """
    mapper = DocumentReferenceMapper()
    return mapper.to_fhir(document)


def fhir_to_document_data(fhir_document_ref):
    """
    Convert FHIR DocumentReference resource to internal document data
    
    Args:
        fhir_document_ref: FHIR DocumentReference resource dictionary
        
    Returns:
        dict: Document data for your internal model
    """
    mapper = DocumentReferenceMapper()
    return mapper.from_fhir(fhir_document_ref)


def create_document_bundle(documents):
    """
    Create FHIR Bundle from multiple documents
    
    Args:
        documents: List of MedicalDocument model instances
        
    Returns:
        dict: FHIR Bundle resource containing DocumentReferences
    """
    mapper = DocumentReferenceMapper()
    return mapper.create_document_bundle(documents)


def add_fhir_routes(app):
    """
    Add FHIR API endpoints to your Flask application
    
    Usage:
        from fhir_utils import add_fhir_routes
        add_fhir_routes(app)
    
    This adds:
        GET /fhir/Patient/{id} - Get single patient as FHIR
        GET /fhir/Patient - Search/list patients as FHIR Bundle
        GET /fhir/Encounter/{id} - Get single appointment as FHIR Encounter
        GET /fhir/Encounter - Search/list appointments as FHIR Bundle
        GET /fhir/DocumentReference/{id} - Get single document as FHIR DocumentReference
        GET /fhir/DocumentReference - Search/list documents as FHIR Bundle
    """
    from models import Patient, Appointment, MedicalDocument
    
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
    
    @app.route('/fhir/Encounter/<int:appointment_id>')
    def get_fhir_encounter(appointment_id):
        """Get appointment as FHIR Encounter resource"""
        appointment = Appointment.query.get_or_404(appointment_id)
        fhir_encounter = appointment_to_fhir(appointment)
        return jsonify(fhir_encounter)
    
    @app.route('/fhir/Encounter')
    def get_fhir_encounters():
        """Get appointments as FHIR Encounter Bundle"""
        from flask import request
        from datetime import datetime, date
        
        # Handle search by patient ID
        patient_id = request.args.get('subject')
        if patient_id and patient_id.startswith('Patient/'):
            patient_id = patient_id.split('/')[1]
            appointments = Appointment.query.filter_by(patient_id=int(patient_id)).all()
        # Handle search by date
        elif request.args.get('date'):
            try:
                search_date = datetime.strptime(request.args.get('date'), '%Y-%m-%d').date()
                appointments = Appointment.query.filter_by(appointment_date=search_date).all()
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            # Return all appointments
            appointments = Appointment.query.all()
        
        bundle = create_encounter_bundle(appointments)
        return jsonify(bundle)
    
    @app.route('/fhir/DocumentReference/<int:document_id>')
    def get_fhir_document_reference(document_id):
        """Get document as FHIR DocumentReference resource"""
        document = MedicalDocument.query.get_or_404(document_id)
        fhir_document_ref = document_to_fhir(document)
        return jsonify(fhir_document_ref)
    
    @app.route('/fhir/DocumentReference')
    def get_fhir_document_references():
        """Get documents as FHIR DocumentReference Bundle"""
        from flask import request
        from datetime import datetime, date
        
        # Handle search by patient ID
        patient_id = request.args.get('subject')
        if patient_id and patient_id.startswith('Patient/'):
            patient_id = patient_id.split('/')[1]
            documents = MedicalDocument.query.filter_by(patient_id=int(patient_id)).all()
        # Handle search by document type
        elif request.args.get('type'):
            doc_type = request.args.get('type')
            documents = MedicalDocument.query.filter_by(document_type=doc_type).all()
        # Handle search by date
        elif request.args.get('date'):
            from datetime import timedelta
            try:
                search_date_str = request.args.get('date')
                search_date = datetime.strptime(search_date_str, '%Y-%m-%d').date()
                documents = MedicalDocument.query.filter(
                    MedicalDocument.document_date >= search_date,
                    MedicalDocument.document_date < search_date + timedelta(days=1)
                ).all()
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            # Return all documents
            documents = MedicalDocument.query.all()
        
        bundle = create_document_bundle(documents)
        return jsonify(bundle)