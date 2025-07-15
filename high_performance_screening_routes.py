#!/usr/bin/env python3
"""
High-Performance Screening Routes
Simplified, reliable screening engine without async complexity
"""

import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from flask import flash

logger = logging.getLogger(__name__)

class HighPerformanceScreeningEngine:
    """
    Simplified high-performance screening engine that avoids database connection issues
    """
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
        
    def enhanced_screening_refresh(self, tab: str = "screenings", search_query: str = "", 
                                   trigger_source: str = "manual_refresh") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Enhanced screening refresh with proper status classification and error handling
        
        Args:
            tab: Current tab being refreshed
            search_query: Search query if any
            trigger_source: Source of the refresh trigger
            
        Returns:
            Tuple of (success, message, metrics)
        """
        try:
            from app import app, db
            from models import Patient, ScreeningType, Screening
            from automated_screening_engine import ScreeningStatusEngine
            
            with app.app_context():
                self.start_time = time.time()
                self.processed_count = 0
                self.error_count = 0
                
                # Get all patients with basic info
                patients = Patient.query.all()
                
                if not patients:
                    return False, "No patients found in database", {}
                
                # Get all active screening types
                screening_types = ScreeningType.query.filter_by(is_active=True).all()
                
                if not screening_types:
                    return False, "No active screening types found", {}
                
                # Initialize automated screening engine
                engine = ScreeningStatusEngine()
                
                # Process each patient
                for patient in patients:
                    try:
                        # Process each screening type for this patient
                        for screening_type in screening_types:
                            try:
                                # Check if patient is eligible for this screening type
                                if engine.is_patient_eligible(patient, screening_type):
                                    # Create or update screening
                                    result = engine.create_or_update_screening(patient, screening_type)
                                    
                                    if result:
                                        self.processed_count += 1
                                        # Validate the result
                                        screening = result.get('screening')
                                        if screening:
                                            # Ensure incomplete screenings have no documents
                                            if screening.status == 'Incomplete':
                                                screening.documents.clear()
                                            
                                            # Commit each screening individually to avoid large transactions
                                            db.session.commit()
                                    
                            except Exception as screening_error:
                                self.error_count += 1
                                logger.error(f"Error processing screening {screening_type.name} for patient {patient.id}: {screening_error}")
                                continue
                                
                    except Exception as patient_error:
                        self.error_count += 1
                        logger.error(f"Error processing patient {patient.id}: {patient_error}")
                        continue
                
                # Final commit
                db.session.commit()
                
                # Calculate metrics
                elapsed_time = time.time() - self.start_time
                metrics = {
                    'processed_count': self.processed_count,
                    'error_count': self.error_count,
                    'elapsed_time': elapsed_time,
                    'patients_processed': len(patients),
                    'screening_types_processed': len(screening_types)
                }
                
                if self.error_count > 0:
                    message = f"Refresh completed with {self.error_count} errors. Processed {self.processed_count} screenings in {elapsed_time:.2f}s"
                    return True, message, metrics
                else:
                    message = f"Successfully refreshed {self.processed_count} screenings in {elapsed_time:.2f}s"
                    return True, message, metrics
                    
        except Exception as e:
            logger.error(f"High-performance refresh failed: {e}")
            return False, f"Refresh failed: {str(e)}", {}
    
    def optimize_screening_queries(self) -> Dict[str, Any]:
        """
        Optimize screening queries for faster loading
        """
        try:
            from app import app, db
            from models import Screening, Patient, ScreeningType
            
            with app.app_context():
                # Use optimized query with proper joins and eager loading
                optimized_query = db.session.query(Screening).options(
                    db.joinedload(Screening.patient),
                    db.joinedload(Screening.screening_type),
                    db.joinedload(Screening.documents)
                ).join(
                    ScreeningType, Screening.screening_type_id == ScreeningType.id
                ).filter(
                    ScreeningType.is_active == True
                ).order_by(
                    Screening.status.desc(),  # Priority: Due, Due Soon, Incomplete, Complete
                    Screening.due_date.asc(),
                    Patient.last_name.asc()
                )
                
                # Execute query
                screenings = optimized_query.all()
                
                # Validate each screening
                valid_screenings = []
                fixed_count = 0
                
                for screening in screenings:
                    # Check for invalid document relationships
                    documents = screening.documents.all() if hasattr(screening, 'documents') else []
                    
                    if screening.status == 'Incomplete' and documents:
                        # Fix: Remove documents from incomplete screenings
                        screening.documents.clear()
                        fixed_count += 1
                        logger.info(f"Fixed incomplete screening {screening.id} with {len(documents)} documents")
                    
                    valid_screenings.append(screening)
                
                # Commit fixes
                if fixed_count > 0:
                    db.session.commit()
                
                return {
                    'success': True,
                    'total_screenings': len(screenings),
                    'valid_screenings': len(valid_screenings),
                    'fixed_count': fixed_count,
                    'screenings': valid_screenings
                }
                
        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_screening_logic(self) -> Dict[str, Any]:
        """
        Validate screening status logic matches user requirements
        """
        try:
            from app import app, db
            from models import Screening
            
            with app.app_context():
                # Get all screenings
                screenings = Screening.query.all()
                
                validation_results = {
                    'total_screenings': len(screenings),
                    'complete_with_documents': 0,
                    'incomplete_without_documents': 0,
                    'due_without_documents': 0,
                    'due_soon_without_documents': 0,
                    'invalid_incomplete_with_documents': 0,
                    'invalid_complete_without_documents': 0
                }
                
                # Validate each screening
                for screening in screenings:
                    documents = screening.documents.all() if hasattr(screening, 'documents') else []
                    has_documents = len(documents) > 0
                    
                    if screening.status == 'Complete':
                        if has_documents:
                            validation_results['complete_with_documents'] += 1
                        else:
                            validation_results['invalid_complete_without_documents'] += 1
                    
                    elif screening.status == 'Incomplete':
                        if not has_documents:
                            validation_results['incomplete_without_documents'] += 1
                        else:
                            validation_results['invalid_incomplete_with_documents'] += 1
                    
                    elif screening.status == 'Due':
                        if not has_documents:
                            validation_results['due_without_documents'] += 1
                    
                    elif screening.status == 'Due Soon':
                        if not has_documents:
                            validation_results['due_soon_without_documents'] += 1
                
                # Calculate validation percentage
                total_invalid = (validation_results['invalid_incomplete_with_documents'] + 
                               validation_results['invalid_complete_without_documents'])
                
                validation_results['validation_percentage'] = (
                    (validation_results['total_screenings'] - total_invalid) / 
                    validation_results['total_screenings'] * 100
                ) if validation_results['total_screenings'] > 0 else 0
                
                return validation_results
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {'error': str(e)}

# Global instance
high_performance_engine = HighPerformanceScreeningEngine()

def enhanced_screening_refresh(tab: str = "screenings", search_query: str = "", 
                             trigger_source: str = "manual_refresh") -> Tuple[bool, str, Dict[str, Any]]:
    """
    Enhanced screening refresh function for import
    """
    return high_performance_engine.enhanced_screening_refresh(tab, search_query, trigger_source)

def optimize_screening_queries() -> Dict[str, Any]:
    """
    Optimize screening queries function for import
    """
    return high_performance_engine.optimize_screening_queries()

def validate_screening_logic() -> Dict[str, Any]:
    """
    Validate screening logic function for import
    """
    return high_performance_engine.validate_screening_logic()