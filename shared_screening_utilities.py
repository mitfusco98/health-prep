#!/usr/bin/env python3
"""
Shared Screening Utilities
Consolidated base classes and utilities to eliminate duplicate logic across screening engines
"""

import json
import re
import html
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Set, Any, Union
from abc import ABC, abstractmethod
import logging

from app import app, db
from models import Patient, ScreeningType, Screening, MedicalDocument, Condition

logger = logging.getLogger(__name__)


class PatientDemographicsMixin:
    """
    Mixin providing centralized demographic filtering logic
    Single source of truth for all patient eligibility checks
    """
    
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
        trigger_conditions = self.get_trigger_conditions(screening_type)
        if trigger_conditions:
            has_conditions = self.patient_has_trigger_conditions(patient, trigger_conditions)
            if not has_conditions:
                return False, f"Patient lacks required trigger conditions: {[t.get('display', t.get('code', '')) for t in trigger_conditions]}"
        
        return True, "Eligible"
    
    def get_trigger_conditions(self, screening_type: ScreeningType) -> List[Dict]:
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
    
    def patient_has_trigger_conditions(self, patient: Patient, trigger_conditions: List[Dict]) -> bool:
        """
        Check if patient has any of the required trigger conditions
        Unified logic for condition matching across all engines
        """
        if not trigger_conditions:
            return True
        
        # Get patient conditions (handle RelationshipProperty correctly)
        try:
            patient_conditions = patient.conditions.all() if hasattr(patient, 'conditions') else []
        except AttributeError:
            # Fallback if conditions relationship doesn't exist
            patient_conditions = []
        
        for trigger in trigger_conditions:
            trigger_code = trigger.get('code', '')
            trigger_display = trigger.get('display', '').lower()
            
            for patient_condition in patient_conditions:
                # Check by SNOMED code (exact match)
                if trigger_code and str(patient_condition.code) == str(trigger_code):
                    return True
                
                # Check by condition name/display (partial match)
                if trigger_display and trigger_display in patient_condition.name.lower():
                    return True
        
        return False


class DocumentMatchingMixin:
    """
    Mixin providing centralized document-screening matching logic
    Eliminates duplicate keyword matching and content analysis
    """
    
    def match_document_keywords(self, screening_type: ScreeningType, document: MedicalDocument) -> Tuple[bool, str, str]:
        """
        Unified document keyword matching logic
        
        Returns:
            Tuple of (matched, match_method, notes)
        """
        # Check filename keywords
        filename_match, filename_notes = self._check_filename_keywords(screening_type, document)
        if filename_match:
            return True, 'filename', filename_notes
        
        # Check content keywords
        content_match, content_notes = self._check_content_keywords(screening_type, document)
        if content_match:
            return True, 'content', content_notes
        
        # Check section keywords
        section_match, section_notes = self._check_section_keywords(screening_type, document)
        if section_match:
            return True, 'section', section_notes
        
        return False, 'none', 'No keyword matches found'
    
    def _check_filename_keywords(self, screening_type: ScreeningType, document: MedicalDocument) -> Tuple[bool, str]:
        """Check if document filename matches screening keywords"""
        if not screening_type.filename_keywords:
            return False, "No filename keywords defined"
        
        keywords = [k.strip().lower() for k in screening_type.filename_keywords.split(',') if k.strip()]
        filename = document.filename.lower() if document.filename else ""
        
        matched_keywords = [k for k in keywords if k in filename]
        if matched_keywords:
            return True, f"Filename matched keywords: {', '.join(matched_keywords)}"
        
        return False, f"Filename '{filename}' didn't match keywords: {', '.join(keywords)}"
    
    def _check_content_keywords(self, screening_type: ScreeningType, document: MedicalDocument) -> Tuple[bool, str]:
        """Check if document content matches screening keywords"""
        if not screening_type.content_keywords:
            return False, "No content keywords defined"
        
        keywords = [k.strip().lower() for k in screening_type.content_keywords.split(',') if k.strip()]
        content = getattr(document, 'content', '') or getattr(document, 'extracted_text', '') or ""
        content = content.lower()
        
        matched_keywords = [k for k in keywords if k in content]
        if matched_keywords:
            return True, f"Content matched keywords: {', '.join(matched_keywords)}"
        
        return False, f"Content didn't match keywords: {', '.join(keywords)}"
    
    def _check_section_keywords(self, screening_type: ScreeningType, document: MedicalDocument) -> Tuple[bool, str]:
        """Check if document section matches screening keywords"""
        # Check if screening type has section-based keywords
        section_keywords = getattr(screening_type, 'section_keywords', None) or getattr(screening_type, 'keywords', None)
        if not section_keywords:
            return False, "No section keywords defined"
        
        keywords = [k.strip().lower() for k in section_keywords.split(',') if k.strip()]
        
        # Check various document section fields
        section_fields = [
            getattr(document, 'section', ''),
            getattr(document, 'document_type', ''),
            getattr(document, 'category', ''),
        ]
        
        for field in section_fields:
            if field:
                field_lower = field.lower()
                matched_keywords = [k for k in keywords if k in field_lower]
                if matched_keywords:
                    return True, f"Section '{field}' matched keywords: {', '.join(matched_keywords)}"
        
        return False, f"No section matches for keywords: {', '.join(keywords)}"


