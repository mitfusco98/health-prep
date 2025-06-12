"""
FHIR Object Mappers

Comprehensive mapping functions to convert internal objects (Patient, Appointment, MedicalDocument) 
to FHIR-compliant resources for prep sheet logic and external API compatibility.

Supports:
- Patient → FHIR Patient resource
- Appointment → FHIR Encounter resource  
- MedicalDocument → FHIR DocumentReference resource
- Complete metadata preservation and bidirectional conversion
"""

import json
from datetime import datetime, date, time
from typing import Dict, List, Any, Optional, Union
from uuid import uuid4

# Import models for type checking
try:
    from models import Patient, Appointment, MedicalDocument, Condition, Vital, Immunization
except ImportError:
    # Handle cases where models might not be directly importable
    Patient = Appointment = MedicalDocument = Condition = Vital = Immunization = None


class FHIRObjectMapper:
    """Central mapper for converting internal objects to FHIR resources"""
    
    def __init__(self, base_url: str = "https://your-system.com/fhir"):
        self.base_url = base_url.rstrip('/')
        
    def generate_fhir_id(self, obj_type: str, internal_id: int) -> str:
        """Generate consistent FHIR resource IDs"""
        return f"{obj_type.lower()}-{internal_id}"
    
    def generate_reference(self, resource_type: str, internal_id: int) -> Dict[str, str]:
        """Generate FHIR reference"""
        fhir_id = self.generate_fhir_id(resource_type, internal_id)
        return {
            "reference": f"{resource_type}/{fhir_id}",
            "display": f"{resource_type} {internal_id}"
        }
    
    def format_fhir_datetime(self, dt: Union[datetime, date, time]) -> str:
        """Format datetime for FHIR compatibility"""
        if isinstance(dt, datetime):
            return dt.isoformat() + 'Z'
        elif isinstance(dt, date):
            return dt.isoformat()
        elif isinstance(dt, time):
            return dt.isoformat()
        return str(dt)
    
    def map_patient_to_fhir(self, patient) -> Dict[str, Any]:
        """
        Convert internal Patient object to FHIR Patient resource
        
        Args:
            patient: Internal Patient model instance
            
        Returns:
            FHIR Patient resource as dictionary
        """
        fhir_patient = {
            "resourceType": "Patient",
            "id": self.generate_fhir_id("Patient", patient.id),
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
                "lastUpdated": self.format_fhir_datetime(patient.updated_at or patient.created_at)
            },
            "identifier": [
                {
                    "use": "usual",
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical Record Number"
                        }]
                    },
                    "system": f"{self.base_url}/mrn",
                    "value": patient.mrn
                }
            ],
            "active": True,
            "name": [{
                "use": "official",
                "family": patient.last_name,
                "given": [patient.first_name]
            }],
            "gender": self._map_gender(patient.sex),
            "birthDate": self.format_fhir_datetime(patient.date_of_birth)
        }
        
        # Add contact information if available
        if patient.phone or patient.email:
            fhir_patient["telecom"] = []
            if patient.phone:
                fhir_patient["telecom"].append({
                    "system": "phone",
                    "value": patient.phone,
                    "use": "home"
                })
            if patient.email:
                fhir_patient["telecom"].append({
                    "system": "email",
                    "value": patient.email,
                    "use": "home"
                })
        
        # Add address if available
        if patient.address:
            fhir_patient["address"] = [{
                "use": "home",
                "type": "physical",
                "text": patient.address
            }]
        
        # Add insurance/coverage extension
        if patient.insurance:
            fhir_patient["extension"] = [{
                "url": f"{self.base_url}/StructureDefinition/insurance-info",
                "valueString": patient.insurance
            }]
        
        return fhir_patient
    
    def map_appointment_to_fhir_encounter(self, appointment) -> Dict[str, Any]:
        """
        Convert internal Appointment object to FHIR Encounter resource
        
        Args:
            appointment: Internal Appointment model instance
            
        Returns:
            FHIR Encounter resource as dictionary
        """
        # Combine date and time for proper datetime
        appointment_datetime = datetime.combine(
            appointment.appointment_date, 
            appointment.appointment_time
        )
        
        fhir_encounter = {
            "resourceType": "Encounter",
            "id": self.generate_fhir_id("Encounter", appointment.id),
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter"],
                "lastUpdated": self.format_fhir_datetime(appointment.updated_at or appointment.created_at)
            },
            "status": self._map_appointment_status(appointment.status),
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory"
            },
            "type": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "11429006",
                    "display": "Consultation"
                }],
                "text": "Outpatient Consultation"
            }],
            "subject": self.generate_reference("Patient", appointment.patient_id),
            "period": {
                "start": self.format_fhir_datetime(appointment_datetime)
            }
        }
        
        # Add appointment notes as reason if available
        if appointment.note:
            fhir_encounter["reasonCode"] = [{
                "text": appointment.note
            }]
        
        # Add service provider information
        fhir_encounter["serviceProvider"] = {
            "reference": f"Organization/{self.generate_fhir_id('Organization', 1)}",
            "display": "Primary Care Clinic"
        }
        
        return fhir_encounter
    
    def map_document_to_fhir_document_reference(self, document) -> Dict[str, Any]:
        """
        Convert internal MedicalDocument object to FHIR DocumentReference resource
        
        Args:
            document: Internal MedicalDocument model instance
            
        Returns:
            FHIR DocumentReference resource as dictionary
        """
        fhir_doc_ref = {
            "resourceType": "DocumentReference",
            "id": self.generate_fhir_id("DocumentReference", document.id),
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-documentreference"],
                "lastUpdated": self.format_fhir_datetime(document.updated_at or document.created_at)
            },
            "status": "current",
            "docStatus": "final",
            "type": self._map_document_type(document.document_type),
            "category": self._map_document_category(document.document_type),
            "subject": self.generate_reference("Patient", document.patient_id),
            "date": self.format_fhir_datetime(document.document_date or document.created_at),
            "author": self._get_document_author(document),
            "description": document.document_name or document.filename,
            "content": self._map_document_content(document)
        }
        
        # Add source system information
        if document.source_system:
            fhir_doc_ref["custodian"] = {
                "reference": f"Organization/{self.generate_fhir_id('Organization', 1)}",
                "display": document.source_system
            }
        
        # Add FHIR metadata from doc_metadata if available
        if document.doc_metadata:
            try:
                metadata = json.loads(document.doc_metadata)
                if 'fhir_primary_code' in metadata:
                    # Use existing FHIR codes from enhanced parser
                    fhir_doc_ref["type"] = metadata['fhir_primary_code']['code']
                    
                # Add custom extensions
                fhir_doc_ref["extension"] = [{
                    "url": f"{self.base_url}/StructureDefinition/document-metadata",
                    "valueString": json.dumps(metadata)
                }]
            except (json.JSONDecodeError, KeyError):
                pass
        
        return fhir_doc_ref
    
    def map_condition_to_fhir(self, condition) -> Dict[str, Any]:
        """
        Convert internal Condition object to FHIR Condition resource
        
        Args:
            condition: Internal Condition model instance
            
        Returns:
            FHIR Condition resource as dictionary
        """
        fhir_condition = {
            "resourceType": "Condition",
            "id": self.generate_fhir_id("Condition", condition.id),
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"],
                "lastUpdated": self.format_fhir_datetime(condition.updated_at or condition.created_at)
            },
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active" if condition.is_active else "inactive",
                    "display": "Active" if condition.is_active else "Inactive"
                }]
            },
            "verificationStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                    "display": "Confirmed"
                }]
            },
            "code": {
                "coding": self._get_condition_coding(condition),
                "text": condition.name
            },
            "subject": self.generate_reference("Patient", condition.patient_id)
        }
        
        # Add onset date if available
        if condition.diagnosed_date:
            fhir_condition["onsetDateTime"] = self.format_fhir_datetime(condition.diagnosed_date)
        
        # Add notes if available
        if condition.notes:
            fhir_condition["note"] = [{
                "text": condition.notes
            }]
        
        return fhir_condition
    
    def map_vital_to_fhir_observation(self, vital) -> List[Dict[str, Any]]:
        """
        Convert internal Vital object to FHIR Observation resources
        
        Args:
            vital: Internal Vital model instance
            
        Returns:
            List of FHIR Observation resources (one per vital sign)
        """
        observations = []
        
        # Map each vital sign to separate Observation resources
        vital_mappings = {
            'weight': {
                'code': '29463-7',
                'display': 'Body weight',
                'unit': 'kg',
                'value': vital.weight
            },
            'height': {
                'code': '8302-2',
                'display': 'Body height',
                'unit': 'cm',
                'value': vital.height
            },
            'bmi': {
                'code': '39156-5',
                'display': 'Body mass index (BMI) [Ratio]',
                'unit': 'kg/m2',
                'value': vital.bmi
            },
            'temperature': {
                'code': '8310-5',
                'display': 'Body temperature',
                'unit': 'Cel',
                'value': vital.temperature
            },
            'pulse': {
                'code': '8867-4',
                'display': 'Heart rate',
                'unit': '/min',
                'value': vital.pulse
            },
            'respiratory_rate': {
                'code': '9279-1',
                'display': 'Respiratory rate',
                'unit': '/min',
                'value': vital.respiratory_rate
            },
            'oxygen_saturation': {
                'code': '2708-6',
                'display': 'Oxygen saturation in Arterial blood',
                'unit': '%',
                'value': vital.oxygen_saturation
            }
        }
        
        # Create blood pressure observation separately (has systolic and diastolic components)
        if vital.blood_pressure_systolic and vital.blood_pressure_diastolic:
            bp_observation = {
                "resourceType": "Observation",
                "id": self.generate_fhir_id("Observation", f"{vital.id}-bp"),
                "meta": {
                    "profile": ["http://hl7.org/fhir/StructureDefinition/bp"]
                },
                "status": "final",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }]
                }],
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel with all children optional"
                    }]
                },
                "subject": self.generate_reference("Patient", vital.patient_id),
                "effectiveDateTime": self.format_fhir_datetime(vital.date),
                "component": [
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": vital.blood_pressure_systolic,
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    },
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": vital.blood_pressure_diastolic,
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    }
                ]
            }
            observations.append(bp_observation)
        
        # Create individual observations for other vital signs
        for vital_name, mapping in vital_mappings.items():
            if mapping['value'] is not None:
                observation = {
                    "resourceType": "Observation",
                    "id": self.generate_fhir_id("Observation", f"{vital.id}-{vital_name}"),
                    "meta": {
                        "profile": ["http://hl7.org/fhir/StructureDefinition/vitalsigns"]
                    },
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": mapping['code'],
                            "display": mapping['display']
                        }]
                    },
                    "subject": self.generate_reference("Patient", vital.patient_id),
                    "effectiveDateTime": self.format_fhir_datetime(vital.date),
                    "valueQuantity": {
                        "value": mapping['value'],
                        "unit": mapping['unit'],
                        "system": "http://unitsofmeasure.org"
                    }
                }
                observations.append(observation)
        
        return observations
    
    def map_immunization_to_fhir(self, immunization) -> Dict[str, Any]:
        """
        Convert internal Immunization object to FHIR Immunization resource
        
        Args:
            immunization: Internal Immunization model instance
            
        Returns:
            FHIR Immunization resource as dictionary
        """
        fhir_immunization = {
            "resourceType": "Immunization",
            "id": self.generate_fhir_id("Immunization", immunization.id),
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-immunization"],
                "lastUpdated": self.format_fhir_datetime(immunization.updated_at or immunization.created_at)
            },
            "status": "completed",
            "vaccineCode": {
                "coding": self._get_vaccine_coding(immunization.vaccine_name),
                "text": immunization.vaccine_name
            },
            "patient": self.generate_reference("Patient", immunization.patient_id),
            "occurrenceDateTime": self.format_fhir_datetime(immunization.administration_date),
            "primarySource": True
        }
        
        # Add dose number if available
        if immunization.dose_number:
            fhir_immunization["doseQuantity"] = {
                "value": immunization.dose_number,
                "unit": "dose"
            }
        
        # Add manufacturer and lot number if available
        if immunization.manufacturer or immunization.lot_number:
            fhir_immunization["lotNumber"] = immunization.lot_number
            if immunization.manufacturer:
                fhir_immunization["manufacturer"] = {
                    "display": immunization.manufacturer
                }
        
        # Add notes if available
        if immunization.notes:
            fhir_immunization["note"] = [{
                "text": immunization.notes
            }]
        
        return fhir_immunization
    
    def create_patient_bundle(self, patient, include_related: bool = True) -> Dict[str, Any]:
        """
        Create a comprehensive FHIR Bundle for a patient with all related resources
        
        Args:
            patient: Internal Patient model instance
            include_related: Whether to include related resources (conditions, vitals, etc.)
            
        Returns:
            FHIR Bundle resource containing patient and related data
        """
        bundle_entries = []
        
        # Add patient resource
        patient_resource = self.map_patient_to_fhir(patient)
        bundle_entries.append({
            "resource": patient_resource,
            "fullUrl": f"{self.base_url}/Patient/{patient_resource['id']}"
        })
        
        if include_related:
            # Add conditions
            for condition in getattr(patient, 'conditions', []):
                condition_resource = self.map_condition_to_fhir(condition)
                bundle_entries.append({
                    "resource": condition_resource,
                    "fullUrl": f"{self.base_url}/Condition/{condition_resource['id']}"
                })
            
            # Add vitals (as observations)
            for vital in getattr(patient, 'vitals', []):
                vital_observations = self.map_vital_to_fhir_observation(vital)
                for obs in vital_observations:
                    bundle_entries.append({
                        "resource": obs,
                        "fullUrl": f"{self.base_url}/Observation/{obs['id']}"
                    })
            
            # Add immunizations
            for immunization in getattr(patient, 'immunizations', []):
                immunization_resource = self.map_immunization_to_fhir(immunization)
                bundle_entries.append({
                    "resource": immunization_resource,
                    "fullUrl": f"{self.base_url}/Immunization/{immunization_resource['id']}"
                })
            
            # Add documents
            for document in getattr(patient, 'documents', []):
                document_resource = self.map_document_to_fhir_document_reference(document)
                bundle_entries.append({
                    "resource": document_resource,
                    "fullUrl": f"{self.base_url}/DocumentReference/{document_resource['id']}"
                })
        
        # Create bundle
        bundle = {
            "resourceType": "Bundle",
            "id": f"patient-{patient.id}-bundle",
            "meta": {
                "lastUpdated": self.format_fhir_datetime(datetime.utcnow())
            },
            "type": "collection",
            "total": len(bundle_entries),
            "entry": bundle_entries
        }
        
        return bundle
    
    # Helper methods for mapping specific fields
    
    def _map_gender(self, sex: str) -> str:
        """Map internal sex to FHIR gender"""
        mapping = {
            'Male': 'male',
            'Female': 'female',
            'Other': 'other',
            'Unknown': 'unknown'
        }
        return mapping.get(sex, 'unknown')
    
    def _map_appointment_status(self, status: str) -> str:
        """Map internal appointment status to FHIR encounter status"""
        mapping = {
            'OOO': 'planned',
            'waiting': 'arrived',
            'provider': 'in-progress',
            'seen': 'finished'
        }
        return mapping.get(status, 'planned')
    
    def _map_document_type(self, doc_type: str) -> Dict[str, Any]:
        """Map internal document type to FHIR coding"""
        type_mappings = {
            'Clinical Note': {
                'system': 'http://loinc.org',
                'code': '11506-3',
                'display': 'Progress note'
            },
            'Discharge Summary': {
                'system': 'http://loinc.org',
                'code': '18842-5',
                'display': 'Discharge summary'
            },
            'Lab Report': {
                'system': 'http://loinc.org',
                'code': '11502-2',
                'display': 'Laboratory report'
            },
            'Radiology Report': {
                'system': 'http://loinc.org',
                'code': '18748-4',
                'display': 'Diagnostic imaging study'
            },
            'Consultation': {
                'system': 'http://loinc.org',
                'code': '11488-4',
                'display': 'Consultation note'
            }
        }
        
        default_coding = {
            'system': 'http://loinc.org',
            'code': '34133-9',
            'display': 'Summarization of episode note'
        }
        
        coding = type_mappings.get(doc_type, default_coding)
        return {
            "coding": [coding],
            "text": doc_type
        }
    
    def _map_document_category(self, doc_type: str) -> List[Dict[str, Any]]:
        """Map document type to FHIR category"""
        category_mappings = {
            'Lab Report': 'laboratory',
            'Radiology Report': 'imaging',
            'Clinical Note': 'exam',
            'Discharge Summary': 'exam',
            'Consultation': 'exam'
        }
        
        category_code = category_mappings.get(doc_type, 'exam')
        return [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": category_code,
                "display": category_code.title()
            }]
        }]
    
    def _get_document_author(self, document) -> List[Dict[str, str]]:
        """Get document author information"""
        if document.provider:
            return [{
                "reference": f"Practitioner/{self.generate_fhir_id('Practitioner', 1)}",
                "display": document.provider
            }]
        return [{
            "reference": f"Organization/{self.generate_fhir_id('Organization', 1)}",
            "display": document.source_system or "Unknown System"
        }]
    
    def _map_document_content(self, document) -> List[Dict[str, Any]]:
        """Map document content for FHIR"""
        content = []
        
        if document.is_binary and document.binary_content:
            # Binary content (images, PDFs, etc.)
            content.append({
                "attachment": {
                    "contentType": document.mime_type or "application/octet-stream",
                    "size": len(document.binary_content) if document.binary_content else 0,
                    "title": document.document_name or document.filename,
                    "url": f"{self.base_url}/Binary/{self.generate_fhir_id('Binary', document.id)}"
                }
            })
        elif document.content:
            # Text content
            content.append({
                "attachment": {
                    "contentType": "text/plain",
                    "data": document.content.encode('utf-8').hex() if document.content else "",
                    "title": document.document_name or document.filename
                }
            })
        
        return content
    
    def _get_condition_coding(self, condition) -> List[Dict[str, str]]:
        """Get FHIR coding for condition"""
        coding = []
        
        if condition.code:
            # Assume ICD-10 if code provided
            coding.append({
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": condition.code,
                "display": condition.name
            })
        
        # Add SNOMED CT coding if available (this would require a mapping service)
        coding.append({
            "system": "http://snomed.info/sct",
            "display": condition.name
        })
        
        return coding
    
    def _get_vaccine_coding(self, vaccine_name: str) -> List[Dict[str, str]]:
        """Get FHIR coding for vaccine"""
        # Basic vaccine name to CVX code mapping
        vaccine_mappings = {
            'influenza': {'code': '141', 'display': 'Influenza, seasonal, injectable'},
            'flu': {'code': '141', 'display': 'Influenza, seasonal, injectable'},
            'covid': {'code': '208', 'display': 'COVID-19 vaccine'},
            'tdap': {'code': '115', 'display': 'Tdap'},
            'shingles': {'code': '187', 'display': 'Zoster vaccine recombinant'},
            'pneumonia': {'code': '133', 'display': 'Pneumococcal conjugate PCV 13'}
        }
        
        vaccine_lower = vaccine_name.lower()
        for key, mapping in vaccine_mappings.items():
            if key in vaccine_lower:
                return [{
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": mapping['code'],
                    "display": mapping['display']
                }]
        
        # Default if no mapping found
        return [{
            "system": "http://hl7.org/fhir/sid/cvx",
            "display": vaccine_name
        }]


