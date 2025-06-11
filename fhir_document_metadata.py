"""
FHIR-Style Document Metadata System

This module provides FHIR-structured metadata for your documents without changing
existing database fields. New features use FHIR field patterns like:
- code.coding.code
- code.coding.system  
- type.coding.display
- effectiveDateTime
- category

Existing fields like doc_metadata, document_type, etc. remain unchanged.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class FHIRCodingSystem(Enum):
    """Standard FHIR coding systems for document metadata"""
    LOINC = "http://loinc.org"
    SNOMED_CT = "http://snomed.info/sct"
    ICD10 = "http://hl7.org/fhir/sid/icd-10"
    CPT = "http://www.ama-assn.org/go/cpt"
    US_CORE_DOCUMENT_TYPE = "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category"
    HL7_DOCUMENT_TYPE = "http://terminology.hl7.org/CodeSystem/c80-doc-typecodes"


@dataclass
class FHIRCoding:
    """FHIR coding structure: code.coding"""
    system: str
    code: str
    display: str
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "system": self.system,
            "code": self.code,
            "display": self.display
        }
        if self.version:
            result["version"] = self.version
        return result


@dataclass
class FHIRCodeableConcept:
    """FHIR CodeableConcept structure: type.coding"""
    coding: List[FHIRCoding]
    text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "coding": [coding.to_dict() for coding in self.coding]
        }
        if self.text:
            result["text"] = self.text
        return result


@dataclass
class DocumentFHIRMetadata:
    """
    FHIR-structured document metadata that enhances your existing doc_metadata field.
    This uses FHIR field patterns without changing your database schema.
    """
    
    # FHIR-style coding for document classification
    code: Optional[FHIRCodeableConcept] = None  # Primary document code
    type: Optional[FHIRCodeableConcept] = None  # Document type classification
    category: Optional[FHIRCodeableConcept] = None  # Document category
    
    # FHIR-style temporal data
    effectiveDateTime: Optional[datetime] = None  # When document takes effect
    authenticatedTime: Optional[datetime] = None  # When document was authenticated
    
    # Additional FHIR extensions
    extensions: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        result = {}
        
        if self.code:
            result["code"] = self.code.to_dict()
        if self.type:
            result["type"] = self.type.to_dict()
        if self.category:
            result["category"] = self.category.to_dict()
        if self.effectiveDateTime:
            result["effectiveDateTime"] = self.effectiveDateTime.isoformat()
        if self.authenticatedTime:
            result["authenticatedTime"] = self.authenticatedTime.isoformat()
        if self.extensions:
            result["extensions"] = self.extensions
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string for database storage"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentFHIRMetadata':
        """Create from dictionary"""
        metadata = cls()
        
        if "code" in data:
            code_data = data["code"]
            codings = [FHIRCoding(**coding) for coding in code_data.get("coding", [])]
            metadata.code = FHIRCodeableConcept(
                coding=codings,
                text=code_data.get("text")
            )
        
        if "type" in data:
            type_data = data["type"]
            codings = [FHIRCoding(**coding) for coding in type_data.get("coding", [])]
            metadata.type = FHIRCodeableConcept(
                coding=codings,
                text=type_data.get("text")
            )
        
        if "category" in data:
            category_data = data["category"]
            codings = [FHIRCoding(**coding) for coding in category_data.get("coding", [])]
            metadata.category = FHIRCodeableConcept(
                coding=codings,
                text=category_data.get("text")
            )
        
        if "effectiveDateTime" in data:
            metadata.effectiveDateTime = datetime.fromisoformat(data["effectiveDateTime"].replace("Z", "+00:00"))
        
        if "authenticatedTime" in data:
            metadata.authenticatedTime = datetime.fromisoformat(data["authenticatedTime"].replace("Z", "+00:00"))
        
        if "extensions" in data:
            metadata.extensions = data["extensions"]
        
        return metadata
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DocumentFHIRMetadata':
        """Create from JSON string"""
        if not json_str:
            return cls()
        
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return cls()


class DocumentFHIRMetadataBuilder:
    """Helper class to build FHIR-structured metadata for documents"""
    
    # Standard document type mappings to FHIR codes
    DOCUMENT_TYPE_MAPPINGS = {
        "Lab Results": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "11502-2",
            "display": "Laboratory report"
        },
        "Imaging": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "18748-4",
            "display": "Diagnostic imaging study"
        },
        "Progress Notes": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "11506-3",
            "display": "Progress note"
        },
        "Discharge Summary": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "18842-5",
            "display": "Discharge summary"
        },
        "Consultation": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "11488-4",
            "display": "Consultation note"
        },
        "Operative Note": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "11504-8",
            "display": "Surgical operation note"
        },
        "Pathology": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "11526-1",
            "display": "Pathology study"
        },
        "Radiology": {
            "system": FHIRCodingSystem.LOINC.value,
            "code": "18726-0",
            "display": "Radiology studies"
        }
    }
    
    # Standard category mappings
    CATEGORY_MAPPINGS = {
        "Lab Results": {
            "system": FHIRCodingSystem.US_CORE_DOCUMENT_TYPE.value,
            "code": "laboratory",
            "display": "Laboratory"
        },
        "Imaging": {
            "system": FHIRCodingSystem.US_CORE_DOCUMENT_TYPE.value,
            "code": "imaging",
            "display": "Imaging"
        },
        "Radiology": {
            "system": FHIRCodingSystem.US_CORE_DOCUMENT_TYPE.value,
            "code": "imaging",
            "display": "Imaging"
        }
    }
    
    @classmethod
    def create_lab_result_metadata(cls, test_type: str, lab_id: str, status: str = "final") -> DocumentFHIRMetadata:
        """Create FHIR metadata for lab results"""
        metadata = DocumentFHIRMetadata()
        
        # Primary code for the specific lab test
        if test_type.upper() == "CBC":
            code_system = FHIRCodingSystem.LOINC.value
            code_value = "58410-2"
            code_display = "Complete blood count (hemogram) panel - Blood by Automated count"
        elif test_type.upper() == "BMP":
            code_system = FHIRCodingSystem.LOINC.value
            code_value = "51990-0"
            code_display = "Basic metabolic panel - Blood"
        else:
            # Generic lab test
            code_system = FHIRCodingSystem.LOINC.value
            code_value = "33747-0"
            code_display = "General laboratory test"
        
        metadata.code = FHIRCodeableConcept(
            coding=[FHIRCoding(
                system=code_system,
                code=code_value,
                display=code_display
            )],
            text=f"{test_type} Lab Test"
        )
        
        # Document type
        type_mapping = cls.DOCUMENT_TYPE_MAPPINGS["Lab Results"]
        metadata.type = FHIRCodeableConcept(
            coding=[FHIRCoding(**type_mapping)],
            text="Lab Results"
        )
        
        # Category
        category_mapping = cls.CATEGORY_MAPPINGS["Lab Results"]
        metadata.category = FHIRCodeableConcept(
            coding=[FHIRCoding(**category_mapping)],
            text="Laboratory"
        )
        
        # Extensions for lab-specific data
        metadata.extensions = {
            "lab_id": lab_id,
            "test_type": test_type,
            "status": status
        }
        
        return metadata
    
    @classmethod
    def create_imaging_metadata(cls, study_type: str, modality: str, body_part: str) -> DocumentFHIRMetadata:
        """Create FHIR metadata for imaging studies"""
        metadata = DocumentFHIRMetadata()
        
        # Primary code for imaging study
        if modality.upper() == "CT":
            code_system = FHIRCodingSystem.LOINC.value
            code_value = "18748-4"
            code_display = "Diagnostic imaging study"
        elif modality.upper() == "MRI":
            code_system = FHIRCodingSystem.LOINC.value
            code_value = "18755-9"
            code_display = "MR study"
        elif modality.upper() == "XRAY":
            code_system = FHIRCodingSystem.LOINC.value
            code_value = "18726-0"
            code_display = "Radiology studies"
        else:
            code_system = FHIRCodingSystem.LOINC.value
            code_value = "18748-4"
            code_display = "Diagnostic imaging study"
        
        metadata.code = FHIRCodeableConcept(
            coding=[FHIRCoding(
                system=code_system,
                code=code_value,
                display=code_display
            )],
            text=f"{modality} {body_part}"
        )
        
        # Document type
        type_mapping = cls.DOCUMENT_TYPE_MAPPINGS["Imaging"]
        metadata.type = FHIRCodeableConcept(
            coding=[FHIRCoding(**type_mapping)],
            text="Imaging Study"
        )
        
        # Category
        category_mapping = cls.CATEGORY_MAPPINGS["Imaging"]
        metadata.category = FHIRCodeableConcept(
            coding=[FHIRCoding(**category_mapping)],
            text="Imaging"
        )
        
        # Extensions for imaging-specific data
        metadata.extensions = {
            "study_type": study_type,
            "modality": modality,
            "body_part": body_part
        }
        
        return metadata
    
    @classmethod
    def create_clinical_note_metadata(cls, note_type: str, specialty: str = None) -> DocumentFHIRMetadata:
        """Create FHIR metadata for clinical notes"""
        metadata = DocumentFHIRMetadata()
        
        # Map note type to LOINC codes
        note_mappings = {
            "Progress Note": {"code": "11506-3", "display": "Progress note"},
            "Consultation": {"code": "11488-4", "display": "Consultation note"},
            "Discharge Summary": {"code": "18842-5", "display": "Discharge summary"},
            "Operative Note": {"code": "11504-8", "display": "Surgical operation note"},
            "History and Physical": {"code": "11492-6", "display": "History and physical note"}
        }
        
        note_info = note_mappings.get(note_type, {"code": "34133-9", "display": "Summarization of episode note"})
        
        metadata.code = FHIRCodeableConcept(
            coding=[FHIRCoding(
                system=FHIRCodingSystem.LOINC.value,
                code=note_info["code"],
                display=note_info["display"]
            )],
            text=note_type
        )
        
        # Document type
        if note_type in cls.DOCUMENT_TYPE_MAPPINGS:
            type_mapping = cls.DOCUMENT_TYPE_MAPPINGS[note_type]
        else:
            type_mapping = {
                "system": FHIRCodingSystem.LOINC.value,
                "code": "34133-9",
                "display": "Summarization of episode note"
            }
        
        metadata.type = FHIRCodeableConcept(
            coding=[FHIRCoding(**type_mapping)],
            text=note_type
        )
        
        # Category - clinical note
        metadata.category = FHIRCodeableConcept(
            coding=[FHIRCoding(
                system=FHIRCodingSystem.US_CORE_DOCUMENT_TYPE.value,
                code="clinical-note",
                display="Clinical Note"
            )],
            text="Clinical Note"
        )
        
        # Extensions
        extensions = {"note_type": note_type}
        if specialty:
            extensions["specialty"] = specialty
        metadata.extensions = extensions
        
        return metadata
    
    @classmethod
    def enhance_existing_document(cls, document, additional_metadata: Dict[str, Any] = None) -> str:
        """
        Enhance an existing document's metadata with FHIR structure.
        
        Args:
            document: Your MedicalDocument model instance
            additional_metadata: Additional metadata to include
        
        Returns:
            JSON string with enhanced FHIR-structured metadata
        """
        # Start with existing metadata if available
        existing_metadata = {}
        if document.doc_metadata:
            try:
                existing_metadata = json.loads(document.doc_metadata)
            except (json.JSONDecodeError, TypeError):
                existing_metadata = {}
        
        # Create FHIR metadata based on document type
        if document.document_type == "Lab Results":
            test_type = existing_metadata.get("test_type", "General")
            lab_id = existing_metadata.get("lab_id", f"LAB-{document.id}")
            status = existing_metadata.get("status", "final")
            fhir_metadata = cls.create_lab_result_metadata(test_type, lab_id, status)
        
        elif document.document_type in ["Imaging", "Radiology"]:
            modality = existing_metadata.get("modality", "XRAY")
            body_part = existing_metadata.get("body_part", "Chest")
            study_type = existing_metadata.get("study_type", "Diagnostic")
            fhir_metadata = cls.create_imaging_metadata(study_type, modality, body_part)
        
        elif document.document_type in ["Progress Notes", "Consultation", "Discharge Summary", "Operative Note"]:
            specialty = existing_metadata.get("specialty")
            fhir_metadata = cls.create_clinical_note_metadata(document.document_type, specialty)
        
        else:
            # Generic document
            fhir_metadata = DocumentFHIRMetadata()
            fhir_metadata.type = FHIRCodeableConcept(
                coding=[FHIRCoding(
                    system=FHIRCodingSystem.LOINC.value,
                    code="34133-9",
                    display="Summarization of episode note"
                )],
                text=document.document_type or "Clinical Document"
            )
        
        # Set effective date time
        if document.document_date:
            fhir_metadata.effectiveDateTime = document.document_date
        
        # Merge existing metadata with FHIR structure
        result = {
            "fhir": fhir_metadata.to_dict(),
            "legacy": existing_metadata
        }
        
        # Add any additional metadata
        if additional_metadata:
            result["additional"] = additional_metadata
        
        return json.dumps(result, default=str)


def get_fhir_metadata_from_document(document) -> DocumentFHIRMetadata:
    """
    Extract FHIR metadata from a document's doc_metadata field.
    
    Args:
        document: Your MedicalDocument model instance
    
    Returns:
        DocumentFHIRMetadata object
    """
    if not document.doc_metadata:
        return DocumentFHIRMetadata()
    
    try:
        metadata_dict = json.loads(document.doc_metadata)
        fhir_data = metadata_dict.get("fhir", {})
        return DocumentFHIRMetadata.from_dict(fhir_data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return DocumentFHIRMetadata()


def update_document_with_fhir_metadata(document, fhir_metadata: DocumentFHIRMetadata):
    """
    Update a document's metadata with FHIR structure while preserving existing data.
    
    Args:
        document: Your MedicalDocument model instance
        fhir_metadata: DocumentFHIRMetadata object
    """
    # Get existing metadata
    existing_data = {}
    if document.doc_metadata:
        try:
            existing_data = json.loads(document.doc_metadata)
        except (json.JSONDecodeError, TypeError):
            existing_data = {}
    
    # Update with FHIR data
    existing_data["fhir"] = fhir_metadata.to_dict()
    
    # Update the document
    document.doc_metadata = json.dumps(existing_data, default=str)