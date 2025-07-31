#!/usr/bin/env python3
"""
Cached Operations Implementation
Implements caching for the most expensive operations in the healthcare system
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib
import json

from app import app, db
from models import Patient, MedicalDocument, ScreeningType, Screening
from enhanced_cache_service import get_healthcare_cache_service, cache_expensive_operation

logger = logging.getLogger(__name__)


# =============================================================================
# CACHED DOCUMENT REPOSITORY (addresses 1313ms slow query)
# =============================================================================

def get_cached_documents_for_patient(patient_id: int, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Cached version of expensive document repository query
    Addresses the 1313ms slow query seen in automatic updates
    """
    cache_service = get_healthcare_cache_service()
    
    # Try cache first
    cached_docs = cache_service.get_cached_document_repository(patient_id, filters)
    if cached_docs is not None:
        return cached_docs
    
    # Execute expensive query
    try:
        query = MedicalDocument.query.filter_by(patient_id=patient_id)
        
        # Apply filters
        if filters:
            if 'document_type' in filters:
                query = query.filter(MedicalDocument.document_type == filters['document_type'])
            if 'date_from' in filters:
                query = query.filter(MedicalDocument.created_at >= filters['date_from'])
            if 'date_to' in filters:
                query = query.filter(MedicalDocument.created_at <= filters['date_to'])
        
        documents = query.order_by(MedicalDocument.created_at.desc()).all()
        
        # Convert to serializable format
        doc_data = []
        for doc in documents:
            doc_dict = {
                'id': doc.id,
                'filename': doc.filename,
                'document_name': doc.document_name,
                'document_type': doc.document_type,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                'document_date': doc.document_date.isoformat() if hasattr(doc, 'document_date') and doc.document_date else None,
                'patient_id': doc.patient_id,
                'is_binary': getattr(doc, 'is_binary', False),
                'mime_type': getattr(doc, 'mime_type', None),
                'has_ocr_text': bool(getattr(doc, 'ocr_text', None))
            }
            doc_data.append(doc_dict)
        
        # Cache the results
        cache_service.cache_document_repository(doc_data, patient_id, filters)
        
        logger.info(f"📋 Loaded and cached {len(doc_data)} documents for patient {patient_id}")
        return doc_data
        
    except Exception as e:
        logger.error(f"Error loading documents for patient {patient_id}: {e}")
        return []


