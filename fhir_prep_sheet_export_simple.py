"""
Simplified FHIR Prep Sheet Export
Works with existing database schema - exports prep sheets as FHIR-compliant resources
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, date

from app import db
from models import Patient, Appointment, MedicalDocument, Condition
from fhir_object_mappers import FHIRObjectMapper
from document_screening_matcher import generate_prep_sheet_screening_recommendations


def export_prep_sheet_as_custom_resource(patient_id: int, appointment_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Export prep sheet as FHIR custom resource
    
    Args:
        patient_id: Patient ID
        appointment_id: Optional appointment ID
        
    Returns:
        FHIR custom PrepSheet resource
    """
    patient = Patient.query.get(patient_id)
    if not patient:
        raise ValueError(f"Patient {patient_id} not found")
    
    # Generate prep sheet data
    prep_data = generate_prep_sheet_screening_recommendations(patient_id, enable_ai_fuzzy=True)
    
    # Get basic patient data
    patient_name = f"{patient.first_name} {patient.last_name}"
    
    # Create custom FHIR resource
    prep_sheet_resource = {
        "resourceType": "PrepSheet",
        "id": f"prep-sheet-{patient_id}-{int(datetime.now().timestamp())}",
        "meta": {
            "profile": ["http://example.org/fhir/StructureDefinition/PrepSheet"],
            "versionId": "1",
            "lastUpdated": datetime.now().isoformat() + "Z"
        },
        "identifier": [{
            "system": "http://example.org/fhir/prep-sheet-id",
            "value": f"PREP-{patient_id}-{date.today().strftime('%Y%m%d')}"
        }],
        "status": "completed",
        "patient": {
            "reference": f"Patient/{patient_id}",
            "display": patient_name
        },
        "generatedDateTime": datetime.now().isoformat() + "Z",
        
        # Core prep sheet data
        "demographics": {
            "name": patient_name,
            "mrn": patient.mrn,
            "dateOfBirth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "age": patient.age
        },
        
        "medicalHistory": _get_medical_history_section(patient_id),
        "screeningRecommendations": _get_screening_recommendations_section(prep_data),
        "documentSummary": _get_document_summary_section(patient_id),
        
        # Extensions with prep sheet metadata
        "extension": [
            {
                "url": "http://example.org/fhir/extension/prep-sheet-metadata",
                "valueString": json.dumps({
                    "document_count": prep_data.get('document_count', 0),
                    "total_recommendations": len(prep_data.get('screening_recommendations', [])),
                    "generation_method": "fhir_export"
                })
            }
        ]
    }
    
    return prep_sheet_resource


