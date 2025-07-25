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

        # Global PHI filtering control
        self.phi_filtering_enabled = True

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
        self._patient_names_cache = None
        self._cache_timestamp = None

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""

        # Social Security Numbers (flexible patterns for OCR-extracted text)
        # CRITICAL FIX: Using explicit character classes due to \d regex engine issue
        self.ssn_patterns = [
            # Labeled SSN patterns
            re.compile(r'(?:SSN|Social Security|Social Sec|SS)\s*[:#]?\s*([0-9]{1,3}(?:[-\s]?[0-9]{1,2})?(?:[-\s]?[0-9]{1,4})?)', re.IGNORECASE),
            # CRITICAL: Explicit character class SSN pattern that WORKS
            re.compile(r'[0-9]{3}-[0-9]{2}-[0-9]{4}'),
            # Alternative explicit SSN pattern 
            re.compile(r'[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]'),
            # Colon-separated contexts (common in documents) 
            re.compile(r':\s*([0-9]{3}-[0-9]{2}-[0-9]{4})'),
            # Standard SSN patterns with explicit boundaries
            re.compile(r'(?<![a-zA-Z0-9])([0-9]{3}[-\s][0-9]{2}[-\s][0-9]{4})(?![a-zA-Z0-9])'),
            # Partial SSN patterns in context (like "Last 4: 1234")
            re.compile(r'(?:last\s+4|last\s+four)\s*[:#]?\s*([0-9]{4})', re.IGNORECASE),
            # Be very selective with partial numeric sequences to avoid medical values
            re.compile(r'(?:SSN|Social)\s*.*?([0-9]{4})', re.IGNORECASE)
        ]

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

        # Name patterns (be very selective to avoid medical terms)
        self.name_patterns = [
            # Explicit labeled names
            re.compile(r'\b(?:Patient|Patient Name|Full Name)\s*[:#]?\s*([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s*\n|$)', re.IGNORECASE),
            re.compile(r'\bName\s*[:#]?\s*([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s*\n|$)', re.IGNORECASE),
            re.compile(r'^Name\s*[:#]?\s*([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s*\n|$)', re.IGNORECASE | re.MULTILINE),
            # Enhanced contextual name patterns
            re.compile(r'^([A-Z][a-z]+\s+[A-Z][a-z]+)(?=\s*\n|\s*$)', re.MULTILINE),  # First line capitalized names only
            re.compile(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s*(?=\d{2,3}[-/]\d{2}[-/]\d{2,4})', re.IGNORECASE),  # Names directly before dates
            re.compile(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s*(?=\d{3}[-\s]?\d{2}[-\s]?\d{4})', re.IGNORECASE),  # Names directly before SSNs
            # Additional name patterns for common document formats
            re.compile(r'(?:^|\n)\s*([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\s*(?:\n|$)', re.MULTILINE),  # Full names on their own line
            re.compile(r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\s*(?:DOB|Date of Birth|Born|SSN|Social|Phone|Address)', re.IGNORECASE),  # Names before common PHI fields
            re.compile(r'(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', re.IGNORECASE),  # Names with titles
        ]

        # Date of birth patterns (contextual detection)
        self.dob_patterns = [
            re.compile(r'(?:DOB|Date of Birth|Born)\s*[:#]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
            re.compile(r'(?:DOB|Date of Birth|Born)\s*[:#]?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', re.IGNORECASE),
            # Contextual DOB (dates appearing after potential names - using word boundaries)
            re.compile(r'(?:[A-Z][a-z]+\s+[A-Z][a-z]+)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'),
        ]

    def _get_rostered_patient_names(self) -> Set[str]:
        """Get all patient names from the database for PHI detection"""
        from datetime import datetime, timedelta
        import time
        
        # Cache patient names for 5 minutes to avoid excessive database queries
        current_time = time.time()
        if (self._patient_names_cache is not None and 
            self._cache_timestamp and 
            (current_time - self._cache_timestamp) < 300):  # 5 minutes
            return self._patient_names_cache
        
        try:
            # Import here to avoid circular imports
            import sys
            if 'models' in sys.modules:
                Patient = sys.modules['models'].Patient
                app = sys.modules['app'].app
                db = sys.modules['app'].db
            else:
                from models import Patient
                from app import app, db
            
            patient_names = set()
            
            with app.app_context():
                patients = Patient.query.all()
                for patient in patients:
                    if patient.first_name:
                        patient_names.add(patient.first_name.strip())
                    if patient.last_name:
                        patient_names.add(patient.last_name.strip())
                    if patient.full_name:
                        patient_names.add(patient.full_name.strip())
                    
                    # Add common combinations
                    if patient.first_name and patient.last_name:
                        patient_names.add(f"{patient.first_name.strip()} {patient.last_name.strip()}")
            
            # Cache the results
            self._patient_names_cache = patient_names
            self._cache_timestamp = current_time
            
            logger.debug(f"Cached {len(patient_names)} patient names for PHI detection")
            return patient_names
            
        except Exception as e:
            logger.warning(f"Could not load patient names for PHI detection: {e}")
            # Return empty set if database access fails
            return set()

    def _detect_rostered_patient_names(self, text: str) -> List[Dict]:
        """Detect names of rostered patients in text"""
        detections = []
        patient_names = self._get_rostered_patient_names()
        
        if not patient_names:
            return detections
        
        # Sort by length (longest first) to avoid partial matches
        sorted_names = sorted(patient_names, key=len, reverse=True)
        
        for name in sorted_names:
            if len(name.strip()) < 3:  # Skip very short names
                continue
                
            # Create a regex pattern for this name (case-insensitive, word boundaries)
            escaped_name = re.escape(name)
            pattern = re.compile(r'\b' + escaped_name + r'\b', re.IGNORECASE)
            
            for match in pattern.finditer(text):
                # Additional context check to ensure this is actually a name reference
                context_start = max(0, match.start() - 20)
                context_end = min(len(text), match.end() + 20)
                context = text[context_start:context_end].lower()
                
                # Skip if this appears to be part of a medical term
                if any(med_term in context for med_term in ['panel', 'test', 'screening', 'examination']):
                    continue
                
                detections.append({
                    'type': 'rostered_patient_name',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'replacement': self.config.name_token,
                    'patient_name': name
                })
        
        return detections

    def detect_phi_in_text(self, text: str) -> List[Dict]:
        """Detect all PHI patterns in text and return match details"""
        detections = []

        if self.config.filter_ssn:
            # CRITICAL WORKAROUND: Direct string search for SSN patterns due to regex engine issue
            ssn_detections = self._detect_ssn_direct(text)
            detections.extend(ssn_detections)
            
            # Also try regex patterns as backup
            for i, pattern in enumerate(self.ssn_patterns):
                for match in pattern.finditer(text):
                    # Skip if this looks like a medical value (blood pressure, etc.)
                    matched_text = match.group(1) if match.groups() else match.group()
                    
                    # DEBUG: Log pattern matches
                    logger.debug(f"SSN Pattern {i+1} matched: '{match.group()}' -> '{matched_text}'")
                    
                    if not self._is_medical_value(matched_text):
                        # For labeled SSNs, preserve label structure
                        if 'SSN' in match.group().upper() or 'SOCIAL' in match.group().upper():
                            replacement = f"SSN: {self.config.id_token}"
                        else:
                            replacement = self.config.id_token

                        detections.append({
                            'type': 'ssn',
                            'matched_text': matched_text,
                            'text': match.group(),
                            'start': match.start(),
                            'end': match.end(),
                            'replacement': replacement
                        })
                    else:
                        logger.debug(f"SSN candidate '{matched_text}' skipped as medical value")

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
                    full_match = match.group()

                    # Check if this might be a medical term instead of a name
                    if not self._is_likely_medical_term(full_match):
                        matched_text = match.group(1) if match.groups() else match.group()

                        # Additional check: ensure we're not partially matching medical terms
                        context_start = max(0, match.start() - 10)
                        context_end = min(len(text), match.end() + 10)
                        context = text[context_start:context_end].lower()

                        # Skip if the match appears to be part of a medical term
                        if any(med_term in context for med_term in ['lipid panel', 'blood panel', 'test panel', 'lab panel']):
                            continue

                        # For labeled names, preserve label structure
                        if 'name' in full_match.lower():
                            replacement = f"Name: {self.config.name_token}"
                        else:
                            replacement = self.config.name_token

                        detections.append({
                            'type': 'name',
                            'matched_text': matched_text,
                            'text': full_match,
                            'start': match.start(),
                            'end': match.end(),
                            'replacement': replacement
                        })

        # Add DOB detection
        if self.config.filter_dates:
            for pattern in self.dob_patterns:
                for match in pattern.finditer(text):
                    if not self._is_medical_value(match.group()):
                        matched_text = match.group(1) if match.groups() else match.group()

                        # For labeled DOBs, preserve label structure
                        if any(label in match.group().lower() for label in ['dob', 'date of birth', 'born']):
                            replacement = f"DOB: {self.config.date_token}"
                        else:
                            replacement = self.config.date_token

                        detections.append({
                            'type': 'dob',
                            'matched_text': matched_text,
                            'text': match.group(),
                            'start': match.start(),
                            'end': match.end(),
                            'replacement': replacement
                        })

        # Add rostered patient name detection
        if self.config.filter_names:
            rostered_name_detections = self._detect_rostered_patient_names(text)
            detections.extend(rostered_name_detections)

        # Sort by position to enable proper replacement
        return sorted(detections, key=lambda x: x['start'])

    def _is_medical_value(self, text: str) -> bool:
        """Check if text appears to be a medical measurement rather than PHI"""
        text_str = str(text).strip().lower()

        # Medical measurement patterns that should NOT be filtered as PHI
        medical_patterns = [
            r'\d+/\d+$',  # Blood pressure (120/80)
            r'\d+\.\d+%?$',  # Decimal values and percentages (6.5%, 98.6)
            r'\d+\s*mg(/dl)?$',  # Medical units (mg, mg/dl)
            r'\d+\s*mmhg$',  # Blood pressure units
        ]

        for pattern in medical_patterns:
            if re.match(pattern, text_str):
                return True

        # CRITICAL: Do NOT classify SSN patterns as medical values
        # SSN patterns like "100-20-100" should NEVER be considered medical
        if re.match(r'\d{3}-\d{2}-\d{4}', text_str):
            return False  # This is definitely a potential SSN, not medical

        # Avoid filtering common medical numeric ranges (but be more selective)
        if len(text_str) <= 3 and text_str.isdigit():
            # Simple 1-3 digit numbers are likely medical values, not SSN fragments
            return True

        return False
    
    def _detect_ssn_direct(self, text: str) -> List[Dict]:
        """Direct string-based SSN detection as workaround for regex engine issues"""
        detections = []
        
        # Look for XXX-XX-XXXX patterns where X is a digit
        import re
        
        # Use a more robust approach - find all digit sequences separated by hyphens
        potential_ssns = []
        
        # Split text into words and check each for SSN pattern  
        words = text.split()
        for word in words:
            # Check for both 10 and 11 character SSN patterns
            for length in [10, 11]:
                if len(word) >= length:
                    for i in range(len(word) - length + 1):
                        candidate = word[i:i+length]
                        if self._is_ssn_pattern(candidate):
                            potential_ssns.append((candidate, text.find(candidate)))
        
        # Also check for patterns that might span multiple "words" due to OCR
        lines = text.split('\n')
        for line in lines:
            if ':' in line:  # Common in "Name: [NAME]: 100-20-100" patterns
                parts = line.split(':')
                for part in parts:
                    part = part.strip()
                    if self._is_ssn_pattern(part):
                        potential_ssns.append((part, text.find(part)))
        
        # Process found SSNs - remove duplicates first
        unique_ssns = list(set(potential_ssns))
        for ssn_text, start_pos in unique_ssns:
            if start_pos >= 0 and not self._is_medical_value(ssn_text):
                logger.debug(f"SSN detected: '{ssn_text}' at position {start_pos}")
                detections.append({
                    'type': 'ssn',
                    'matched_text': ssn_text,
                    'text': ssn_text,
                    'start': start_pos,
                    'end': start_pos + len(ssn_text),
                    'replacement': self.config.id_token
                })
        
        return detections
    
    def _is_ssn_pattern(self, text: str) -> bool:
        """Check if text matches SSN-like pattern XXX-XX-XXX or XXX-XX-XXXX"""
        # Support both 10 and 11 character formats for comprehensive PHI detection
        if len(text) not in [10, 11]:
            return False
        
        # Check character by character based on length
        if len(text) == 10:  # Format: XXX-XX-XXX (like "100-20-100")
            hyphen_positions = [3, 6]
        else:  # Format: XXX-XX-XXXX (standard SSN)
            hyphen_positions = [3, 6]
        
        for i, char in enumerate(text):
            if i in hyphen_positions:  # Positions should be hyphens
                if char != '-':
                    return False
            else:  # All other positions should be digits
                if not char.isdigit():
                    return False
        
        # PHI detection should be comprehensive - accept various ID formats
        return True

    def _is_likely_medical_term(self, text: str) -> bool:
        """Check if a name-like pattern is actually a medical term"""
        text_lower = text.lower()

        # Check configured whitelist
        for term in self.config.medical_terms_whitelist:
            if term in text_lower:
                return True

        # Additional medical terms that might be mistaken for names
        medical_terms = [
            'lipid panel', 'blood panel', 'lab panel', 'test panel',
            'lipid p', 'blood p', 'lab p',  # Protect partial matches
            'glucose', 'cholesterol', 'triglyceride', 
            'mammogram', 'mammography', 'colonoscopy',
            'panel', 'test', 'lab', 'results'
        ]

        for term in medical_terms:
            if term in text_lower:
                return True

        # Check if text starts with medical terminology
        medical_prefixes = ['lipid', 'blood', 'glucose', 'cholesterol', 'test', 'lab', 'panel']
        for prefix in medical_prefixes:
            if text_lower.startswith(prefix):
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

        # Check if PHI filtering is globally disabled
        if not self.config.phi_filtering_enabled:
            return {
                'filtered_text': text,
                'original_text': text,
                'phi_detected': [],
                'phi_count': 0,
                'filter_applied': False,
                'filter_disabled': True
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

        # Remove overlapping detections (keep the most specific one)
        non_overlapping_detections = []
        sorted_detections = sorted(phi_detections, key=lambda x: (x['start'], -x['end']))

        for detection in sorted_detections:
            # Check if this detection overlaps with any existing ones
            is_overlapping = False
            for existing in non_overlapping_detections:
                if (detection['start'] < existing['end'] and detection['end'] > existing['start']):
                    is_overlapping = True
                    break

            if not is_overlapping:
                non_overlapping_detections.append(detection)

        # Apply redactions (work backwards to maintain positions)
        filtered_text = text
        for detection in reversed(sorted(non_overlapping_detections, key=lambda x: x['start'])):
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
                'phi_filtering_enabled': self.config.phi_filtering_enabled,
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