#!/usr/bin/env python3
"""
Async Document Subsection Processor
Specialized processor for handling the 5 medical data subsections
Integrates with DocumentScreeningMatcher for document-screening relationships
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from database_access_layer import DatabaseAccessLayer
from intelligent_cache_manager import get_cache_manager
from document_screening_matcher import DocumentScreeningMatcher
from cutoff_utils import get_cutoff_date_for_patient

logger = logging.getLogger(__name__)

class MedicalSubsection(Enum):
    """Enum for medical data subsections"""
    LABORATORIES = "laboratories"
    IMAGING = "imaging"
    CONSULTS = "consults"
    HOSPITAL_RECORDS = "hospital_records"
    OTHER = "other"

class AsyncDocumentSubsectionProcessor:
    """
    Specialized async processor for medical document subsections
    Handles document-screening relationships and subsection-specific processing
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.db_layer = DatabaseAccessLayer()
        self.cache_manager = get_cache_manager()
        self.document_matcher = DocumentScreeningMatcher()
        
        # Subsection-specific configurations
        self.subsection_config = {
            MedicalSubsection.LABORATORIES: {
                'document_types': ['LAB_RESULT', 'LABORATORY_REPORT', 'PATHOLOGY_REPORT'],
                'keywords': ['lab', 'laboratory', 'blood', 'urine', 'pathology', 'specimen'],
                'priority': 'high',
                'default_cutoff_months': 12,
                'screening_relevance': ['colonoscopy', 'mammogram', 'pap_smear', 'blood_pressure'],
                'content_patterns': [
                    r'(?i)(lab|laboratory)\s*(result|report)',
                    r'(?i)(blood|urine|serum)\s*(test|analysis)',
                    r'(?i)(pathology|specimen)\s*(report|analysis)'
                ]
            },
            MedicalSubsection.IMAGING: {
                'document_types': ['RADIOLOGY_REPORT', 'IMAGING_REPORT', 'XRAY_REPORT', 'CT_SCAN', 'MRI_REPORT'],
                'keywords': ['imaging', 'radiology', 'xray', 'ct', 'mri', 'ultrasound', 'mammogram'],
                'priority': 'high',
                'default_cutoff_months': 24,
                'screening_relevance': ['mammogram', 'colonoscopy', 'bone_density', 'chest_xray'],
                'content_patterns': [
                    r'(?i)(radiology|imaging)\s*(report|study)',
                    r'(?i)(ct|mri|ultrasound|xray)\s*(scan|study)',
                    r'(?i)(mammogram|mammography)\s*(report|screening)'
                ]
            },
            MedicalSubsection.CONSULTS: {
                'document_types': ['CONSULTATION_NOTE', 'REFERRAL_LETTER', 'SPECIALIST_REPORT'],
                'keywords': ['consultation', 'referral', 'specialist', 'cardiology', 'oncology'],
                'priority': 'medium',
                'default_cutoff_months': 18,
                'screening_relevance': ['colonoscopy', 'mammogram', 'pap_smear', 'eye_exam'],
                'content_patterns': [
                    r'(?i)(consultation|referral)\s*(note|letter)',
                    r'(?i)(specialist|cardiology|oncology)\s*(report|note)',
                    r'(?i)(follow.up|recommendation)\s*(for|regarding)'
                ]
            },
            MedicalSubsection.HOSPITAL_RECORDS: {
                'document_types': ['HOSPITAL_SUMMARY', 'DISCHARGE_SUMMARY', 'INPATIENT_REPORT'],
                'keywords': ['hospital', 'admission', 'discharge', 'inpatient', 'emergency'],
                'priority': 'medium',
                'default_cutoff_months': 12,
                'screening_relevance': ['colonoscopy', 'mammogram', 'pap_smear', 'blood_pressure'],
                'content_patterns': [
                    r'(?i)(hospital|admission)\s*(summary|record)',
                    r'(?i)(discharge|inpatient)\s*(summary|report)',
                    r'(?i)(emergency|er)\s*(visit|record)'
                ]
            },
            MedicalSubsection.OTHER: {
                'document_types': ['MEDICAL_DOCUMENT', 'CLINICAL_NOTE', 'PROGRESS_NOTE'],
                'keywords': ['medical', 'clinical', 'progress', 'note', 'record'],
                'priority': 'low',
                'default_cutoff_months': 6,
                'screening_relevance': ['general_screening'],
                'content_patterns': [
                    r'(?i)(medical|clinical)\s*(document|note)',
                    r'(?i)(progress|follow.up)\s*(note|report)',
                    r'(?i)(patient|medical)\s*(record|history)'
                ]
            }
        }
        
        # Processing metrics
        self.subsection_metrics = {
            subsection.value: {
                'documents_processed': 0,
                'screenings_matched': 0,
                'processing_time': 0,
                'errors': 0
            }
            for subsection in MedicalSubsection
        }
        
        logger.info("✅ Async Document Subsection Processor initialized")
    
    async def process_document_for_subsection(self, document_id: int, patient_id: int, subsection: MedicalSubsection) -> Dict[str, Any]:
        """
        Process a document for a specific medical subsection
        
        Args:
            document_id: Document ID
            patient_id: Patient ID
            subsection: Medical subsection enum
            
        Returns:
            Processing result
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"🔄 Processing document {document_id} for subsection {subsection.value}")
            
            # Get document details
            document = await self._get_document_details_async(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Get patient demographics
            patient_demographics = await self._get_patient_demographics_async(patient_id)
            if not patient_demographics:
                raise ValueError(f"Patient {patient_id} not found")
            
            # Get subsection configuration
            config = self.subsection_config[subsection]
            
            # Validate document type for subsection
            if not self._validate_document_type_for_subsection(document, subsection):
                logger.warning(f"Document {document_id} type mismatch for subsection {subsection.value}")
                return {
                    'success': False,
                    'reason': 'document_type_mismatch',
                    'document_id': document_id,
                    'subsection': subsection.value
                }
            
            # Get relevant screening types for this subsection
            screening_types = await self._get_screening_types_for_subsection(subsection)
            
            # Process document against each relevant screening type
            screening_matches = []
            for screening_type in screening_types:
                # Check demographic eligibility
                if not self._check_demographic_eligibility(patient_demographics, screening_type):
                    continue
                
                # Check document-screening match
                match_result = await self._process_document_screening_match(
                    document, screening_type, subsection, config
                )
                
                if match_result['matches']:
                    screening_matches.append(match_result)
            
            # Update screening relationships
            updated_screenings = []
            for match in screening_matches:
                update_result = await self._update_screening_document_relationship(
                    patient_id, match['screening_type'], document_id, match, subsection
                )
                updated_screenings.append(update_result)
            
            # Calculate cutoff implications
            cutoff_analysis = await self._analyze_cutoff_implications(
                patient_id, document, subsection, screening_matches
            )
            
            # Update metrics
            self.subsection_metrics[subsection.value]['documents_processed'] += 1
            self.subsection_metrics[subsection.value]['screenings_matched'] += len(screening_matches)
            self.subsection_metrics[subsection.value]['processing_time'] += asyncio.get_event_loop().time() - start_time
            
            return {
                'success': True,
                'document_id': document_id,
                'patient_id': patient_id,
                'subsection': subsection.value,
                'screening_matches': len(screening_matches),
                'updated_screenings': updated_screenings,
                'cutoff_analysis': cutoff_analysis,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
            
        except Exception as e:
            self.subsection_metrics[subsection.value]['errors'] += 1
            logger.error(f"❌ Subsection processing error: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id,
                'subsection': subsection.value,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
    
    async def process_subsection_refresh(self, patient_id: int, subsection: MedicalSubsection) -> Dict[str, Any]:
        """
        Refresh all documents in a subsection for a patient
        
        Args:
            patient_id: Patient ID
            subsection: Medical subsection enum
            
        Returns:
            Refresh result
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"🔄 Refreshing subsection {subsection.value} for patient {patient_id}")
            
            # Get all documents for patient in this subsection
            documents = await self._get_patient_documents_by_subsection(patient_id, subsection)
            
            # Process each document
            processed_documents = []
            for document in documents:
                result = await self.process_document_for_subsection(
                    document['id'], patient_id, subsection
                )
                processed_documents.append(result)
            
            # Calculate subsection summary
            subsection_summary = self._calculate_subsection_summary(processed_documents, subsection)
            
            # Update subsection-specific cache
            await self._update_subsection_cache(patient_id, subsection, subsection_summary)
            
            return {
                'success': True,
                'patient_id': patient_id,
                'subsection': subsection.value,
                'documents_processed': len(processed_documents),
                'subsection_summary': subsection_summary,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
            
        except Exception as e:
            logger.error(f"❌ Subsection refresh error: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'patient_id': patient_id,
                'subsection': subsection.value,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
    
    async def process_all_subsections_for_patient(self, patient_id: int) -> Dict[str, Any]:
        """
        Process all medical subsections for a patient
        
        Args:
            patient_id: Patient ID
            
        Returns:
            Complete processing result
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"🔄 Processing all subsections for patient {patient_id}")
            
            # Process each subsection concurrently
            tasks = []
            for subsection in MedicalSubsection:
                task = self.process_subsection_refresh(patient_id, subsection)
                tasks.append(task)
            
            # Wait for all subsections to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            subsection_results = {}
            total_documents = 0
            total_screenings = 0
            errors = []
            
            for i, result in enumerate(results):
                subsection = list(MedicalSubsection)[i]
                
                if isinstance(result, Exception):
                    errors.append({
                        'subsection': subsection.value,
                        'error': str(result)
                    })
                    subsection_results[subsection.value] = {
                        'success': False,
                        'error': str(result)
                    }
                else:
                    subsection_results[subsection.value] = result
                    if result['success']:
                        total_documents += result['documents_processed']
                        total_screenings += result['subsection_summary'].get('total_screenings', 0)
            
            # Generate patient screening summary
            patient_summary = await self._generate_patient_screening_summary(patient_id, subsection_results)
            
            return {
                'success': len(errors) == 0,
                'patient_id': patient_id,
                'subsection_results': subsection_results,
                'patient_summary': patient_summary,
                'total_documents_processed': total_documents,
                'total_screenings_updated': total_screenings,
                'errors': errors,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
            
        except Exception as e:
            logger.error(f"❌ All subsections processing error: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'patient_id': patient_id,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
    
    async def handle_document_deletion_by_subsection(self, document_id: int, patient_id: int, subsection: MedicalSubsection) -> Dict[str, Any]:
        """
        Handle document deletion for a specific subsection
        
        Args:
            document_id: Document ID
            patient_id: Patient ID
            subsection: Medical subsection
            
        Returns:
            Deletion handling result
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"🔄 Handling document deletion {document_id} for subsection {subsection.value}")
            
            # Get affected screenings
            affected_screenings = await self._get_screenings_with_document_in_subsection(
                document_id, subsection
            )
            
            # Remove document from screening relationships
            removed_relationships = []
            for screening in affected_screenings:
                removal_result = await self._remove_document_from_screening_relationship(
                    screening['id'], document_id
                )
                removed_relationships.append(removal_result)
            
            # Recalculate screening statuses
            updated_screenings = []
            for screening in affected_screenings:
                # Get patient demographics
                patient_demographics = await self._get_patient_demographics_async(patient_id)
                
                # Recalculate screening status
                recalc_result = await self._recalculate_screening_status_after_deletion(
                    screening['id'], patient_demographics, subsection
                )
                updated_screenings.append(recalc_result)
            
            # Update subsection cache
            await self._invalidate_subsection_cache(patient_id, subsection)
            
            return {
                'success': True,
                'document_id': document_id,
                'patient_id': patient_id,
                'subsection': subsection.value,
                'affected_screenings': len(affected_screenings),
                'removed_relationships': removed_relationships,
                'updated_screenings': updated_screenings,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
            
        except Exception as e:
            logger.error(f"❌ Document deletion handling error: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id,
                'subsection': subsection.value,
                'processing_time': asyncio.get_event_loop().time() - start_time
            }
    
    # Helper methods
    
    async def _get_document_details_async(self, document_id: int) -> Optional[Dict]:
        """Get document details asynchronously"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.db_layer.get_document_details,
            document_id
        )
    
    async def _get_patient_demographics_async(self, patient_id: int) -> Optional[Dict]:
        """Get patient demographics asynchronously"""
        cache_key = f"patient_demographics_{patient_id}"
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data:
            return cached_data
        
        demographics = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.db_layer.get_patient_demographics,
            patient_id
        )
        
        if demographics:
            self.cache_manager.set(cache_key, demographics, timeout=300)
        
        return demographics
    
    def _validate_document_type_for_subsection(self, document: Dict, subsection: MedicalSubsection) -> bool:
        """Validate if document type matches subsection"""
        config = self.subsection_config[subsection]
        document_type = document.get('document_type', '')
        
        return document_type in config['document_types']
    
    async def _get_screening_types_for_subsection(self, subsection: MedicalSubsection) -> List[Dict]:
        """Get screening types relevant to subsection"""
        cache_key = f"screening_types_subsection_{subsection.value}"
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Get screening types from database
        config = self.subsection_config[subsection]
        screening_types = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.db_layer.get_screening_types_by_relevance,
            config['screening_relevance']
        )
        
        if screening_types:
            self.cache_manager.set(cache_key, screening_types, timeout=600)
        
        return screening_types or []
    
    def _check_demographic_eligibility(self, patient_demographics: Dict, screening_type: Dict) -> bool:
        """Check demographic eligibility for screening type"""
        # Age check
        if screening_type.get('min_age') and patient_demographics.get('age', 0) < screening_type['min_age']:
            return False
        
        if screening_type.get('max_age') and patient_demographics.get('age', 999) > screening_type['max_age']:
            return False
        
        # Gender check
        if screening_type.get('gender_specific') and patient_demographics.get('gender') != screening_type['gender_specific']:
            return False
        
        return True
    
    async def _process_document_screening_match(self, document: Dict, screening_type: Dict, subsection: MedicalSubsection, config: Dict) -> Dict[str, Any]:
        """Process document-screening match with subsection context"""
        # Use DocumentScreeningMatcher with subsection-specific configuration
        base_match = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.document_matcher.check_document_match,
            document,
            screening_type
        )
        
        if not base_match['matches']:
            return base_match
        
        # Enhance match with subsection-specific analysis
        subsection_analysis = self._analyze_subsection_specific_match(
            document, screening_type, subsection, config
        )
        
        # Combine results
        enhanced_match = {
            **base_match,
            'subsection': subsection.value,
            'subsection_analysis': subsection_analysis,
            'confidence': min(base_match['confidence'] + subsection_analysis['confidence_boost'], 1.0)
        }
        
        return enhanced_match
    
    def _analyze_subsection_specific_match(self, document: Dict, screening_type: Dict, subsection: MedicalSubsection, config: Dict) -> Dict[str, Any]:
        """Analyze subsection-specific matching factors"""
        confidence_boost = 0.0
        match_factors = []
        
        # Check content patterns
        document_content = document.get('content', '')
        for pattern in config['content_patterns']:
            import re
            if re.search(pattern, document_content):
                confidence_boost += 0.1
                match_factors.append(f"content_pattern_{pattern}")
        
        # Check subsection priority
        if config['priority'] == 'high':
            confidence_boost += 0.05
        elif config['priority'] == 'medium':
            confidence_boost += 0.03
        
        # Check screening relevance
        if screening_type.get('name', '').lower() in [r.lower() for r in config['screening_relevance']]:
            confidence_boost += 0.15
            match_factors.append("screening_relevance")
        
        return {
            'confidence_boost': min(confidence_boost, 0.3),  # Cap at 0.3
            'match_factors': match_factors,
            'subsection_priority': config['priority']
        }
    
    def get_subsection_metrics(self) -> Dict[str, Any]:
        """Get processing metrics for all subsections"""
        return {
            'subsection_metrics': self.subsection_metrics,
            'total_documents_processed': sum(m['documents_processed'] for m in self.subsection_metrics.values()),
            'total_screenings_matched': sum(m['screenings_matched'] for m in self.subsection_metrics.values()),
            'total_processing_time': sum(m['processing_time'] for m in self.subsection_metrics.values()),
            'total_errors': sum(m['errors'] for m in self.subsection_metrics.values()),
            'timestamp': datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Graceful shutdown of the subsection processor"""
        logger.info("🔄 Shutting down document subsection processor")
        
        # Wait for pending tasks
        await asyncio.sleep(1)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("✅ Document subsection processor shut down")

# Global instance
_subsection_processor = None

def get_subsection_processor() -> AsyncDocumentSubsectionProcessor:
    """Get or create the global subsection processor instance"""
    global _subsection_processor
    if _subsection_processor is None:
        _subsection_processor = AsyncDocumentSubsectionProcessor()
    return _subsection_processor

# Utility functions for subsection processing

def get_subsection_from_document_type(document_type: str) -> MedicalSubsection:
    """Determine medical subsection from document type"""
    if document_type in ['LAB_RESULT', 'LABORATORY_REPORT', 'PATHOLOGY_REPORT']:
        return MedicalSubsection.LABORATORIES
    elif document_type in ['RADIOLOGY_REPORT', 'IMAGING_REPORT', 'XRAY_REPORT', 'CT_SCAN', 'MRI_REPORT']:
        return MedicalSubsection.IMAGING
    elif document_type in ['CONSULTATION_NOTE', 'REFERRAL_LETTER', 'SPECIALIST_REPORT']:
        return MedicalSubsection.CONSULTS
    elif document_type in ['HOSPITAL_SUMMARY', 'DISCHARGE_SUMMARY', 'INPATIENT_REPORT']:
        return MedicalSubsection.HOSPITAL_RECORDS
    else:
        return MedicalSubsection.OTHER

def get_subsection_from_endpoint(endpoint: str) -> MedicalSubsection:
    """Determine medical subsection from Flask endpoint"""
    if 'lab' in endpoint:
        return MedicalSubsection.LABORATORIES
    elif 'imaging' in endpoint:
        return MedicalSubsection.IMAGING
    elif 'consult' in endpoint:
        return MedicalSubsection.CONSULTS
    elif 'hospital' in endpoint:
        return MedicalSubsection.HOSPITAL_RECORDS
    else:
        return MedicalSubsection.OTHER

if __name__ == "__main__":
    # Test the subsection processor
    async def test_subsection_processor():
        processor = AsyncDocumentSubsectionProcessor()
        
        # Test document processing
        result = await processor.process_document_for_subsection(
            1, 1, MedicalSubsection.LABORATORIES
        )
        
        print(f"Test result: {result}")
        
        # Test metrics
        metrics = processor.get_subsection_metrics()
        print(f"Metrics: {metrics}")
        
        await processor.shutdown()
    
    # Run test
    asyncio.run(test_subsection_processor())