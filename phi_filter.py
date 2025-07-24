"""
PHI (Protected Health Information) Filter for OCR Text Processing
Removes or redacts sensitive patient information while preserving medical terminology
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, date
import json

logger = logging.getLogger(__name__)


class PHIFilterConfig:
    """Configuration for PHI filtering behavior"""
    
    def __init__(self):
        # Filtering strategies
        self.redaction_token = "[REDACTED]"
        self.date_token = "[DATE]"
        self.name_token = "[NAME]"
        self.phone_token = "[PHONE]"
        self.address_token = "[ADDRESS]"
        self.id_token = "[ID]"
        
        # Enable/disable specific filters
        self.filter_ssn = True
        self.filter_phone = True
        self.filter_dates = True
        self.filter_addresses = True
        self.filter_names = True
        self.filter_mrn = True
        self.filter_insurance = True
        
        # Medical terms to preserve (never filter these)
        self.medical_terms_whitelist = {
            'glucose', 'cholesterol', 'blood pressure', 'hemoglobin', 'a1c', 'hba1c',
            'mammogram', 'colonoscopy', 'endoscopy', 'biopsy', 'ultrasound', 'ct scan',
            'mri', 'x-ray', 'ecg', 'ekg', 'blood work', 'lab results', 'pathology',
            'diagnosis', 'symptoms', 'medication', 'prescription', 'dosage', 'mg', 'ml',
            'diabetes', 'hypertension', 'cancer', 'tumor', 'lesion', 'fracture',
            'test', 'screening', 'examination', 'consultation', 'procedure'
        }


class PHIPatternDetector:
    """Detects various PHI patterns in text"""
    
    def __init__(self, config: PHIFilterConfig):
        self.config = config
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        
        # Social Security Numbers (XXX-XX-XXXX, XXXXXXXXX)
        self.ssn_pattern = re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b')
        
        # Phone numbers (various formats)
        self.phone_pattern = re.compile(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
        
        # Dates (MM/DD/YYYY, MM-DD-YYYY, Month DD, YYYY, etc.)
        self.date_patterns = [
            re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),  # MM/DD/YYYY, MM-DD-YYYY
            re.compile(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'),     # YYYY/MM/DD, YYYY-MM-DD
            re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', re.IGNORECASE),
            re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b', re.IGNORECASE),
        ]
        
        # Medical Record Numbers (common patterns)
        self.mrn_patterns = [
            re.compile(r'\bMRN:?\s*(\d{6,})\b', re.IGNORECASE),
            re.compile(r'\bMedical\s+Record\s+Number:?\s*(\d{6,})\b', re.IGNORECASE),
            re.compile(r'\bRecord\s+#:?\s*(\d{6,})\b', re.IGNORECASE),
        ]
        
        # Insurance/Account numbers
        self.insurance_patterns = [
            re.compile(r'\bPolicy\s+#:?\s*([A-Z0-9]{6,})\b', re.IGNORECASE),
            re.compile(r'\bInsurance\s+ID:?\s*([A-Z0-9]{6,})\b', re.IGNORECASE),
            re.compile(r'\bMember\s+ID:?\s*([A-Z0-9]{6,})\b', re.IGNORECASE),
        ]
        
        # Address patterns (basic street addresses)
        self.address_pattern = re.compile(r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Circle|Cir|Court|Ct)\b', re.IGNORECASE)
        
        # Common name patterns (this is more complex and may need NLP)
        self.name_patterns = [
            re.compile(r'\bPatient:?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b'),
            re.compile(r'\bName:?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b'),
        ]
    
    def detect_phi_in_text(self, text: str) -> List[Dict]:
        """Detect all PHI patterns in text and return match details"""
        detections = []
        
        if self.config.filter_ssn:
            for match in self.ssn_pattern.finditer(text):
                detections.append({
                    'type': 'ssn',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'replacement': self.config.id_token
                })
        
        if self.config.filter_phone:
            for match in self.phone_pattern.finditer(text):
                detections.append({
                    'type': 'phone',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'replacement': self.config.phone_token
                })
        
        if self.config.filter_dates:
            for pattern in self.date_patterns:
                for match in pattern.finditer(text):
                    # Skip if this looks like a medical value (e.g., "120/80" for blood pressure)
                    if not self._is_medical_value(match.group()):
                        detections.append({
                            'type': 'date',
                            'text': match.group(),
                            'start': match.start(),
                            'end': match.end(),
                            'replacement': self.config.date_token
                        })
        
        if self.config.filter_mrn:
            for pattern in self.mrn_patterns:
                for match in pattern.finditer(text):
                    detections.append({
                        'type': 'mrn',
                        'text': match.group(),
                        'start': match.start(),
                        'end': match.end(),
                        'replacement': self.config.id_token
                    })
        
        if self.config.filter_insurance:
            for pattern in self.insurance_patterns:
                for match in pattern.finditer(text):
                    detections.append({
                        'type': 'insurance',
                        'text': match.group(),
                        'start': match.start(),
                        'end': match.end(),
                        'replacement': self.config.id_token
                    })
        
        if self.config.filter_addresses:
            for match in self.address_pattern.finditer(text):
                detections.append({
                    'type': 'address',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'replacement': self.config.address_token
                })
        
        if self.config.filter_names:
            for pattern in self.name_patterns:
                for match in pattern.finditer(text):
                    # Check if this might be a medical term instead of a name
                    if not self._is_likely_medical_term(match.group()):
                        detections.append({
                            'type': 'name',
                            'text': match.group(),
                            'start': match.start(),
                            'end': match.end(),
                            'replacement': self.config.name_token
                        })
        
        # Sort by position to enable proper replacement
        return sorted(detections, key=lambda x: x['start'])
    
    def _is_medical_value(self, text: str) -> bool:
        """Check if a date-like pattern is actually a medical value"""
        # Blood pressure pattern (XXX/XX)
        if re.match(r'\d{2,3}/\d{2,3}', text):
            return True
        return False
    
    def _is_likely_medical_term(self, text: str) -> bool:
        """Check if a name-like pattern is actually a medical term"""
        text_lower = text.lower()
        for term in self.config.medical_terms_whitelist:
            if term in text_lower:
                return True
        return False


class PHIFilter:
    """Main PHI filtering class that orchestrates detection and redaction"""
    
    def __init__(self, config: Optional[PHIFilterConfig] = None):
        self.config = config or PHIFilterConfig()
        self.detector = PHIPatternDetector(self.config)
        self.filter_stats = {
            'documents_processed': 0,
            'phi_instances_found': 0,
            'phi_instances_redacted': 0,
            'phi_types_detected': {}
        }
    
    def filter_text(self, text: str, preserve_medical_terms: bool = True) -> Dict:
        """
        Filter PHI from text while preserving medical terminology
        
        Args:
            text: Input text to filter
            preserve_medical_terms: Whether to preserve medical terminology
            
        Returns:
            Dict with filtered text and metadata
        """
        if not text or not isinstance(text, str):
            return {
                'filtered_text': text,
                'original_text': text,
                'phi_detected': [],
                'phi_count': 0,
                'filter_applied': False
            }
        
        # Detect PHI patterns
        phi_detections = self.detector.detect_phi_in_text(text)
        
        if not phi_detections:
            return {
                'filtered_text': text,
                'original_text': text,
                'phi_detected': [],
                'phi_count': 0,
                'filter_applied': False
            }
        
        # Apply redactions (work backwards to maintain positions)
        filtered_text = text
        for detection in reversed(phi_detections):
            filtered_text = (
                filtered_text[:detection['start']] +
                detection['replacement'] +
                filtered_text[detection['end']:]
            )
        
        # Update statistics
        self.filter_stats['documents_processed'] += 1
        self.filter_stats['phi_instances_found'] += len(phi_detections)
        self.filter_stats['phi_instances_redacted'] += len(phi_detections)
        
        for detection in phi_detections:
            phi_type = detection['type']
            self.filter_stats['phi_types_detected'][phi_type] = \
                self.filter_stats['phi_types_detected'].get(phi_type, 0) + 1
        
        logger.info(f"PHI Filter: Redacted {len(phi_detections)} PHI instances from text")
        
        return {
            'filtered_text': filtered_text,
            'original_text': text,
            'phi_detected': phi_detections,
            'phi_count': len(phi_detections),
            'filter_applied': True,
            'medical_terms_preserved': preserve_medical_terms
        }
    
    def get_filter_statistics(self) -> Dict:
        """Get PHI filtering statistics"""
        return {
            'stats': self.filter_stats.copy(),
            'config': {
                'ssn_filtering': self.config.filter_ssn,
                'phone_filtering': self.config.filter_phone,
                'date_filtering': self.config.filter_dates,
                'address_filtering': self.config.filter_addresses,
                'name_filtering': self.config.filter_names,
                'mrn_filtering': self.config.filter_mrn,
                'insurance_filtering': self.config.filter_insurance
            }
        }
    
    def reset_statistics(self):
        """Reset filtering statistics"""
        self.filter_stats = {
            'documents_processed': 0,
            'phi_instances_found': 0,
            'phi_instances_redacted': 0,
            'phi_types_detected': {}
        }


# Global PHI filter instance
phi_filter = PHIFilter()


def filter_phi_from_text(text: str, config: Optional[PHIFilterConfig] = None) -> str:
    """
    Convenience function to filter PHI from text
    
    Args:
        text: Text to filter
        config: Optional custom PHI filter configuration
        
    Returns:
        Filtered text with PHI redacted
    """
    if config:
        temp_filter = PHIFilter(config)
        result = temp_filter.filter_text(text)
    else:
        result = phi_filter.filter_text(text)
    
    return result['filtered_text']


def test_phi_filter():
    """Test function to demonstrate PHI filtering capabilities"""
    test_text = """
    Patient: John Smith
    DOB: 03/15/1985
    SSN: 123-45-6789
    Phone: (555) 123-4567
    Address: 123 Main Street, Anytown
    MRN: 1234567
    Insurance ID: ABC123456789
    
    Test Results:
    Glucose: 120 mg/dL
    Blood Pressure: 120/80
    HbA1c: 6.5%
    Cholesterol: 180 mg/dL
    
    Scheduled for mammogram screening on 04/20/2025.
    """
    
    result = phi_filter.filter_text(test_text)
    
    print("=== PHI FILTER TEST ===")
    print(f"Original text length: {len(test_text)}")
    print(f"Filtered text length: {len(result['filtered_text'])}")
    print(f"PHI instances found: {result['phi_count']}")
    print("\nFiltered text:")
    print(result['filtered_text'])
    print("\nPHI detected:")
    for detection in result['phi_detected']:
        print(f"  {detection['type']}: '{detection['text']}' -> '{detection['replacement']}'")


if __name__ == "__main__":
    test_phi_filter()