#!/usr/bin/env python3
"""
Efficient Screening Matcher
Streamlined keyword matching system that uses only the current 'manage screening types' system
Eliminates redundant API calls and old system references
"""

from typing import Dict, List, Optional, Set
from models import ScreeningType, Patient, MedicalDocument
from app import db
import logging

logger = logging.getLogger(__name__)

class EfficientScreeningMatcher:
    """
    Efficient screening matcher that caches screening types and eliminates redundant calls
    """
    
    def __init__(self):
        self._screening_cache = {}
        self._keywords_cache = {}
        
    def get_all_active_screenings(self) -> List[ScreeningType]:
        """Get all active screening types with caching"""
        if not self._screening_cache:
            screenings = ScreeningType.query.filter_by(is_active=True, status='active').all()
            self._screening_cache = {s.id: s for s in screenings}
        
        return list(self._screening_cache.values())
    
    def get_screening_keywords(self, screening_id: int) -> Dict[str, List[str]]:
        """
        Get all keywords for a screening type with caching
        Returns dict with 'filename', 'content', 'document' keyword lists
        """
        if screening_id in self._keywords_cache:
            return self._keywords_cache[screening_id]
        
        screening = self._screening_cache.get(screening_id)
        if not screening:
            screening = ScreeningType.query.get(screening_id)
            if screening:
                self._screening_cache[screening_id] = screening
        
        if not screening:
            return {'filename': [], 'content': [], 'document': []}
        
        # Get keywords only from user-defined fields - no auto-generation
        keywords = {
            'filename': screening.get_filename_keywords() or [],
            'content': screening.get_content_keywords() or [],
            'document': screening.get_document_keywords() or []
        }
        
        self._keywords_cache[screening_id] = keywords
        return keywords
    
    def clear_cache(self):
        """Clear the internal cache"""
        self._screening_cache.clear()
        self._keywords_cache.clear()
    
    def match_document_bulk(self, document: MedicalDocument, patient: Patient) -> List[Dict]:
        """
        Match a document against all active screening types efficiently
        Returns list of matches with scores
        """
        matches = []
        
        # Get all active screenings once
        screenings = self.get_all_active_screenings()
        
        for screening in screenings:
            # Quick demographic filter
            if not self._check_demographics_quick(screening, patient):
                continue
            
            # Get keywords once per screening
            keywords = self.get_screening_keywords(screening.id)
            
            # Calculate match score
            match_score = self._calculate_match_score(document, keywords)
            
            if match_score > 0:
                matches.append({
                    'screening_id': screening.id,
                    'screening_name': screening.name,
                    'match_score': match_score,
                    'keywords_matched': self._get_matched_keywords(document, keywords)
                })
        
        # Sort by match score descending
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches
    
    def _check_demographics_quick(self, screening: ScreeningType, patient: Patient) -> bool:
        """Quick demographic check"""
        # Age check
        patient_age = patient.age
        if screening.min_age is not None and patient_age < screening.min_age:
            return False
        if screening.max_age is not None and patient_age > screening.max_age:
            return False
        
        # Gender check
        if screening.gender_specific:
            if patient.sex.lower() != screening.gender_specific.lower():
                return False
        
        return True
    
    def _calculate_match_score(self, document: MedicalDocument, keywords: Dict[str, List[str]]) -> float:
        """Calculate match score for a document against keywords"""
        score = 0.0
        
        # Prepare document text
        filename_text = (document.filename or '').lower()
        content_text = ((document.content or '') + ' ' + (document.extracted_text or '')).lower()
        
        # Filename matches (weight: 3.0)
        for keyword in keywords['filename']:
            if keyword.lower() in filename_text:
                score += 3.0
        
        # Content matches (weight: 2.0)
        for keyword in keywords['content']:
            if keyword.lower() in content_text:
                score += 2.0
        
        # Document type matches (weight: 1.0)
        for keyword in keywords['document']:
            if keyword.lower() in content_text or keyword.lower() in filename_text:
                score += 1.0
        
        return score
    
    def _get_matched_keywords(self, document: MedicalDocument, keywords: Dict[str, List[str]]) -> List[str]:
        """Get list of keywords that matched"""
        matched = []
        
        filename_text = (document.filename or '').lower()
        content_text = ((document.content or '') + ' ' + (document.extracted_text or '')).lower()
        
        # Check all keyword types
        for keyword_type, keyword_list in keywords.items():
            for keyword in keyword_list:
                if keyword.lower() in filename_text or keyword.lower() in content_text:
                    matched.append(f"{keyword} ({keyword_type})")
        
        return matched

# Global instance for reuse
efficient_matcher = EfficientScreeningMatcher()

def match_document_efficiently(document: MedicalDocument, patient: Patient) -> List[Dict]:
    """
    Convenience function to match a document efficiently
    Uses global cached instance
    """
    return efficient_matcher.match_document_bulk(document, patient)

def clear_screening_cache():
    """Clear the global screening cache"""
    efficient_matcher.clear_cache()

if __name__ == "__main__":
    print("Efficient Screening Matcher - Test Mode")
    print("This module provides efficient keyword matching using only the current manage screening types system")