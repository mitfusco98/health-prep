"""
Dual Storage System for Documents and Prep Sheets

Maintains both internal keys (tag, section, matched_screening) and FHIR-style keys 
(code.coding.code, category, effectiveDateTime) to support legacy code and FHIR exports.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from fhir_object_mappers import document_to_fhir_document_reference
from enhanced_parser_integration import extract_tags_from_document
from admin_middleware import log_admin_access


class DualStorageManager:
    """
    Manages dual storage of document metadata with both internal and FHIR keys
    """
    
    def __init__(self):
        self.internal_keys = [
            'tag', 'section', 'matched_screening', 'document_type', 
            'extracted_tags', 'classification', 'confidence_score'
        ]
        self.fhir_keys = [
            'code', 'category', 'type', 'effectiveDateTime', 'status',
            'author', 'custodian', 'content', 'subject'
        ]
    
    def create_dual_metadata(self, document, content: str = None, filename: str = None) -> Dict[str, Any]:
        """
        Create metadata with both internal and FHIR-style keys
        
        Args:
            document: Document object
            content: Document content for analysis
            filename: Document filename
            
        Returns:
            Dual-key metadata dictionary
        """
        metadata = {
            # Internal keys (legacy compatibility)
            'internal': {},
            # FHIR-style keys (standards compliance)
            'fhir': {},
            # Metadata about the dual storage
            'storage_info': {
                'created_at': datetime.utcnow().isoformat(),
                'storage_version': '1.0',
                'has_internal_keys': True,
                'has_fhir_keys': True
            }
        }
        
        # Extract FHIR codes using enhanced parser
        if content or filename:
            fhir_codes = extract_tags_from_document(content or "", filename)
            
            # Internal keys (existing format)
            metadata['internal'] = {
                'tag': self._extract_legacy_tag(document.document_type),
                'section': self._map_to_internal_section(document.document_type),
                'matched_screening': self._find_matched_screening(fhir_codes),
                'document_type': document.document_type,
                'extracted_tags': self._format_legacy_tags(fhir_codes),
                'classification': document.document_type.lower().replace(' ', '_'),
                'confidence_score': 0.95,
                'source_system': document.source_system,
                'provider': document.provider
            }
            
            # FHIR-style keys (standards format)
            fhir_doc_ref = document_to_fhir_document_reference(document)
            metadata['fhir'] = {
                'code': fhir_codes.get('code', fhir_doc_ref.get('type', {})),
                'category': fhir_doc_ref.get('category', []),
                'type': fhir_doc_ref.get('type', {}),
                'effectiveDateTime': (document.document_date or document.created_at).isoformat(),
                'status': 'current',
                'author': fhir_doc_ref.get('author', []),
                'custodian': fhir_doc_ref.get('custodian', {}),
                'content': fhir_doc_ref.get('content', []),
                'subject': {
                    'reference': f'Patient/{document.patient_id}',
                    'display': f'Patient {document.patient_id}'
                }
            }
        
        return metadata
    
    def save_document_with_dual_metadata(self, document, content: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        Save document with both internal and FHIR metadata, log admin action
        
        Args:
            document: MedicalDocument object
            content: Document content for analysis
            user_id: User performing the action
            
        Returns:
            Result dictionary with storage information
        """
        try:
            # Create dual metadata
            dual_metadata = self.create_dual_metadata(document, content, document.filename)
            
            # Store in document
            document.doc_metadata = json.dumps(dual_metadata)
            document.is_processed = True
            document.updated_at = datetime.utcnow()
            
            # Log admin action
            log_details = {
                'action': 'document_saved_dual_storage',
                'document_id': document.id,
                'patient_id': document.patient_id,
                'filename': document.filename,
                'document_name': document.document_name,
                'document_type': document.document_type,
                'internal_keys': list(dual_metadata['internal'].keys()),
                'fhir_keys': list(dual_metadata['fhir'].keys()),
                'storage_version': dual_metadata['storage_info']['storage_version'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
            log_admin_access(
                action="Document Saved with Dual Storage",
                details=log_details,
                user_id=user_id
            )
            
            return {
                'success': True,
                'document_id': document.id,
                'storage_type': 'dual',
                'internal_keys_count': len(dual_metadata['internal']),
                'fhir_keys_count': len(dual_metadata['fhir']),
                'logged': True
            }
            
        except Exception as e:
            # Log error
            log_admin_access(
                action="Document Save Error",
                details={
                    'error': str(e),
                    'document_id': getattr(document, 'id', None),
                    'filename': getattr(document, 'filename', None),
                    'timestamp': datetime.utcnow().isoformat()
                },
                user_id=user_id
            )
            
            return {
                'success': False,
                'error': str(e),
                'logged': True
            }
    
    def get_metadata_by_key_type(self, document, key_type: str = 'both') -> Dict[str, Any]:
        """
        Retrieve metadata by key type (internal, fhir, or both)
        
        Args:
            document: MedicalDocument object
            key_type: 'internal', 'fhir', or 'both'
            
        Returns:
            Metadata dictionary filtered by key type
        """
        if not document.doc_metadata:
            return {}
        
        try:
            metadata = json.loads(document.doc_metadata)
            
            if key_type == 'internal':
                return metadata.get('internal', {})
            elif key_type == 'fhir':
                return metadata.get('fhir', {})
            else:
                return metadata
                
        except json.JSONDecodeError:
            return {}
    
    def migrate_legacy_metadata(self, document) -> Dict[str, Any]:
        """
        Migrate existing document metadata to dual-key format
        
        Args:
            document: MedicalDocument object with legacy metadata
            
        Returns:
            Migration result
        """
        if not document.doc_metadata:
            return {'success': False, 'reason': 'No existing metadata'}
        
        try:
            existing_metadata = json.loads(document.doc_metadata)
            
            # Check if already in dual format
            if 'internal' in existing_metadata and 'fhir' in existing_metadata:
                return {'success': False, 'reason': 'Already in dual format'}
            
            # Create new dual metadata
            dual_metadata = self.create_dual_metadata(document, document.content, document.filename)
            
            # Preserve any existing custom fields
            if isinstance(existing_metadata, dict):
                dual_metadata['legacy'] = existing_metadata
            
            # Update document
            document.doc_metadata = json.dumps(dual_metadata)
            
            return {
                'success': True,
                'migrated_from': 'legacy',
                'preserved_fields': len(existing_metadata) if isinstance(existing_metadata, dict) else 0
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Helper methods for internal key generation
    
    def _extract_legacy_tag(self, document_type: str) -> str:
        """Extract legacy tag format from document type"""
        tag_mapping = {
            'Lab Report': 'lab',
            'Radiology Report': 'imaging',
            'Clinical Note': 'note',
            'Discharge Summary': 'discharge',
            'Consultation': 'consult',
            'Operative Report': 'procedure',
            'Pathology Report': 'pathology'
        }
        return tag_mapping.get(document_type, 'document')
    
    def _map_to_internal_section(self, document_type: str) -> str:
        """Map document type to internal section"""
        section_mapping = {
            'Lab Report': 'labs',
            'Radiology Report': 'imaging',
            'Clinical Note': 'notes',
            'Discharge Summary': 'summaries',
            'Consultation': 'consults',
            'Operative Report': 'procedures',
            'Pathology Report': 'pathology'
        }
        return section_mapping.get(document_type, 'documents')
    
    def _find_matched_screening(self, fhir_codes: Dict[str, Any]) -> Optional[str]:
        """Find matched screening type from FHIR codes"""
        if not fhir_codes or 'code' not in fhir_codes:
            return None
        
        # Map LOINC codes to screening types
        loinc_to_screening = {
            '4548-4': 'hba1c',
            '57698-3': 'lipid_panel',
            '24604-1': 'mammogram',
            '2857-1': 'psa_test',
            '36643-5': 'chest_xray'
        }
        
        try:
            coding = fhir_codes['code']['coding'][0]
            loinc_code = coding.get('code')
            return loinc_to_screening.get(loinc_code)
        except (KeyError, IndexError, TypeError):
            return None
    
    def _format_legacy_tags(self, fhir_codes: Dict[str, Any]) -> List[str]:
        """Format FHIR codes as legacy tag list"""
        if not fhir_codes or 'code' not in fhir_codes:
            return []
        
        try:
            coding = fhir_codes['code']['coding'][0]
            return [coding.get('display', '').lower().replace(' ', '_')]
        except (KeyError, IndexError, TypeError):
            return []


class PrepSheetDualStorage:
    """
    Manages dual storage for prep sheet data
    """
    
    def __init__(self):
        self.dual_manager = DualStorageManager()
    
    def save_prep_sheet_with_dual_keys(self, patient_id: int, prep_data: Dict[str, Any], 
                                     filename: str, user_id: int = None) -> Dict[str, Any]:
        """
        Save prep sheet with both internal and FHIR keys
        
        Args:
            patient_id: Patient ID
            prep_data: Prep sheet data
            filename: Generated filename
            user_id: User generating the prep sheet
            
        Returns:
            Storage result
        """
        try:
            # Create dual-key prep sheet metadata
            prep_metadata = {
                'internal': {
                    'patient_id': patient_id,
                    'generated_at': datetime.utcnow().isoformat(),
                    'filename': filename,
                    'sections': self._extract_internal_sections(prep_data),
                    'screening_count': self._count_screenings(prep_data),
                    'document_count': self._count_documents(prep_data),
                    'prep_type': 'comprehensive'
                },
                'fhir': {
                    'resourceType': 'Bundle',
                    'type': 'document',
                    'subject': {
                        'reference': f'Patient/{patient_id}',
                        'display': f'Patient {patient_id}'
                    },
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'author': [{
                        'reference': f'User/{user_id}' if user_id else 'System/prep-generator',
                        'display': f'User {user_id}' if user_id else 'Prep Sheet Generator'
                    }],
                    'title': f'Preparation Sheet for Patient {patient_id}',
                    'status': 'final',
                    'date': datetime.utcnow().isoformat() + 'Z'
                },
                'storage_info': {
                    'created_at': datetime.utcnow().isoformat(),
                    'storage_version': '1.0',
                    'content_type': 'prep_sheet'
                }
            }
            
            # Log admin action for prep sheet generation
            log_details = {
                'action': 'prep_sheet_generated_dual_storage',
                'patient_id': patient_id,
                'filename': filename,
                'internal_sections': prep_metadata['internal']['sections'],
                'fhir_resource_type': prep_metadata['fhir']['resourceType'],
                'screening_count': prep_metadata['internal']['screening_count'],
                'document_count': prep_metadata['internal']['document_count'],
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id
            }
            
            log_admin_access(
                action="Prep Sheet Generated with Dual Storage",
                details=log_details,
                user_id=user_id
            )
            
            return {
                'success': True,
                'patient_id': patient_id,
                'filename': filename,
                'metadata': prep_metadata,
                'storage_type': 'dual',
                'logged': True
            }
            
        except Exception as e:
            # Log error
            log_admin_access(
                action="Prep Sheet Generation Error",
                details={
                    'error': str(e),
                    'patient_id': patient_id,
                    'filename': filename,
                    'timestamp': datetime.utcnow().isoformat()
                },
                user_id=user_id
            )
            
            return {
                'success': False,
                'error': str(e),
                'logged': True
            }
    
    def _extract_internal_sections(self, prep_data: Dict[str, Any]) -> List[str]:
        """Extract internal section names from prep data"""
        sections = []
        if 'screenings' in prep_data:
            sections.append('screenings')
        if 'conditions' in prep_data:
            sections.append('conditions')
        if 'vitals' in prep_data:
            sections.append('vitals')
        if 'documents' in prep_data:
            sections.append('documents')
        if 'immunizations' in prep_data:
            sections.append('immunizations')
        return sections
    
    def _count_screenings(self, prep_data: Dict[str, Any]) -> int:
        """Count screenings in prep data"""
        screenings = prep_data.get('screenings', [])
        return len(screenings) if isinstance(screenings, list) else 0
    
    def _count_documents(self, prep_data: Dict[str, Any]) -> int:
        """Count documents in prep data"""
        documents = prep_data.get('documents', [])
        return len(documents) if isinstance(documents, list) else 0


# Global instances
dual_storage_manager = DualStorageManager()
prep_sheet_dual_storage = PrepSheetDualStorage()


# Convenience functions for easy integration
def save_document_dual_keys(document, content: str = None, user_id: int = None) -> Dict[str, Any]:
    """Save document with dual-key metadata"""
    return dual_storage_manager.save_document_with_dual_metadata(document, content, user_id)

def save_prep_sheet_dual_keys(patient_id: int, prep_data: Dict[str, Any], 
                            filename: str, user_id: int = None) -> Dict[str, Any]:
    """Save prep sheet with dual-key metadata"""
    return prep_sheet_dual_storage.save_prep_sheet_with_dual_keys(patient_id, prep_data, filename, user_id)

def get_document_metadata(document, key_type: str = 'both') -> Dict[str, Any]:
    """Get document metadata by key type"""
    return dual_storage_manager.get_metadata_by_key_type(document, key_type)

def migrate_document_metadata(document) -> Dict[str, Any]:
    """Migrate legacy metadata to dual-key format"""
    return dual_storage_manager.migrate_legacy_metadata(document)