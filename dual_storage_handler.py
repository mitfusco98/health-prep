"""
Dual Storage Handler

Manages dual storage of internal and FHIR keys for documents and prep sheets,
with comprehensive admin logging for all save/delete operations.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Union
from flask import request, session
from flask_login import current_user

try:
    from models import MedicalDocument, PrepSheet, db
    from admin_middleware import log_admin_access
except ImportError:
    # Handle import issues gracefully
    MedicalDocument = PrepSheet = db = None
    log_admin_access = lambda *args, **kwargs: None


class DualStorageHandler:
    """Handles dual storage and admin logging for documents and prep sheets"""
    
    @staticmethod
    def log_document_action(action: str, document: Union[MedicalDocument, PrepSheet], 
                          user_id: Optional[int] = None, additional_details: Dict = None):
        """
        Log document/prep sheet actions to admin log with comprehensive details
        
        Args:
            action: 'document_save', 'document_delete', 'prep_sheet_save', 'prep_sheet_delete'
            document: Document or PrepSheet instance
            user_id: User ID performing the action
            additional_details: Additional details to log
        """
        try:
            # Get user information
            if not user_id and hasattr(current_user, 'id'):
                user_id = current_user.id
            
            # Determine document type
            doc_type = "prep_sheet" if isinstance(document, PrepSheet) else "document"
            
            # Build comprehensive log details
            log_details = {
                "action_type": action,
                "document_type": doc_type,
                "filename": document.filename,
                "patient_id": document.patient_id,
                "document_id": document.id,
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "ip_address": request.remote_addr if request else "system",
                "user_agent": request.headers.get('User-Agent', 'unknown') if request else "system"
            }
            
            # Add document-specific details
            if hasattr(document, 'document_name') and document.document_name:
                log_details["document_name"] = document.document_name
            
            if hasattr(document, 'document_type') and document.document_type:
                log_details["document_type_category"] = document.document_type
            
            if hasattr(document, 'appointment_date') and document.appointment_date:
                log_details["appointment_date"] = document.appointment_date.isoformat()
            
            # Add internal keys
            internal_keys = document.get_internal_keys()
            if any(internal_keys.values()):
                log_details["internal_keys"] = internal_keys
            
            # Add FHIR keys
            fhir_keys = document.get_fhir_keys()
            if any(v for v in fhir_keys.values() if v):
                log_details["fhir_keys"] = fhir_keys
            
            # Add additional details
            if additional_details:
                log_details.update(additional_details)
            
            # Log to admin system
            log_admin_access(
                action=action,
                details=log_details,
                user_id=user_id
            )
            
            print(f"Logged {action}: {document.filename} for patient {document.patient_id}")
            
        except Exception as e:
            print(f"Error logging document action: {str(e)}")
    
    @staticmethod
    def save_document_with_dual_storage(document: MedicalDocument, 
                                      internal_data: Dict = None,
                                      fhir_data: Dict = None,
                                      user_id: Optional[int] = None) -> bool:
        """
        Save document with dual storage keys and admin logging
        
        Args:
            document: MedicalDocument instance
            internal_data: Internal keys like {'tag': 'lab', 'section': 'results'}
            fhir_data: FHIR keys like {'code': {...}, 'category': {...}}
            user_id: User performing the action
            
        Returns:
            bool: Success status
        """
        try:
            # Set dual storage keys
            if internal_data or fhir_data:
                document.set_dual_storage_keys(internal_data, fhir_data)
            
            # Determine if this is a new document
            is_new = document.id is None
            
            # Save to database
            if is_new:
                db.session.add(document)
            
            db.session.commit()
            
            # Log the action
            action = "document_save"
            DualStorageHandler.log_document_action(
                action=action,
                document=document,
                user_id=user_id,
                additional_details={
                    "is_new_document": is_new,
                    "file_size": len(document.content) if document.content else 0,
                    "mime_type": document.mime_type,
                    "source_system": document.source_system
                }
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving document: {str(e)}")
            return False
    
    @staticmethod
    def delete_document_with_logging(document: MedicalDocument, 
                                   user_id: Optional[int] = None) -> bool:
        """
        Delete document with comprehensive admin logging
        
        Args:
            document: MedicalDocument instance to delete
            user_id: User performing the action
            
        Returns:
            bool: Success status
        """
        try:
            # Capture document details before deletion
            doc_details = {
                "document_id": document.id,
                "filename": document.filename,
                "document_name": document.document_name,
                "document_type": document.document_type,
                "patient_id": document.patient_id,
                "internal_keys": document.get_internal_keys(),
                "fhir_keys": document.get_fhir_keys(),
                "created_at": document.created_at.isoformat() if document.created_at else None,
                "updated_at": document.updated_at.isoformat() if document.updated_at else None
            }
            
            # Log before deletion
            DualStorageHandler.log_document_action(
                action="document_delete",
                document=document,
                user_id=user_id,
                additional_details=doc_details
            )
            
            # Delete from database
            db.session.delete(document)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting document: {str(e)}")
            return False
    
    @staticmethod
    def save_prep_sheet_with_dual_storage(prep_sheet: PrepSheet,
                                        internal_data: Dict = None,
                                        fhir_data: Dict = None,
                                        user_id: Optional[int] = None) -> bool:
        """
        Save prep sheet with dual storage keys and admin logging
        
        Args:
            prep_sheet: PrepSheet instance
            internal_data: Internal keys like {'tag': 'prep', 'section': 'preventive'}
            fhir_data: FHIR keys like {'code': {...}, 'category': {...}}
            user_id: User performing the action
            
        Returns:
            bool: Success status
        """
        try:
            # Set dual storage keys
            if internal_data or fhir_data:
                prep_sheet.set_dual_storage_keys(internal_data, fhir_data)
            
            # Determine if this is a new prep sheet
            is_new = prep_sheet.id is None
            
            # Save to database
            if is_new:
                db.session.add(prep_sheet)
            
            db.session.commit()
            
            # Log the action
            action = "prep_sheet_save"
            DualStorageHandler.log_document_action(
                action=action,
                document=prep_sheet,
                user_id=user_id,
                additional_details={
                    "is_new_prep_sheet": is_new,
                    "appointment_date": prep_sheet.appointment_date.isoformat(),
                    "content_length": len(prep_sheet.content) if prep_sheet.content else 0,
                    "file_path": prep_sheet.file_path
                }
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving prep sheet: {str(e)}")
            return False
    
    @staticmethod
    def delete_prep_sheet_with_logging(prep_sheet: PrepSheet,
                                     user_id: Optional[int] = None) -> bool:
        """
        Delete prep sheet with comprehensive admin logging
        
        Args:
            prep_sheet: PrepSheet instance to delete
            user_id: User performing the action
            
        Returns:
            bool: Success status
        """
        try:
            # Capture prep sheet details before deletion
            prep_details = {
                "prep_sheet_id": prep_sheet.id,
                "filename": prep_sheet.filename,
                "appointment_date": prep_sheet.appointment_date.isoformat(),
                "patient_id": prep_sheet.patient_id,
                "internal_keys": prep_sheet.get_internal_keys(),
                "fhir_keys": prep_sheet.get_fhir_keys(),
                "created_at": prep_sheet.created_at.isoformat() if prep_sheet.created_at else None,
                "file_path": prep_sheet.file_path
            }
            
            # Log before deletion
            DualStorageHandler.log_document_action(
                action="prep_sheet_delete",
                document=prep_sheet,
                user_id=user_id,
                additional_details=prep_details
            )
            
            # Delete from database
            db.session.delete(prep_sheet)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting prep sheet: {str(e)}")
            return False
    
    @staticmethod
    def extract_fhir_from_document_metadata(doc_metadata: str) -> Dict:
        """
        Extract FHIR data from document metadata JSON
        
        Args:
            doc_metadata: JSON string containing document metadata
            
        Returns:
            Dict: FHIR data structure for dual storage
        """
        try:
            if not doc_metadata:
                return {}
            
            metadata = json.loads(doc_metadata)
            fhir_data = {}
            
            # Extract FHIR code
            if 'fhir_primary_code' in metadata:
                primary_code = metadata['fhir_primary_code']
                if 'code' in primary_code:
                    fhir_data['code'] = primary_code['code']['coding'][0] if 'coding' in primary_code['code'] else primary_code['code']
            
            # Extract FHIR category
            if 'fhir_category' in metadata:
                fhir_data['category'] = metadata['fhir_category']
            
            # Extract effective date time
            if 'fhir_effective_datetime' in metadata:
                fhir_data['effectiveDateTime'] = datetime.fromisoformat(metadata['fhir_effective_datetime'].replace('Z', '+00:00'))
            
            return fhir_data
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error extracting FHIR data from metadata: {str(e)}")
            return {}
    
    @staticmethod
    def create_prep_sheet_fhir_data(appointment_date: datetime) -> Dict:
        """
        Create standard FHIR data for prep sheets
        
        Args:
            appointment_date: Date of the appointment
            
        Returns:
            Dict: Standard FHIR data for prep sheets
        """
        return {
            'code': {
                'system': 'http://loinc.org',
                'code': '75492-9',
                'display': 'Preventive care note'
            },
            'category': {
                'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                'code': 'survey',
                'display': 'Survey'
            },
            'effectiveDateTime': appointment_date
        }


# Convenience functions for easy integration
def save_document_dual_storage(document: MedicalDocument, 
                             tag: str = None, section: str = None, 
                             matched_screening: str = None,
                             fhir_code: Dict = None, fhir_category: Dict = None,
                             effective_datetime: datetime = None) -> bool:
    """
    Convenience function to save document with dual storage
    
    Args:
        document: MedicalDocument instance
        tag: Internal tag
        section: Internal section
        matched_screening: Internal matched screening
        fhir_code: FHIR code dict
        fhir_category: FHIR category dict
        effective_datetime: FHIR effective datetime
        
    Returns:
        bool: Success status
    """
    internal_data = {
        'tag': tag,
        'section': section,
        'matched_screening': matched_screening
    }
    
    fhir_data = {}
    if fhir_code:
        fhir_data['code'] = fhir_code
    if fhir_category:
        fhir_data['category'] = fhir_category
    if effective_datetime:
        fhir_data['effectiveDateTime'] = effective_datetime
    
    return DualStorageHandler.save_document_with_dual_storage(
        document=document,
        internal_data=internal_data,
        fhir_data=fhir_data
    )

def save_prep_sheet_dual_storage(prep_sheet: PrepSheet,
                                tag: str = "prep_sheet",
                                section: str = "preventive_care",
                                matched_screening: str = None) -> bool:
    """
    Convenience function to save prep sheet with dual storage
    
    Args:
        prep_sheet: PrepSheet instance
        tag: Internal tag (default: "prep_sheet")
        section: Internal section (default: "preventive_care")
        matched_screening: Internal matched screening
        
    Returns:
        bool: Success status
    """
    internal_data = {
        'tag': tag,
        'section': section,
        'matched_screening': matched_screening
    }
    
    # Standard FHIR data for prep sheets
    fhir_data = DualStorageHandler.create_prep_sheet_fhir_data(
        datetime.combine(prep_sheet.appointment_date, datetime.min.time())
    )
    
    return DualStorageHandler.save_prep_sheet_with_dual_storage(
        prep_sheet=prep_sheet,
        internal_data=internal_data,
        fhir_data=fhir_data
    )

def delete_document_with_logging(document: MedicalDocument) -> bool:
    """Convenience function to delete document with logging"""
    return DualStorageHandler.delete_document_with_logging(document)

def delete_prep_sheet_with_logging(prep_sheet: PrepSheet) -> bool:
    """Convenience function to delete prep sheet with logging"""
    return DualStorageHandler.delete_prep_sheet_with_logging(prep_sheet)