# Global mapper instance
fhir_mapper = FHIRObjectMapper()

# Convenience functions for easy access
def patient_to_fhir(patient) -> Dict[str, Any]:
    """Convert Patient to FHIR Patient resource"""
    return fhir_mapper.map_patient_to_fhir(patient)

def appointment_to_fhir_encounter(appointment) -> Dict[str, Any]:
    """Convert Appointment to FHIR Encounter resource"""
    return fhir_mapper.map_appointment_to_fhir_encounter(appointment)

def document_to_fhir_document_reference(document) -> Dict[str, Any]:
    """Convert MedicalDocument to FHIR DocumentReference resource"""
    return fhir_mapper.map_document_to_fhir_document_reference(document)

def create_patient_fhir_bundle(patient, include_related: bool = True) -> Dict[str, Any]:
    """Create comprehensive FHIR Bundle for patient"""
    return fhir_mapper.create_patient_bundle(patient, include_related)

def condition_to_fhir(condition) -> Dict[str, Any]:
    """Convert Condition to FHIR Condition resource"""
    return fhir_mapper.map_condition_to_fhir(condition)

def vital_to_fhir_observations(vital) -> List[Dict[str, Any]]:
    """Convert Vital to FHIR Observation resources"""
    return fhir_mapper.map_vital_to_fhir_observation(vital)

def immunization_to_fhir(immunization) -> Dict[str, Any]:
    """Convert Immunization to FHIR Immunization resource"""
    return fhir_mapper.map_immunization_to_fhir(immunization)