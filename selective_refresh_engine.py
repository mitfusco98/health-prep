#!/usr/bin/env python3
"""
Selective Refresh Engine
Implements intelligent selective refresh to prevent comprehensive refresh crashes
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from app import db
from models import Patient, Screening, ScreeningType
from unified_screening_engine import unified_engine

logger = logging.getLogger(__name__)

class SelectiveRefreshEngine:
    """Manages selective refresh operations to prevent system crashes"""
    
    def __init__(self):
        self.batch_size = 25  # Process in small batches
        self.timeout_per_patient = 10  # 10 seconds max per patient
        self.max_total_timeout = 300  # 5 minutes total timeout
        
    def selective_patient_refresh(self, patient_ids: List[int] = None, search_query: str = None) -> Dict[str, Any]:
        """
        Perform selective refresh for specific patients or based on search query
        
        Args:
            patient_ids: List of specific patient IDs to refresh
            search_query: Search query to filter patients
            
        Returns:
            Dict with refresh results and metrics
        """
        start_time = datetime.now()
        
        try:
            # Determine patients to refresh
            if patient_ids:
                patients = Patient.query.filter(Patient.id.in_(patient_ids)).all()
            elif search_query:
                patients = Patient.query.filter(
                    (Patient.first_name.ilike(f'%{search_query}%')) |
                    (Patient.last_name.ilike(f'%{search_query}%'))
                ).limit(self.batch_size).all()
            else:
                # For full refresh, process in batches
                patients = Patient.query.limit(self.batch_size).all()
            
            logger.info(f"Starting selective refresh for {len(patients)} patients")
            
            # Process patients with timeout protection
            results = {
                'success': True,
                'patients_processed': 0,
                'screenings_updated': 0,
                'errors': [],
                'duration': 0
            }
            
            for patient in patients:
                # Check total timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self.max_total_timeout:
                    logger.warning(f"Selective refresh timeout after {elapsed}s, stopping")
                    break
                
                try:
                    # Generate screenings for this patient
                    patient_start = datetime.now()
                    screenings = unified_engine.generate_patient_screenings(patient.id)
                    
                    # Check individual patient timeout
                    patient_elapsed = (datetime.now() - patient_start).total_seconds()
                    if patient_elapsed > self.timeout_per_patient:
                        logger.warning(f"Patient {patient.id} took {patient_elapsed}s, skipping")
                        results['errors'].append(f"Patient {patient.id} timed out")
                        continue
                    
                    if screenings:
                        results['screenings_updated'] += len(screenings)
                    
                    results['patients_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error refreshing patient {patient.id}: {e}")
                    results['errors'].append(f"Patient {patient.id}: {str(e)}")
                    continue
            
            # Calculate final metrics
            results['duration'] = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Selective refresh completed: {results['patients_processed']} patients, "
                       f"{results['screenings_updated']} screenings, {len(results['errors'])} errors")
            
            return results
            
        except Exception as e:
            logger.error(f"Selective refresh engine error: {e}")
            return {
                'success': False,
                'error': str(e),
                'patients_processed': 0,
                'screenings_updated': 0,
                'duration': (datetime.now() - start_time).total_seconds()
            }
    
    def selective_screening_type_refresh(self, screening_type_ids: List[int]) -> Dict[str, Any]:
        """
        Refresh screenings for specific screening types only
        
        Args:
            screening_type_ids: List of screening type IDs to refresh
            
        Returns:
            Dict with refresh results
        """
        start_time = datetime.now()
        
        try:
            # Get affected patients (those who have these screening types)
            affected_patients = db.session.query(Patient.id).join(
                Screening, Patient.id == Screening.patient_id
            ).filter(
                Screening.screening_type_id.in_(screening_type_ids)
            ).distinct().limit(self.batch_size).all()
            
            patient_ids = [p[0] for p in affected_patients]
            
            logger.info(f"Selective screening type refresh for {len(patient_ids)} affected patients")
            
            # Use patient refresh for the affected patients
            return self.selective_patient_refresh(patient_ids=patient_ids)
            
        except Exception as e:
            logger.error(f"Selective screening type refresh error: {e}")
            return {
                'success': False,
                'error': str(e),
                'patients_processed': 0,
                'screenings_updated': 0,
                'duration': (datetime.now() - start_time).total_seconds()
            }
    
    def selective_document_triggered_refresh(self, patient_id: int, document_id: int) -> Dict[str, Any]:
        """
        Refresh screenings for a specific patient triggered by document upload/change
        
        Args:
            patient_id: Patient ID whose document changed
            document_id: Document ID that was added/modified
            
        Returns:
            Dict with refresh results
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Document-triggered selective refresh for patient {patient_id}, document {document_id}")
            
            # Only refresh the specific patient
            return self.selective_patient_refresh(patient_ids=[patient_id])
            
        except Exception as e:
            logger.error(f"Document-triggered selective refresh error: {e}")
            return {
                'success': False,
                'error': str(e),
                'patients_processed': 0,
                'screenings_updated': 0,
                'duration': (datetime.now() - start_time).total_seconds()
            }
    
    def get_refresh_recommendations(self) -> Dict[str, Any]:
        """
        Analyze system state and recommend refresh strategy
        
        Returns:
            Dict with refresh recommendations
        """
        try:
            total_patients = Patient.query.count()
            total_screenings = Screening.query.count()
            active_screening_types = ScreeningType.query.filter_by(is_active=True).count()
            
            recommendations = {
                'total_patients': total_patients,
                'total_screenings': total_screenings,
                'active_screening_types': active_screening_types,
                'recommended_batch_size': self.batch_size,
                'estimated_time_minutes': max(1, total_patients / 10)  # Conservative estimate
            }
            
            if total_patients > 50:
                recommendations['strategy'] = 'batch_processing'
                recommendations['message'] = f"Recommend batch processing due to {total_patients} patients"
            else:
                recommendations['strategy'] = 'full_refresh'
                recommendations['message'] = f"Can handle full refresh with {total_patients} patients"
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting refresh recommendations: {e}")
            return {
                'strategy': 'selective_only',
                'message': 'Error analyzing system, recommend selective refresh only'
            }

# Global selective refresh engine instance
selective_refresh_engine = SelectiveRefreshEngine()