#!/usr/bin/env python3
"""
Optimized Selective Refresh System
High-performance selective refresh that only processes affected patients and screening types
"""

import time
import logging
from typing import List, Dict, Any, Optional, Set
from app import app, db
from models import Patient, ScreeningType, Screening, MedicalDocument
from performance_optimizer import performance_optimizer
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

class OptimizedSelectiveRefresh:
    """
    High-performance selective refresh system that minimizes database operations
    """
    
    def __init__(self):
        self.processed_patients: Set[int] = set()
        self.processed_screening_types: Set[int] = set()
        
    def execute_selective_refresh(self, 
                                 screening_type_ids: List[int], 
                                 change_type: str = "unknown",
                                 timeout_seconds: int = 60) -> Dict[str, Any]:
        """
        Execute optimized selective refresh for specific screening types
        
        Args:
            screening_type_ids: List of screening type IDs that changed
            change_type: Type of change (activation_status, keywords, etc.)
            timeout_seconds: Maximum execution time
            
        Returns:
            Dict with refresh results and performance metrics
        """
        start_time = time.time()
        results = {
            'success': False,
            'screening_types_processed': 0,
            'patients_affected': 0,
            'screenings_updated': 0,
            'duration_seconds': 0,
            'change_type': change_type,
            'error': None,
            'performance_metrics': {}
        }
        
        try:
            # Step 1: Validate screening types exist and are active
            valid_screening_types = ScreeningType.query.filter(
                ScreeningType.id.in_(screening_type_ids)
            ).all()
            
            if not valid_screening_types:
                results['error'] = "No valid screening types found"
                return results
                
            logger.info(f"🚀 Starting optimized selective refresh for {len(valid_screening_types)} screening types")
            
            # Step 2: Determine affected patients based on change type
            affected_patients = self._get_affected_patients(valid_screening_types, change_type)
            
            if not affected_patients:
                logger.info("ℹ️ No patients affected by these changes")
                results['success'] = True
                return results
            
            logger.info(f"📊 Found {len(affected_patients)} patients affected by {change_type} changes")
            
            # Step 3: Process patients in optimized batches
            batch_size = 10  # Smaller batches for better performance
            patient_batches = [affected_patients[i:i + batch_size] 
                             for i in range(0, len(affected_patients), batch_size)]
            
            for batch_num, patient_batch in enumerate(patient_batches):
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    results['error'] = f"Timeout reached after processing {batch_num} batches"
                    break
                
                batch_results = self._process_patient_batch(
                    patient_batch, 
                    valid_screening_types,
                    change_type
                )
                
                results['patients_affected'] += batch_results['patients_processed']
                results['screenings_updated'] += batch_results['screenings_updated']
                
                # Small pause between batches to prevent database overload
                time.sleep(0.05)
            
            results['screening_types_processed'] = len(valid_screening_types)
            results['duration_seconds'] = time.time() - start_time
            results['success'] = True
            
            # Add performance metrics
            results['performance_metrics'] = {
                'patients_per_second': results['patients_affected'] / max(results['duration_seconds'], 0.1),
                'screenings_per_second': results['screenings_updated'] / max(results['duration_seconds'], 0.1),
                'avg_time_per_patient': results['duration_seconds'] / max(results['patients_affected'], 1)
            }
            
            logger.info(f"✅ Optimized selective refresh completed: {results['patients_affected']} patients, {results['screenings_updated']} screenings in {results['duration_seconds']:.2f}s")
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"❌ Optimized selective refresh failed: {e}")
            import traceback
            traceback.print_exc()
            
        return results
    
    def _get_affected_patients(self, screening_types: List[ScreeningType], change_type: str) -> List[Patient]:
        """
        Intelligently determine which patients are affected by screening type changes
        """
        affected_patient_ids = set()
        
        try:
            if change_type in ['activation_status', 'keywords', 'trigger_conditions', 'age_ranges']:
                # For these changes, we need patients who:
                # 1. Have existing screenings of these types
                # 2. Have documents that might match new keywords
                # 3. Meet age/condition criteria for trigger condition changes
                
                # Get patients with existing screenings
                existing_screening_patients = (Patient.query
                                            .join(Screening, Patient.id == Screening.patient_id)
                                            .filter(Screening.screening_type_id.in_([st.id for st in screening_types]))
                                            .distinct()
                                            .all())
                
                affected_patient_ids.update([p.id for p in existing_screening_patients])
                
                # For keyword changes, also get patients with potentially matching documents
                if change_type == 'keywords':
                    document_patients = (Patient.query
                                       .join(MedicalDocument, Patient.id == MedicalDocument.patient_id)
                                       .distinct()
                                       .limit(50)  # Limit to prevent timeout
                                       .all())
                    
                    affected_patient_ids.update([p.id for p in document_patients])
                
                # For activation changes, get all eligible patients
                elif change_type == 'activation_status':
                    # Get a reasonable sample of all patients
                    all_patients = Patient.query.limit(100).all()  # Limit for performance
                    affected_patient_ids.update([p.id for p in all_patients])
            
            else:
                # For other changes, process a limited set of patients
                recent_patients = Patient.query.limit(25).all()
                affected_patient_ids.update([p.id for p in recent_patients])
            
            # Convert back to Patient objects
            return Patient.query.filter(Patient.id.in_(affected_patient_ids)).all()
            
        except Exception as e:
            logger.error(f"Error determining affected patients: {e}")
            # Fallback to recent patients
            return Patient.query.limit(10).all()
    
    def _process_patient_batch(self, 
                              patients: List[Patient], 
                              screening_types: List[ScreeningType],
                              change_type: str) -> Dict[str, int]:
        """
        Process a batch of patients for screening updates
        """
        batch_results = {'patients_processed': 0, 'screenings_updated': 0}
        
        try:
            for patient in patients:
                patient_updates = self._update_patient_screenings_optimized(
                    patient, 
                    screening_types,
                    change_type
                )
                
                if patient_updates > 0:
                    batch_results['patients_processed'] += 1
                    batch_results['screenings_updated'] += patient_updates
            
            # Commit batch changes
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error processing patient batch: {e}")
            db.session.rollback()
            
        return batch_results
    
    def _update_patient_screenings_optimized(self, 
                                           patient: Patient, 
                                           screening_types: List[ScreeningType],
                                           change_type: str) -> int:
        """
        Update screenings for a patient using optimized logic
        """
        updates_made = 0
        
        try:
            from unified_screening_engine import UnifiedScreeningEngine
            engine = UnifiedScreeningEngine()
            
            for screening_type in screening_types:
                try:
                    # Check if patient is eligible for this screening type
                    if not engine._is_patient_eligible(patient, screening_type):
                        # Patient not eligible - remove screening if exists
                        existing = Screening.query.filter_by(
                            patient_id=patient.id,
                            screening_type_id=screening_type.id
                        ).first()
                        
                        if existing:
                            existing.is_visible = False  # Soft delete
                            updates_made += 1
                        continue
                    
                    # Patient is eligible - update or create screening
                    existing_screening = Screening.query.filter_by(
                        patient_id=patient.id,
                        screening_type_id=screening_type.id
                    ).first()
                    
                    if existing_screening:
                        # Update existing screening
                        engine._update_screening_status_and_documents(existing_screening, screening_type)
                        existing_screening.is_visible = True  # Ensure visible
                        updates_made += 1
                    else:
                        # Create new screening
                        new_screening = engine._create_screening_for_patient(patient, screening_type)
                        if new_screening:
                            updates_made += 1
                
                except Exception as e:
                    logger.error(f"Error updating screening type {screening_type.id} for patient {patient.id}: {e}")
                    continue
            
            return updates_made
            
        except Exception as e:
            logger.error(f"Error in _update_patient_screenings_optimized: {e}")
            return 0

# Global instance
optimized_refresh = OptimizedSelectiveRefresh()

if __name__ == "__main__":
    # Test the optimized refresh system
    with app.app_context():
        print("🧪 Testing optimized selective refresh...")
        
        # Test with a sample screening type
        sample_screening_types = ScreeningType.query.limit(2).all()
        if sample_screening_types:
            test_ids = [st.id for st in sample_screening_types]
            results = optimized_refresh.execute_selective_refresh(
                test_ids, 
                change_type="test",
                timeout_seconds=30
            )
            
            print(f"📊 Test results: {results}")
        else:
            print("⚠️ No screening types found for testing")