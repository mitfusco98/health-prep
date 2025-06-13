"""
FHIR Prep Sheet Integration

Integration functions that use FHIR-compliant resources for prep sheet logic
and external API compatibility. Converts internal objects to standardized
FHIR format for consistent data exchange.
"""

import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from fhir_object_mappers import (
    fhir_mapper,
    patient_to_fhir,
    appointment_to_fhir_encounter,
    document_to_fhir_document_reference,
    create_patient_fhir_bundle
)
from screening_rules import (
    apply_screening_rules,
    SCREENING_TYPES_CONFIG,
    create_fhir_screening_recommendation
)

try:
    from models import Patient, Appointment, MedicalDocument
    from fhir_condition_screening_matcher import ConditionScreeningMatcher, add_condition_triggered_screenings_to_prep_sheet
except ImportError:
    Patient = Appointment = MedicalDocument = None


class FHIRPrepSheetGenerator:
    """
    Generate prep sheets using FHIR-compliant patient data and screening recommendations
    """
    
    def __init__(self):
        self.mapper = fhir_mapper
    
    def generate_fhir_prep_sheet_data(self, patient, appointment_date: date) -> Dict[str, Any]:
        """
        Generate comprehensive prep sheet data in FHIR format
        
        Args:
            patient: Internal Patient object
            appointment_date: Date of upcoming appointment
            
        Returns:
            Dictionary containing FHIR-formatted prep sheet data
        """
        # Convert patient to FHIR
        fhir_patient = patient_to_fhir(patient)
        
        # Get patient conditions for screening rules
        condition_names = [condition.name.lower() for condition in getattr(patient, 'conditions', [])]
        
        # Generate FHIR screening recommendations
        screening_recommendations = apply_screening_rules(patient, condition_names)
        
        # Get recent appointments as FHIR encounters
        recent_appointments = self._get_recent_appointments_as_fhir(patient, appointment_date)
        
        # Get relevant documents as FHIR document references
        relevant_documents = self._get_relevant_documents_as_fhir(patient, appointment_date)
        
        # Get current medications and conditions as FHIR resources
        current_conditions = self._get_conditions_as_fhir(patient)
        current_vitals = self._get_recent_vitals_as_fhir(patient)
        immunization_history = self._get_immunizations_as_fhir(patient)
        
        # Compile prep sheet data
        prep_sheet_data = {
            "resourceType": "Bundle",
            "id": f"prep-sheet-{patient.id}-{appointment_date}",
            "meta": {
                "lastUpdated": datetime.utcnow().isoformat() + 'Z',
                "profile": ["http://your-system.com/fhir/StructureDefinition/prep-sheet-bundle"]
            },
            "type": "document",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "entry": [
                {
                    "resource": {
                        "resourceType": "Composition",
                        "id": f"prep-sheet-composition-{patient.id}",
                        "status": "final",
                        "type": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "11506-3",
                                "display": "Preparation sheet"
                            }]
                        },
                        "subject": {
                            "reference": f"Patient/{fhir_patient['id']}",
                            "display": f"{patient.first_name} {patient.last_name}"
                        },
                        "date": datetime.utcnow().isoformat() + 'Z',
                        "author": [{
                            "reference": "Organization/prep-sheet-system",
                            "display": "Automated Prep Sheet System"
                        }],
                        "title": f"Preparation Sheet for {patient.first_name} {patient.last_name}",
                        "section": [
                            {
                                "title": "Patient Information",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "29762-2",
                                        "display": "Social history"
                                    }]
                                },
                                "entry": [{"reference": f"Patient/{fhir_patient['id']}"}]
                            },
                            {
                                "title": "Recommended Screenings",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "75492-9",
                                        "display": "Preventive care note"
                                    }]
                                },
                                "entry": [{"reference": f"ServiceRequest/{rec['id']}"} for rec in screening_recommendations]
                            },
                            {
                                "title": "Recent Encounters",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "46240-8",
                                        "display": "History of encounters"
                                    }]
                                },
                                "entry": [{"reference": f"Encounter/{enc['id']}"} for enc in recent_appointments]
                            },
                            {
                                "title": "Current Conditions",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "11450-4",
                                        "display": "Problem list"
                                    }]
                                },
                                "entry": [{"reference": f"Condition/{cond['id']}"} for cond in current_conditions]
                            },
                            {
                                "title": "Recent Vitals",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "8716-3",
                                        "display": "Vital signs"
                                    }]
                                },
                                "entry": [{"reference": f"Observation/{obs['id']}"} for obs_list in current_vitals for obs in obs_list]
                            },
                            {
                                "title": "Immunization History",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "11369-6",
                                        "display": "History of immunization"
                                    }]
                                },
                                "entry": [{"reference": f"Immunization/{imm['id']}"} for imm in immunization_history]
                            },
                            {
                                "title": "Relevant Documents",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "18842-5",
                                        "display": "Relevant documents"
                                    }]
                                },
                                "entry": [{"reference": f"DocumentReference/{doc['id']}"} for doc in relevant_documents]
                            }
                        ]
                    }
                },
                {"resource": fhir_patient}
            ]
        }
        
        # Add all referenced resources to bundle
        for rec in screening_recommendations:
            prep_sheet_data["entry"].append({"resource": rec})
        
        for enc in recent_appointments:
            prep_sheet_data["entry"].append({"resource": enc})
        
        for cond in current_conditions:
            prep_sheet_data["entry"].append({"resource": cond})
        
        for obs_list in current_vitals:
            for obs in obs_list:
                prep_sheet_data["entry"].append({"resource": obs})
        
        for imm in immunization_history:
            prep_sheet_data["entry"].append({"resource": imm})
        
        for doc in relevant_documents:
            prep_sheet_data["entry"].append({"resource": doc})
        
        return prep_sheet_data
    
    def generate_screening_summary_fhir(self, patient) -> Dict[str, Any]:
        """
        Generate FHIR-formatted screening summary for prep sheet
        
        Args:
            patient: Internal Patient object
            
        Returns:
            FHIR Bundle with screening recommendations organized by category
        """
        condition_names = [condition.name.lower() for condition in getattr(patient, 'conditions', [])]
        recommendations = apply_screening_rules(patient, condition_names)
        
        # Group recommendations by document section
        sections = {}
        for rec in recommendations:
            # Find the document section for this recommendation
            section = None
            for screening_id, config in SCREENING_TYPES_CONFIG.items():
                if config['code']['coding'][0]['code'] == rec['code']['coding'][0]['code']:
                    section = config['document_section']
                    break
            
            if section:
                if section not in sections:
                    sections[section] = []
                sections[section].append(rec)
        
        # Create screening summary bundle
        summary_bundle = {
            "resourceType": "Bundle",
            "id": f"screening-summary-{patient.id}",
            "type": "collection",
            "total": len(recommendations),
            "entry": []
        }
        
        # Add recommendations grouped by category
        for section_name, section_recs in sections.items():
            for rec in section_recs:
                summary_bundle["entry"].append({
                    "resource": rec,
                    "fullUrl": f"ServiceRequest/{rec['id']}"
                })
        
        return summary_bundle
    
    def _get_recent_appointments_as_fhir(self, patient, current_date: date, days_back: int = 90) -> List[Dict[str, Any]]:
        """Get recent appointments as FHIR Encounter resources"""
        encounters = []
        cutoff_date = current_date - timedelta(days=days_back)
        
        # Get appointments from the last 90 days
        recent_appointments = []
        for appointment in getattr(patient, 'appointments', []):
            if appointment.appointment_date >= cutoff_date and appointment.appointment_date < current_date:
                recent_appointments.append(appointment)
        
        # Convert to FHIR encounters
        for appointment in recent_appointments:
            encounter = appointment_to_fhir_encounter(appointment)
            encounters.append(encounter)
        
        return encounters
    
    def _get_relevant_documents_as_fhir(self, patient, appointment_date: date, days_back: int = 180) -> List[Dict[str, Any]]:
        """Get relevant documents as FHIR DocumentReference resources"""
        document_refs = []
        cutoff_date = appointment_date - timedelta(days=days_back)
        
        # Get documents from the last 6 months
        relevant_docs = []
        for document in getattr(patient, 'documents', []):
            doc_date = document.document_date or document.created_at
            if doc_date and doc_date.date() >= cutoff_date:
                relevant_docs.append(document)
        
        # Convert to FHIR document references
        for document in relevant_docs:
            doc_ref = document_to_fhir_document_reference(document)
            document_refs.append(doc_ref)
        
        return document_refs
    
    def _get_conditions_as_fhir(self, patient) -> List[Dict[str, Any]]:
        """Get active conditions as FHIR Condition resources"""
        conditions = []
        
        for condition in getattr(patient, 'conditions', []):
            if condition.is_active:
                fhir_condition = self.mapper.map_condition_to_fhir(condition)
                conditions.append(fhir_condition)
        
        return conditions
    
    def _get_recent_vitals_as_fhir(self, patient, days_back: int = 30) -> List[List[Dict[str, Any]]]:
        """Get recent vitals as FHIR Observation resources"""
        vitals_observations = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Get vitals from the last 30 days
        recent_vitals = []
        for vital in getattr(patient, 'vitals', []):
            if vital.date >= cutoff_date:
                recent_vitals.append(vital)
        
        # Convert to FHIR observations
        for vital in recent_vitals:
            observations = self.mapper.map_vital_to_fhir_observation(vital)
            vitals_observations.append(observations)
        
        return vitals_observations
    
    def _get_immunizations_as_fhir(self, patient) -> List[Dict[str, Any]]:
        """Get immunizations as FHIR Immunization resources"""
        immunizations = []
        
        for immunization in getattr(patient, 'immunizations', []):
            fhir_immunization = self.mapper.map_immunization_to_fhir(immunization)
            immunizations.append(fhir_immunization)
        
        return immunizations


