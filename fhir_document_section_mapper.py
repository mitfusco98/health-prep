"""
FHIR Document Section Mapping System
Maps document sections (labs, imaging, consults) to FHIR category codes during parsing and matching
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from app import db
from models import ScreeningType, MedicalDocument


class DocumentSectionMapper:
    """
    Maps document sections to FHIR categories and manages section-based screening triggers
    """
    
    # Standard FHIR observation categories
    STANDARD_FHIR_CATEGORIES = {
        "laboratory": {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "laboratory",
            "display": "Laboratory"
        },
        "imaging": {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "imaging", 
            "display": "Imaging"
        },
        "exam": {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "exam",
            "display": "Exam"
        },
        "procedure": {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "procedure",
            "display": "Procedure"
        },
        "vital-signs": {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "vital-signs",
            "display": "Vital Signs"
        },
        "survey": {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "survey",
            "display": "Survey"
        }
    }
    
    # Default section mappings for common document types
    DEFAULT_SECTION_MAPPINGS = {
        "labs": {
            "fhir_category": STANDARD_FHIR_CATEGORIES["laboratory"],
            "document_types": ["Lab Report", "Laboratory Results", "Blood Work"],
            "keywords": ["lab", "laboratory", "blood", "urine", "chemistry", "hematology"]
        },
        "imaging": {
            "fhir_category": STANDARD_FHIR_CATEGORIES["imaging"],
            "document_types": ["Radiology Report", "X-Ray", "CT Scan", "MRI", "Ultrasound"],
            "keywords": ["radiology", "imaging", "x-ray", "ct", "mri", "ultrasound", "scan"]
        },
        "consults": {
            "fhir_category": STANDARD_FHIR_CATEGORIES["exam"],
            "document_types": ["Consultation Note", "Specialist Report", "Referral"],
            "keywords": ["consult", "consultation", "specialist", "referral", "evaluation"]
        },
        "procedures": {
            "fhir_category": STANDARD_FHIR_CATEGORIES["procedure"],
            "document_types": ["Procedure Note", "Operative Report", "Surgery Note"],
            "keywords": ["procedure", "surgery", "operative", "intervention"]
        },
        "vitals": {
            "fhir_category": STANDARD_FHIR_CATEGORIES["vital-signs"],
            "document_types": ["Vital Signs", "Nursing Note", "Triage Note"],
            "keywords": ["vital", "vitals", "blood pressure", "temperature", "pulse", "weight"]
        },
        "clinical_notes": {
            "fhir_category": STANDARD_FHIR_CATEGORIES["exam"],
            "document_types": ["Clinical Note", "Progress Note", "Discharge Summary"],
            "keywords": ["clinical", "progress", "note", "discharge", "summary"]
        }
    }
    
    def __init__(self):
        pass
    
    def detect_document_section(self, document_name: str, document_type: str = None, content: str = None) -> str:
        """
        Detect the section of a document based on name, type, and content
        
        Args:
            document_name: Name/filename of the document
            document_type: Type of the document 
            content: Document content for keyword analysis
            
        Returns:
            str: Detected section name or "unknown"
        """
        # Check document type first
        if document_type:
            for section, config in self.DEFAULT_SECTION_MAPPINGS.items():
                if document_type in config.get("document_types", []):
                    return section
        
        # Check document name for keywords
        if document_name:
            document_name_lower = document_name.lower()
            for section, config in self.DEFAULT_SECTION_MAPPINGS.items():
                keywords = config.get("keywords", [])
                if any(keyword in document_name_lower for keyword in keywords):
                    return section
        
        # Check content for keywords if available
        if content:
            content_lower = content.lower()
            keyword_scores = {}
            
            for section, config in self.DEFAULT_SECTION_MAPPINGS.items():
                keywords = config.get("keywords", [])
                score = sum(1 for keyword in keywords if keyword in content_lower)
                if score > 0:
                    keyword_scores[section] = score
            
            if keyword_scores:
                # Return section with highest keyword match score
                return max(keyword_scores, key=keyword_scores.get)
        
        return "unknown"
    
    def get_fhir_category_for_document(self, document_section: str, screening_type_id: int = None) -> Dict[str, Any]:
        """
        Get FHIR category for a document section, optionally using screening type configuration
        
        Args:
            document_section: The document section
            screening_type_id: Optional screening type ID for custom mappings
            
        Returns:
            dict: FHIR category structure
        """
        # Check if specific screening type has custom mappings
        if screening_type_id:
            screening_type = ScreeningType.query.get(screening_type_id)
            if screening_type:
                custom_category = screening_type.get_fhir_category_for_section(document_section)
                if custom_category:
                    return custom_category
        
        # Use default mappings
        if document_section in self.DEFAULT_SECTION_MAPPINGS:
            return self.DEFAULT_SECTION_MAPPINGS[document_section]["fhir_category"]
        
        # Fallback to exam category
        return self.STANDARD_FHIR_CATEGORIES["exam"]
    
    def configure_screening_section_mappings(self, screening_type_id: int, section_mappings: Dict[str, Any]):
        """
        Configure document section mappings for a specific screening type
        
        Args:
            screening_type_id: ID of the screening type
            section_mappings: Dictionary of section configurations
        """
        screening_type = ScreeningType.query.get(screening_type_id)
        if not screening_type:
            raise ValueError(f"Screening type {screening_type_id} not found")
        
        screening_type.set_document_section_mappings(section_mappings)
        db.session.commit()
    
    def find_screenings_by_document_section(self, document_section: str, document_type: str = None) -> List[ScreeningType]:
        """
        Find screening types that match a document section
        
        Args:
            document_section: The document section to match
            document_type: Optional document type for additional matching
            
        Returns:
            List[ScreeningType]: Matching screening types
        """
        matching_screenings = []
        
        # Get all active screening types
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        for screening_type in screening_types:
            if screening_type.matches_document_section(document_section, document_type):
                matching_screenings.append(screening_type)
        
        return matching_screenings
    
    def enhance_document_with_fhir_metadata(self, document: MedicalDocument) -> Dict[str, Any]:
        """
        Enhance a document with FHIR metadata based on section mapping
        
        Args:
            document: MedicalDocument instance
            
        Returns:
            dict: Enhanced FHIR metadata
        """
        # Detect document section
        document_section = self.detect_document_section(
            document.filename or document.document_name,
            document.document_type,
            document.content[:500] if document.content else None  # Sample first 500 chars
        )
        
        # Get FHIR category
        fhir_category = self.get_fhir_category_for_document(document_section)
        
        # Find matching screening types
        matching_screenings = self.find_screenings_by_document_section(document_section, document.document_type)
        
        # Build enhanced metadata
        enhanced_metadata = {
            "detected_section": document_section,
            "fhir_category": fhir_category,
            "matching_screenings": [
                {
                    "id": screening.id,
                    "name": screening.name,
                    "description": screening.description
                }
                for screening in matching_screenings
            ],
            "section_confidence": self._calculate_section_confidence(document, document_section),
            "processing_timestamp": datetime.now().isoformat()
        }
        
        return enhanced_metadata
    
    def _calculate_section_confidence(self, document: MedicalDocument, detected_section: str) -> float:
        """
        Calculate confidence score for section detection
        
        Args:
            document: MedicalDocument instance
            detected_section: The detected section
            
        Returns:
            float: Confidence score between 0 and 1
        """
        confidence = 0.0
        
        if detected_section == "unknown":
            return 0.0
        
        section_config = self.DEFAULT_SECTION_MAPPINGS.get(detected_section, {})
        
        # Check document type match
        if document.document_type in section_config.get("document_types", []):
            confidence += 0.6
        
        # Check filename keywords
        if document.filename:
            filename_lower = document.filename.lower()
            keywords = section_config.get("keywords", [])
            keyword_matches = sum(1 for keyword in keywords if keyword in filename_lower)
            if keyword_matches > 0:
                confidence += min(0.4, keyword_matches * 0.1)
        
        return min(1.0, confidence)
    
    def get_section_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about document sections in the database
        
        Returns:
            dict: Section statistics
        """
        try:
            # Get all documents
            documents = MedicalDocument.query.all()
            
            section_counts = {}
            total_documents = len(documents)
            
            for document in documents:
                section = self.detect_document_section(
                    document.filename or document.document_name,
                    document.document_type
                )
                section_counts[section] = section_counts.get(section, 0) + 1
            
            return {
                "total_documents": total_documents,
                "section_distribution": section_counts,
                "sections_mapped": len([s for s in section_counts.keys() if s != "unknown"]),
                "unmapped_documents": section_counts.get("unknown", 0),
                "mapping_coverage": (total_documents - section_counts.get("unknown", 0)) / total_documents if total_documents > 0 else 0
            }
        
        except Exception as e:
            return {
                "error": str(e),
                "total_documents": 0,
                "section_distribution": {},
                "sections_mapped": 0,
                "unmapped_documents": 0,
                "mapping_coverage": 0
            }


