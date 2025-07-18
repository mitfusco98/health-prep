#!/usr/bin/env python3
"""
Unified Screening Engine - Reliable and Consistent
Consolidates all screening logic with proper keyword matching, demographic filtering, and status determination
"""

import json
import re
import html
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Set
from app import app, db
from models import Patient, ScreeningType, Screening, MedicalDocument
import logging

logger = logging.getLogger(__name__)

class UnifiedScreeningEngine:
    """
    Single, authoritative screening engine that handles:
    - Consistent keyword matching (no fallback to screening names)
    - Centralized demographic filtering
    - Reliable status determination
    - Proper document-screening relationships
    """
    
    # Status Constants
    STATUS_DUE = "Due"
    STATUS_DUE_SOON = "Due Soon"
    STATUS_INCOMPLETE = "Incomplete"
    STATUS_COMPLETE = "Complete"
    
    # Configuration
    DUE_SOON_THRESHOLD_DAYS = 30
    MIN_KEYWORD_CONFIDENCE = 0.5  # Lowered threshold for better matching sensitivity
    
    def __init__(self):
        self.debug_mode = False
    
    # =============================================================================
    # CENTRALIZED DEMOGRAPHIC FILTERING
    # =============================================================================
    
    def is_patient_eligible(self, patient: Patient, screening_type: ScreeningType) -> Tuple[bool, str]:
        """
        Centralized demographic filtering - single source of truth
        
        Args:
            patient: Patient object
            screening_type: ScreeningType object
            
        Returns:
            Tuple of (is_eligible, reason)
        """
        # Age filtering
        if screening_type.min_age is not None:
            if patient.age < screening_type.min_age:
                return False, f"Patient age {patient.age} below minimum {screening_type.min_age}"
        
        if screening_type.max_age is not None:
            if patient.age > screening_type.max_age:
                return False, f"Patient age {patient.age} above maximum {screening_type.max_age}"
        
        # Gender filtering
        if screening_type.gender_specific and screening_type.gender_specific.strip():
            expected_gender = screening_type.gender_specific.strip().lower()
            patient_gender = patient.sex.lower() if patient.sex else ""
            
            if expected_gender not in ["", "both", "all"] and expected_gender != patient_gender:
                return False, f"Gender mismatch: requires {expected_gender}, patient is {patient_gender}"
        
        # Trigger conditions (for variants)
        trigger_conditions = self._get_trigger_conditions(screening_type)
        if trigger_conditions:
            has_conditions = self._patient_has_trigger_conditions(patient, trigger_conditions)
            if not has_conditions:
                return False, f"Patient lacks required trigger conditions: {trigger_conditions}"
        
        return True, "Eligible"
    
    def _get_trigger_conditions(self, screening_type: ScreeningType) -> List[Dict]:
        """Get trigger conditions from screening type"""
        if not screening_type.trigger_conditions:
            return []
        
        try:
            # Handle HTML entities in JSON
            clean_json = html.unescape(screening_type.trigger_conditions)
            conditions = json.loads(clean_json)
            return conditions if isinstance(conditions, list) else []
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid trigger conditions JSON for {screening_type.name}")
            return []
    
    def _patient_has_trigger_conditions(self, patient: Patient, trigger_conditions: List[Dict]) -> bool:
        """
        Check if patient has any of the required trigger conditions
        Fixed to properly handle SNOMED codes and condition matching
        """
        if not trigger_conditions:
            return True
        
        # Get patient conditions with proper attributes
        patient_conditions = patient.conditions
        
        # Debug logging
        if self.debug_mode:
            print(f"  Checking trigger conditions for patient {patient.id}")
            print(f"  Patient conditions: {[c.name for c in patient_conditions]}")
            print(f"  Required triggers: {trigger_conditions}")
        
        for trigger in trigger_conditions:
            trigger_code = trigger.get('code', '')
            trigger_display = trigger.get('display', '').lower()
            
            for patient_condition in patient_conditions:
                # Check by SNOMED code (exact match)
                if trigger_code and str(patient_condition.code) == str(trigger_code):
                    if self.debug_mode:
                        print(f"  ✅ Code match: {patient_condition.code} == {trigger_code}")
                    return True
                
                # Check by condition name/display (partial match)
                if trigger_display and trigger_display in patient_condition.name.lower():
                    if self.debug_mode:
                        print(f"  ✅ Name match: '{trigger_display}' in '{patient_condition.name.lower()}'")
                    return True
                
                # Check for diabetes-specific matching
                if 'diabetes' in trigger_display and 'diabetes' in patient_condition.name.lower():
                    if self.debug_mode:
                        print(f"  ✅ Diabetes match: '{patient_condition.name}'")
                    return True
        
        if self.debug_mode:
            print(f"  ❌ No matching conditions found")
        return False
    
    # =============================================================================
    # SCREENING GENERATION METHODS
    # =============================================================================
    
    def generate_patient_screenings(self, patient_id: int) -> List[Dict]:
        """
        Generate automated screenings for a specific patient using unified engine
        
        Args:
            patient_id: Patient ID to generate screenings for
            
        Returns:
            List of screening dictionaries with status determinations
        """
        patient = Patient.query.get(patient_id)
        if not patient:
            return []
        
        # Get all active screening types
        all_screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        # Generate status for each applicable screening
        screenings = []
        for screening_type in all_screening_types:
            # Check if patient is eligible for this screening type
            is_eligible, reason = self.is_patient_eligible(patient, screening_type)
            
            if is_eligible:
                # Generate screening data
                screening_data = self._generate_screening_data(patient, screening_type)
                if screening_data:
                    screenings.append(screening_data)
        
        return screenings
    
    def _generate_screening_data(self, patient: Patient, screening_type: ScreeningType) -> Optional[Dict]:
        """
        Generate screening data for a patient and screening type
        
        Args:
            patient: Patient object
            screening_type: ScreeningType object
            
        Returns:
            Dictionary with screening data
        """
        # Find matching documents
        matching_documents = self._find_matching_documents(patient, screening_type)
        
        # Determine status based on documents and timing
        status = self._determine_status_from_documents(matching_documents, screening_type)
        
        # Calculate due date based on frequency
        due_date = self._calculate_due_date(screening_type, matching_documents)
        
        # Get last completed date from documents
        last_completed = self._get_last_completed_date(matching_documents)
        
        return {
            'screening_type': screening_type.name,
            'patient_id': patient.id,
            'status': status,
            'due_date': due_date,
            'last_completed': last_completed,
            'frequency': screening_type.formatted_frequency,
            'matched_documents': [doc.id for doc in matching_documents],
            'match_source': 'unified_screening_engine'
        }
    
    def _find_matching_documents(self, patient: Patient, screening_type: ScreeningType) -> List[MedicalDocument]:
        """Find documents that match the screening type's criteria"""
        matching_documents = []
        
        # Get all documents for this patient
        patient_documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
        
        for document in patient_documents:
            match_result = self.match_document_to_screening(document, screening_type)
            if match_result['is_match']:
                matching_documents.append(document)
        
        return matching_documents
    
    def _determine_status_from_documents(self, matching_documents: List[MedicalDocument], screening_type: ScreeningType) -> str:
        """Determine screening status based on matched documents"""
        if not matching_documents:
            return self.STATUS_DUE
        
        # If we have documents, check timing
        last_completed = self._get_last_completed_date(matching_documents)
        if not last_completed:
            return self.STATUS_INCOMPLETE
        
        # Check if screening is due based on frequency
        due_date = self._calculate_due_date(screening_type, matching_documents)
        if due_date:
            today = date.today()
            # Ensure both are date objects for comparison
            if isinstance(due_date, datetime):
                due_date = due_date.date()
            if today >= due_date:
                return self.STATUS_DUE
            elif (due_date - today).days <= self.DUE_SOON_THRESHOLD_DAYS:
                return self.STATUS_DUE_SOON
        
        return self.STATUS_COMPLETE
    
    def _calculate_due_date(self, screening_type: ScreeningType, matching_documents: List[MedicalDocument]) -> Optional[date]:
        """Calculate when screening is due next"""
        if not screening_type.frequency_number or not screening_type.frequency_unit:
            return None
        
        last_completed = self._get_last_completed_date(matching_documents)
        if not last_completed:
            return date.today()  # Due now if never completed
        
        # Calculate next due date based on frequency
        if screening_type.frequency_unit == 'months':
            from dateutil.relativedelta import relativedelta
            return last_completed + relativedelta(months=screening_type.frequency_number)
        elif screening_type.frequency_unit == 'years':
            from dateutil.relativedelta import relativedelta
            return last_completed + relativedelta(years=screening_type.frequency_number)
        elif screening_type.frequency_unit == 'days':
            return last_completed + timedelta(days=screening_type.frequency_number)
        
        return None
    
    def _get_last_completed_date(self, matching_documents: List[MedicalDocument]) -> Optional[date]:
        """Get the most recent completion date from matching documents"""
        if not matching_documents:
            return None
        
        # Use document_date (medical event date) or created_at (upload date)
        latest_date = None
        for document in matching_documents:
            doc_date = document.document_date or document.created_at.date()
            if not latest_date or doc_date > latest_date:
                latest_date = doc_date
        
        return latest_date
    
    # =============================================================================
    # UNIFIED KEYWORD MATCHING - NO FALLBACK TO SCREENING NAMES
    # =============================================================================
    
    def match_document_to_screening(self, document: MedicalDocument, screening_type: ScreeningType) -> Dict:
        """
        Authoritative document-to-screening matching
        CRITICAL: Only matches on explicitly configured keywords - NO fallback to screening names
        
        Args:
            document: MedicalDocument to analyze
            screening_type: ScreeningType with matching criteria
            
        Returns:
            Dict with match results
        """
        if not document or not screening_type:
            return self._no_match_result("Invalid input")
        
        # Get configured keywords only - no auto-generation or fallbacks
        keywords_config = self._get_configured_keywords(screening_type)
        
        # If no keywords are configured, do not match
        if not any(keywords_config.values()):
            return self._no_match_result("No keywords configured - intentional non-match")
        
        # Perform keyword matching
        matches = []
        match_types_confidence = []
        
        # Content keyword matching
        if keywords_config['content'] and document.content:
            content_match = self._match_keywords_in_text(
                document.content, 
                keywords_config['content'], 
                'content'
            )
            if content_match['matched']:
                matches.extend(content_match['matches'])
                match_types_confidence.append(content_match['confidence'])
        
        # Filename keyword matching (also check document_name)
        filename_text = document.filename or document.document_name or ""
        if keywords_config['filename'] and filename_text:
            filename_match = self._match_keywords_in_text(
                filename_text, 
                keywords_config['filename'], 
                'filename'
            )
            if filename_match['matched']:
                matches.extend(filename_match['matches'])
                match_types_confidence.append(filename_match['confidence'])
        
        # Document type keyword matching
        if keywords_config['document'] and document.document_type:
            doc_type_match = self._match_keywords_in_text(
                document.document_type, 
                keywords_config['document'], 
                'document_type'
            )
            if doc_type_match['matched']:
                matches.extend(doc_type_match['matches'])
                match_types_confidence.append(doc_type_match['confidence'])
        
        # Determine overall match - use the highest confidence from any match type
        avg_confidence = max(match_types_confidence) if match_types_confidence else 0.0
        is_match = avg_confidence >= self.MIN_KEYWORD_CONFIDENCE
        
        if is_match:
            return {
                'is_match': True,
                'confidence': avg_confidence,
                'matched_keywords': matches,
                'match_source': f"Keywords matched with {avg_confidence:.2f} confidence",
                'screening_type': screening_type.name,
                'document_id': document.id
            }
        else:
            return self._no_match_result(f"Confidence {avg_confidence:.2f} below threshold {self.MIN_KEYWORD_CONFIDENCE}")
    
    def _get_configured_keywords(self, screening_type: ScreeningType) -> Dict[str, List[str]]:
        """
        Get only explicitly configured keywords - no fallbacks or auto-generation
        """
        keywords = {
            'content': [],
            'filename': [],
            'document': []
        }
        
        # Content keywords
        if screening_type.content_keywords:
            try:
                clean_json = html.unescape(screening_type.content_keywords)
                content_kw = json.loads(clean_json)
                if isinstance(content_kw, list):
                    keywords['content'] = [kw.strip() for kw in content_kw if kw.strip()]
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid content keywords JSON for {screening_type.name}")
        
        # Filename keywords
        if screening_type.filename_keywords:
            try:
                clean_json = html.unescape(screening_type.filename_keywords)
                filename_kw = json.loads(clean_json)
                if isinstance(filename_kw, list):
                    keywords['filename'] = [kw.strip() for kw in filename_kw if kw.strip()]
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid filename keywords JSON for {screening_type.name}")
        
        # Document type keywords
        if screening_type.document_keywords:
            try:
                clean_json = html.unescape(screening_type.document_keywords)
                doc_kw = json.loads(clean_json)
                if isinstance(doc_kw, list):
                    keywords['document'] = [kw.strip() for kw in doc_kw if kw.strip()]
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid document keywords JSON for {screening_type.name}")
        
        return keywords
    
    def _match_keywords_in_text(self, text: str, keywords: List[str], match_type: str) -> Dict:
        """
        Match keywords in text with proper phrase and word boundary handling
        """
        if not text or not keywords:
            return {'matched': False, 'matches': [], 'confidence': 0.0}
        
        text_lower = text.lower()
        matches = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            if not keyword_lower:
                continue
            
            # Multi-word phrase matching
            if ' ' in keyword_lower:
                if self._match_phrase_in_text(text_lower, keyword_lower):
                    matches.append({
                        'keyword': keyword,
                        'type': match_type,
                        'match_method': 'phrase',
                        'confidence': 0.9  # High confidence for phrase matches
                    })
            else:
                # Single word with word boundaries
                if self._match_word_in_text(text_lower, keyword_lower):
                    matches.append({
                        'keyword': keyword,
                        'type': match_type,
                        'match_method': 'word',
                        'confidence': 0.8  # Good confidence for word matches
                    })
        
        # Calculate overall confidence
        confidence = sum(m['confidence'] for m in matches) / len(matches) if matches else 0.0
        
        return {
            'matched': len(matches) > 0,
            'matches': matches,
            'confidence': confidence
        }
    
    def _match_phrase_in_text(self, text: str, phrase: str) -> bool:
        """Match multi-word phrases with flexible spacing"""
        words = phrase.split()
        pattern_parts = []
        
        for i, word in enumerate(words):
            escaped_word = re.escape(word)
            pattern_parts.append(escaped_word)
            
            if i < len(words) - 1:
                pattern_parts.append(r'[\s\-_\.]*')  # Flexible separators
        
        pattern = r'\b' + ''.join(pattern_parts) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _match_word_in_text(self, text: str, word: str) -> bool:
        """Match single words with word boundaries"""
        pattern = r'\b' + re.escape(word) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _no_match_result(self, reason: str) -> Dict:
        """Standard no-match result"""
        return {
            'is_match': False,
            'confidence': 0.0,
            'matched_keywords': [],
            'match_source': reason,
            'screening_type': None,
            'document_id': None
        }
    
    # =============================================================================
    # RELIABLE STATUS DETERMINATION
    # =============================================================================
    
    def determine_screening_status(self, patient: Patient, screening_type: ScreeningType) -> Dict:
        """
        Reliable, consistent screening status determination
        
        Args:
            patient: Patient object
            screening_type: ScreeningType object
            
        Returns:
            Dict with status information
        """
        # Check eligibility first
        is_eligible, eligibility_reason = self.is_patient_eligible(patient, screening_type)
        if not is_eligible:
            return {
                'status': None,
                'eligible': False,
                'reason': eligibility_reason,
                'due_date': None,
                'last_completed': None,
                'matching_documents': []
            }
        
        # Find matching documents
        matching_documents = self._find_matching_documents(patient, screening_type)
        
        # Determine completion status
        if matching_documents:
            # Find most recent completion
            latest_doc = max(matching_documents, 
                           key=lambda d: d.document_date or d.created_at or datetime.min)
            last_completed = latest_doc.document_date or latest_doc.created_at
            
            # Calculate next due date based on frequency
            next_due = self._calculate_next_due_date(last_completed, screening_type)
            
            # Determine status based on due date
            if next_due and next_due <= date.today():
                status = self.STATUS_DUE
            elif next_due and (next_due - date.today()).days <= self.DUE_SOON_THRESHOLD_DAYS:
                status = self.STATUS_DUE_SOON
            else:
                status = self.STATUS_COMPLETE
        else:
            # No matching documents - incomplete
            last_completed = None
            next_due = date.today()  # Due now
            status = self.STATUS_INCOMPLETE
        
        return {
            'status': status,
            'eligible': True,
            'reason': 'Eligible for screening',
            'due_date': next_due,
            'last_completed': last_completed,
            'matching_documents': matching_documents
        }
    
    def _find_matching_documents(self, patient: Patient, screening_type: ScreeningType) -> List[MedicalDocument]:
        """Find documents that match this screening type for the patient"""
        patient_documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
        matching_docs = []
        
        for document in patient_documents:
            match_result = self.match_document_to_screening(document, screening_type)
            if match_result['is_match']:
                matching_docs.append(document)
        
        return matching_docs
    
    def _calculate_next_due_date(self, last_completed: datetime, screening_type: ScreeningType) -> Optional[date]:
        """Calculate next due date based on frequency"""
        if not last_completed or not screening_type.frequency_number or not screening_type.frequency_unit:
            return None
        
        # Convert datetime to date if needed
        if isinstance(last_completed, datetime):
            last_date = last_completed.date()
        else:
            last_date = last_completed
        
        frequency_num = int(screening_type.frequency_number)
        frequency_unit = screening_type.frequency_unit.lower()
        
        if frequency_unit in ['year', 'years', 'annually']:
            return date(last_date.year + frequency_num, last_date.month, last_date.day)
        elif frequency_unit in ['month', 'months', 'monthly']:
            # Handle month overflow
            new_month = last_date.month + frequency_num
            new_year = last_date.year + (new_month - 1) // 12
            new_month = ((new_month - 1) % 12) + 1
            return date(new_year, new_month, last_date.day)
        elif frequency_unit in ['day', 'days', 'daily']:
            return last_date + timedelta(days=frequency_num)
        else:
            logger.warning(f"Unknown frequency unit: {frequency_unit}")
            return None
    
    # =============================================================================
    # SCREENING GENERATION AND MANAGEMENT
    # =============================================================================
    
    def generate_screening_for_patient(self, patient: Patient, screening_type: ScreeningType) -> Optional[Screening]:
        """
        Generate a single screening for a patient if eligible
        
        Returns:
            Screening object if created, None if not eligible or already exists
        """
        # Check if screening already exists
        existing = Screening.query.filter_by(
            patient_id=patient.id,
            screening_type=screening_type.name,
            is_visible=True
        ).first()
        
        if existing:
            logger.debug(f"Screening already exists for {patient.full_name} - {screening_type.name}")
            return None
        
        # Check eligibility
        is_eligible, reason = self.is_patient_eligible(patient, screening_type)
        if not is_eligible:
            logger.debug(f"Patient {patient.full_name} not eligible for {screening_type.name}: {reason}")
            return None
        
        # Determine status
        status_info = self.determine_screening_status(patient, screening_type)
        
        # Create screening
        screening = Screening(
            patient_id=patient.id,
            screening_type=screening_type.name,
            screening_type_id=screening_type.id,
            status=status_info['status'],
            due_date=status_info['due_date'],
            last_completed=status_info['last_completed'],
            is_visible=True,
            is_system_generated=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(screening)
        
        # Link matching documents
        for document in status_info['matching_documents']:
            try:
                # Add to screening_documents association table
                db.session.execute(
                    "INSERT INTO screening_documents (screening_id, document_id, confidence_score, match_source) "
                    "VALUES (:screening_id, :document_id, :confidence, :source) "
                    "ON CONFLICT DO NOTHING",
                    {
                        'screening_id': screening.id,
                        'document_id': document.id,
                        'confidence': 0.8,
                        'source': 'unified_engine'
                    }
                )
            except Exception as link_error:
                logger.warning(f"Could not link document {document.id} to screening: {link_error}")
        
        logger.info(f"Generated {screening_type.name} screening for {patient.full_name} (status: {status_info['status']})")
        return screening
    
    def bulk_generate_screenings(self, limit_patients: int = None) -> Dict:
        """
        Generate screenings for all eligible patients and active screening types
        
        Args:
            limit_patients: Optional limit on number of patients to process
            
        Returns:
            Summary of generation results
        """
        start_time = datetime.now()
        logger.info("🔄 Starting bulk screening generation with unified engine")
        
        # Get active screening types
        active_screening_types = ScreeningType.query.filter_by(is_active=True).all()
        logger.info(f"Found {len(active_screening_types)} active screening types")
        
        # Get patients
        patients_query = Patient.query
        if limit_patients:
            patients_query = patients_query.limit(limit_patients)
        patients = patients_query.all()
        logger.info(f"Processing {len(patients)} patients")
        
        # Generation counters
        results = {
            'total_generated': 0,
            'total_skipped': 0,
            'errors': 0,
            'by_screening_type': {},
            'processing_time': None
        }
        
        for screening_type in active_screening_types:
            type_generated = 0
            
            for patient in patients:
                try:
                    screening = self.generate_screening_for_patient(patient, screening_type)
                    if screening:
                        type_generated += 1
                        results['total_generated'] += 1
                    else:
                        results['total_skipped'] += 1
                        
                except Exception as e:
                    logger.error(f"Error generating {screening_type.name} for {patient.full_name}: {e}")
                    results['errors'] += 1
            
            results['by_screening_type'][screening_type.name] = type_generated
            
            # Commit after each screening type
            try:
                db.session.commit()
                logger.info(f"✅ Generated {type_generated} {screening_type.name} screenings")
            except Exception as commit_error:
                logger.error(f"Error committing {screening_type.name} screenings: {commit_error}")
                db.session.rollback()
        
        end_time = datetime.now()
        results['processing_time'] = (end_time - start_time).total_seconds()
        
        logger.info(f"🎉 Bulk generation complete: {results['total_generated']} generated, "
                   f"{results['total_skipped']} skipped, {results['errors']} errors "
                   f"in {results['processing_time']:.2f}s")
        
        return results

# Global instance
unified_engine = UnifiedScreeningEngine()