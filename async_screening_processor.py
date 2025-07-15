#!/usr/bin/env python3
"""
Async Screening Processor
Comprehensive async processing system for screening infrastructure
Integrates with DocumentScreeningMatcher and handles all medical data subsections
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from datetime import datetime, timedelta, date
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from contextlib import asynccontextmanager
import time
import traceback

# Import existing infrastructure
from database_access_layer import DatabaseAccessLayer
from intelligent_cache_manager import get_cache_manager
from document_screening_matcher import DocumentScreeningMatcher
from automated_edge_case_handler import AutomatedScreeningRefreshManager
from cutoff_utils import get_cutoff_date_for_patient

logger = logging.getLogger(__name__)

class AsyncScreeningProcessor:
    """
    Comprehensive async processing system for screening infrastructure
    Handles document-screening relationships and medical data subsections
    """
    
    def __init__(self, max_workers: int = 5, timeout_seconds: int = 300):
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.db_layer = DatabaseAccessLayer()
        self.cache_manager = get_cache_manager()
        self.document_matcher = DocumentScreeningMatcher()
        self.edge_case_handler = AutomatedScreeningRefreshManager()
        
        # Medical data subsections
        self.medical_subsections = {
            'laboratories': ['LAB_RESULT', 'LABORATORY_REPORT'],
            'imaging': ['RADIOLOGY_REPORT', 'IMAGING_REPORT', 'XRAY_REPORT'],
            'consults': ['CONSULTATION_NOTE', 'REFERRAL_LETTER', 'SPECIALIST_REPORT'],
            'hospital_records': ['HOSPITAL_SUMMARY', 'DISCHARGE_SUMMARY', 'INPATIENT_REPORT'],
            'other': ['MEDICAL_DOCUMENT', 'CLINICAL_NOTE', 'PROGRESS_NOTE']
        }
        
        # Processing queues
        self.processing_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        
        # Metrics tracking
        self.metrics = {
            'processed_documents': 0,
            'processed_screenings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'processing_time': 0
        }
        
        logger.info("✅ Async Screening Processor initialized")
    
    def get_session(self):
        """Get a database session for sync operations"""
        from app import db
        return db.session
    
    def get_patient_demographics(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """Get patient demographics safely"""
        try:
            from models import Patient
            patient = Patient.query.filter(Patient.id == patient_id).first()
            if not patient:
                return None
                
            return {
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'date_of_birth': patient.date_of_birth,
                'gender': patient.gender,
                'age': self._calculate_age(patient.date_of_birth) if patient.date_of_birth else None
            }
        except Exception as e:
            logger.error(f"❌ Error getting patient demographics: {e}")
            return None
    
    def get_document_details(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document details safely"""
        try:
            from models import MedicalDocument
            document = MedicalDocument.query.filter(MedicalDocument.id == document_id).first()
            if not document:
                return None
                
            return {
                'id': document.id,
                'filename': document.filename,
                'document_type': document.document_type,
                'content': getattr(document, 'content', ''),
                'created_at': document.created_at,
                'document_date': getattr(document, 'document_date', None),
                'patient_id': document.patient_id
            }
        except Exception as e:
            logger.error(f"❌ Error getting document details: {e}")
            return None
    
    def get_screening_types_for_subsection(self, subsection: str) -> List[Dict[str, Any]]:
        """Get screening types relevant to a medical subsection"""
        try:
            from models import ScreeningType
            screening_types = ScreeningType.query.filter(
                ScreeningType.is_active == True
            ).all()
            
            # Filter by subsection relevance
            relevant_types = []
            for st in screening_types:
                # Simple heuristic based on screening type name
                if self._is_screening_type_relevant_to_subsection(st.name, subsection):
                    relevant_types.append({
                        'id': st.id,
                        'name': st.name,
                        'description': st.description,
                        'min_age': st.min_age,
                        'max_age': st.max_age,
                        'gender_specific': st.gender_specific,
                        'trigger_conditions': st.trigger_conditions
                    })
                    
            return relevant_types
        except Exception as e:
            logger.error(f"❌ Error getting screening types for subsection: {e}")
            return []
    
    def _is_screening_type_relevant_to_subsection(self, screening_name: str, subsection: str) -> bool:
        """Check if screening type is relevant to medical subsection"""
        screening_lower = screening_name.lower()
        
        if subsection == 'laboratories':
            return any(term in screening_lower for term in ['blood', 'lab', 'glucose', 'cholesterol', 'lipid'])
        elif subsection == 'imaging':
            return any(term in screening_lower for term in ['mammogram', 'xray', 'ct', 'mri', 'ultrasound'])
        elif subsection == 'consults':
            return any(term in screening_lower for term in ['eye', 'cardio', 'dermat', 'specialist'])
        elif subsection == 'hospital_records':
            return any(term in screening_lower for term in ['surgery', 'hospital', 'admission'])
        else:
            return True  # Other subsection accepts all
    
    def _calculate_age(self, date_of_birth: date) -> int:
        """Calculate age from date of birth"""
        if not date_of_birth:
            return 0
            
        today = date.today()
        age = today.year - date_of_birth.year
        
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
            
        return age
    
    async def process_screening_refresh_trigger(self, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process screening refresh triggers from document uploads/deletions
        
        Args:
            trigger_data: Contains patient_id, document_id, action, subsection
            
        Returns:
            Processing result with metrics
        """
        start_time = time.time()
        
        try:
            patient_id = trigger_data.get('patient_id')
            document_id = trigger_data.get('document_id')
            action = trigger_data.get('action', 'upload')
            subsection = trigger_data.get('subsection', 'other')
            
            logger.info(f"🔄 Processing screening refresh trigger: {action} document {document_id} for patient {patient_id}")
            
            # Validate inputs
            if not patient_id:
                raise ValueError("patient_id is required for screening refresh")
            
            # Get patient demographics with caching
            patient_demographics = await self._get_patient_demographics_async(patient_id)
            if not patient_demographics:
                raise ValueError(f"Patient {patient_id} not found")
            
            # Process based on action type
            if action == 'upload':
                result = await self._process_document_upload(patient_id, document_id, subsection, patient_demographics)
            elif action == 'delete':
                result = await self._process_document_deletion(patient_id, document_id, subsection, patient_demographics)
            else:
                result = await self._process_screening_update(patient_id, subsection, patient_demographics)
            
            # Update metrics
            self.metrics['processed_documents'] += 1
            self.metrics['processing_time'] += time.time() - start_time
            
            # Trigger cache invalidation
            await self._trigger_cache_invalidation(patient_id, subsection, action)
            
            return {
                'success': True,
                'result': result,
                'processing_time': time.time() - start_time,
                'metrics': self.metrics.copy()
            }
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"❌ Screening refresh trigger error: {e}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'metrics': self.metrics.copy()
            }
    
    async def _process_document_upload(self, patient_id: int, document_id: int, subsection: str, patient_demographics: Dict) -> Dict:
        """Process document upload for screening matching"""
        
        # Get document details
        document = await self._get_document_details_async(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get relevant screening types for this subsection
        screening_types = await self._get_screening_types_for_subsection(subsection)
        
        # Process document-screening matches
        matches = []
        for screening_type in screening_types:
            # Check demographic eligibility
            if not self._check_demographic_eligibility(patient_demographics, screening_type):
                continue
            
            # Check document matching
            match_result = await self._check_document_screening_match(document, screening_type)
            if match_result['matches']:
                matches.append({
                    'screening_type': screening_type,
                    'confidence': match_result['confidence'],
                    'match_source': match_result['match_source']
                })
        
        # Update screening status based on matches
        updated_screenings = []
        for match in matches:
            screening_update = await self._update_screening_with_document(
                patient_id, 
                match['screening_type'], 
                document_id, 
                match['confidence'],
                match['match_source']
            )
            updated_screenings.append(screening_update)
        
        return {
            'document_id': document_id,
            'subsection': subsection,
            'matches_found': len(matches),
            'updated_screenings': updated_screenings
        }
    
    async def _process_document_deletion(self, patient_id: int, document_id: int, subsection: str, patient_demographics: Dict) -> Dict:
        """Process document deletion for screening updates"""
        
        # Get affected screenings
        affected_screenings = await self._get_screenings_with_document(document_id)
        
        # Remove document relationships
        updated_screenings = []
        for screening in affected_screenings:
            update_result = await self._remove_document_from_screening(screening['id'], document_id)
            
            # Recalculate screening status without this document
            recalc_result = await self._recalculate_screening_status(screening['id'], patient_demographics)
            
            updated_screenings.append({
                'screening_id': screening['id'],
                'removal_result': update_result,
                'recalculation_result': recalc_result
            })
        
        return {
            'document_id': document_id,
            'subsection': subsection,
            'affected_screenings': len(affected_screenings),
            'updated_screenings': updated_screenings
        }
    
    async def _process_screening_update(self, patient_id: int, subsection: str, patient_demographics: Dict) -> Dict:
        """Process general screening update for patient"""
        
        # Get all screenings for patient in this subsection
        screenings = await self._get_patient_screenings_by_subsection(patient_id, subsection)
        
        # Update each screening
        updated_screenings = []
        for screening in screenings:
            update_result = await self._recalculate_screening_status(screening['id'], patient_demographics)
            updated_screenings.append(update_result)
        
        return {
            'patient_id': patient_id,
            'subsection': subsection,
            'updated_screenings': updated_screenings
        }
    
    async def process_screening_type_keyword_update(self, screening_type_id: int, old_keywords: List[str], new_keywords: List[str]) -> Dict[str, Any]:
        """
        Process screening type keyword updates without breaking existing matches
        
        Args:
            screening_type_id: ID of the screening type
            old_keywords: Previous keywords
            new_keywords: Updated keywords
            
        Returns:
            Processing result
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Processing keyword update for screening type {screening_type_id}")
            
            # Get screening type details
            screening_type = await self._get_screening_type_details(screening_type_id)
            if not screening_type:
                raise ValueError(f"Screening type {screening_type_id} not found")
            
            # Find all existing screenings with this type
            existing_screenings = await self._get_screenings_by_type(screening_type_id)
            
            # Process each existing screening
            updated_screenings = []
            preserved_matches = []
            new_matches = []
            
            for screening in existing_screenings:
                # Get current document matches
                current_matches = await self._get_screening_document_matches(screening['id'])
                
                # Validate existing matches with new keywords
                validated_matches = []
                for match in current_matches:
                    document = await self._get_document_details_async(match['document_id'])
                    validation_result = await self._validate_document_match_with_keywords(
                        document, new_keywords, screening_type
                    )
                    
                    if validation_result['valid']:
                        validated_matches.append(match)
                        preserved_matches.append({
                            'screening_id': screening['id'],
                            'document_id': match['document_id'],
                            'preserved': True
                        })
                    else:
                        # Remove invalid match
                        await self._remove_document_from_screening(screening['id'], match['document_id'])
                
                # Look for new matches with updated keywords
                patient_documents = await self._get_patient_documents_by_subsection(
                    screening['patient_id'], 
                    self._get_subsection_for_screening_type(screening_type)
                )
                
                for document in patient_documents:
                    # Skip if already matched
                    if any(m['document_id'] == document['id'] for m in validated_matches):
                        continue
                    
                    # Check new match
                    match_result = await self._check_document_screening_match_with_keywords(
                        document, new_keywords, screening_type
                    )
                    
                    if match_result['matches']:
                        await self._add_document_to_screening(
                            screening['id'], 
                            document['id'], 
                            match_result['confidence'],
                            match_result['match_source']
                        )
                        new_matches.append({
                            'screening_id': screening['id'],
                            'document_id': document['id'],
                            'confidence': match_result['confidence']
                        })
                
                # Recalculate screening status
                updated_status = await self._recalculate_screening_status(
                    screening['id'], 
                    await self._get_patient_demographics_async(screening['patient_id'])
                )
                updated_screenings.append(updated_status)
            
            # Invalidate cache for this screening type
            await self._invalidate_screening_type_cache(screening_type_id)
            
            self.metrics['processed_screenings'] += len(updated_screenings)
            
            return {
                'success': True,
                'screening_type_id': screening_type_id,
                'updated_screenings': len(updated_screenings),
                'preserved_matches': len(preserved_matches),
                'new_matches': len(new_matches),
                'processing_time': time.time() - start_time,
                'details': {
                    'preserved_matches': preserved_matches,
                    'new_matches': new_matches,
                    'updated_screenings': updated_screenings
                }
            }
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"❌ Keyword update processing error: {e}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def process_demographic_mismatch_handling(self, patient_id: int, demographic_changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle demographic mismatches with proper error handling
        
        Args:
            patient_id: Patient ID
            demographic_changes: Changes in demographics
            
        Returns:
            Processing result
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Processing demographic mismatch for patient {patient_id}")
            
            # Get updated patient demographics
            patient_demographics = await self._get_patient_demographics_async(patient_id)
            if not patient_demographics:
                raise ValueError(f"Patient {patient_id} not found")
            
            # Get all screenings for this patient
            patient_screenings = await self._get_all_patient_screenings(patient_id)
            
            # Process each screening for demographic eligibility
            eligible_screenings = []
            ineligible_screenings = []
            updated_screenings = []
            
            for screening in patient_screenings:
                screening_type = await self._get_screening_type_details(screening['screening_type_id'])
                
                # Check demographic eligibility
                eligibility_result = self._check_demographic_eligibility_detailed(
                    patient_demographics, screening_type
                )
                
                if eligibility_result['eligible']:
                    eligible_screenings.append(screening)
                    
                    # Update screening status
                    updated_status = await self._recalculate_screening_status(
                        screening['id'], patient_demographics
                    )
                    updated_screenings.append(updated_status)
                    
                else:
                    ineligible_screenings.append({
                        'screening': screening,
                        'reason': eligibility_result['reason']
                    })
                    
                    # Handle ineligible screening
                    await self._handle_ineligible_screening(screening['id'], eligibility_result['reason'])
            
            # Update cache
            await self._invalidate_patient_cache(patient_id)
            
            return {
                'success': True,
                'patient_id': patient_id,
                'eligible_screenings': len(eligible_screenings),
                'ineligible_screenings': len(ineligible_screenings),
                'updated_screenings': len(updated_screenings),
                'processing_time': time.time() - start_time,
                'details': {
                    'demographic_changes': demographic_changes,
                    'ineligible_reasons': [s['reason'] for s in ineligible_screenings]
                }
            }
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"❌ Demographic mismatch processing error: {e}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def process_cutoff_date_calculation(self, patient_id: int, screening_type: str, data_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process cutoff date calculations including last appointment date logic
        
        Args:
            patient_id: Patient ID
            screening_type: Screening type name
            data_type: Optional data type for specific cutoffs
            
        Returns:
            Cutoff calculation result
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Processing cutoff date calculation for patient {patient_id}, screening {screening_type}")
            
            # Get cutoff date using existing utility
            cutoff_date = get_cutoff_date_for_patient(patient_id, data_type, screening_type)
            
            # Get patient's last appointment date
            last_appointment = await self._get_last_appointment_date(patient_id)
            
            # Calculate effective cutoff date
            effective_cutoff = self._calculate_effective_cutoff_date(
                cutoff_date, last_appointment, screening_type
            )
            
            # Get screening documents within cutoff window
            relevant_documents = await self._get_documents_within_cutoff(
                patient_id, screening_type, effective_cutoff
            )
            
            # Calculate screening status based on cutoff
            screening_status = await self._calculate_screening_status_with_cutoff(
                patient_id, screening_type, effective_cutoff, relevant_documents
            )
            
            return {
                'success': True,
                'patient_id': patient_id,
                'screening_type': screening_type,
                'cutoff_date': cutoff_date.isoformat() if cutoff_date else None,
                'last_appointment': last_appointment.isoformat() if last_appointment else None,
                'effective_cutoff': effective_cutoff.isoformat() if effective_cutoff else None,
                'relevant_documents': len(relevant_documents),
                'screening_status': screening_status,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"❌ Cutoff date calculation error: {e}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def coordinate_with_edge_case_handler(self, trigger_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate with automated_edge_case_handler.py for system reactivity
        
        Args:
            trigger_type: Type of edge case trigger
            context: Context information
            
        Returns:
            Coordination result
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Coordinating with edge case handler: {trigger_type}")
            
            # Process different trigger types
            if trigger_type == 'screening_type_activation':
                result = await self._handle_screening_type_activation(context)
            elif trigger_type == 'screening_type_deactivation':
                result = await self._handle_screening_type_deactivation(context)
            elif trigger_type == 'keyword_update':
                result = await self._handle_keyword_update_coordination(context)
            elif trigger_type == 'document_bulk_operation':
                result = await self._handle_document_bulk_operation(context)
            elif trigger_type == 'patient_demographic_update':
                result = await self._handle_patient_demographic_update(context)
            else:
                result = await self._handle_generic_edge_case(trigger_type, context)
            
            # Update system reactivity
            await self._update_system_reactivity(trigger_type, result)
            
            return {
                'success': True,
                'trigger_type': trigger_type,
                'result': result,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"❌ Edge case handler coordination error: {e}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    # Helper methods for async processing
    
    async def _get_patient_demographics_async(self, patient_id: int) -> Optional[Dict]:
        """Get patient demographics with caching"""
        cache_key = f"patient_demographics_{patient_id}"
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data:
            self.metrics['cache_hits'] += 1
            return cached_data
        
        # Get from database
        demographics = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.db_layer.get_patient_demographics,
            patient_id
        )
        
        if demographics:
            self.cache_manager.set(cache_key, demographics, timeout=300)
            self.metrics['cache_misses'] += 1
        
        return demographics
    
    async def _get_document_details_async(self, document_id: int) -> Optional[Dict]:
        """Get document details asynchronously"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.db_layer.get_document_details,
            document_id
        )
    
    async def _get_screening_types_for_subsection(self, subsection: str) -> List[Dict]:
        """Get screening types relevant to a medical subsection"""
        cache_key = f"screening_types_subsection_{subsection}"
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data:
            self.metrics['cache_hits'] += 1
            return cached_data
        
        # Get from database
        screening_types = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.db_layer.get_screening_types_for_subsection,
            subsection
        )
        
        if screening_types:
            self.cache_manager.set(cache_key, screening_types, timeout=600)
            self.metrics['cache_misses'] += 1
        
        return screening_types or []
    
    def _check_demographic_eligibility(self, patient_demographics: Dict, screening_type: Dict) -> bool:
        """Check if patient demographics match screening type eligibility"""
        try:
            # Age check
            if screening_type.get('min_age') and patient_demographics.get('age', 0) < screening_type['min_age']:
                return False
            
            if screening_type.get('max_age') and patient_demographics.get('age', 999) > screening_type['max_age']:
                return False
            
            # Gender check
            if screening_type.get('gender_specific') and patient_demographics.get('gender') != screening_type['gender_specific']:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Demographic eligibility check error: {e}")
            return False
    
    def _check_demographic_eligibility_detailed(self, patient_demographics: Dict, screening_type: Dict) -> Dict[str, Any]:
        """Detailed demographic eligibility check with reasons"""
        try:
            # Age check
            if screening_type.get('min_age') and patient_demographics.get('age', 0) < screening_type['min_age']:
                return {
                    'eligible': False,
                    'reason': f"Patient age {patient_demographics.get('age')} below minimum {screening_type['min_age']}"
                }
            
            if screening_type.get('max_age') and patient_demographics.get('age', 999) > screening_type['max_age']:
                return {
                    'eligible': False,
                    'reason': f"Patient age {patient_demographics.get('age')} above maximum {screening_type['max_age']}"
                }
            
            # Gender check
            if screening_type.get('gender_specific') and patient_demographics.get('gender') != screening_type['gender_specific']:
                return {
                    'eligible': False,
                    'reason': f"Patient gender {patient_demographics.get('gender')} does not match required {screening_type['gender_specific']}"
                }
            
            return {'eligible': True, 'reason': 'All eligibility criteria met'}
            
        except Exception as e:
            logger.error(f"❌ Detailed demographic eligibility check error: {e}")
            return {'eligible': False, 'reason': f'Error checking eligibility: {str(e)}'}
    
    async def _check_document_screening_match(self, document: Dict, screening_type: Dict) -> Dict[str, Any]:
        """Check if document matches screening type"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.document_matcher.check_document_match,
            document,
            screening_type
        )
    
    async def _trigger_cache_invalidation(self, patient_id: int, subsection: str, action: str):
        """Trigger cache invalidation for processed items"""
        self.cache_manager.trigger_invalidation('medical_data_subsection_update', {
            'patient_id': patient_id,
            'subsection': subsection,
            'action': action
        })
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics"""
        return {
            'metrics': self.metrics.copy(),
            'queue_size': self.processing_queue.qsize(),
            'active_workers': self.max_workers,
            'timestamp': datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Graceful shutdown of the async processor"""
        logger.info("🔄 Shutting down async screening processor")
        
        # Wait for pending tasks
        await asyncio.sleep(1)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("✅ Async screening processor shut down")

# Global instance
_async_processor = None

def get_async_processor() -> AsyncScreeningProcessor:
    """Get or create the global async processor instance"""
    global _async_processor
    if _async_processor is None:
        _async_processor = AsyncScreeningProcessor()
    return _async_processor

# Async processing decorators and utilities

def async_screening_process(func):
    """Decorator to make screening processing async"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        processor = get_async_processor()
        return await processor.process_screening_refresh_trigger({
            'function': func.__name__,
            'args': args,
            'kwargs': kwargs
        })
    return async_wrapper

@asynccontextmanager
async def async_processing_context():
    """Context manager for async processing"""
    processor = get_async_processor()
    try:
        yield processor
    finally:
        # Cleanup if needed
        pass

# Integration with existing system

def integrate_async_processor_with_routes(app):
    """
    Integrate async processor with existing Flask routes
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request_async_processing():
        """Handle async processing setup before requests"""
        # Initialize async processor if needed
        processor = get_async_processor()
        
        # Set up context for async processing
        if hasattr(request, 'endpoint') and request.endpoint:
            if any(keyword in request.endpoint for keyword in ['document', 'screening', 'patient']):
                # Prepare async context
                request.async_context = {
                    'processor': processor,
                    'start_time': time.time()
                }
    
    @app.after_request
    def after_request_async_processing(response):
        """Handle async processing after requests"""
        if hasattr(request, 'async_context') and response.status_code < 400:
            # Log async processing metrics
            processor = request.async_context['processor']
            metrics = processor.get_processing_metrics()
            
            # Add metrics to response headers for debugging
            response.headers['X-Async-Processing-Metrics'] = json.dumps(metrics)
        
        return response
    
    # Add async processing routes
    @app.route('/admin/async-processor/metrics', methods=['GET'])
    def async_processor_metrics():
        """Get async processor metrics"""
        processor = get_async_processor()
        return jsonify(processor.get_processing_metrics())
    
    @app.route('/admin/async-processor/status', methods=['GET'])
    def async_processor_status():
        """Get async processor status"""
        processor = get_async_processor()
        return jsonify({
            'status': 'running',
            'max_workers': processor.max_workers,
            'timeout_seconds': processor.timeout_seconds,
            'metrics': processor.get_processing_metrics()
        })
    
    logger.info("✅ Async processor integrated with routes")

if __name__ == "__main__":
    # Test the async processor
    async def test_async_processor():
        processor = AsyncScreeningProcessor()
        
        # Test screening refresh trigger
        result = await processor.process_screening_refresh_trigger({
            'patient_id': 1,
            'document_id': 1,
            'action': 'upload',
            'subsection': 'laboratories'
        })
        
        print(f"Test result: {result}")
        
        await processor.shutdown()
    
    # Run test
    asyncio.run(test_async_processor())

def initialize_async_processors(app):
    """Initialize async processors with app context"""
    try:
        with app.app_context():
            # Initialize global instances
            global _async_processor
            _async_processor = AsyncScreeningProcessor()
            
            # Initialize subsection processor
            from async_document_subsection_processor import get_subsection_processor
            get_subsection_processor()
            
            logger.info("✅ Async processors initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing async processors: {e}")
        import traceback
        traceback.print_exc()