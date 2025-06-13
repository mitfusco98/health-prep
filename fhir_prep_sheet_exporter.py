"""
FHIR Prep Sheet Exporter
Exports completed prep sheets as FHIR-compliant custom resources or Bundles
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from uuid import uuid4

from app import db
from models import Patient, Appointment, MedicalDocument, Condition, Vital, Immunization
from fhir_object_mappers import FHIRObjectMapper
from document_screening_matcher import generate_prep_sheet_screening_recommendations


class FHIRPrepSheetExporter:
    """
    Exports prep sheets as FHIR-compliant custom resources or standard Bundles
    """
    
    def __init__(self):
        self.fhir_mapper = FHIRObjectMapper()
        self.base_url = "http://example.org/fhir"
        
        # FHIR Resource Types for prep sheet components
        self.prep_sheet_profile = f"{self.base_url}/StructureDefinition/PrepSheet"
        self.screening_recommendation_profile = f"{self.base_url}/StructureDefinition/ScreeningRecommendation"
    
    def export_prep_sheet_as_custom_resource(self, patient_id: int, appointment_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Export prep sheet as a FHIR custom resource
        
        Args:
            patient_id: Patient ID
            appointment_id: Optional appointment ID
            
        Returns:
            FHIR custom PrepSheet resource
        """
        patient = Patient.query.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        
        appointment = None
        if appointment_id:
            appointment = Appointment.query.get(appointment_id)
        
        # Generate prep sheet data
        prep_data = self._generate_comprehensive_prep_data(patient_id, appointment_id)
        
        # Create custom FHIR resource
        prep_sheet_resource = {
            "resourceType": "PrepSheet",
            "id": f"prep-sheet-{patient_id}-{int(datetime.now().timestamp())}",
            "meta": {
                "profile": [self.prep_sheet_profile],
                "versionId": "1",
                "lastUpdated": datetime.now().isoformat() + "Z"
            },
            "identifier": [{
                "system": f"{self.base_url}/prep-sheet-id",
                "value": f"PREP-{patient_id}-{date.today().strftime('%Y%m%d')}"
            }],
            "status": "completed",
            "patient": {
                "reference": f"Patient/{patient_id}",
                "display": f"{patient.first_name} {patient.last_name}"
            },
            "encounter": {
                "reference": f"Encounter/{appointment_id}" if appointment_id else None,
                "display": f"Appointment on {appointment.appointment_date}" if appointment else "General Prep Sheet"
            } if appointment_id else None,
            "generatedDateTime": datetime.now().isoformat() + "Z",
            "generatedBy": {
                "system": "PrepSheet Generator",
                "version": "1.0"
            },
            
            # Custom prep sheet sections
            "demographics": self._create_demographics_section(patient),
            "medicalHistory": self._create_medical_history_section(patient_id),
            "screeningRecommendations": self._create_screening_recommendations_section(prep_data),
            "documentSummary": self._create_document_summary_section(patient_id),
            "vitalSigns": self._create_vital_signs_section(patient_id),
            "medications": self._create_medications_section(patient_id),
            "alerts": self._create_alerts_section(patient_id),
            
            # Extensions for additional prep sheet data
            "extension": [
                {
                    "url": f"{self.base_url}/extension/prep-sheet-metadata",
                    "valueString": json.dumps({
                        "document_based_recommendations": prep_data.get('document_count', 0),
                        "confidence_analysis": prep_data.get('summary', {}),
                        "generation_method": "automated_fhir_export"
                    })
                },
                {
                    "url": f"{self.base_url}/extension/prep-sheet-version",
                    "valueString": "2024.1"
                }
            ]
        }
        
        return prep_sheet_resource
    
    def export_prep_sheet_as_bundle(self, patient_id: int, appointment_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Export prep sheet as a FHIR Bundle with Patient, Encounter, and clinical resources
        
        Args:
            patient_id: Patient ID  
            appointment_id: Optional appointment ID
            
        Returns:
            FHIR Bundle containing all prep sheet components
        """
        patient = Patient.query.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        
        bundle_id = f"prep-sheet-bundle-{patient_id}-{int(datetime.now().timestamp())}"
        bundle_entries = []
        
        # 1. Patient resource
        fhir_patient = self.fhir_mapper.map_patient_to_fhir(patient)
        bundle_entries.append({
            "fullUrl": f"{self.base_url}/Patient/{patient_id}",
            "resource": fhir_patient
        })
        
        # 2. Encounter resource (if appointment exists)
        if appointment_id:
            appointment = Appointment.query.get(appointment_id)
            if appointment:
                fhir_encounter = self.fhir_mapper.map_appointment_to_fhir_encounter(appointment)
                bundle_entries.append({
                    "fullUrl": f"{self.base_url}/Encounter/{appointment_id}",
                    "resource": fhir_encounter
                })
        
        # 3. Condition resources
        conditions = Condition.query.filter_by(patient_id=patient_id, is_active=True).all()
        for condition in conditions:
            fhir_condition = self.fhir_mapper.map_condition_to_fhir(condition)
            bundle_entries.append({
                "fullUrl": f"{self.base_url}/Condition/{condition.id}",
                "resource": fhir_condition
            })
        
        # 4. Observation resources (Vitals)
        vitals = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.recorded_date.desc()).limit(10).all()
        for vital in vitals:
            fhir_observation = self.fhir_mapper.map_vital_to_fhir_observation(vital)
            bundle_entries.append({
                "fullUrl": f"{self.base_url}/Observation/{vital.id}",
                "resource": fhir_observation
            })
        
        # 5. Immunization resources
        immunizations = Immunization.query.filter_by(patient_id=patient_id).all()
        for immunization in immunizations:
            fhir_immunization = self.fhir_mapper.map_immunization_to_fhir(immunization)
            bundle_entries.append({
                "fullUrl": f"{self.base_url}/Immunization/{immunization.id}",
                "resource": fhir_immunization
            })
        
        # 6. DocumentReference resources
        documents = MedicalDocument.query.filter_by(patient_id=patient_id).order_by(MedicalDocument.created_at.desc()).limit(20).all()
        for document in documents:
            fhir_doc_ref = self.fhir_mapper.map_document_to_fhir_document_reference(document)
            bundle_entries.append({
                "fullUrl": f"{self.base_url}/DocumentReference/{document.id}",
                "resource": fhir_doc_ref
            })
        
        # 7. Screening Recommendation resources (custom)
        prep_data = self._generate_comprehensive_prep_data(patient_id, appointment_id)
        for rec in prep_data.get('screening_recommendations', []):
            screening_resource = self._create_screening_recommendation_resource(rec, patient_id)
            rec_id = f"screening-rec-{rec['screening_type_id']}-{int(datetime.now().timestamp())}"
            bundle_entries.append({
                "fullUrl": f"{self.base_url}/ScreeningRecommendation/{rec_id}",
                "resource": screening_resource
            })
        
        # Create Bundle
        bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "meta": {
                "profile": [f"{self.base_url}/StructureDefinition/PrepSheetBundle"],
                "lastUpdated": datetime.now().isoformat() + "Z"
            },
            "identifier": {
                "system": f"{self.base_url}/bundle-id",
                "value": f"BUNDLE-PREP-{patient_id}-{date.today().strftime('%Y%m%d')}"
            },
            "type": "collection",
            "timestamp": datetime.now().isoformat() + "Z",
            "total": len(bundle_entries),
            "entry": bundle_entries
        }
        
        return bundle
    
    def export_prep_sheet_for_epic_integration(self, patient_id: int, appointment_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Export prep sheet optimized for Epic EHR integration
        
        Args:
            patient_id: Patient ID
            appointment_id: Optional appointment ID
            
        Returns:
            Epic-optimized FHIR Bundle
        """
        bundle = self.export_prep_sheet_as_bundle(patient_id, appointment_id)
        
        # Add Epic-specific metadata
        bundle["meta"]["tag"] = [
            {
                "system": "http://epic.com/fhir/category",
                "code": "prep-sheet",
                "display": "Visit Preparation Sheet"
            }
        ]
        
        # Add Epic encounter class if appointment exists
        if appointment_id:
            for entry in bundle["entry"]:
                if entry["resource"].get("resourceType") == "Encounter":
                    entry["resource"]["class"] = {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                        "display": "ambulatory"
                    }
        
        return bundle
    
    def _generate_comprehensive_prep_data(self, patient_id: int, appointment_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate comprehensive prep sheet data including document matching"""
        return generate_prep_sheet_screening_recommendations(patient_id, enable_ai_fuzzy=True)
    
    def _create_demographics_section(self, patient: Patient) -> Dict[str, Any]:
        """Create demographics section for custom prep sheet resource"""
        return {
            "name": f"{patient.first_name} {patient.last_name}",
            "mrn": patient.mrn,
            "dateOfBirth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "age": patient.age,
            "gender": getattr(patient, 'gender', 'unknown'),
            "contact": {
                "phone": patient.phone_number,
                "email": patient.email,
                "address": {
                    "street": patient.address,
                    "city": patient.city,
                    "state": patient.state,
                    "zipCode": patient.zip_code
                }
            }
        }
    
    def _create_medical_history_section(self, patient_id: int) -> Dict[str, Any]:
        """Create medical history section"""
        conditions = Condition.query.filter_by(patient_id=patient_id, is_active=True).all()
        
        return {
            "activeConditions": [
                {
                    "name": condition.name,
                    "code": condition.code,
                    "diagnosedDate": condition.diagnosed_date.isoformat() if condition.diagnosed_date else None,
                    "status": "active" if condition.is_active else "inactive"
                }
                for condition in conditions
            ],
            "conditionCount": len(conditions)
        }
    
    def _create_screening_recommendations_section(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create screening recommendations section"""
        recommendations = prep_data.get('screening_recommendations', [])
        
        return {
            "totalRecommendations": len(recommendations),
            "highPriorityCount": sum(1 for r in recommendations if r.get('recommendation_priority') == 'high'),
            "documentBasedCount": prep_data.get('document_count', 0),
            "recommendations": [
                {
                    "screeningName": rec['screening_name'],
                    "priority": rec['recommendation_priority'],
                    "confidence": rec['confidence'],
                    "sources": rec['match_sources'],
                    "supportingDocuments": rec['total_document_matches'],
                    "evidence": {
                        "codes": rec['matched_codes'],
                        "keywords": rec['matched_keywords']
                    }
                }
                for rec in recommendations[:10]  # Top 10 recommendations
            ]
        }
    
    def _create_document_summary_section(self, patient_id: int) -> Dict[str, Any]:
        """Create document summary section"""
        documents = MedicalDocument.query.filter_by(patient_id=patient_id).order_by(MedicalDocument.created_at.desc()).limit(10).all()
        
        return {
            "totalDocuments": len(documents),
            "recentDocuments": [
                {
                    "name": doc.filename or doc.document_name,
                    "type": doc.document_type,
                    "date": doc.created_at.isoformat() if doc.created_at else None,
                    "processed": doc.is_processed
                }
                for doc in documents
            ]
        }
    
    def _create_vital_signs_section(self, patient_id: int) -> Dict[str, Any]:
        """Create vital signs section"""
        recent_vitals = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.recorded_date.desc()).limit(5).all()
        
        return {
            "recentVitals": [
                {
                    "date": vital.recorded_date.isoformat() if vital.recorded_date else None,
                    "height": vital.height,
                    "weight": vital.weight,
                    "bmi": vital.bmi,
                    "bloodPressure": {
                        "systolic": vital.blood_pressure_systolic,
                        "diastolic": vital.blood_pressure_diastolic
                    },
                    "heartRate": vital.heart_rate,
                    "temperature": vital.temperature
                }
                for vital in recent_vitals
            ]
        }
    
    def _create_medications_section(self, patient_id: int) -> Dict[str, Any]:
        """Create medications section"""
        # This would integrate with your medication model if available
        return {
            "activeMedications": [],
            "medicationCount": 0,
            "note": "Medication integration not implemented"
        }
    
    def _create_alerts_section(self, patient_id: int) -> Dict[str, Any]:
        """Create alerts section"""
        # This would integrate with your alerts model if available
        return {
            "activeAlerts": [],
            "alertCount": 0
        }
    
    def _create_screening_recommendation_resource(self, recommendation: Dict[str, Any], patient_id: int) -> Dict[str, Any]:
        """Create a custom ScreeningRecommendation FHIR resource"""
        return {
            "resourceType": "ScreeningRecommendation",
            "id": f"screening-rec-{recommendation['screening_type_id']}-{int(datetime.now().timestamp())}",
            "meta": {
                "profile": [self.screening_recommendation_profile]
            },
            "status": "active",
            "patient": {
                "reference": f"Patient/{patient_id}"
            },
            "recommendation": {
                "code": {
                    "text": recommendation['screening_name']
                },
                "priority": recommendation['recommendation_priority'],
                "confidence": recommendation['confidence'],
                "confidenceLevel": "high" if recommendation['confidence'] >= 0.8 else "medium" if recommendation['confidence'] >= 0.5 else "low"
            },
            "evidence": {
                "documentMatches": recommendation['total_document_matches'],
                "matchSources": recommendation['match_sources'],
                "matchedCodes": recommendation['matched_codes'],
                "matchedKeywords": recommendation['matched_keywords']
            },
            "generatedDateTime": datetime.now().isoformat() + "Z"
        }


def export_patient_prep_sheet(patient_id: int, appointment_id: Optional[int] = None, format_type: str = "bundle") -> Dict[str, Any]:
    """
    Convenience function to export prep sheet in specified format
    
    Args:
        patient_id: Patient ID
        appointment_id: Optional appointment ID
        format_type: "custom", "bundle", or "epic"
        
    Returns:
        FHIR-compliant prep sheet export
    """
    exporter = FHIRPrepSheetExporter()
    
    if format_type == "custom":
        return exporter.export_prep_sheet_as_custom_resource(patient_id, appointment_id)
    elif format_type == "bundle":
        return exporter.export_prep_sheet_as_bundle(patient_id, appointment_id)
    elif format_type == "epic":
        return exporter.export_prep_sheet_for_epic_integration(patient_id, appointment_id)
    else:
        raise ValueError(f"Unsupported format type: {format_type}")


def validate_fhir_export(fhir_resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate FHIR export structure and content
    
    Args:
        fhir_resource: FHIR resource or Bundle to validate
        
    Returns:
        Validation results
    """
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "resource_count": 0,
        "resource_types": []
    }
    
    # Basic structure validation
    if "resourceType" not in fhir_resource:
        validation_results["valid"] = False
        validation_results["errors"].append("Missing resourceType")
        return validation_results
    
    resource_type = fhir_resource["resourceType"]
    validation_results["resource_types"].append(resource_type)
    
    if resource_type == "Bundle":
        # Validate Bundle structure
        if "entry" not in fhir_resource:
            validation_results["errors"].append("Bundle missing entry array")
        else:
            validation_results["resource_count"] = len(fhir_resource["entry"])
            
            # Validate each entry
            for i, entry in enumerate(fhir_resource["entry"]):
                if "resource" not in entry:
                    validation_results["errors"].append(f"Entry {i} missing resource")
                elif "resourceType" not in entry["resource"]:
                    validation_results["errors"].append(f"Entry {i} resource missing resourceType")
                else:
                    entry_type = entry["resource"]["resourceType"]
                    if entry_type not in validation_results["resource_types"]:
                        validation_results["resource_types"].append(entry_type)
    else:
        validation_results["resource_count"] = 1
    
    # Check for required fields
    required_fields = ["id", "meta"]
    for field in required_fields:
        if field not in fhir_resource:
            validation_results["warnings"].append(f"Missing recommended field: {field}")
    
    if validation_results["errors"]:
        validation_results["valid"] = False
    
    return validation_results


# Example usage and testing functions
def demo_fhir_prep_sheet_export():
    """Demonstrate FHIR prep sheet export functionality"""
    from app import app
    
    with app.app_context():
        # Get a patient for testing
        patient = Patient.query.first()
        
        if patient:
            print(f"Exporting prep sheet for: {patient.first_name} {patient.last_name}")
            
            # Test custom resource export
            custom_resource = export_patient_prep_sheet(patient.id, format_type="custom")
            print(f"Custom Resource: {custom_resource['resourceType']} with {len(custom_resource.get('extension', []))} extensions")
            
            # Test bundle export
            bundle = export_patient_prep_sheet(patient.id, format_type="bundle")
            print(f"Bundle: {bundle['total']} resources included")
            
            # Test Epic export
            epic_bundle = export_patient_prep_sheet(patient.id, format_type="epic")
            print(f"Epic Bundle: Optimized for Epic EHR integration")
            
            # Validate exports
            bundle_validation = validate_fhir_export(bundle)
            print(f"Bundle validation: {'✓ Valid' if bundle_validation['valid'] else '✗ Invalid'}")
            print(f"Resource types: {bundle_validation['resource_types']}")
            
        else:
            print("No patients available for demo")


if __name__ == "__main__":
    demo_fhir_prep_sheet_export()