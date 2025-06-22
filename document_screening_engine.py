"""
Document Screening Engine
Parses patient documents and matches them to screening rules to populate prep sheets
"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from models import Patient, ScreeningType, MedicalDocument, Condition, db
from app import app


@dataclass
class DocumentMatch:
    """Represents a match between a document and screening rule"""
    document_id: int
    document_filename: str
    screening_type_id: int
    screening_name: str
    match_type: str  # 'keyword', 'condition', 'fhir_code'
    matched_value: str
    confidence: float
    matched_date: Optional[datetime] = None


@dataclass
class ScreeningStatus:
    """Represents the status of a screening for prep sheet display"""
    screening_type_id: int
    screening_name: str
    status: str  # 'complete', 'due', 'overdue', 'no_documents'
    last_completed: Optional[datetime] = None
    due_date: Optional[datetime] = None
    documents_found: List[DocumentMatch] = None
    notes: str = ""


class DocumentScreeningEngine:
    """
    Main engine that parses documents and matches them to screening rules
    """
    
    def __init__(self):
        self.app = app
        
    def parse_patient_documents(self, patient_id: int) -> List[DocumentMatch]:
        """
        Parse all documents for a patient and find screening matches
        
        Args:
            patient_id: ID of the patient
            
        Returns:
            List of document matches
        """
        with self.app.app_context():
            # Get patient documents
            documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()
            
            # Get all screening types with their rules
            screening_types = ScreeningType.query.all()
            
            matches = []
            
            for document in documents:
                # Parse document content
                doc_matches = self._parse_single_document(document, screening_types)
                matches.extend(doc_matches)
            
            return matches
    
    def _parse_single_document(self, document: MedicalDocument, screening_types: List[ScreeningType]) -> List[DocumentMatch]:
        """
        Parse a single document against all screening rules
        
        Args:
            document: Medical document to parse
            screening_types: List of screening types to match against
            
        Returns:
            List of matches for this document
        """
        matches = []
        
        # Prepare document content for searching
        content = self._prepare_document_content(document)
        
        for screening_type in screening_types:
            # Check keyword matches
            keyword_matches = self._check_keyword_matches(document, screening_type, content)
            matches.extend(keyword_matches)
            
            # Check condition trigger matches
            condition_matches = self._check_condition_matches(document, screening_type, content)
            matches.extend(condition_matches)
            
            # Check FHIR code matches (if document has structured data)
            fhir_matches = self._check_fhir_code_matches(document, screening_type)
            matches.extend(fhir_matches)
        
        return matches
    
    def _prepare_document_content(self, document: MedicalDocument) -> str:
        """
        Prepare document content for text searching
        
        Args:
            document: Medical document
            
        Returns:
            Cleaned and normalized document content
        """
        content_parts = []
        
        # Add filename (often contains useful information)
        if document.filename:
            content_parts.append(document.filename.lower())
        
        # Add document content if available
        if hasattr(document, 'content') and document.content:
            content_parts.append(document.content.lower())
        
        # Add any extracted text
        if hasattr(document, 'extracted_text') and document.extracted_text:
            content_parts.append(document.extracted_text.lower())
        
        # Combine all content
        full_content = ' '.join(content_parts)
        
        # Normalize whitespace and remove special characters for better matching
        full_content = re.sub(r'[^\w\s]', ' ', full_content)
        full_content = re.sub(r'\s+', ' ', full_content)
        
        return full_content.strip()
    
    def _check_keyword_matches(self, document: MedicalDocument, screening_type: ScreeningType, content: str) -> List[DocumentMatch]:
        """
        Check if document content matches screening keywords
        
        Args:
            document: Medical document
            screening_type: Screening type with keywords
            content: Prepared document content
            
        Returns:
            List of keyword matches
        """
        matches = []
        
        # Get keywords for this screening type
        keywords = self._get_screening_keywords(screening_type.id)
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            if keyword_lower and keyword_lower in content:
                confidence = self._calculate_keyword_confidence(keyword, content)
                
                match = DocumentMatch(
                    document_id=document.id,
                    document_filename=document.filename,
                    screening_type_id=screening_type.id,
                    screening_name=screening_type.name,
                    match_type='keyword',
                    matched_value=keyword,
                    confidence=confidence,
                    matched_date=document.upload_date if hasattr(document, 'upload_date') else None
                )
                matches.append(match)
        
        return matches
    
    def _check_condition_matches(self, document: MedicalDocument, screening_type: ScreeningType, content: str) -> List[DocumentMatch]:
        """
        Check if document content matches trigger conditions
        
        Args:
            document: Medical document
            screening_type: Screening type with trigger conditions
            content: Prepared document content
            
        Returns:
            List of condition matches
        """
        matches = []
        
        # Get trigger conditions for this screening type
        trigger_conditions = self._get_trigger_conditions(screening_type)
        
        for condition in trigger_conditions:
            # Check if condition display name or code appears in content
            display_name = condition.get('display', '').lower()
            code = condition.get('code', '').lower()
            
            matched_value = None
            if display_name and display_name in content:
                matched_value = condition.get('display')
            elif code and code in content:
                matched_value = condition.get('code')
            
            if matched_value:
                confidence = self._calculate_condition_confidence(condition, content)
                
                match = DocumentMatch(
                    document_id=document.id,
                    document_filename=document.filename,
                    screening_type_id=screening_type.id,
                    screening_name=screening_type.name,
                    match_type='condition',
                    matched_value=matched_value,
                    confidence=confidence,
                    matched_date=document.upload_date if hasattr(document, 'upload_date') else None
                )
                matches.append(match)
        
        return matches
    
    def _check_fhir_code_matches(self, document: MedicalDocument, screening_type: ScreeningType) -> List[DocumentMatch]:
        """
        Check if document has FHIR codes that match screening triggers
        
        Args:
            document: Medical document
            screening_type: Screening type with trigger conditions
            
        Returns:
            List of FHIR code matches
        """
        matches = []
        
        # Check if document has FHIR data
        if not hasattr(document, 'fhir_data') or not document.fhir_data:
            return matches
        
        try:
            fhir_data = json.loads(document.fhir_data) if isinstance(document.fhir_data, str) else document.fhir_data
        except (json.JSONDecodeError, TypeError):
            return matches
        
        # Get trigger conditions for this screening type
        trigger_conditions = self._get_trigger_conditions(screening_type)
        
        # Extract codes from FHIR data
        document_codes = self._extract_fhir_codes(fhir_data)
        
        for condition in trigger_conditions:
            condition_code = condition.get('code', '').lower()
            condition_system = condition.get('system', '')
            
            for doc_code in document_codes:
                if (condition_code == doc_code.get('code', '').lower() and 
                    condition_system == doc_code.get('system', '')):
                    
                    match = DocumentMatch(
                        document_id=document.id,
                        document_filename=document.filename,
                        screening_type_id=screening_type.id,
                        screening_name=screening_type.name,
                        match_type='fhir_code',
                        matched_value=f"{condition_code} ({condition_system})",
                        confidence=0.95,  # High confidence for exact FHIR code matches
                        matched_date=document.upload_date if hasattr(document, 'upload_date') else None
                    )
                    matches.append(match)
        
        return matches
    
    def _get_screening_keywords(self, screening_type_id: int) -> List[str]:
        """Get keywords for a screening type"""
        try:
            # Get keywords from the screening keyword manager
            from screening_keyword_manager import ScreeningKeywordManager
            keyword_manager = ScreeningKeywordManager()
            keywords = keyword_manager.get_keywords_for_screening(screening_type_id)
            return keywords if keywords else []
        except Exception as e:
            print(f"Error getting keywords for screening {screening_type_id}: {e}")
            return []
    
    def _get_trigger_conditions(self, screening_type: ScreeningType) -> List[Dict[str, str]]:
        """Get trigger conditions for a screening type"""
        if not screening_type.trigger_conditions:
            return []
        
        try:
            if isinstance(screening_type.trigger_conditions, str):
                return json.loads(screening_type.trigger_conditions)
            return screening_type.trigger_conditions
        except (json.JSONDecodeError, TypeError):
            return []
    
    def _extract_fhir_codes(self, fhir_data: Dict) -> List[Dict[str, str]]:
        """Extract codes from FHIR data structure"""
        codes = []
        
        def extract_codes_recursive(obj):
            if isinstance(obj, dict):
                # Look for code structures
                if 'code' in obj and 'system' in obj:
                    codes.append({
                        'code': obj.get('code', ''),
                        'system': obj.get('system', ''),
                        'display': obj.get('display', '')
                    })
                
                # Look for coding arrays
                if 'coding' in obj and isinstance(obj['coding'], list):
                    for coding in obj['coding']:
                        if isinstance(coding, dict):
                            codes.append({
                                'code': coding.get('code', ''),
                                'system': coding.get('system', ''),
                                'display': coding.get('display', '')
                            })
                
                # Recurse into nested objects
                for value in obj.values():
                    extract_codes_recursive(value)
            
            elif isinstance(obj, list):
                for item in obj:
                    extract_codes_recursive(item)
        
        extract_codes_recursive(fhir_data)
        return codes
    
    def _calculate_keyword_confidence(self, keyword: str, content: str) -> float:
        """Calculate confidence score for keyword match"""
        # Count occurrences
        occurrences = content.lower().count(keyword.lower())
        
        # Base confidence
        confidence = 0.6
        
        # Boost for multiple occurrences
        if occurrences > 1:
            confidence += min(0.2, occurrences * 0.05)
        
        # Boost for longer keywords
        if len(keyword) > 10:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_condition_confidence(self, condition: Dict, content: str) -> float:
        """Calculate confidence score for condition match"""
        # Higher confidence for condition matches
        confidence = 0.8
        
        # Check if both code and display are present
        display = condition.get('display', '')
        code = condition.get('code', '')
        
        if display.lower() in content and code.lower() in content:
            confidence = 0.95
        
        return confidence
    
    def generate_prep_sheet_screening_status(self, patient_id: int) -> List[ScreeningStatus]:
        """
        Generate screening status for prep sheet display
        
        Args:
            patient_id: ID of the patient
            
        Returns:
            List of screening statuses for prep sheet
        """
        with self.app.app_context():
            # Get all document matches for this patient
            document_matches = self.parse_patient_documents(patient_id)
            
            # Get all screening types
            screening_types = ScreeningType.query.all()
            
            # Group matches by screening type
            matches_by_screening = defaultdict(list)
            for match in document_matches:
                matches_by_screening[match.screening_type_id].append(match)
            
            screening_statuses = []
            
            for screening_type in screening_types:
                matches = matches_by_screening.get(screening_type.id, [])
                
                if matches:
                    # Determine status based on matches and timing
                    status = self._determine_screening_status(screening_type, matches)
                    
                    # Find most recent match
                    most_recent_match = max(matches, key=lambda m: m.matched_date or datetime.min)
                    
                    screening_status = ScreeningStatus(
                        screening_type_id=screening_type.id,
                        screening_name=screening_type.name,
                        status=status,
                        last_completed=most_recent_match.matched_date,
                        documents_found=matches,
                        notes=f"Found {len(matches)} matching document(s)"
                    )
                else:
                    # No documents found for this screening
                    screening_status = ScreeningStatus(
                        screening_type_id=screening_type.id,
                        screening_name=screening_type.name,
                        status='no_documents',
                        documents_found=[],
                        notes="No documents found"
                    )
                
                screening_statuses.append(screening_status)
            
            return screening_statuses
    
    def _determine_screening_status(self, screening_type: ScreeningType, matches: List[DocumentMatch]) -> str:
        """
        Determine screening status based on matches and timing
        
        Args:
            screening_type: The screening type
            matches: List of document matches
            
        Returns:
            Status string: 'complete', 'due', 'overdue'
        """
        if not matches:
            return 'no_documents'
        
        # Find most recent match
        most_recent_match = max(matches, key=lambda m: m.matched_date or datetime.min)
        
        if not most_recent_match.matched_date:
            return 'complete'  # Document found but no date
        
        # Calculate if screening is due based on frequency
        if screening_type.frequency_number and screening_type.frequency_unit:
            try:
                # Calculate next due date
                frequency_days = self._convert_frequency_to_days(
                    screening_type.frequency_number, 
                    screening_type.frequency_unit
                )
                
                next_due = most_recent_match.matched_date + timedelta(days=frequency_days)
                today = datetime.now()
                
                if next_due <= today:
                    return 'due'
                else:
                    return 'complete'
            except:
                return 'complete'
        
        return 'complete'
    
    def _convert_frequency_to_days(self, frequency_number: int, frequency_unit: str) -> int:
        """Convert frequency to days"""
        multipliers = {
            'days': 1,
            'weeks': 7,
            'months': 30,
            'years': 365
        }
        return frequency_number * multipliers.get(frequency_unit.lower(), 365)


# Global instance
document_screening_engine = DocumentScreeningEngine()