"""
Document Screening Matcher
Matches medical documents to screening types using patient profile and document metadata/content
Uses ScreeningType rules from /screenings?tab=types
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
import re
import json
from models import ScreeningType, Patient, MedicalDocument
from app import db


class DocumentScreeningMatcher:
    """Matches documents to screening types based on content, keywords, and patient criteria"""
    
    def __init__(self):
        self.screening_types = self._load_screening_types()
    
    def _load_screening_types(self) -> List[ScreeningType]:
        """Load all active screening types"""
        return ScreeningType.query.filter_by(is_active=True, status='active').all()
    
    def match_document_to_screening(
        self, 
        screening_type: ScreeningType, 
        document: MedicalDocument, 
        patient: Patient
    ) -> Dict[str, Any]:
        """
        Match a document to a specific screening type using ScreeningType rules
        
        Args:
            screening_type: ScreeningType object with matching criteria
            document: MedicalDocument object to analyze
            patient: Patient object for demographic matching
            
        Returns:
            Dict containing:
                - matched: bool
                - match_method: str ('content' | 'filename' | 'keywords')
                - document_id: int
                - notes: str
                - status: str (derived status string)
        """
        result = {
            'matched': False,
            'match_method': None,
            'document_id': document.id,
            'notes': '',
            'status': 'no_match'
        }
        
        # Step 1: Use conditions, gender, and age to filter applicable screenings
        demographic_match, demographic_notes = self._check_patient_demographics(screening_type, patient)
        if not demographic_match:
            result['notes'] = demographic_notes
            result['status'] = 'demographic_mismatch'
            return result
        
        # Step 2: Match documents based on filename_keywords in document name
        filename_match, filename_notes = self._check_filename_keywords(screening_type, document)
        if filename_match:
            result.update({
                'matched': True,
                'match_method': 'filename',
                'notes': f"Demographics OK. {filename_notes}",
                'status': 'matched_filename'
            })
            return result
        
        # Step 3: Match documents based on keywords in content  
        content_match, content_notes = self._check_content_keywords(screening_type, document)
        if content_match:
            result.update({
                'matched': True,
                'match_method': 'content',
                'notes': f"Demographics OK. {content_notes}",
                'status': 'matched_content'
            })
            return result
        
        # Step 4: Match document.section (or existing equivalent) matches screening_type.section
        section_match, section_notes = self._check_document_section_keywords(screening_type, document)
        if section_match:
            result.update({
                'matched': True,
                'match_method': 'keywords',
                'notes': f"Demographics OK. {section_notes}",
                'status': 'matched_section'
            })
            return result
        
        # No matches found but demographics OK
        result['notes'] = f"Demographics OK but no content/filename/section matches for {screening_type.name}"
        result['status'] = 'no_keyword_match'
        return result
    
    def _check_patient_demographics(
        self, 
        screening_type: ScreeningType, 
        patient: Patient
    ) -> Tuple[bool, str]:
        """Check if patient demographics match screening criteria"""
        notes = []
        
        # Check age criteria
        patient_age = patient.age
        if screening_type.min_age is not None and patient_age < screening_type.min_age:
            return False, f"Patient age {patient_age} below minimum {screening_type.min_age}"
        
        if screening_type.max_age is not None and patient_age > screening_type.max_age:
            return False, f"Patient age {patient_age} above maximum {screening_type.max_age}"
        
        # Check gender criteria
        if screening_type.gender_specific:
            if patient.sex.lower() != screening_type.gender_specific.lower():
                return False, f"Patient gender {patient.sex} doesn't match required {screening_type.gender_specific}"
        
        # Demographics match
        age_note = f"age {patient_age}"
        if screening_type.min_age or screening_type.max_age:
            age_range = f"{screening_type.min_age or 0}-{screening_type.max_age or '∞'}"
            age_note += f" (range: {age_range})"
        
        gender_note = f"gender {patient.sex}"
        if screening_type.gender_specific:
            gender_note += f" (required: {screening_type.gender_specific})"
        
        return True, f"Demographics match: {age_note}, {gender_note}"
    
    def _check_filename_keywords(
        self, 
        screening_type: ScreeningType, 
        document: MedicalDocument
    ) -> Tuple[bool, str]:
        """Check if document filename matches screening filename keywords"""
        # Use only unified keywords to prevent duplication
        unified_keywords = screening_type.unified_keywords or []
        if not unified_keywords:
            return False, "No filename keywords defined"
        
        filename = document.filename.lower() if document.filename else ""
        matched_keywords = []
        
        for keyword in unified_keywords:
            if keyword.lower() in filename:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            return True, f"Filename keywords matched: {', '.join(matched_keywords)}"
        
        return False, f"No filename keyword matches in '{document.filename}'"
    
    def _check_content_keywords(
        self, 
        screening_type: ScreeningType, 
        document: MedicalDocument
    ) -> Tuple[bool, str]:
        """Check if document content matches screening content keywords"""
        # Use only unified keywords to prevent duplication
        unified_keywords = screening_type.unified_keywords or []
        if not unified_keywords:
            return False, "No content keywords defined"
        
        # Combine searchable text from document
        searchable_text = ""
        if document.content:
            searchable_text += document.content.lower()
        if document.extracted_text:
            searchable_text += " " + document.extracted_text.lower()
        
        if not searchable_text.strip():
            return False, "No document content available for matching"
        
        matched_keywords = []
        for keyword in unified_keywords:
            if keyword.lower() in searchable_text:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            return True, f"Content keywords matched: {', '.join(matched_keywords)}"
        
        return False, f"No content keyword matches found"
    
    def _check_document_section_keywords(
        self, 
        screening_type: ScreeningType, 
        document: MedicalDocument
    ) -> Tuple[bool, str]:
        """Check if document.section matches screening_type document keywords"""
        # Use only unified keywords to prevent duplication
        unified_keywords = screening_type.unified_keywords or []
        if not unified_keywords:
            return False, "No document section keywords defined"
        
        # Get document section - check multiple possible attributes
        document_section = ""
        if hasattr(document, 'section') and document.section:
            document_section = document.section.lower()
        elif hasattr(document, 'document_type') and document.document_type:
            document_section = document.document_type.value.lower()
        elif hasattr(document, 'category') and document.category:
            document_section = document.category.lower()
        
        if not document_section:
            return False, "No document section available for matching"
        
        matched_keywords = []
        for keyword in unified_keywords:
            keyword_lower = keyword.lower()
            # Check exact match or contains match
            if (keyword_lower == document_section or 
                keyword_lower in document_section or
                document_section in keyword_lower):
                matched_keywords.append(keyword)
        
        if matched_keywords:
            return True, f"Section keywords matched: {', '.join(matched_keywords)} (document section: '{document_section}')"
        
        return False, f"No section keyword matches for document section '{document_section}'"
    
    def find_matching_screenings(
        self, 
        document: MedicalDocument, 
        patient: Patient
    ) -> List[Dict[str, Any]]:
        """
        Find all screening types that match a given document and patient
        
        Returns:
            List of match results for each screening type
        """
        matches = []
        
        for screening_type in self.screening_types:
            match_result = self.match_document_to_screening(screening_type, document, patient)
            match_result['screening_type'] = screening_type.name
            match_result['screening_id'] = screening_type.id
            matches.append(match_result)
        
        # Sort by matched first, then by match strength
        def sort_key(match):
            if not match['matched']:
                return (0, match['screening_type'])
            
            # Prioritize match methods
            method_priority = {
                'content': 3,
                'filename': 2,
                'keywords': 1
            }
            priority = method_priority.get(match['match_method'], 0)
            return (1, priority, match['screening_type'])
        
        matches.sort(key=sort_key, reverse=True)
        return matches
    
    def get_screening_recommendations(
        self, 
        patient: Patient, 
        documents: List[MedicalDocument] = None
    ) -> Dict[str, Any]:
        """
        Get screening recommendations for a patient based on their documents
        
        Args:
            patient: Patient object
            documents: Optional list of documents to analyze
            
        Returns:
            Dict with screening recommendations and document analysis
        """
        if documents is None:
            documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
        
        recommendations = {
            'patient_id': patient.id,
            'patient_name': patient.full_name,
            'analysis_date': datetime.now().isoformat(),
            'document_count': len(documents),
            'screening_matches': {},
            'recommendations': []
        }
        
        # Analyze each document
        all_matches = []
        for document in documents:
            matches = self.find_matching_screenings(document, patient)
            for match in matches:
                if match['matched']:
                    all_matches.append(match)
        
        # Group matches by screening type
        screening_matches = {}
        for match in all_matches:
            screening_name = match['screening_type']
            if screening_name not in screening_matches:
                screening_matches[screening_name] = []
            screening_matches[screening_name].append(match)
        
        recommendations['screening_matches'] = screening_matches
        
        # Generate recommendations
        for screening_name, matches in screening_matches.items():
            screening_type = next(
                (st for st in self.screening_types if st.name == screening_name), 
                None
            )
            
            if screening_type:
                freq_text = screening_type.formatted_frequency or "As recommended"
                recommendation = {
                    'screening_type': screening_name,
                    'frequency': freq_text,
                    'matched_documents': len(matches),
                    'last_match': max(matches, key=lambda x: x['document_id'])['notes'],
                    'priority': 'high' if len(matches) > 1 else 'normal'
                }
                recommendations['recommendations'].append(recommendation)
        
        return recommendations


# Convenience function for direct use
def match_document_to_screening(
    screening_type: ScreeningType, 
    document: MedicalDocument, 
    patient: Patient
) -> Dict[str, Any]:
    """
    Convenience function to match a document to a screening type
    
    Args:
        screening_type: ScreeningType object with matching criteria
        document: MedicalDocument object to analyze  
        patient: Patient object for demographic matching
        
    Returns:
        Dict containing match results:
        - matched: bool
        - match_method: str ('content', 'filename', 'keywords')
        - document_id: int
        - notes: str
        - status: str (derived status string)
    """
    matcher = DocumentScreeningMatcher()
    return matcher.match_document_to_screening(screening_type, document, patient)


# Example usage function
def demo_document_matching():
    """Demonstrate document matching functionality"""
    from models import Patient, MedicalDocument, ScreeningType
    
    # Get a sample patient and document
    patient = Patient.query.first()
    document = MedicalDocument.query.first()
    screening_type = ScreeningType.query.filter_by(is_active=True).first()
    
    if not all([patient, document, screening_type]):
        print("Missing required data for demo")
        return
    
    print(f"Demo: Matching document '{document.filename}' to screening '{screening_type.name}'")
    print(f"Patient: {patient.full_name}, Age: {patient.age}, Gender: {patient.sex}")
    
    result = match_document_to_screening(screening_type, document, patient)
    
    print(f"\nResult:")
    print(f"  Matched: {result['matched']}")
    print(f"  Method: {result['match_method']}")
    print(f"  Status: {result['status']}")
    print(f"  Notes: {result['notes']}")
    
    # Show all screening matches for this document
    matcher = DocumentScreeningMatcher()
    all_matches = matcher.find_matching_screenings(document, patient)
    
    print(f"\nAll screening matches for this document:")
    for match in all_matches[:5]:  # Show top 5
        status = "✓" if match['matched'] else "✗"
        print(f"  {status} {match['screening_type']}: {match['status']}")


if __name__ == '__main__':
    demo_document_matching()