def export_prep_sheet_as_bundle(patient_id: int, appointment_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Export prep sheet as FHIR Bundle with Patient, Encounter, and clinical resources
    
    Args:
        patient_id: Patient ID
        appointment_id: Optional appointment ID
        
    Returns:
        FHIR Bundle containing prep sheet components
    """
    patient = Patient.query.get(patient_id)
    if not patient:
        raise ValueError(f"Patient {patient_id} not found")
    
    fhir_mapper = FHIRObjectMapper()
    bundle_entries = []
    
    # 1. Patient resource
    fhir_patient = fhir_mapper.map_patient_to_fhir(patient)
    bundle_entries.append({
        "fullUrl": f"http://example.org/fhir/Patient/{patient_id}",
        "resource": fhir_patient
    })
    
    # 2. Encounter resource (if appointment exists)
    if appointment_id:
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            fhir_encounter = fhir_mapper.map_appointment_to_fhir_encounter(appointment)
            bundle_entries.append({
                "fullUrl": f"http://example.org/fhir/Encounter/{appointment_id}",
                "resource": fhir_encounter
            })
    
    # 3. Condition resources
    conditions = Condition.query.filter_by(patient_id=patient_id, is_active=True).all()
    for condition in conditions:
        fhir_condition = fhir_mapper.map_condition_to_fhir(condition)
        bundle_entries.append({
            "fullUrl": f"http://example.org/fhir/Condition/{condition.id}",
            "resource": fhir_condition
        })
    
    # 4. DocumentReference resources
    documents = MedicalDocument.query.filter_by(patient_id=patient_id).order_by(MedicalDocument.created_at.desc()).limit(10).all()
    for document in documents:
        fhir_doc_ref = fhir_mapper.map_document_to_fhir_document_reference(document)
        bundle_entries.append({
            "fullUrl": f"http://example.org/fhir/DocumentReference/{document.id}",
            "resource": fhir_doc_ref
        })
    
    # 5. Screening Recommendation resources (custom)
    prep_data = generate_prep_sheet_screening_recommendations(patient_id, enable_ai_fuzzy=True)
    for i, rec in enumerate(prep_data.get('screening_recommendations', [])):
        screening_resource = _create_screening_recommendation_resource(rec, patient_id, i)
        bundle_entries.append({
            "fullUrl": f"http://example.org/fhir/ScreeningRecommendation/{rec['screening_type_id']}-{i}",
            "resource": screening_resource
        })
    
    # Create Bundle
    bundle_id = f"prep-sheet-bundle-{patient_id}-{int(datetime.now().timestamp())}"
    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {
            "profile": ["http://example.org/fhir/StructureDefinition/PrepSheetBundle"],
            "lastUpdated": datetime.now().isoformat() + "Z"
        },
        "identifier": {
            "system": "http://example.org/fhir/bundle-id",
            "value": f"BUNDLE-PREP-{patient_id}-{date.today().strftime('%Y%m%d')}"
        },
        "type": "collection",
        "timestamp": datetime.now().isoformat() + "Z",
        "total": len(bundle_entries),
        "entry": bundle_entries
    }
    
    return bundle


def export_prep_sheet_for_epic(patient_id: int, appointment_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Export prep sheet optimized for Epic EHR integration
    
    Args:
        patient_id: Patient ID
        appointment_id: Optional appointment ID
        
    Returns:
        Epic-optimized FHIR Bundle
    """
    bundle = export_prep_sheet_as_bundle(patient_id, appointment_id)
    
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


def _get_medical_history_section(patient_id: int) -> Dict[str, Any]:
    """Get medical history section data"""
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


def _get_screening_recommendations_section(prep_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get screening recommendations section data"""
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
                "supportingDocuments": rec['total_document_matches']
            }
            for rec in recommendations[:5]  # Top 5 recommendations
        ]
    }


def _get_document_summary_section(patient_id: int) -> Dict[str, Any]:
    """Get document summary section data"""
    documents = MedicalDocument.query.filter_by(patient_id=patient_id).order_by(MedicalDocument.created_at.desc()).limit(5).all()
    
    return {
        "totalDocuments": len(documents),
        "recentDocuments": [
            {
                "name": doc.filename or doc.document_name,
                "type": doc.document_type,
                "date": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in documents
        ]
    }


def _create_screening_recommendation_resource(recommendation: Dict[str, Any], patient_id: int, index: int) -> Dict[str, Any]:
    """Create a custom ScreeningRecommendation FHIR resource"""
    return {
        "resourceType": "ScreeningRecommendation",
        "id": f"screening-rec-{recommendation['screening_type_id']}-{index}",
        "meta": {
            "profile": ["http://example.org/fhir/StructureDefinition/ScreeningRecommendation"]
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
            "confidence": recommendation['confidence']
        },
        "evidence": {
            "documentMatches": recommendation['total_document_matches'],
            "matchSources": recommendation['match_sources'],
            "matchedCodes": recommendation['matched_codes'],
            "matchedKeywords": recommendation['matched_keywords']
        },
        "generatedDateTime": datetime.now().isoformat() + "Z"
    }


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
    required_fields = ["id"]
    for field in required_fields:
        if field not in fhir_resource:
            validation_results["warnings"].append(f"Missing recommended field: {field}")
    
    if validation_results["errors"]:
        validation_results["valid"] = False
    
    return validation_results


# Convenience function for all export types
def export_patient_prep_sheet(patient_id: int, appointment_id: Optional[int] = None, format_type: str = "bundle") -> Dict[str, Any]:
    """
    Export prep sheet in specified format
    
    Args:
        patient_id: Patient ID
        appointment_id: Optional appointment ID
        format_type: "custom", "bundle", or "epic"
        
    Returns:
        FHIR-compliant prep sheet export
    """
    if format_type == "custom":
        return export_prep_sheet_as_custom_resource(patient_id, appointment_id)
    elif format_type == "bundle":
        return export_prep_sheet_as_bundle(patient_id, appointment_id)
    elif format_type == "epic":
        return export_prep_sheet_for_epic(patient_id, appointment_id)
    else:
        raise ValueError(f"Unsupported format type: {format_type}")


if __name__ == "__main__":
    # Test the export system
    from app import app
    
    with app.app_context():
        patient = Patient.query.first()
        if patient:
            print(f"Testing FHIR export for patient: {patient.first_name} {patient.last_name}")
            
            # Test all export formats
            try:
                custom = export_patient_prep_sheet(patient.id, format_type="custom")
                print(f"Custom resource: {custom['resourceType']} with ID {custom['id']}")
                
                bundle = export_patient_prep_sheet(patient.id, format_type="bundle")
                print(f"Bundle: {bundle['total']} resources")
                
                epic = export_patient_prep_sheet(patient.id, format_type="epic")
                print(f"Epic bundle: Optimized for EHR integration")
                
                # Validate
                validation = validate_fhir_export(bundle)
                print(f"Validation: {'Valid' if validation['valid'] else 'Invalid'}")
                
                print("FHIR prep sheet export system working correctly")
                
            except Exception as e:
                print(f"Error testing export: {str(e)}")
        else:
            print("No patients found for testing")