class FHIRExternalAPIAdapter:
    """
    Adapter for external API compatibility using FHIR resources
    """
    
    def __init__(self):
        self.mapper = fhir_mapper
    
    def export_patient_fhir_bundle(self, patient_id: int, include_documents: bool = True) -> Dict[str, Any]:
        """
        Export complete patient data as FHIR Bundle for external APIs
        
        Args:
            patient_id: Patient ID
            include_documents: Whether to include document content
            
        Returns:
            Complete FHIR Bundle ready for external API consumption
        """
        # This would typically query the database
        # For now, we'll show the structure
        
        try:
            # Query patient with relationships
            patient = Patient.query.options(
                db.joinedload(Patient.conditions),
                db.joinedload(Patient.vitals),
                db.joinedload(Patient.immunizations),
                db.joinedload(Patient.documents)
            ).get(patient_id)
            
            if not patient:
                return {"error": "Patient not found"}
            
            # Create comprehensive FHIR bundle
            bundle = create_patient_fhir_bundle(patient, include_related=True)
            
            # Add API metadata
            bundle["meta"]["tag"] = [{
                "system": "http://your-system.com/fhir/tags",
                "code": "external-api-export",
                "display": "External API Export"
            }]
            
            # Remove binary content if requested
            if not include_documents:
                for entry in bundle["entry"]:
                    if entry["resource"]["resourceType"] == "DocumentReference":
                        # Remove actual content, keep metadata
                        if "content" in entry["resource"]:
                            for content in entry["resource"]["content"]:
                                if "attachment" in content and "data" in content["attachment"]:
                                    del content["attachment"]["data"]
            
            return bundle
            
        except Exception as e:
            return {"error": f"Failed to export patient data: {str(e)}"}
    
    def get_patient_fhir_resource(self, patient_id: int) -> Dict[str, Any]:
        """
        Get individual patient as FHIR Patient resource
        
        Args:
            patient_id: Patient ID
            
        Returns:
            FHIR Patient resource
        """
        try:
            patient = Patient.query.get(patient_id)
            if not patient:
                return {"error": "Patient not found"}
            
            return patient_to_fhir(patient)
        except Exception as e:
            return {"error": f"Failed to get patient: {str(e)}"}
    
    def get_appointment_fhir_encounter(self, appointment_id: int) -> Dict[str, Any]:
        """
        Get appointment as FHIR Encounter resource
        
        Args:
            appointment_id: Appointment ID
            
        Returns:
            FHIR Encounter resource
        """
        try:
            appointment = Appointment.query.get(appointment_id)
            if not appointment:
                return {"error": "Appointment not found"}
            
            return appointment_to_fhir_encounter(appointment)
        except Exception as e:
            return {"error": f"Failed to get appointment: {str(e)}"}
    
    def get_document_fhir_reference(self, document_id: int, include_content: bool = False) -> Dict[str, Any]:
        """
        Get document as FHIR DocumentReference resource
        
        Args:
            document_id: Document ID
            include_content: Whether to include actual content
            
        Returns:
            FHIR DocumentReference resource
        """
        try:
            document = MedicalDocument.query.get(document_id)
            if not document:
                return {"error": "Document not found"}
            
            doc_ref = document_to_fhir_document_reference(document)
            
            # Remove content if not requested
            if not include_content and "content" in doc_ref:
                for content in doc_ref["content"]:
                    if "attachment" in content and "data" in content["attachment"]:
                        del content["attachment"]["data"]
            
            return doc_ref
        except Exception as e:
            return {"error": f"Failed to get document: {str(e)}"}
    
    def search_patients_fhir(self, search_params: Dict[str, str]) -> Dict[str, Any]:
        """
        Search patients and return FHIR Bundle
        
        Args:
            search_params: Search parameters (name, birthdate, identifier, etc.)
            
        Returns:
            FHIR Bundle with search results
        """
        try:
            # Build query based on search parameters
            query = Patient.query
            
            if 'name' in search_params:
                name = search_params['name'].lower()
                query = query.filter(
                    db.or_(
                        Patient.first_name.ilike(f'%{name}%'),
                        Patient.last_name.ilike(f'%{name}%')
                    )
                )
            
            if 'birthdate' in search_params:
                query = query.filter(Patient.date_of_birth == search_params['birthdate'])
            
            if 'identifier' in search_params:
                query = query.filter(Patient.mrn == search_params['identifier'])
            
            patients = query.limit(50).all()  # Limit results
            
            # Create search results bundle
            bundle = {
                "resourceType": "Bundle",
                "id": f"patient-search-{datetime.now().isoformat()}",
                "type": "searchset",
                "total": len(patients),
                "entry": []
            }
            
            for patient in patients:
                fhir_patient = patient_to_fhir(patient)
                bundle["entry"].append({
                    "resource": fhir_patient,
                    "fullUrl": f"{self.mapper.base_url}/Patient/{fhir_patient['id']}",
                    "search": {"mode": "match"}
                })
            
            return bundle
            
        except Exception as e:
            return {"error": f"Failed to search patients: {str(e)}"}


# Global instances
fhir_prep_sheet_generator = FHIRPrepSheetGenerator()
fhir_external_api_adapter = FHIRExternalAPIAdapter()

# Convenience functions
def generate_fhir_prep_sheet(patient, appointment_date: date) -> Dict[str, Any]:
    """Generate FHIR-compliant prep sheet data"""
    return fhir_prep_sheet_generator.generate_fhir_prep_sheet_data(patient, appointment_date)

def export_patient_as_fhir_bundle(patient_id: int, include_documents: bool = True) -> Dict[str, Any]:
    """Export patient data as FHIR Bundle for external APIs"""
    return fhir_external_api_adapter.export_patient_fhir_bundle(patient_id, include_documents)

def search_patients_as_fhir(search_params: Dict[str, str]) -> Dict[str, Any]:
    """Search patients and return FHIR Bundle"""
    return fhir_external_api_adapter.search_patients_fhir(search_params)