"""
Centralized Screening Type Document Parsing Logic
Integrates all screening type matching rules into a unified system
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from models import ScreeningType, Patient
from app import db


class ScreeningDocumentParser:
    """Centralized document parser using ScreeningType model configuration"""
    
    def __init__(self):
        self.screening_types = None
        self._load_screening_types()
    
    def _load_screening_types(self):
        """Load all active screening types from database"""
        self.screening_types = ScreeningType.query.filter_by(is_active=True).all()
    
    def refresh_cache(self):
        """Refresh the cached screening types"""
        self._load_screening_types()
    
    def parse_document(
        self, 
        content: str = None, 
        filename: str = None, 
        document_section: str = None,
        patient: Patient = None
    ) -> List[Dict[str, Any]]:
        """
        Parse a document and return matching screening types
        
        Args:
            content: Document text content
            filename: Document filename
            document_section: Document section (labs, imaging, etc.)
            patient: Patient object for demographic matching
            
        Returns:
            List of matching screening type dictionaries with match reasons
        """
        if not self.screening_types:
            self._load_screening_types()
        
        matches = []
        
        for screening_type in self.screening_types:
            match_result = self._evaluate_screening_match(
                screening_type, content, filename, document_section, patient
            )
            
            if match_result['matches']:
                matches.append({
                    'screening_type': screening_type,
                    'match_score': match_result['score'],
                    'match_reasons': match_result['reasons'],
                    'confidence': match_result['confidence']
                })
        
        # Sort by match score (highest first)
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches
    
    def _evaluate_screening_match(
        self, 
        screening_type: ScreeningType, 
        content: str = None, 
        filename: str = None, 
        document_section: str = None,
        patient: Patient = None
    ) -> Dict[str, Any]:
        """
        Evaluate if a screening type matches the given document/patient criteria
        
        Returns:
            Dictionary with match result, score, reasons, and confidence
        """
        match_score = 0
        reasons = []
        confidence = 0.0
        
        # Check patient demographic criteria first
        if patient and not screening_type.matches_patient_criteria(patient):
            return {
                'matches': False,
                'score': 0,
                'reasons': ['Patient does not meet age/gender criteria'],
                'confidence': 0.0
            }
        
        # Document section matching (highest weight)
        if document_section and screening_type.matches_document_section(document_section):
            match_score += 50
            reasons.append(f"Document section '{document_section}' matches")
            confidence += 0.3
        
        # Content keyword matching
        if content and screening_type.matches_content_keywords(content):
            keyword_matches = []
            for keyword in screening_type.get_keywords():
                if keyword.lower() in content.lower():
                    keyword_matches.append(keyword)
            
            match_score += len(keyword_matches) * 10
            reasons.append(f"Content keywords matched: {', '.join(keyword_matches)}")
            confidence += min(0.4, len(keyword_matches) * 0.1)
        
        # Filename keyword matching
        if filename and screening_type.matches_filename_keywords(filename):
            filename_keyword_matches = []
            for keyword in screening_type.get_filename_keywords():
                if keyword.lower() in filename.lower():
                    filename_keyword_matches.append(keyword)
            
            match_score += len(filename_keyword_matches) * 15
            reasons.append(f"Filename keywords matched: {', '.join(filename_keyword_matches)}")
            confidence += min(0.3, len(filename_keyword_matches) * 0.15)
        
        # Patient demographic bonus (if patient matches criteria)
        if patient and screening_type.matches_patient_criteria(patient):
            match_score += 5
            reasons.append("Patient meets demographic criteria")
            confidence += 0.1
        
        matches = match_score > 0
        confidence = min(1.0, confidence)  # Cap confidence at 1.0
        
        return {
            'matches': matches,
            'score': match_score,
            'reasons': reasons,
            'confidence': confidence
        }
    
    def get_screening_recommendations(
        self, 
        patient: Patient, 
        document_section: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get screening recommendations for a patient based on demographics and optional document section
        
        Args:
            patient: Patient object
            document_section: Optional document section to filter by
            
        Returns:
            List of recommended screening types with rationale
        """
        if not self.screening_types:
            self._load_screening_types()
        
        recommendations = []
        
        for screening_type in self.screening_types:
            if screening_type.matches_patient_criteria(patient):
                recommendation = {
                    'screening_type': screening_type,
                    'frequency_months': screening_type.frequency_months,
                    'rationale': [],
                    'priority': 'standard'
                }
                
                # Add demographic rationale
                if screening_type.min_age and patient.age >= screening_type.min_age:
                    recommendation['rationale'].append(f"Age {patient.age} meets minimum age {screening_type.min_age}")
                
                if screening_type.gender and screening_type.gender.lower() == patient.sex.lower():
                    recommendation['rationale'].append(f"Gender-specific screening for {patient.sex}")
                
                # Check document section relevance
                if document_section and screening_type.matches_document_section(document_section):
                    recommendation['rationale'].append(f"Relevant to {document_section} section")
                    recommendation['priority'] = 'high'
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def get_trigger_condition_screenings(self, condition_codes: List[str]) -> List[ScreeningType]:
        """
        Get screening types triggered by specific medical condition codes
        
        Args:
            condition_codes: List of condition codes (ICD-10, SNOMED, etc.)
            
        Returns:
            List of triggered screening types
        """
        if not self.screening_types:
            self._load_screening_types()
        
        triggered_screenings = []
        
        for screening_type in self.screening_types:
            trigger_conditions = screening_type.get_trigger_conditions()
            
            for condition_code in condition_codes:
                for trigger in trigger_conditions:
                    if trigger.get('code') == condition_code:
                        triggered_screenings.append(screening_type)
                        break
        
        return triggered_screenings
    
    def get_screenings_by_section(self, document_section: str) -> List[ScreeningType]:
        """
        Get all screening types for a specific document section
        
        Args:
            document_section: Document section name
            
        Returns:
            List of screening types for that section
        """
        if not self.screening_types:
            self._load_screening_types()
        
        return [
            st for st in self.screening_types 
            if st.matches_document_section(document_section)
        ]
    
    def search_by_keywords(self, keywords: List[str]) -> List[Tuple[ScreeningType, List[str]]]:
        """
        Search screening types by keywords
        
        Args:
            keywords: List of keywords to search for
            
        Returns:
            List of tuples (ScreeningType, matched_keywords)
        """
        if not self.screening_types:
            self._load_screening_types()
        
        results = []
        
        for screening_type in self.screening_types:
            matched_keywords = []
            screening_keywords = screening_type.get_keywords()
            
            for keyword in keywords:
                for screening_keyword in screening_keywords:
                    if keyword.lower() in screening_keyword.lower() or screening_keyword.lower() in keyword.lower():
                        matched_keywords.append(screening_keyword)
            
            if matched_keywords:
                results.append((screening_type, matched_keywords))
        
        return results


# Global parser instance
screening_parser = ScreeningDocumentParser()


def get_screening_parser() -> ScreeningDocumentParser:
    """Get the global screening parser instance"""
    return screening_parser


def refresh_screening_cache():
    """Refresh the global screening parser cache"""
    screening_parser.refresh_cache()