class ScreeningStatusMixin:
    """
    Mixin providing centralized screening status determination logic
    Eliminates duplicate status calculation across engines
    """
    
    # Status Constants
    STATUS_DUE = "Due"
    STATUS_DUE_SOON = "Due Soon"
    STATUS_INCOMPLETE = "Incomplete"
    STATUS_COMPLETE = "Complete"
    
    # Configuration
    DUE_SOON_THRESHOLD_DAYS = 30
    
    def determine_screening_status(self, patient: Patient, screening_type: ScreeningType, 
                                 matched_documents: Optional[List[MedicalDocument]] = None) -> str:
        """
        Unified screening status determination logic
        
        Args:
            patient: Patient object
            screening_type: ScreeningType object
            matched_documents: List of documents that match this screening (optional)
            
        Returns:
            Status string (Due, Due Soon, Incomplete, Complete)
        """
        # Check if we have matching documents
        if matched_documents:
            # If we have documents, status is likely Complete
            return self.STATUS_COMPLETE
        
        # Check existing screening records
        existing_screening = Screening.query.filter_by(
            patient_id=patient.id,
            screening_type=screening_type.name
        ).first()
        
        if existing_screening:
            # If screening exists but no documents matched, it might be incomplete
            if not existing_screening.documents.count():
                return self.STATUS_INCOMPLETE
            else:
                return self.STATUS_COMPLETE
        
        # No existing screening - determine if due or due soon
        return self._calculate_due_status(patient, screening_type)
    
    def _calculate_due_status(self, patient: Patient, screening_type: ScreeningType) -> str:
        """Calculate due status based on patient age and screening frequency"""
        # Simple logic - can be enhanced based on specific requirements
        # For now, assume all eligible patients are "Due"
        return self.STATUS_DUE


class ScreeningUtilities:
    """
    Static utility functions for common screening operations
    Replaces duplicate utility code across multiple files
    """
    
    @staticmethod
    def calculate_age(birth_date: Union[date, datetime, str]) -> Optional[int]:
        """Calculate age from birth date - unified implementation"""
        if not birth_date:
            return None
        
        try:
            if isinstance(birth_date, str):
                # Try to parse string date
                try:
                    birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        birth_date = datetime.strptime(birth_date, '%m/%d/%Y').date()
                    except ValueError:
                        return None
            elif isinstance(birth_date, datetime):
                birth_date = birth_date.date()
            
            today = date.today()
            age = today.year - birth_date.year
            
            # Adjust if birthday hasn't occurred this year
            if today < birth_date.replace(year=today.year):
                age -= 1
                
            return max(0, age)  # Ensure non-negative age
            
        except Exception as e:
            logger.warning(f"Error calculating age from {birth_date}: {e}")
            return None
    
    @staticmethod
    def safe_get_patient_demographics(patient_id: int) -> Optional[Dict[str, Any]]:
        """Safely get patient demographics - unified implementation"""
        try:
            patient = Patient.query.filter(Patient.id == patient_id).first()
            if not patient:
                return None
                
            return {
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'date_of_birth': patient.date_of_birth,
                'gender': patient.gender,
                'sex': patient.sex,
                'age': patient.age or ScreeningUtilities.calculate_age(patient.date_of_birth)
            }
        except Exception as e:
            logger.error(f"Error getting patient demographics: {e}")
            return None
    
    @staticmethod
    def safe_get_document_details(document_id: int) -> Optional[Dict[str, Any]]:
        """Safely get document details - unified implementation"""
        try:
            document = MedicalDocument.query.filter(MedicalDocument.id == document_id).first()
            if not document:
                return None
                
            return {
                'id': document.id,
                'filename': document.filename,
                'document_type': document.document_type,
                'content': getattr(document, 'content', ''),
                'extracted_text': getattr(document, 'extracted_text', ''),
                'created_at': document.created_at,
                'document_date': getattr(document, 'document_date', None),
                'patient_id': document.patient_id
            }
        except Exception as e:
            logger.error(f"Error getting document details: {e}")
            return None
    
    @staticmethod
    def get_active_screening_types() -> List[ScreeningType]:
        """Get all active screening types - unified query"""
        return ScreeningType.query.filter_by(is_active=True, status='active').all()


class BaseScreeningEngine(PatientDemographicsMixin, DocumentMatchingMixin, ScreeningStatusMixin, ABC):
    """
    Abstract base class for all screening engines
    Provides common functionality and enforces consistent interface
    """
    
    def __init__(self):
        self.debug_mode = False
        self.utilities = ScreeningUtilities()
    
    @abstractmethod
    def process_patient_screenings(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Abstract method that each screening engine must implement
        Should return list of screening data dictionaries
        """
        pass
    
    def validate_inputs(self, patient_id: Optional[int] = None, document_id: Optional[int] = None, 
                       screening_type_id: Optional[int] = None) -> Tuple[bool, str]:
        """Common input validation"""
        if patient_id is not None and not Patient.query.get(patient_id):
            return False, f"Patient {patient_id} not found"
        
        if document_id is not None and not MedicalDocument.query.get(document_id):
            return False, f"Document {document_id} not found"
        
        if screening_type_id is not None and not ScreeningType.query.get(screening_type_id):
            return False, f"ScreeningType {screening_type_id} not found"
        
        return True, "Valid"
    
    def log_debug(self, message: str):
        """Unified debug logging"""
        if self.debug_mode:
            logger.debug(f"[{self.__class__.__name__}] {message}")