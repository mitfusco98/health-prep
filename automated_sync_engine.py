"""
Automated Synchronization Engine
Ensures unified screening engine results are synchronized with database records
"""

from models import Patient, Screening, MedicalDocument, db
from unified_screening_engine import unified_engine
import logging

logger = logging.getLogger(__name__)

class AutomatedSyncEngine:
    """Synchronizes unified engine results with database records"""
    
    def sync_patient_screenings(self, patient_id):
        """Synchronize unified engine results with database for a single patient"""
        try:
            # Get unified engine results
            unified_results = unified_engine.generate_patient_screenings(patient_id)
            
            updates_made = 0
            
            for unified_screening in unified_results:
                screening_type_name = unified_screening.get('screening_type')
                
                # Find corresponding database record
                db_screening = Screening.query.filter_by(
                    patient_id=patient_id,
                    screening_type=screening_type_name
                ).first()
                
                if db_screening:
                    # Check if update is needed
                    unified_status = unified_screening.get('status', 'Incomplete')
                    status_changed = db_screening.status != unified_status
                    
                    matched_doc_ids = unified_screening.get('matched_documents', [])
                    current_doc_ids = [doc.id for doc in db_screening.documents]
                    docs_changed = set(matched_doc_ids) != set(current_doc_ids)
                    
                    if status_changed or docs_changed:
                        # Update status
                        db_screening.status = unified_status
                        
                        # Update last completed date
                        if unified_screening.get('last_completed'):
                            db_screening.last_completed = unified_screening.get('last_completed')
                        
                        # Clear and rebuild document relationships
                        db_screening.documents = []
                        
                        # Add new document relationships
                        for doc_id in matched_doc_ids:
                            doc = MedicalDocument.query.get(doc_id)
                            if doc:
                                db_screening.documents.append(doc)
                        
                        updates_made += 1
                        logger.info(f"Updated {screening_type_name} for patient {patient_id}: {unified_status}")
                        
            if updates_made > 0:
                db.session.commit()
                logger.info(f"Synchronized {updates_made} screenings for patient {patient_id}")
            
            return updates_made
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing patient {patient_id}: {e}")
            return 0
    
    def sync_all_patients(self):
        """Synchronize unified engine results for all patients"""
        try:
            patients = Patient.query.all()
            total_updates = 0
            
            for patient in patients:
                updates = self.sync_patient_screenings(patient.id)
                total_updates += updates
                
            logger.info(f"Synchronized {total_updates} screenings across {len(patients)} patients")
            return total_updates
            
        except Exception as e:
            logger.error(f"Error in system-wide sync: {e}")
            return 0
    
    def sync_after_document_upload(self, patient_id, document_id):
        """Sync screenings after a new document is uploaded"""
        logger.info(f"Syncing screenings after document {document_id} uploaded for patient {patient_id}")
        return self.sync_patient_screenings(patient_id)
    
    def sync_after_screening_type_change(self, screening_type_id):
        """Sync all patients after a screening type is modified"""
        logger.info(f"Syncing all patients after screening type {screening_type_id} was modified")
        return self.sync_all_patients()

# Create global instance
automated_sync_engine = AutomatedSyncEngine()