def get_cached_all_documents_repository(page: int = 1, per_page: int = 50, 
                                      search_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Cached version of expensive all documents repository query
    """
    cache_service = get_healthcare_cache_service()
    
    # Create cache key
    key_params = {'page': page, 'per_page': per_page, 'search': search_query}
    cache_key = f"all_docs_repo:{hashlib.md5(json.dumps(key_params, sort_keys=True).encode()).hexdigest()}"
    
    # Try cache first
    cached_result = cache_service.cache_manager.get(cache_key)
    if cached_result:
        logger.debug(f"📋 All documents repository cache HIT for page {page}")
        return cached_result
    
    # Execute expensive query
    try:
        query = MedicalDocument.query
        
        # Apply search filter
        if search_query:
            search_filter = f"%{search_query}%"
            query = query.join(Patient).filter(
                db.or_(
                    MedicalDocument.filename.ilike(search_filter),
                    MedicalDocument.document_name.ilike(search_filter),
                    Patient.first_name.ilike(search_filter),
                    Patient.last_name.ilike(search_filter)
                )
            )
        
        # Paginate
        paginated = query.order_by(MedicalDocument.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Convert to serializable format with full patient information
        documents_data = []
        for doc in paginated.items:
            # Get patient information
            patient_first = doc.patient.first_name if doc.patient else "Unknown"
            patient_last = doc.patient.last_name if doc.patient else "Patient"
            
            doc_dict = {
                'id': doc.id,
                'filename': doc.filename,
                'document_name': doc.document_name,
                'document_type': doc.document_type,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                'document_date': doc.document_date.isoformat() if hasattr(doc, 'document_date') and doc.document_date else None,
                'patient_id': doc.patient_id,
                'patient_name': f"{patient_first} {patient_last}",
                'patient_first_name': patient_first,
                'patient_last_name': patient_last,
                'has_ocr_text': bool(getattr(doc, 'ocr_text', None)),
                'is_binary': getattr(doc, 'is_binary', False),
                'mime_type': getattr(doc, 'mime_type', None),
                'source_system': getattr(doc, 'source_system', None),
                'provider': getattr(doc, 'provider', None)
            }
            documents_data.append(doc_dict)
        
        result = {
            'documents': documents_data,
            'pagination': {
                'page': paginated.page,
                'per_page': paginated.per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_prev': paginated.has_prev,
                'has_next': paginated.has_next
            },
            'search_query': search_query,
            'cached_at': datetime.now().isoformat()
        }
        
        # Cache the results
        tags = {'document_repository', 'all_documents'}
        cache_service.cache_manager.set(cache_key, result, ttl=1800, tags=tags)  # 30 min TTL
        
        logger.info(f"📋 Loaded and cached document repository page {page} with {len(documents_data)} documents")
        return result
        
    except Exception as e:
        logger.error(f"Error loading all documents repository: {e}")
        return {'documents': [], 'pagination': {}, 'error': str(e)}


# =============================================================================
# CACHED OCR OPERATIONS
# =============================================================================

def get_cached_ocr_text(document_id: int) -> Optional[str]:
    """
    Get OCR text with caching, utilizing the existing ocr_text database field
    """
    cache_service = get_healthcare_cache_service()
    
    # Check cache and database
    ocr_result = cache_service.get_cached_ocr_result(document_id)
    if ocr_result and ocr_result.get('text'):
        return ocr_result['text']
    
    return None


def cache_ocr_processing_result(document_id: int, ocr_text: str, processing_metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Cache OCR processing results both in memory and database
    """
    cache_service = get_healthcare_cache_service()
    
    ocr_result = {
        'success': True,
        'text': ocr_text,
        'processing_metadata': processing_metadata or {},
        'processed_at': datetime.now().isoformat(),
        'source': 'processing'
    }
    
    cache_service.cache_ocr_result(document_id, ocr_result)


# =============================================================================
# CACHED PREP SHEET OPERATIONS
# =============================================================================

def get_cached_prep_sheet_data(patient_id: int, include_documents: bool = True) -> Optional[Dict[str, Any]]:
    """
    Get cached prep sheet data including expensive document matching
    """
    cache_service = get_healthcare_cache_service()
    return cache_service.get_cached_prep_sheet(patient_id, include_documents)


def cache_prep_sheet_data(patient_id: int, prep_sheet_data: Dict[str, Any], include_documents: bool = True) -> None:
    """
    Cache prep sheet data with intelligent invalidation
    """
    cache_service = get_healthcare_cache_service()
    cache_service.cache_prep_sheet(patient_id, prep_sheet_data, include_documents)


def generate_cached_prep_sheet(patient_id: int) -> Dict[str, Any]:
    """
    Generate prep sheet with caching for expensive operations
    """
    cache_service = get_healthcare_cache_service()
    
    # Check cache first
    cached_prep = cache_service.get_cached_prep_sheet(patient_id, include_documents=True)
    if cached_prep:
        logger.debug(f"📄 Using cached prep sheet for patient {patient_id}")
        return cached_prep
    
    # Generate prep sheet (expensive operation)
    try:
        from demo_routes import generate_prep_sheet
        
        # Get patient data
        patient = Patient.query.get(patient_id)
        if not patient:
            return {'error': 'Patient not found'}
        
        # Get cached documents
        documents = get_cached_documents_for_patient(patient_id)
        
        # Get other data (these could also be cached separately)
        recent_vitals = []  # TODO: Implement caching for vitals
        recent_labs = []    # TODO: Implement caching for labs
        recent_imaging = [] # TODO: Implement caching for imaging
        recent_consults = []# TODO: Implement caching for consults
        recent_hospital = []# TODO: Implement caching for hospital records
        active_conditions = [] # TODO: Implement caching for conditions
        
        # Get cached screening data
        screening_summary = cache_service.get_cached_patient_screening_summary(patient_id)
        if not screening_summary:
            # Generate screening summary (expensive)
            from screening_performance_optimizer import screening_optimizer
            query_result = screening_optimizer.get_optimized_screenings(
                page=1, page_size=100,
                search_query=f"{patient.first_name} {patient.last_name}"
            )
            screenings = query_result.get('screenings', [])
            screening_summary = {'screenings': screenings}
            cache_service.cache_patient_screening_summary(patient_id, screening_summary)
        
        # Generate prep sheet
        prep_data = generate_prep_sheet(
            patient, recent_vitals, recent_labs, recent_imaging,
            recent_consults, recent_hospital, active_conditions,
            screening_summary['screenings'], None, []
        )
        
        # Cache the result
        cache_service.cache_prep_sheet(patient_id, prep_data, include_documents=True)
        
        logger.info(f"📄 Generated and cached prep sheet for patient {patient_id}")
        return prep_data
        
    except Exception as e:
        logger.error(f"Error generating prep sheet for patient {patient_id}: {e}")
        return {'error': str(e)}


# =============================================================================
# CACHED SCREENING OPERATIONS
# =============================================================================

def get_cached_patient_screenings(patient_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached patient screening data
    """
    cache_service = get_healthcare_cache_service()
    summary = cache_service.get_cached_patient_screening_summary(patient_id)
    return summary.get('screenings') if summary else None


def cache_patient_screenings(patient_id: int, screenings: List[Dict[str, Any]]) -> None:
    """
    Cache patient screening data
    """
    cache_service = get_healthcare_cache_service()
    summary_data = {
        'screenings': screenings,
        'total_screenings': len(screenings),
        'generated_at': datetime.now().isoformat()
    }
    cache_service.cache_patient_screening_summary(patient_id, summary_data)


# =============================================================================
# CACHED DOCUMENT-SCREENING MATCHING
# =============================================================================

def get_cached_document_screening_matches(patient_id: int) -> Optional[Dict[str, Any]]:
    """
    Get cached document-screening matching results (expensive operation)
    """
    cache_service = get_healthcare_cache_service()
    return cache_service.get_cached_document_screening_matches(patient_id)


def cache_document_screening_matches(patient_id: int, matches_data: Dict[str, Any]) -> None:
    """
    Cache document-screening matching results
    """
    cache_service = get_healthcare_cache_service()
    cache_service.cache_document_screening_matches(patient_id, matches_data)


def generate_cached_document_screening_matches(patient_id: int) -> Dict[str, Any]:
    """
    Generate document-screening matches with caching
    """
    cache_service = get_healthcare_cache_service()
    
    # Check cache first
    cached_matches = cache_service.get_cached_document_screening_matches(patient_id)
    if cached_matches:
        logger.debug(f"🔗 Using cached document-screening matches for patient {patient_id}")
        return cached_matches
    
    # Generate matches (expensive operation)
    try:
        from document_screening_matcher import generate_prep_sheet_screening_recommendations
        
        # Generate recommendations with document matching
        matches_data = generate_prep_sheet_screening_recommendations(
            patient_id, enable_ai_fuzzy=True
        )
        
        # Cache the results
        cache_service.cache_document_screening_matches(patient_id, matches_data)
        
        logger.info(f"🔗 Generated and cached document-screening matches for patient {patient_id}")
        return matches_data
        
    except Exception as e:
        logger.error(f"Error generating document-screening matches for patient {patient_id}: {e}")
        return {'screening_recommendations': [], 'document_matches': {}, 'summary': {}}


# =============================================================================
# CACHE INVALIDATION HELPERS
# =============================================================================

def invalidate_patient_cache(patient_id: int) -> None:
    """
    Invalidate all cached data for a patient
    """
    cache_service = get_healthcare_cache_service()
    cache_service.invalidate_patient_cache(patient_id)
    logger.info(f"🔄 Invalidated all cache for patient {patient_id}")


def invalidate_document_cache(document_id: int) -> None:
    """
    Invalidate all cached data for a document
    """
    cache_service = get_healthcare_cache_service()
    cache_service.invalidate_document_cache(document_id)
    logger.info(f"🔄 Invalidated all cache for document {document_id}")


def invalidate_screening_cache(screening_type_id: int) -> None:
    """
    Invalidate all cached data for a screening type
    """
    cache_service = get_healthcare_cache_service()
    cache_service.invalidate_screening_type_cache(screening_type_id)
    logger.info(f"🔄 Invalidated all cache for screening type {screening_type_id}")


# =============================================================================
# CACHE WARMING FUNCTIONS
# =============================================================================

def warm_frequently_accessed_caches() -> Dict[str, bool]:
    """
    Warm up caches for frequently accessed data
    """
    cache_service = get_healthcare_cache_service()
    results = cache_service.warm_healthcare_caches()
    
    # Warm up additional caches
    try:
        # Pre-load active screening types
        active_types = cache_service.get_active_screening_types()
        results['active_screening_types'] = len(active_types) > 0
        
        # Pre-load recent patients with documents
        recent_patients = Patient.query.limit(10).all()
        for patient in recent_patients:
            try:
                docs = get_cached_documents_for_patient(patient.id)
                results[f'patient_{patient.id}_documents'] = len(docs) >= 0
            except Exception as e:
                logger.debug(f"Could not warm cache for patient {patient.id}: {e}")
                results[f'patient_{patient.id}_documents'] = False
        
        logger.info(f"🔥 Warmed {len([k for k, v in results.items() if v])} caches successfully")
        
    except Exception as e:
        logger.error(f"Error warming frequently accessed caches: {e}")
    
    return results


# =============================================================================
# MONITORING AND STATISTICS
# =============================================================================

def get_cache_performance_stats() -> Dict[str, Any]:
    """
    Get comprehensive cache performance statistics
    """
    cache_service = get_healthcare_cache_service()
    return cache_service.get_cache_statistics()