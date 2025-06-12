"""
Enhanced Document Processor with Dual Storage

Automatically extracts and stores both internal and FHIR keys when processing
documents and prep sheets, with comprehensive admin logging.
"""

import json
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from dual_storage_handler import (
    DualStorageHandler,
    save_document_dual_storage,
    save_prep_sheet_dual_storage
)

try:
    from models import MedicalDocument, PrepSheet, Patient
    from screening_rules import SCREENING_TYPES_CONFIG
    from fhir_document_parser import FHIRDocumentParser
except ImportError:
    MedicalDocument = PrepSheet = Patient = None
    SCREENING_TYPES_CONFIG = {}
    FHIRDocumentParser = None


class EnhancedDocumentProcessor:
    """Process documents with automatic dual storage key extraction"""
    
    def __init__(self):
        self.fhir_parser = FHIRDocumentParser() if FHIRDocumentParser else None
        
        # Document type to FHIR code mapping
        self.document_type_mappings = {
            'Lab Report': {
                'fhir_code': {
                    'system': 'http://loinc.org',
                    'code': '11502-2',
                    'display': 'Laboratory report'
                },
                'fhir_category': {
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'laboratory',
                    'display': 'Laboratory'
                },
                'internal_tag': 'lab',
                'internal_section': 'laboratory_results'
            },
            'Radiology Report': {
                'fhir_code': {
                    'system': 'http://loinc.org',
                    'code': '18748-4',
                    'display': 'Diagnostic imaging study'
                },
                'fhir_category': {
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'imaging',
                    'display': 'Imaging'
                },
                'internal_tag': 'radiology',
                'internal_section': 'imaging_studies'
            },
            'Clinical Note': {
                'fhir_code': {
                    'system': 'http://loinc.org',
                    'code': '11506-3',
                    'display': 'Progress note'
                },
                'fhir_category': {
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'exam',
                    'display': 'Exam'
                },
                'internal_tag': 'clinical',
                'internal_section': 'clinical_notes'
            },
            'Discharge Summary': {
                'fhir_code': {
                    'system': 'http://loinc.org',
                    'code': '18842-5',
                    'display': 'Discharge summary'
                },
                'fhir_category': {
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'exam',
                    'display': 'Exam'
                },
                'internal_tag': 'discharge',
                'internal_section': 'hospital_records'
            },
            'Consultation': {
                'fhir_code': {
                    'system': 'http://loinc.org',
                    'code': '11488-4',
                    'display': 'Consultation note'
                },
                'fhir_category': {
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'exam',
                    'display': 'Exam'
                },
                'internal_tag': 'consult',
                'internal_section': 'specialist_reports'
            }
        }
        
        # Screening detection patterns
        self.screening_patterns = {
            'mammogram': ['mammogram', 'mammography', 'breast imaging', 'breast screening'],
            'colonoscopy': ['colonoscopy', 'colon screening', 'colorectal screening'],
            'pap_smear': ['pap smear', 'cervical screening', 'pap test'],
            'bone_density': ['bone density', 'dexa scan', 'osteoporosis screening'],
            'cholesterol': ['cholesterol', 'lipid panel', 'lipid screening'],
            'diabetes': ['hba1c', 'glucose', 'diabetes screening', 'hemoglobin a1c'],
            'blood_pressure': ['blood pressure', 'hypertension screening', 'bp check']
        }
    
    def process_new_document(self, document: MedicalDocument, 
                           user_id: Optional[int] = None) -> bool:
        """
        Process new document with automatic dual storage key extraction
        
        Args:
            document: MedicalDocument instance
            user_id: User performing the action
            
        Returns:
            bool: Success status
        """
        try:
            # Extract internal keys
            internal_data = self._extract_internal_keys(document)
            
            # Extract FHIR keys
            fhir_data = self._extract_fhir_keys(document)
            
            # Enhance with document-specific FHIR data
            if document.document_type in self.document_type_mappings:
                mapping = self.document_type_mappings[document.document_type]
                if not fhir_data.get('code'):
                    fhir_data['code'] = mapping['fhir_code']
                if not fhir_data.get('category'):
                    fhir_data['category'] = mapping['fhir_category']
            
            # Set effective datetime if not provided
            if not fhir_data.get('effectiveDateTime'):
                fhir_data['effectiveDateTime'] = document.document_date or document.created_at
            
            # Save with dual storage
            success = DualStorageHandler.save_document_with_dual_storage(
                document=document,
                internal_data=internal_data,
                fhir_data=fhir_data,
                user_id=user_id
            )
            
            if success:
                print(f"Successfully processed document: {document.filename}")
                print(f"Internal keys: {internal_data}")
                print(f"FHIR keys: {fhir_data}")
            
            return success
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return False
    
    def process_new_prep_sheet(self, prep_sheet: PrepSheet,
                             screening_types: List[str] = None,
                             user_id: Optional[int] = None) -> bool:
        """
        Process new prep sheet with automatic dual storage key extraction
        
        Args:
            prep_sheet: PrepSheet instance
            screening_types: List of screening types included
            user_id: User performing the action
            
        Returns:
            bool: Success status
        """
        try:
            # Extract internal keys for prep sheet
            internal_data = {
                'tag': 'prep_sheet',
                'section': 'preventive_care',
                'matched_screening': ','.join(screening_types) if screening_types else None
            }
            
            # Create FHIR data for prep sheet
            fhir_data = DualStorageHandler.create_prep_sheet_fhir_data(
                datetime.combine(prep_sheet.appointment_date, datetime.min.time())
            )
            
            # Save with dual storage
            success = DualStorageHandler.save_prep_sheet_with_dual_storage(
                prep_sheet=prep_sheet,
                internal_data=internal_data,
                fhir_data=fhir_data,
                user_id=user_id
            )
            
            if success:
                print(f"Successfully processed prep sheet: {prep_sheet.filename}")
                print(f"Internal keys: {internal_data}")
                print(f"FHIR keys: {fhir_data}")
            
            return success
            
        except Exception as e:
            print(f"Error processing prep sheet: {str(e)}")
            return False
    
    def _extract_internal_keys(self, document: MedicalDocument) -> Dict[str, str]:
        """Extract internal keys from document content and metadata"""
        internal_data = {}
        
        # Get base mapping from document type
        if document.document_type in self.document_type_mappings:
            mapping = self.document_type_mappings[document.document_type]
            internal_data['tag'] = mapping['internal_tag']
            internal_data['section'] = mapping['internal_section']
        
        # Detect screening type from content
        matched_screening = self._detect_screening_type(document)
        if matched_screening:
            internal_data['matched_screening'] = matched_screening
        
        return internal_data
    
    def _extract_fhir_keys(self, document: MedicalDocument) -> Dict[str, Any]:
        """Extract FHIR keys from document metadata and content"""
        fhir_data = {}
        
        # Try to extract from existing metadata first
        if document.doc_metadata:
            existing_fhir = DualStorageHandler.extract_fhir_from_document_metadata(
                document.doc_metadata
            )
            fhir_data.update(existing_fhir)
        
        # Use FHIR parser if available
        if self.fhir_parser and document.content:
            try:
                parsed_fhir = self.fhir_parser.parse_document_content(
                    document.content,
                    document.document_type
                )
                if parsed_fhir:
                    fhir_data.update(parsed_fhir)
            except Exception as e:
                print(f"FHIR parser error: {str(e)}")
        
        return fhir_data
    
    def _detect_screening_type(self, document: MedicalDocument) -> Optional[str]:
        """Detect screening type from document content"""
        if not document.content:
            return None
        
        content_lower = document.content.lower()
        
        # Check each screening pattern
        for screening_type, patterns in self.screening_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    return screening_type
        
        return None
    
    def update_existing_documents_with_dual_storage(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Update existing documents to include dual storage keys
        
        Args:
            batch_size: Number of documents to process per batch
            
        Returns:
            Dict with update statistics
        """
        if not MedicalDocument:
            return {"error": "MedicalDocument model not available"}
        
        try:
            stats = {
                "processed": 0,
                "updated": 0,
                "errors": 0,
                "skipped": 0
            }
            
            # Get documents without dual storage keys
            documents = MedicalDocument.query.filter(
                MedicalDocument.tag.is_(None)
            ).limit(batch_size).all()
            
            for document in documents:
                stats["processed"] += 1
                
                try:
                    # Skip if already has keys
                    if document.tag or document.fhir_code_code:
                        stats["skipped"] += 1
                        continue
                    
                    # Extract and set dual storage keys
                    internal_data = self._extract_internal_keys(document)
                    fhir_data = self._extract_fhir_keys(document)
                    
                    # Enhance with document-specific FHIR data
                    if document.document_type in self.document_type_mappings:
                        mapping = self.document_type_mappings[document.document_type]
                        if not fhir_data.get('code'):
                            fhir_data['code'] = mapping['fhir_code']
                        if not fhir_data.get('category'):
                            fhir_data['category'] = mapping['fhir_category']
                    
                    # Set effective datetime
                    if not fhir_data.get('effectiveDateTime'):
                        fhir_data['effectiveDateTime'] = document.document_date or document.created_at
                    
                    # Update document
                    document.set_dual_storage_keys(internal_data, fhir_data)
                    stats["updated"] += 1
                    
                except Exception as e:
                    print(f"Error updating document {document.id}: {str(e)}")
                    stats["errors"] += 1
            
            # Commit all changes
            if stats["updated"] > 0:
                from app import db
                db.session.commit()
                print(f"Updated {stats['updated']} documents with dual storage keys")
            
            return stats
            
        except Exception as e:
            print(f"Error in batch update: {str(e)}")
            return {"error": str(e)}
    
    def search_by_internal_keys(self, tag: str = None, section: str = None, 
                              matched_screening: str = None) -> List[MedicalDocument]:
        """Search documents using internal keys"""
        if not MedicalDocument:
            return []
        
        query = MedicalDocument.query
        
        if tag:
            query = query.filter(MedicalDocument.tag == tag)
        if section:
            query = query.filter(MedicalDocument.section == section)
        if matched_screening:
            query = query.filter(MedicalDocument.matched_screening == matched_screening)
        
        return query.all()
    
    def search_by_fhir_keys(self, code_system: str = None, code_code: str = None,
                          category_code: str = None) -> List[MedicalDocument]:
        """Search documents using FHIR keys"""
        if not MedicalDocument:
            return []
        
        query = MedicalDocument.query
        
        if code_system:
            query = query.filter(MedicalDocument.fhir_code_system == code_system)
        if code_code:
            query = query.filter(MedicalDocument.fhir_code_code == code_code)
        if category_code:
            query = query.filter(MedicalDocument.fhir_category_code == category_code)
        
        return query.all()
    
    def get_document_export_data(self, document_id: int) -> Dict[str, Any]:
        """
        Get document data formatted for both internal and FHIR exports
        
        Args:
            document_id: Document ID
            
        Returns:
            Dict containing both internal and FHIR formatted data
        """
        if not MedicalDocument:
            return {"error": "MedicalDocument model not available"}
        
        document = MedicalDocument.query.get(document_id)
        if not document:
            return {"error": "Document not found"}
        
        return {
            "document_id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,
            "patient_id": document.patient_id,
            "internal_keys": document.get_internal_keys(),
            "fhir_keys": document.get_fhir_keys(),
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "is_dual_storage_enabled": bool(document.tag or document.fhir_code_code)
        }


# Global processor instance
enhanced_processor = EnhancedDocumentProcessor()

# Convenience functions
def process_document_with_dual_storage(document: MedicalDocument, user_id: int = None) -> bool:
    """Process document with automatic dual storage key extraction"""
    return enhanced_processor.process_new_document(document, user_id)

def process_prep_sheet_with_dual_storage(prep_sheet: PrepSheet, 
                                       screening_types: List[str] = None,
                                       user_id: int = None) -> bool:
    """Process prep sheet with automatic dual storage key extraction"""
    return enhanced_processor.process_new_prep_sheet(prep_sheet, screening_types, user_id)

def search_documents_by_internal_keys(tag: str = None, section: str = None, 
                                    matched_screening: str = None):
    """Search documents using internal keys"""
    return enhanced_processor.search_by_internal_keys(tag, section, matched_screening)

def search_documents_by_fhir_keys(code_system: str = None, code_code: str = None,
                                category_code: str = None):
    """Search documents using FHIR keys"""
    return enhanced_processor.search_by_fhir_keys(code_system, code_code, category_code)

def update_legacy_documents(batch_size: int = 100):
    """Update existing documents with dual storage keys"""
    return enhanced_processor.update_existing_documents_with_dual_storage(batch_size)