def setup_default_screening_section_mappings():
    """
    Setup default document section mappings for existing screening types
    """
    mapper = DocumentSectionMapper()
    
    # Default configurations for common screening types
    default_configs = {
        "Diabetes Management": {
            "labs": {
                "fhir_category": mapper.STANDARD_FHIR_CATEGORIES["laboratory"],
                "document_types": ["Lab Report", "HbA1c Results", "Glucose Test"],
                "keywords": ["glucose", "hba1c", "diabetes", "blood sugar"]
            },
            "clinical_notes": {
                "fhir_category": mapper.STANDARD_FHIR_CATEGORIES["exam"],
                "document_types": ["Endocrinology Note", "Diabetes Visit"],
                "keywords": ["diabetes", "endocrine", "insulin"]
            }
        },
        "Hypertension Monitoring": {
            "vitals": {
                "fhir_category": mapper.STANDARD_FHIR_CATEGORIES["vital-signs"],
                "document_types": ["Vital Signs", "Blood Pressure Log"],
                "keywords": ["blood pressure", "hypertension", "bp"]
            },
            "clinical_notes": {
                "fhir_category": mapper.STANDARD_FHIR_CATEGORIES["exam"],
                "document_types": ["Cardiology Note", "Hypertension Visit"],
                "keywords": ["hypertension", "cardiac", "cardiovascular"]
            }
        },
        "Cancer Risk Screening": {
            "imaging": {
                "fhir_category": mapper.STANDARD_FHIR_CATEGORIES["imaging"],
                "document_types": ["Mammogram", "CT Scan", "MRI"],
                "keywords": ["mammogram", "screening", "tumor", "mass"]
            },
            "labs": {
                "fhir_category": mapper.STANDARD_FHIR_CATEGORIES["laboratory"],
                "document_types": ["Tumor Markers", "Cancer Screening Labs"],
                "keywords": ["tumor marker", "cea", "psa", "ca-125"]
            }
        }
    }
    
    # Apply configurations to existing screening types
    for screening_name, section_mappings in default_configs.items():
        screening_type = ScreeningType.query.filter_by(name=screening_name).first()
        if screening_type:
            try:
                mapper.configure_screening_section_mappings(screening_type.id, section_mappings)
                print(f"Configured section mappings for: {screening_name}")
            except Exception as e:
                print(f"Error configuring {screening_name}: {str(e)}")


# Example usage and configuration
EXAMPLE_SECTION_CONFIGURATIONS = {
    "comprehensive_diabetes": {
        "labs": {
            "fhir_category": {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            },
            "document_types": ["HbA1c", "Glucose Test", "Lipid Panel"],
            "keywords": ["glucose", "hba1c", "lipid", "cholesterol"],
            "loinc_codes": ["4548-4", "33747-0", "2093-3"]  # HbA1c, glucose, cholesterol
        },
        "imaging": {
            "fhir_category": {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "imaging",
                "display": "Imaging"
            },
            "document_types": ["Retinal Exam", "Foot X-Ray", "Renal Ultrasound"],
            "keywords": ["retinal", "foot", "renal", "kidney", "eye"],
            "cpt_codes": ["92134", "73620", "76700"]  # Retinal, foot x-ray, renal US
        },
        "procedures": {
            "fhir_category": {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "procedure",
                "display": "Procedure"
            },
            "document_types": ["Foot Exam", "Eye Exam", "Nephrology Consult"],
            "keywords": ["foot exam", "diabetic foot", "eye exam", "nephrology"],
            "cpt_codes": ["99213", "92014", "99242"]  # Office visit, eye exam, consult
        }
    }
}