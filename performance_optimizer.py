#!/usr/bin/env python3
"""
Comprehensive Performance Optimization System
Addresses slow database queries, file uploads, and selective refresh operations
"""

import time
import logging
from typing import List, Dict, Any, Optional
from app import app, db
from models import Patient, ScreeningType, Screening, MedicalDocument
from sqlalchemy import text, and_, or_
from sqlalchemy.orm import joinedload, selectinload
import html

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """
    Centralized performance optimization for healthcare app
    """
    
    def __init__(self):
        self.batch_size = 25
        self.timeout_seconds = 120
        
    def optimize_medical_document_queries(self):
        """
        Optimize medical document queries with proper eager loading and filtering
        """
        try:
            # Add additional composite indexes for common query patterns
            composite_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_medical_doc_patient_created ON medical_document(patient_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_medical_doc_type_date ON medical_document(document_type, document_date DESC);",
                "CREATE INDEX IF NOT EXISTS idx_screening_patient_type ON screening(patient_id, screening_type);",
                "CREATE INDEX IF NOT EXISTS idx_screening_status ON screening(status);",
                "CREATE INDEX IF NOT EXISTS idx_screening_docs_screening ON screening_documents(screening_id);",
                "CREATE INDEX IF NOT EXISTS idx_screening_docs_document ON screening_documents(document_id);"
            ]
            
            for index_sql in composite_indexes:
                db.session.execute(text(index_sql))
                
            db.session.commit()
            logger.info("✅ Advanced performance indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Error creating performance indexes: {e}")
            db.session.rollback()
    
    def get_optimized_patient_documents(self, patient_id: int, limit: int = 50) -> List[MedicalDocument]:
        """
        Get patient documents with optimized query and proper eager loading
        """
        try:
            return (MedicalDocument.query
                   .filter(MedicalDocument.patient_id == patient_id)
                   .order_by(MedicalDocument.document_date.desc().nullslast(),
                            MedicalDocument.created_at.desc())
                   .limit(limit)
                   .all())
        except Exception as e:
            logger.error(f"Error in optimized document query: {e}")
            return []
    
    def get_optimized_screenings_with_documents(self, patient_id: Optional[int] = None) -> List[Screening]:
        """
        Get screenings with documents using optimized joins and eager loading
        """
        try:
            query = (Screening.query
                    .options(
                        joinedload(Screening.patient),
                        selectinload(Screening.documents),
                        joinedload(Screening.screening_type_rel)
                    )
                    .join(ScreeningType, Screening.screening_type_id == ScreeningType.id)
                    .filter(ScreeningType.is_active == True))
            
            if patient_id:
                query = query.filter(Screening.patient_id == patient_id)
            
            return query.order_by(Screening.created_at.desc()).limit(100).all()
            
        except Exception as e:
            logger.error(f"Error in optimized screenings query: {e}")
            return []
    
    def fast_selective_refresh(self, screening_type_ids: List[int]) -> Dict[str, Any]:
        """
        Optimized selective refresh that only processes affected patients
        """
        start_time = time.time()
        results = {
            'success': False,
            'patients_processed': 0,
            'screenings_updated': 0,
            'duration_seconds': 0,
            'error': None
        }
        
        try:
            # Get only patients who actually have documents or existing screenings for these types
            affected_patients = (Patient.query
                               .join(MedicalDocument, Patient.id == MedicalDocument.patient_id, isouter=True)
                               .join(Screening, Patient.id == Screening.patient_id, isouter=True)
                               .filter(or_(
                                   MedicalDocument.id.isnot(None),
                                   and_(Screening.screening_type_id.in_(screening_type_ids))
                               ))
                               .distinct()
                               .limit(self.batch_size)
                               .all())
            
            logger.info(f"Fast refresh processing {len(affected_patients)} affected patients")
            
            for patient in affected_patients:
                if time.time() - start_time > self.timeout_seconds:
                    results['error'] = "Timeout reached"
                    break
                
                try:
                    # Process only the specific screening types for this patient
                    patient_updated = self._update_patient_screenings(patient.id, screening_type_ids)
                    if patient_updated:
                        results['patients_processed'] += 1
                        results['screenings_updated'] += patient_updated
                        
                except Exception as e:
                    logger.error(f"Error processing patient {patient.id}: {e}")
                    continue
            
            results['success'] = True
            results['duration_seconds'] = time.time() - start_time
            
            logger.info(f"✅ Fast selective refresh completed in {results['duration_seconds']:.2f}s")
            return results
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"❌ Fast selective refresh failed: {e}")
            return results
    
    def _update_patient_screenings(self, patient_id: int, screening_type_ids: List[int]) -> int:
        """
        Update screenings for a specific patient and screening types only
        """
        updated_count = 0
        
        try:
            from unified_screening_engine import UnifiedScreeningEngine
            engine = UnifiedScreeningEngine()
            
            # Only generate screenings for the specific types that changed
            screening_types = ScreeningType.query.filter(
                ScreeningType.id.in_(screening_type_ids),
                ScreeningType.is_active == True
            ).all()
            
            patient = Patient.query.get(patient_id)
            if not patient:
                return 0
            
            for screening_type in screening_types:
                try:
                    # Check if patient is eligible for this screening type
                    if engine._is_patient_eligible(patient, screening_type):
                        # Update or create screening for this specific type
                        existing_screening = Screening.query.filter_by(
                            patient_id=patient_id,
                            screening_type_id=screening_type.id
                        ).first()
                        
                        if existing_screening:
                            # Update existing screening status and documents
                            engine._update_screening_status_and_documents(existing_screening, screening_type)
                            updated_count += 1
                        else:
                            # Create new screening if patient is now eligible
                            new_screening = engine._create_screening_for_patient(patient, screening_type)
                            if new_screening:
                                updated_count += 1
                                
                except Exception as e:
                    logger.error(f"Error updating screening type {screening_type.id} for patient {patient_id}: {e}")
                    continue
            
            # Commit changes for this patient
            db.session.commit()
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in _update_patient_screenings: {e}")
            db.session.rollback()
            return 0
    
    def fix_html_entity_encoding(self) -> Dict[str, int]:
        """
        Fix HTML entity encoding issues in keywords and trigger conditions
        """
        results = {'keywords_fixed': 0, 'trigger_conditions_fixed': 0}
        
        try:
            screening_types = ScreeningType.query.all()
            
            for st in screening_types:
                # Fix keywords
                if st.content_keywords and '&quot;' in st.content_keywords:
                    try:
                        decoded_keywords = html.unescape(st.content_keywords)
                        st.content_keywords = decoded_keywords
                        results['keywords_fixed'] += 1
                    except Exception as e:
                        logger.error(f"Error fixing keywords for screening type {st.id}: {e}")
                
                # Fix trigger conditions
                if st.trigger_conditions and '&quot;' in st.trigger_conditions:
                    try:
                        decoded_conditions = html.unescape(st.trigger_conditions)
                        st.trigger_conditions = decoded_conditions
                        results['trigger_conditions_fixed'] += 1
                    except Exception as e:
                        logger.error(f"Error fixing trigger conditions for screening type {st.id}: {e}")
            
            db.session.commit()
            logger.info(f"✅ Fixed HTML entities: {results['keywords_fixed']} keywords, {results['trigger_conditions_fixed']} trigger conditions")
            
        except Exception as e:
            logger.error(f"❌ Error fixing HTML entities: {e}")
            db.session.rollback()
            
        return results
    
    def optimize_file_upload_processing(self, file_size_mb: float) -> Dict[str, Any]:
        """
        Optimize file upload processing based on file size
        """
        config = {
            'chunk_size': 8192,  # 8KB chunks
            'enable_streaming': False,
            'enable_compression': False,
            'processing_timeout': 30
        }
        
        # Adjust based on file size
        if file_size_mb > 10:
            config['chunk_size'] = 32768  # 32KB chunks for large files
            config['enable_streaming'] = True
            config['processing_timeout'] = 120
        
        if file_size_mb > 50:
            config['enable_compression'] = True
            config['processing_timeout'] = 300
            
        return config

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

if __name__ == "__main__":
    # Run optimization when script is executed directly
    with app.app_context():
        print("🚀 Starting performance optimization...")
        
        # Add advanced indexes
        performance_optimizer.optimize_medical_document_queries()
        
        # Fix HTML entity encoding issues
        results = performance_optimizer.fix_html_entity_encoding()
        print(f"📝 Fixed HTML encoding: {results}")
        
        print("✅ Performance optimization completed!")