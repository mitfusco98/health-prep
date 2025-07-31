#!/usr/bin/env python3
"""
Enhanced Cache Service for Healthcare Operations
Implements caching for expensive operations including document processing, OCR results,
prep sheet generation, and screening recommendations with intelligent invalidation.
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from functools import wraps, lru_cache
import threading
import time

from app import app, db
from models import Patient, MedicalDocument, ScreeningType, Screening
from intelligent_cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class HealthcareCacheService:
    """
    Enhanced caching service for expensive healthcare operations
    Built on top of intelligent_cache_manager with healthcare-specific optimizations
    """
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.lock = threading.RLock()
        
        # Cache TTLs (in seconds)
        self.ttls = {
            'document_repository': 3600,      # 1 hour for document lists
            'ocr_results': 86400,             # 24 hours for OCR results
            'prep_sheet': 1800,               # 30 minutes for prep sheets
            'patient_screening_summary': 1800, # 30 minutes for screening summaries
            'document_screening_matches': 3600, # 1 hour for document-screening matches
            'screening_types_active': 7200,   # 2 hours for active screening types
            'patient_demographics': 3600,     # 1 hour for patient demographics
            'medical_document_content': 86400, # 24 hours for document content
        }
        
        # Cache tags for intelligent invalidation
        self.cache_tags = {
            'patient': 'patient_{patient_id}',
            'document': 'document_{document_id}',
            'screening_type': 'screening_type_{screening_type_id}',
            'prep_sheet': 'prep_sheet_{patient_id}',
            'ocr': 'ocr_{document_id}',
        }
        
        logger.info("✅ Enhanced Healthcare Cache Service initialized")
    
    # =============================================================================
    # DOCUMENT REPOSITORY CACHING (addresses 1313ms slow query)
    # =============================================================================
    
    def get_cached_document_repository(self, patient_id: Optional[int] = None, 
                                     filters: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Cache expensive document repository queries
        Addresses the 1313ms slow query seen in logs
        """
        # Create cache key based on parameters
        key_params = {
            'patient_id': patient_id,
            'filters': filters or {}
        }
        cache_key = f"document_repository:{hashlib.md5(json.dumps(key_params, sort_keys=True).encode()).hexdigest()}"
        
        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"📋 Document repository cache HIT for key: {cache_key}")
            return cached_result
        
        logger.debug(f"📋 Document repository cache MISS for key: {cache_key}")
        return None
    
    def cache_document_repository(self, documents: List[Dict[str, Any]], 
                                patient_id: Optional[int] = None, 
                                filters: Optional[Dict[str, Any]] = None) -> None:
        """Cache document repository results with appropriate tags"""
        key_params = {
            'patient_id': patient_id,
            'filters': filters or {}
        }
        cache_key = f"document_repository:{hashlib.md5(json.dumps(key_params, sort_keys=True).encode()).hexdigest()}"
        
        # Determine cache tags
        tags = {'document_repository'}
        if patient_id:
            tags.add(f'patient_{patient_id}')
        
        # Add document-specific tags
        for doc in documents:
            if 'id' in doc:
                tags.add(f"document_{doc['id']}")
        
        self.cache_manager.set(
            cache_key, 
            documents, 
            ttl=self.ttls['document_repository'],
            tags=tags
        )
        logger.debug(f"📋 Cached document repository with {len(documents)} documents")
    
    # =============================================================================
    # OCR RESULTS CACHING
    # =============================================================================
    
    def get_cached_ocr_result(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached OCR results, utilizing the existing ocr_text field in database
        """
        # First check if OCR is already in database
        try:
            document = MedicalDocument.query.get(document_id)
            if document and hasattr(document, 'ocr_text') and document.ocr_text:
                return {
                    'success': True,
                    'text': document.ocr_text,
                    'source': 'database',
                    'cached_at': document.updated_at or document.created_at
                }
        except Exception as e:
            logger.warning(f"Error checking database OCR for document {document_id}: {e}")
        
        # Check memory cache for processing results
        cache_key = f"ocr_result:{document_id}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"🔍 OCR cache HIT for document {document_id}")
            return cached_result
        
        return None
    
    def cache_ocr_result(self, document_id: int, ocr_result: Dict[str, Any]) -> None:
        """
        Cache OCR results both in memory and update database ocr_text field
        """
        cache_key = f"ocr_result:{document_id}"
        tags = {f'document_{document_id}', 'ocr_results'}
        
        # Cache in memory
        self.cache_manager.set(
            cache_key,
            ocr_result,
            ttl=self.ttls['ocr_results'],
            tags=tags
        )
        
        # Update database if successful OCR
        if ocr_result.get('success') and ocr_result.get('text'):
            try:
                document = MedicalDocument.query.get(document_id)
                if document and hasattr(document, 'ocr_text'):
                    document.ocr_text = ocr_result['text']
                    db.session.commit()
                    logger.debug(f"🔍 Saved OCR text to database for document {document_id}")
            except Exception as e:
                logger.error(f"Failed to save OCR to database for document {document_id}: {e}")
                db.session.rollback()
        
        logger.debug(f"🔍 Cached OCR result for document {document_id}")
    
    # =============================================================================
    # PREP SHEET CACHING
    # =============================================================================
    
    def get_cached_prep_sheet(self, patient_id: int, include_documents: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get cached prep sheet data including document matching results
        """
        cache_key = f"prep_sheet:{patient_id}:docs_{include_documents}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"📄 Prep sheet cache HIT for patient {patient_id}")
            return cached_result
        
        return None
    
    def cache_prep_sheet(self, patient_id: int, prep_sheet_data: Dict[str, Any], 
                        include_documents: bool = True) -> None:
        """
        Cache prep sheet data with patient-specific invalidation
        """
        cache_key = f"prep_sheet:{patient_id}:docs_{include_documents}"
        tags = {
            f'patient_{patient_id}',
            f'prep_sheet_{patient_id}',
            'prep_sheets'
        }
        
        # Add document tags if prep sheet includes document analysis
        if include_documents and 'document_based_screenings' in prep_sheet_data:
            doc_matches = prep_sheet_data['document_based_screenings'].get('document_matches', {})
            for screening_type, matches in doc_matches.items():
                for match in matches.get('matched_documents', []):
                    if 'id' in match:
                        tags.add(f"document_{match['id']}")
        
        self.cache_manager.set(
            cache_key,
            prep_sheet_data,
            ttl=self.ttls['prep_sheet'],
            tags=tags
        )
        logger.debug(f"📄 Cached prep sheet for patient {patient_id}")
    
    # =============================================================================
    # PATIENT SCREENING SUMMARY CACHING
    # =============================================================================
    
    def get_cached_patient_screening_summary(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached patient screening summary (used in multiple places)
        """
        cache_key = f"patient_screening_summary:{patient_id}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"👤 Patient screening summary cache HIT for patient {patient_id}")
            return cached_result
        
        return None
    
    def cache_patient_screening_summary(self, patient_id: int, summary_data: Dict[str, Any]) -> None:
        """
        Cache patient screening summary with screening-specific tags
        """
        cache_key = f"patient_screening_summary:{patient_id}"
        tags = {
            f'patient_{patient_id}',
            'patient_screening_summaries'
        }
        
        # Add screening type tags
        if 'screenings' in summary_data:
            for screening in summary_data['screenings']:
                if 'screening_type_id' in screening:
                    tags.add(f"screening_type_{screening['screening_type_id']}")
        
        self.cache_manager.set(
            cache_key,
            summary_data,
            ttl=self.ttls['patient_screening_summary'],
            tags=tags
        )
        logger.debug(f"👤 Cached screening summary for patient {patient_id}")
    
    # =============================================================================
    # DOCUMENT-SCREENING MATCHING CACHING
    # =============================================================================
    
    def get_cached_document_screening_matches(self, patient_id: int, document_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached document-screening matching results (expensive operation)
        """
        cache_key = f"doc_screening_matches:{patient_id}"
        if document_id:
            cache_key += f":doc_{document_id}"
        
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"🔗 Document-screening matches cache HIT for patient {patient_id}")
            return cached_result
        
        return None
    
    def cache_document_screening_matches(self, patient_id: int, matches_data: Dict[str, Any], 
                                       document_id: Optional[int] = None) -> None:
        """
        Cache document-screening matching results
        """
        cache_key = f"doc_screening_matches:{patient_id}"
        if document_id:
            cache_key += f":doc_{document_id}"
        
        tags = {
            f'patient_{patient_id}',
            'document_screening_matches'
        }
        
        if document_id:
            tags.add(f'document_{document_id}')
        
        # Add screening type tags from matches
        if 'screening_recommendations' in matches_data:
            for rec in matches_data['screening_recommendations']:
                if 'screening_type_id' in rec:
                    tags.add(f"screening_type_{rec['screening_type_id']}")
        
        self.cache_manager.set(
            cache_key,
            matches_data,
            ttl=self.ttls['document_screening_matches'],
            tags=tags
        )
        logger.debug(f"🔗 Cached document-screening matches for patient {patient_id}")
    
    # =============================================================================
    # SCREENING TYPES CACHING
    # =============================================================================
    
    @lru_cache(maxsize=128)
    def get_active_screening_types(self) -> List[Dict[str, Any]]:
        """
        Cache active screening types using LRU cache (frequently accessed)
        """
        try:
            # Ensure we're in an application context
            if not app.app_context:
                logger.warning("No Flask application context available for screening types cache")
                return []
                
            screening_types = ScreeningType.query.filter_by(is_active=True, status='active').all()
            return [
                {
                    'id': st.id,
                    'name': st.name,
                    'min_age': st.min_age,
                    'max_age': st.max_age,
                    'gender_specific': st.gender_specific,
                    'filename_keywords': st.filename_keywords,
                    'content_keywords': st.content_keywords,
                    'trigger_conditions': st.trigger_conditions
                }
                for st in screening_types
            ]
        except Exception as e:
            logger.error(f"Error getting active screening types: {e}")
            return []
    
    def invalidate_screening_types_cache(self):
        """Invalidate the LRU cache for screening types"""
        self.get_active_screening_types.cache_clear()
        logger.debug("🔄 Cleared screening types LRU cache")
    
    # =============================================================================
    # MEDICAL DOCUMENT CONTENT CACHING
    # =============================================================================
    
    def get_cached_document_content(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        Cache medical document content and metadata
        """
        cache_key = f"document_content:{document_id}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"📄 Document content cache HIT for document {document_id}")
            return cached_result
        
        return None
    
    def cache_document_content(self, document_id: int, content_data: Dict[str, Any]) -> None:
        """
        Cache document content with document-specific tags
        """
        cache_key = f"document_content:{document_id}"
        tags = {
            f'document_{document_id}',
            'document_content'
        }
        
        # Add patient tag if available
        if 'patient_id' in content_data:
            tags.add(f"patient_{content_data['patient_id']}")
        
        self.cache_manager.set(
            cache_key,
            content_data,
            ttl=self.ttls['medical_document_content'],
            tags=tags
        )
        logger.debug(f"📄 Cached document content for document {document_id}")
    
    # =============================================================================
    # CACHE INVALIDATION HELPERS
    # =============================================================================
    
    def invalidate_patient_cache(self, patient_id: int) -> None:
        """
        Invalidate all cache entries for a specific patient
        """
        tags_to_invalidate = [
            f'patient_{patient_id}',
            f'prep_sheet_{patient_id}'
        ]
        
        for tag in tags_to_invalidate:
            self.cache_manager.invalidate_by_tag(tag)
        
        logger.debug(f"🔄 Invalidated all cache for patient {patient_id}")
    
    def invalidate_document_cache(self, document_id: int) -> None:
        """
        Invalidate all cache entries for a specific document
        """
        tags_to_invalidate = [
            f'document_{document_id}',
            f'ocr_{document_id}'
        ]
        
        for tag in tags_to_invalidate:
            self.cache_manager.invalidate_by_tag(tag)
        
        logger.debug(f"🔄 Invalidated all cache for document {document_id}")
    
    def invalidate_screening_type_cache(self, screening_type_id: int) -> None:
        """
        Invalidate all cache entries for a specific screening type
        """
        self.cache_manager.invalidate_by_tag(f'screening_type_{screening_type_id}')
        self.invalidate_screening_types_cache()  # Clear LRU cache too
        logger.debug(f"🔄 Invalidated all cache for screening type {screening_type_id}")
    
    # =============================================================================
    # CACHE STATISTICS AND MONITORING
    # =============================================================================
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics including healthcare-specific metrics
        """
        base_stats = self.cache_manager.get_stats()
        
        # Add healthcare-specific statistics
        healthcare_stats = {
            'active_screening_types_cache_info': self.get_active_screening_types.cache_info()._asdict(),
            'cache_ttls': self.ttls,
            'total_tags': len(self.cache_manager.tag_registry) if hasattr(self.cache_manager, 'tag_registry') else 0,
        }
        
        return {
            **base_stats,
            'healthcare_specific': healthcare_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def warm_healthcare_caches(self) -> Dict[str, bool]:
        """
        Warm up frequently accessed caches
        """
        results = {}
        
        try:
            # Warm up active screening types
            screening_types = self.get_active_screening_types()
            results['screening_types'] = len(screening_types) > 0
            logger.info(f"🔥 Warmed screening types cache: {len(screening_types)} types")
        except Exception as e:
            logger.error(f"Failed to warm screening types cache: {e}")
            results['screening_types'] = False
        
        return results


# Global instance
_healthcare_cache_service = None
_cache_lock = threading.Lock()

def get_healthcare_cache_service() -> HealthcareCacheService:
    """
    Get or create the global healthcare cache service instance
    Thread-safe singleton pattern
    """
    global _healthcare_cache_service
    
    if _healthcare_cache_service is None:
        with _cache_lock:
            if _healthcare_cache_service is None:
                _healthcare_cache_service = HealthcareCacheService()
    
    return _healthcare_cache_service


# =============================================================================
# CACHING DECORATORS FOR EXPENSIVE OPERATIONS
# =============================================================================

def cache_expensive_operation(cache_key_func, ttl=3600, tags_func=None):
    """
    Decorator to cache expensive operations with automatic invalidation
    
    Args:
        cache_key_func: Function to generate cache key from function args
        ttl: Time to live in seconds
        tags_func: Function to generate cache tags from function args
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_service = get_healthcare_cache_service()
            
            # Generate cache key
            cache_key = cache_key_func(*args, **kwargs)
            
            # Try to get from cache
            cached_result = cache_service.cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"⚡ Cache HIT for {func.__name__}: {cache_key}")
                return cached_result
            
            # Execute function
            logger.debug(f"⚡ Cache MISS for {func.__name__}: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache result
            tags = tags_func(*args, **kwargs) if tags_func else set()
            cache_service.cache_manager.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        return wrapper
    return decorator