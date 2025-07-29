#!/usr/bin/env python3
"""
Timeout-Safe Smart Refresh System
Prevents worker timeouts during screening refresh operations
Enhanced with performance optimization integration
"""

import time
from app import app, db
from models import Patient, ScreeningType, Screening, MedicalDocument
from unified_screening_engine import UnifiedScreeningEngine
from performance_optimizer import performance_optimizer
import logging

logger = logging.getLogger(__name__)

class TimeoutSafeRefresh:
    """
    Handles smart refresh operations with timeout protection and batch processing
    """
    
    def __init__(self, max_patients=15, timeout_seconds=180):
        self.max_patients = max_patients
        self.timeout_seconds = timeout_seconds
        self.unified_engine = UnifiedScreeningEngine()
        
    def safe_smart_refresh(self, screening_type_ids=None):
        """
        Perform smart refresh with timeout protection and performance optimization
        
        Args:
            screening_type_ids: Optional list of specific screening type IDs to refresh
        
        Returns:
            tuple: (success_count, total_patients, error_message)
        """
        start_time = time.time()
        
        try:
            # Use performance optimizer for targeted refresh if specific types provided
            if screening_type_ids:
                app.logger.info(f"Using fast selective refresh for screening types: {screening_type_ids}")
                results = performance_optimizer.fast_selective_refresh(screening_type_ids)
                
                if results['success']:
                    return results['patients_processed'], results['patients_processed'], None
                else:
                    return 0, 0, results['error']
            
            # Fallback to original method for general refresh
            success_count = 0
            error_message = None
            
            # Get limited number of patients to prevent timeout
            patients = Patient.query.limit(self.max_patients).all()
            app.logger.info(f"Starting timeout-safe refresh for {len(patients)} patients")
            
            for i, patient in enumerate(patients):
                # Check timeout
                if time.time() - start_time > self.timeout_seconds:
                    error_message = f"Timeout reached after processing {i} patients"
                    break
                
                try:
                    # Process single patient with individual commit
                    patient_success = self._refresh_single_patient(patient.id)
                    if patient_success:
                        success_count += 1
                        
                    # Small pause to prevent database overload
                    time.sleep(0.1)
                    
                except Exception as e:
                    app.logger.error(f"Error processing patient {patient.id}: {e}")
                    db.session.rollback()
                    continue
            
            return success_count, len(patients), error_message
            
        except Exception as e:
            app.logger.error(f"Critical error in safe_smart_refresh: {e}")
            db.session.rollback()
            return 0, 0, str(e)
    
    def _refresh_single_patient(self, patient_id):
        """
        Refresh screenings for a single patient with individual transaction
        
        Args:
            patient_id: Patient ID to refresh
            
        Returns:
            bool: Success status
        """
        try:
            # Generate new screenings
            screenings = self.unified_engine.generate_patient_screenings(patient_id)
            
            if not screenings:
                return True  # No screenings to process is still success
            
            updated_count = 0
            
            # Process each screening
            for screening_data in screenings:
                # Find or create screening
                existing_screening = Screening.query.filter_by(
                    patient_id=screening_data['patient_id'],
                    screening_type=screening_data['screening_type']
                ).first()
                
                if existing_screening:
                    # Update existing
                    existing_screening.status = screening_data['status']
                    # Ensure date fields are date objects, not datetime
                    last_completed = screening_data.get('last_completed')
                    if last_completed and hasattr(last_completed, 'date'):
                        last_completed = last_completed.date()
                    existing_screening.last_completed = last_completed
                    
                    existing_screening.frequency = screening_data.get('frequency')
                    
                    due_date = screening_data.get('due_date')
                    if due_date and hasattr(due_date, 'date'):
                        due_date = due_date.date()
                    existing_screening.due_date = due_date
                else:
                    # Create new - ensure date fields are date objects, not datetime
                    last_completed = screening_data.get('last_completed')
                    if last_completed and hasattr(last_completed, 'date'):
                        last_completed = last_completed.date()
                    
                    due_date = screening_data.get('due_date')
                    if due_date and hasattr(due_date, 'date'):
                        due_date = due_date.date()
                    
                    existing_screening = Screening(
                        patient_id=screening_data['patient_id'],
                        screening_type=screening_data['screening_type'],
                        status=screening_data['status'],
                        last_completed=last_completed,
                        frequency=screening_data.get('frequency'),
                        due_date=due_date
                    )
                    db.session.add(existing_screening)
                
                # Handle document relationships
                if screening_data.get('matched_documents'):
                    # Clear existing relationships safely for AppenderQuery objects
                    # Remove all existing document relationships
                    for doc in list(existing_screening.documents):
                        existing_screening.documents.remove(doc)
                    
                    # Add new relationships
                    for doc_id in screening_data['matched_documents']:
                        document = MedicalDocument.query.get(doc_id)
                        if document:
                            existing_screening.documents.append(document)
                
                updated_count += 1
            
            # Single commit for all patient screenings
            db.session.commit()
            app.logger.info(f"Successfully refreshed {updated_count} screenings for patient {patient_id}")
            return True
            
        except Exception as e:
            app.logger.error(f"Error refreshing patient {patient_id}: {e}")
            db.session.rollback()
            raise

# Global instance
timeout_safe_refresh = TimeoutSafeRefresh()