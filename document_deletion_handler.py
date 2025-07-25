#!/usr/bin/env python3
"""
Document Deletion Handler - Maintains Screening Status Integrity
Ensures when documents are deleted, dependent screenings automatically update their status
"""

import logging
from typing import List, Dict
from app import app, db
from models import MedicalDocument, Screening, ScreeningType
from unified_screening_engine import UnifiedScreeningEngine

logger = logging.getLogger(__name__)

class DocumentDeletionHandler:
    """
    Handles document deletion cascade logic to maintain screening status integrity
    """
    
    def __init__(self):
        self.engine = UnifiedScreeningEngine()
    
    def handle_document_deletion(self, document_id: int) -> Dict:
        """
        Handle document deletion and update dependent screening statuses
        
        Args:
            document_id: ID of the document being deleted
            
        Returns:
            Dictionary with deletion results and affected screenings
        """
        try:
            # Get the document before deletion
            document = MedicalDocument.query.get(document_id)
            if not document:
                return {'error': 'Document not found', 'affected_screenings': []}
            
            patient_id = document.patient_id
            document_name = document.document_name
            
            # Find all screenings linked to this document
            affected_screenings = []
            from models import screening_documents
            
            # Query the association table to find linked screenings
            linked_screening_ids = db.session.execute(
                db.select(screening_documents.c.screening_id)
                .where(screening_documents.c.document_id == document_id)
            ).scalars().all()
            
            # Get the actual screening objects
            linked_screenings = []
            for screening_id in linked_screening_ids:
                screening = Screening.query.get(screening_id)
                if screening:
                    linked_screenings.append(screening)
                    affected_screenings.append({
                        'screening_id': screening.id,
                        'screening_type': screening.screening_type,
                        'old_status': screening.status,
                        'patient_id': screening.patient_id
                    })
            
            logger.info(f"Document deletion: {document_name} (ID: {document_id}) affects {len(linked_screenings)} screenings")
            
            # Delete the document (this will automatically remove the association table entries)
            db.session.delete(document)
            db.session.flush()  # Ensure deletion is processed
            
            # Now update the affected screenings
            updated_screenings = []
            for screening in linked_screenings:
                try:
                    # Re-evaluate the screening status without the deleted document
                    screening_type = ScreeningType.query.get(screening.screening_type_id)
                    if screening_type:
                        # Get patient
                        from models import Patient
                        patient = Patient.query.get(screening.patient_id)
                        
                        if patient:
                            # Find remaining matching documents
                            remaining_docs = self.engine._find_matching_documents(patient, screening_type)
                            
                            # Determine new status based on remaining documents
                            new_status = self.engine._determine_status_from_documents(remaining_docs, screening_type)
                            
                            # Update screening
                            old_status = screening.status
                            screening.status = new_status
                            screening.last_completed = self.engine._get_last_completed_date(remaining_docs)
                            screening.due_date = self.engine._calculate_due_date(screening_type, remaining_docs)
                            
                            # Clear document relationships and add remaining ones
                            screening.documents.clear()
                            for doc in remaining_docs:
                                screening.documents.append(doc)
                            
                            updated_screenings.append({
                                'screening_id': screening.id,
                                'screening_type': screening.screening_type,
                                'old_status': old_status,
                                'new_status': new_status,
                                'remaining_documents': len(remaining_docs)
                            })
                            
                            logger.info(f"Updated screening {screening.id}: {old_status} -> {new_status} "
                                      f"({len(remaining_docs)} remaining documents)")
                        
                except Exception as e:
                    logger.error(f"Error updating screening {screening.id}: {e}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            return {
                'success': True,
                'deleted_document': {
                    'id': document_id,
                    'name': document_name,
                    'patient_id': patient_id
                },
                'affected_screenings': affected_screenings,
                'updated_screenings': updated_screenings,
                'message': f"Deleted document '{document_name}' and updated {len(updated_screenings)} dependent screenings"
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling document deletion {document_id}: {e}")
            return {
                'error': f"Failed to handle document deletion: {str(e)}",
                'affected_screenings': []
            }
    
    def validate_screening_integrity(self, patient_id: int = None) -> Dict:
        """
        Validate that all screenings have correct status based on their linked documents
        
        Args:
            patient_id: Optional patient ID to check, if None checks all patients
            
        Returns:
            Dictionary with validation results
        """
        try:
            query = Screening.query
            if patient_id:
                query = query.filter_by(patient_id=patient_id)
            
            screenings = query.all()
            integrity_issues = []
            
            for screening in screenings:
                # Get linked documents
                linked_docs = list(screening.documents)
                
                # Get screening type
                screening_type = ScreeningType.query.get(screening.screening_type_id)
                if not screening_type:
                    continue
                
                # Calculate expected status
                expected_status = self.engine._determine_status_from_documents(linked_docs, screening_type)
                
                # Check for mismatch
                if screening.status != expected_status:
                    integrity_issues.append({
                        'screening_id': screening.id,
                        'patient_id': screening.patient_id,
                        'screening_type': screening.screening_type,
                        'current_status': screening.status,
                        'expected_status': expected_status,
                        'linked_documents': len(linked_docs),
                        'document_names': [doc.document_name for doc in linked_docs]
                    })
            
            return {
                'total_screenings_checked': len(screenings),
                'integrity_issues': integrity_issues,
                'issues_found': len(integrity_issues)
            }
            
        except Exception as e:
            logger.error(f"Error validating screening integrity: {e}")
            return {'error': str(e)}

# Global instance
document_deletion_handler = DocumentDeletionHandler()