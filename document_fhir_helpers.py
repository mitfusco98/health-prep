"""
Document FHIR Helpers

Integration functions to add FHIR-style metadata to your existing document workflows.
These functions work with your current MedicalDocument model without requiring database changes.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from fhir_document_metadata import (
    DocumentFHIRMetadata,
    DocumentFHIRMetadataBuilder,
    FHIRCoding,
    FHIRCodeableConcept,
    FHIRCodingSystem,
    get_fhir_metadata_from_document,
    update_document_with_fhir_metadata
)


def enhance_document_on_upload(document, form_data: Dict[str, Any] = None):
    """
    Enhance a newly uploaded document with FHIR metadata.
    Call this function when processing document uploads.
    
    Args:
        document: MedicalDocument instance
        form_data: Optional form data with additional metadata
    """
    builder = DocumentFHIRMetadataBuilder()
    
    # Create FHIR metadata based on document type and form data
    if document.document_type == "Lab Results":
        test_type = form_data.get("test_type", "General Lab") if form_data else "General Lab"
        lab_id = form_data.get("lab_id", f"LAB-{document.id}") if form_data else f"LAB-{document.id}"
        status = form_data.get("lab_status", "final") if form_data else "final"
        fhir_metadata = builder.create_lab_result_metadata(test_type, lab_id, status)
        
    elif document.document_type in ["Imaging", "Radiology"]:
        modality = form_data.get("modality", "XRAY") if form_data else "XRAY"
        body_part = form_data.get("body_part", "Chest") if form_data else "Chest"
        study_type = form_data.get("study_type", "Diagnostic") if form_data else "Diagnostic"
        fhir_metadata = builder.create_imaging_metadata(study_type, modality, body_part)
        
    elif document.document_type in ["Progress Notes", "Consultation", "Discharge Summary", "Operative Note"]:
        specialty = form_data.get("specialty") if form_data else None
        fhir_metadata = builder.create_clinical_note_metadata(document.document_type, specialty)
        
    else:
        # Generic document with basic FHIR structure
        fhir_metadata = DocumentFHIRMetadata()
        fhir_metadata.type = FHIRCodeableConcept(
            coding=[FHIRCoding(
                system=FHIRCodingSystem.LOINC.value,
                code="34133-9",
                display="Summarization of episode note"
            )],
            text=document.document_type or "Clinical Document"
        )
    
    # Set effective date from document date or current time
    fhir_metadata.effectiveDateTime = document.document_date or datetime.utcnow()
    
    # Add provider and source system to extensions
    if not fhir_metadata.extensions:
        fhir_metadata.extensions = {}
    
    if document.provider:
        fhir_metadata.extensions["provider"] = document.provider
    if document.source_system:
        fhir_metadata.extensions["source_system"] = document.source_system
    
    # Update document with FHIR metadata
    update_document_with_fhir_metadata(document, fhir_metadata)


def add_fhir_coding_to_document(document, code_system: str, code: str, display: str, coding_type: str = "code"):
    """
    Add a specific FHIR coding to a document's metadata.
    
    Args:
        document: MedicalDocument instance
        code_system: FHIR coding system URL
        code: The code value
        display: Human-readable display text
        coding_type: Type of coding ("code", "type", or "category")
    """
    fhir_metadata = get_fhir_metadata_from_document(document)
    
    new_coding = FHIRCoding(
        system=code_system,
        code=code,
        display=display
    )
    
    if coding_type == "code":
        if not fhir_metadata.code:
            fhir_metadata.code = FHIRCodeableConcept(coding=[])
        fhir_metadata.code.coding.append(new_coding)
        
    elif coding_type == "type":
        if not fhir_metadata.type:
            fhir_metadata.type = FHIRCodeableConcept(coding=[])
        fhir_metadata.type.coding.append(new_coding)
        
    elif coding_type == "category":
        if not fhir_metadata.category:
            fhir_metadata.category = FHIRCodeableConcept(coding=[])
        fhir_metadata.category.coding.append(new_coding)
    
    update_document_with_fhir_metadata(document, fhir_metadata)


def set_document_effective_datetime(document, effective_datetime: datetime):
    """
    Set the FHIR effectiveDateTime for a document.
    
    Args:
        document: MedicalDocument instance
        effective_datetime: When the document becomes effective
    """
    fhir_metadata = get_fhir_metadata_from_document(document)
    fhir_metadata.effectiveDateTime = effective_datetime
    update_document_with_fhir_metadata(document, fhir_metadata)


def add_document_extension(document, key: str, value: Any):
    """
    Add a custom extension to document FHIR metadata.
    
    Args:
        document: MedicalDocument instance
        key: Extension key
        value: Extension value
    """
    fhir_metadata = get_fhir_metadata_from_document(document)
    
    if not fhir_metadata.extensions:
        fhir_metadata.extensions = {}
    
    fhir_metadata.extensions[key] = value
    update_document_with_fhir_metadata(document, fhir_metadata)


def get_document_fhir_codes(document) -> Dict[str, List[Dict[str, str]]]:
    """
    Get all FHIR codes from a document in a structured format.
    
    Args:
        document: MedicalDocument instance
        
    Returns:
        Dictionary with code, type, and category coding lists
    """
    fhir_metadata = get_fhir_metadata_from_document(document)
    result = {
        "code": [],
        "type": [],
        "category": []
    }
    
    if fhir_metadata.code:
        result["code"] = [coding.to_dict() for coding in fhir_metadata.code.coding]
    
    if fhir_metadata.type:
        result["type"] = [coding.to_dict() for coding in fhir_metadata.type.coding]
    
    if fhir_metadata.category:
        result["category"] = [coding.to_dict() for coding in fhir_metadata.category.coding]
    
    return result


def search_documents_by_fhir_code(documents, code_system: str, code: str, coding_type: str = "type"):
    """
    Search documents by FHIR code.
    
    Args:
        documents: List of MedicalDocument instances
        code_system: FHIR coding system to search
        code: Code value to search for
        coding_type: Type of coding to search ("code", "type", or "category")
        
    Returns:
        List of matching documents
    """
    matching_documents = []
    
    for document in documents:
        fhir_codes = get_document_fhir_codes(document)
        target_codes = fhir_codes.get(coding_type, [])
        
        for coding in target_codes:
            if coding.get("system") == code_system and coding.get("code") == code:
                matching_documents.append(document)
                break
    
    return matching_documents


def get_document_display_metadata(document) -> Dict[str, Any]:
    """
    Get formatted metadata for display in UI.
    
    Args:
        document: MedicalDocument instance
        
    Returns:
        Dictionary with formatted metadata for display
    """
    fhir_metadata = get_fhir_metadata_from_document(document)
    
    result = {
        "document_id": document.id,
        "filename": document.filename,
        "document_name": document.document_name,
        "legacy_type": document.document_type,
        "fhir_metadata": {}
    }
    
    # FHIR code information
    if fhir_metadata.code:
        primary_coding = fhir_metadata.code.coding[0] if fhir_metadata.code.coding else None
        if primary_coding:
            result["fhir_metadata"]["code"] = {
                "system": primary_coding.system,
                "code": primary_coding.code,
                "display": primary_coding.display,
                "text": fhir_metadata.code.text
            }
    
    # FHIR type information
    if fhir_metadata.type:
        primary_coding = fhir_metadata.type.coding[0] if fhir_metadata.type.coding else None
        if primary_coding:
            result["fhir_metadata"]["type"] = {
                "system": primary_coding.system,
                "code": primary_coding.code,
                "display": primary_coding.display,
                "text": fhir_metadata.type.text
            }
    
    # FHIR category information
    if fhir_metadata.category:
        primary_coding = fhir_metadata.category.coding[0] if fhir_metadata.category.coding else None
        if primary_coding:
            result["fhir_metadata"]["category"] = {
                "system": primary_coding.system,
                "code": primary_coding.code,
                "display": primary_coding.display,
                "text": fhir_metadata.category.text
            }
    
    # Temporal data
    if fhir_metadata.effectiveDateTime:
        result["fhir_metadata"]["effectiveDateTime"] = fhir_metadata.effectiveDateTime.isoformat()
    
    if fhir_metadata.authenticatedTime:
        result["fhir_metadata"]["authenticatedTime"] = fhir_metadata.authenticatedTime.isoformat()
    
    # Extensions
    if fhir_metadata.extensions:
        result["fhir_metadata"]["extensions"] = fhir_metadata.extensions
    
    return result


def bulk_enhance_existing_documents(documents):
    """
    Enhance multiple existing documents with FHIR metadata.
    Useful for migrating existing documents to FHIR structure.
    
    Args:
        documents: List of MedicalDocument instances
        
    Returns:
        Dictionary with enhancement results
    """
    results = {
        "enhanced": 0,
        "skipped": 0,
        "errors": 0,
        "details": []
    }
    
    builder = DocumentFHIRMetadataBuilder()
    
    for document in documents:
        try:
            # Check if already has FHIR metadata
            existing_fhir = get_fhir_metadata_from_document(document)
            if existing_fhir.type or existing_fhir.code or existing_fhir.category:
                results["skipped"] += 1
                results["details"].append(f"Document {document.id}: Already has FHIR metadata")
                continue
            
            # Enhance with FHIR metadata
            enhanced_metadata = builder.enhance_existing_document(document)
            document.doc_metadata = enhanced_metadata
            
            results["enhanced"] += 1
            results["details"].append(f"Document {document.id}: Enhanced with FHIR metadata")
            
        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Document {document.id}: Error - {str(e)}")
    
    return results


# Document model extension functions (to be used as methods)
def get_fhir_type_display(document) -> str:
    """Get the FHIR type display text for a document"""
    fhir_metadata = get_fhir_metadata_from_document(document)
    if fhir_metadata.type and fhir_metadata.type.coding:
        return fhir_metadata.type.coding[0].display
    return document.document_type or "Unknown"


def get_fhir_category_display(document) -> str:
    """Get the FHIR category display text for a document"""
    fhir_metadata = get_fhir_metadata_from_document(document)
    if fhir_metadata.category and fhir_metadata.category.coding:
        return fhir_metadata.category.coding[0].display
    return "Clinical Document"


def get_fhir_primary_code(document) -> Optional[Dict[str, str]]:
    """Get the primary FHIR code for a document"""
    fhir_metadata = get_fhir_metadata_from_document(document)
    if fhir_metadata.code and fhir_metadata.code.coding:
        coding = fhir_metadata.code.coding[0]
        return {
            "system": coding.system,
            "code": coding.code,
            "display": coding.display
        }
    return None


def has_fhir_metadata(document) -> bool:
    """Check if document has FHIR-structured metadata"""
    fhir_metadata = get_fhir_metadata_from_document(document)
    return bool(fhir_metadata.type or fhir_metadata.code or fhir_metadata.category)


def get_effective_datetime(document) -> Optional[datetime]:
    """Get the FHIR effective datetime for a document"""
    fhir_metadata = get_fhir_metadata_from_document(document)
    return fhir_metadata.effectiveDateTime