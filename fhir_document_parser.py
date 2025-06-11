"""
Enhanced Document Parser with FHIR Code.Coding Format

This module modifies your document parser to return extracted tags in the FHIR format:
{ 'code': { 'coding': [{ 'system': 'http://loinc.org', 'code': '4548-4', 'display': 'Hemoglobin A1C' }] } }
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from models import DocumentType
from fhir_document_metadata import FHIRCodingSystem


class FHIRDocumentParser:
    """Enhanced document parser that extracts tags in FHIR code.coding format"""
    
    def __init__(self):
        # Lab test patterns with LOINC codes
        self.lab_test_patterns = {
            # Common lab tests with their LOINC codes
            r'hemoglobin\s+a1?c|hba1c|glycated\s+hemoglobin': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '4548-4',
                'display': 'Hemoglobin A1c/Hemoglobin.total in Blood'
            },
            r'complete\s+blood\s+count|cbc': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '58410-2',
                'display': 'Complete blood count (hemogram) panel - Blood by Automated count'
            },
            r'basic\s+metabolic\s+panel|bmp': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '51990-0',
                'display': 'Basic metabolic panel - Blood'
            },
            r'comprehensive\s+metabolic\s+panel|cmp': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '24323-8',
                'display': 'Comprehensive metabolic panel - Blood'
            },
            r'lipid\s+panel|cholesterol\s+panel': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '57698-3',
                'display': 'Lipid panel with direct LDL - Serum or Plasma'
            },
            r'thyroid\s+stimulating\s+hormone|tsh': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '3016-3',
                'display': 'Thyrotropin [Units/volume] in Serum or Plasma'
            },
            r'urinalysis|urine\s+analysis': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '24356-8',
                'display': 'Urinalysis complete panel - Urine'
            },
            r'glucose|blood\s+sugar': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '2339-0',
                'display': 'Glucose [Mass/volume] in Blood'
            },
            r'creatinine': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '2160-0',
                'display': 'Creatinine [Mass/volume] in Serum or Plasma'
            },
            r'liver\s+function|hepatic\s+panel': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '24326-1',
                'display': 'Hepatic function panel - Serum or Plasma'
            }
        }
        
        # Imaging study patterns with LOINC codes
        self.imaging_patterns = {
            r'chest\s+x-?ray|chest\s+radiograph': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '36643-5',
                'display': 'Chest X-ray'
            },
            r'ct\s+scan|computed\s+tomography': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '18748-4',
                'display': 'Diagnostic imaging study'
            },
            r'mri|magnetic\s+resonance': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '18755-9',
                'display': 'MR study'
            },
            r'ultrasound|sonogram': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '18760-9',
                'display': 'Ultrasound study'
            },
            r'mammogram|mammography': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '37551-8',
                'display': 'Mammography'
            },
            r'echocardiogram|echo': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '11522-0',
                'display': 'Echocardiography study'
            }
        }
        
        # Clinical document patterns with LOINC codes
        self.document_patterns = {
            r'discharge\s+summary': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '18842-5',
                'display': 'Discharge summary'
            },
            r'progress\s+note|clinical\s+note': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '11506-3',
                'display': 'Progress note'
            },
            r'consultation\s+note|consult': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '11488-4',
                'display': 'Consultation note'
            },
            r'operative\s+report|surgery\s+report': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '11504-8',
                'display': 'Surgical operation note'
            },
            r'pathology\s+report': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '11526-1',
                'display': 'Pathology study'
            },
            r'history\s+and\s+physical|h&p': {
                'system': FHIRCodingSystem.LOINC.value,
                'code': '11492-6',
                'display': 'History and physical note'
            }
        }
        
        # Medical specialty patterns with SNOMED CT codes
        self.specialty_patterns = {
            r'cardiology|cardiac|heart': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '394579002',
                'display': 'Cardiology'
            },
            r'endocrinology|diabetes|thyroid': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '394583002',
                'display': 'Endocrinology'
            },
            r'gastroenterology|gi|gastrointestinal': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '394584008',
                'display': 'Gastroenterology'
            },
            r'neurology|neurological': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '394591006',
                'display': 'Neurology'
            },
            r'oncology|cancer|tumor': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '394593009',
                'display': 'Medical oncology'
            },
            r'orthopedic|orthopedics|bone|joint': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '394594003',
                'display': 'Orthopedics'
            },
            r'dermatology|skin': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '394582007',
                'display': 'Dermatology'
            }
        }
        
        # Body system patterns
        self.body_system_patterns = {
            r'cardiovascular|cardiac|heart|circulatory': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '113257007',
                'display': 'Cardiovascular system'
            },
            r'respiratory|pulmonary|lung|breathing': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '20139000',
                'display': 'Respiratory system'
            },
            r'gastrointestinal|digestive|stomach|intestine': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '86762007',
                'display': 'Digestive system'
            },
            r'neurological|nervous|brain|neurologic': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '25087005',
                'display': 'Nervous system'
            },
            r'musculoskeletal|muscle|bone|joint': {
                'system': FHIRCodingSystem.SNOMED_CT.value,
                'code': '113192009',
                'display': 'Musculoskeletal system'
            }
        }
    
    def parse_document(self, content: str, filename: str = None) -> Dict[str, Any]:
        """
        Parse document and extract tags in FHIR code.coding format.
        
        Args:
            content: Document content text
            filename: Optional filename
            
        Returns:
            Dictionary with extracted FHIR codes and metadata
        """
        result = {
            'success': True,
            'extracted_codes': [],
            'document_classification': None,
            'metadata': {},
            'error': None
        }
        
        try:
            content_lower = content.lower()
            
            # Extract lab test codes
            lab_codes = self._extract_lab_test_codes(content_lower, filename)
            result['extracted_codes'].extend(lab_codes)
            
            # Extract imaging codes
            imaging_codes = self._extract_imaging_codes(content_lower, filename)
            result['extracted_codes'].extend(imaging_codes)
            
            # Extract document type codes
            document_codes = self._extract_document_type_codes(content_lower, filename)
            result['extracted_codes'].extend(document_codes)
            
            # Extract specialty codes
            specialty_codes = self._extract_specialty_codes(content_lower, filename)
            result['extracted_codes'].extend(specialty_codes)
            
            # Extract body system codes
            body_system_codes = self._extract_body_system_codes(content_lower, filename)
            result['extracted_codes'].extend(body_system_codes)
            
            # Classify document for primary code
            primary_code = self._classify_document_primary_code(content_lower, filename)
            if primary_code:
                result['document_classification'] = primary_code
            
            # Extract additional metadata
            result['metadata'] = self._extract_additional_metadata(content, filename)
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _extract_lab_test_codes(self, content_lower: str, filename: str = None) -> List[Dict[str, Any]]:
        """Extract lab test codes from content and filename"""
        codes = []
        
        # Check filename first
        if filename:
            filename_lower = filename.lower()
            for pattern, coding_info in self.lab_test_patterns.items():
                if re.search(pattern, filename_lower):
                    codes.append({
                        'code': {
                            'coding': [coding_info]
                        },
                        'source': 'filename',
                        'matched_text': filename
                    })
        
        # Check content
        for pattern, coding_info in self.lab_test_patterns.items():
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                codes.append({
                    'code': {
                        'coding': [coding_info]
                    },
                    'source': 'content',
                    'matched_text': match.group(0)
                })
        
        return codes
    
    def _extract_imaging_codes(self, content_lower: str, filename: str = None) -> List[Dict[str, Any]]:
        """Extract imaging study codes from content and filename"""
        codes = []
        
        # Check filename first
        if filename:
            filename_lower = filename.lower()
            for pattern, coding_info in self.imaging_patterns.items():
                if re.search(pattern, filename_lower):
                    codes.append({
                        'code': {
                            'coding': [coding_info]
                        },
                        'source': 'filename',
                        'matched_text': filename
                    })
        
        # Check content
        for pattern, coding_info in self.imaging_patterns.items():
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                codes.append({
                    'code': {
                        'coding': [coding_info]
                    },
                    'source': 'content',
                    'matched_text': match.group(0)
                })
        
        return codes
    
    def _extract_document_type_codes(self, content_lower: str, filename: str = None) -> List[Dict[str, Any]]:
        """Extract document type codes from content and filename"""
        codes = []
        
        # Check filename first
        if filename:
            filename_lower = filename.lower()
            for pattern, coding_info in self.document_patterns.items():
                if re.search(pattern, filename_lower):
                    codes.append({
                        'code': {
                            'coding': [coding_info]
                        },
                        'source': 'filename',
                        'matched_text': filename
                    })
        
        # Check content
        for pattern, coding_info in self.document_patterns.items():
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                codes.append({
                    'code': {
                        'coding': [coding_info]
                    },
                    'source': 'content',
                    'matched_text': match.group(0)
                })
        
        return codes
    
    def _extract_specialty_codes(self, content_lower: str, filename: str = None) -> List[Dict[str, Any]]:
        """Extract medical specialty codes from content and filename"""
        codes = []
        
        # Check filename first
        if filename:
            filename_lower = filename.lower()
            for pattern, coding_info in self.specialty_patterns.items():
                if re.search(pattern, filename_lower):
                    codes.append({
                        'code': {
                            'coding': [coding_info]
                        },
                        'source': 'filename',
                        'matched_text': filename
                    })
        
        # Check content
        for pattern, coding_info in self.specialty_patterns.items():
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                codes.append({
                    'code': {
                        'coding': [coding_info]
                    },
                    'source': 'content',
                    'matched_text': match.group(0)
                })
        
        return codes
    
    def _extract_body_system_codes(self, content_lower: str, filename: str = None) -> List[Dict[str, Any]]:
        """Extract body system codes from content and filename"""
        codes = []
        
        # Check content for body system references
        for pattern, coding_info in self.body_system_patterns.items():
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                codes.append({
                    'code': {
                        'coding': [coding_info]
                    },
                    'source': 'content',
                    'matched_text': match.group(0)
                })
        
        return codes
    
    def _classify_document_primary_code(self, content_lower: str, filename: str = None) -> Optional[Dict[str, Any]]:
        """Determine the primary document classification code"""
        
        # Priority order for document classification
        classification_priority = [
            (self.lab_test_patterns, 'Laboratory report'),
            (self.imaging_patterns, 'Imaging study'),
            (self.document_patterns, 'Clinical document')
        ]
        
        # Check filename first for highest priority match
        if filename:
            filename_lower = filename.lower()
            for pattern_dict, category in classification_priority:
                for pattern, coding_info in pattern_dict.items():
                    if re.search(pattern, filename_lower):
                        return {
                            'code': {
                                'coding': [coding_info]
                            },
                            'category': category,
                            'confidence': 'high',
                            'source': 'filename'
                        }
        
        # Check content for classification
        for pattern_dict, category in classification_priority:
            for pattern, coding_info in pattern_dict.items():
                if re.search(pattern, content_lower):
                    return {
                        'code': {
                            'coding': [coding_info]
                        },
                        'category': category,
                        'confidence': 'medium',
                        'source': 'content'
                    }
        
        # Default classification
        return {
            'code': {
                'coding': [{
                    'system': FHIRCodingSystem.LOINC.value,
                    'code': '34133-9',
                    'display': 'Summarization of episode note'
                }]
            },
            'category': 'Clinical document',
            'confidence': 'low',
            'source': 'default'
        }
    
    def _extract_additional_metadata(self, content: str, filename: str = None) -> Dict[str, Any]:
        """Extract additional metadata from document"""
        metadata = {}
        content_lower = content.lower()
        
        # Extract dates
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}'
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dates_found.extend(matches)
        
        if dates_found:
            metadata['extracted_dates'] = dates_found[:5]  # Limit to first 5 dates
        
        # Extract provider names (simple pattern)
        provider_pattern = r'dr\.?\s+([a-z]+(?:\s+[a-z]+)*)|physician:\s*([a-z]+(?:\s+[a-z]+)*)'
        provider_matches = re.findall(provider_pattern, content_lower)
        if provider_matches:
            providers = [match[0] or match[1] for match in provider_matches if match[0] or match[1]]
            metadata['extracted_providers'] = providers[:3]  # Limit to first 3
        
        # Extract patient identifiers
        mrn_pattern = r'mrn[:\s]+([a-z0-9-]+)'
        mrn_matches = re.findall(mrn_pattern, content_lower)
        if mrn_matches:
            metadata['extracted_mrn'] = mrn_matches[0]
        
        # Extract vital signs values
        vitals_patterns = {
            'blood_pressure': r'bp[:\s]*(\d{2,3}[/\\]\d{2,3})',
            'heart_rate': r'hr[:\s]*(\d{2,3})\s*bpm',
            'temperature': r'temp[:\s]*(\d{2,3}\.?\d?)[°f]?',
            'weight': r'weight[:\s]*(\d{2,3}\.?\d?)\s*(?:lbs?|kg)',
            'height': r'height[:\s]*(\d[\'\"]?\s*\d{1,2}[\"\']?|\d{2,3}\s*cm)'
        }
        
        for vital_name, pattern in vitals_patterns.items():
            matches = re.findall(pattern, content_lower)
            if matches:
                metadata[f'extracted_{vital_name}'] = matches[0]
        
        # Count words and sentences for document complexity
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?]+', content))
        
        metadata['document_stats'] = {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'estimated_complexity': 'high' if word_count > 1000 else 'medium' if word_count > 300 else 'low'
        }
        
        return metadata
    
    def get_primary_code_only(self, content: str, filename: str = None) -> Dict[str, Any]:
        """
        Extract only the primary document code in FHIR format.
        
        Returns:
            Dictionary with single code in format:
            { 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }
        """
        try:
            classification = self._classify_document_primary_code(content.lower(), filename)
            if classification:
                return classification['code']
            else:
                # Return default code
                return {
                    'code': {
                        'coding': [{
                            'system': FHIRCodingSystem.LOINC.value,
                            'code': '34133-9',
                            'display': 'Summarization of episode note'
                        }]
                    }
                }
        except Exception:
            # Return default code on error
            return {
                'code': {
                    'coding': [{
                        'system': FHIRCodingSystem.LOINC.value,
                        'code': '34133-9',
                        'display': 'Summarization of episode note'
                    }]
                }
            }


# Global parser instance
_fhir_parser = FHIRDocumentParser()


def parse_document_with_fhir_codes(content: str, filename: str = None) -> Dict[str, Any]:
    """
    Parse document and return extracted tags in FHIR code.coding format.
    
    Args:
        content: Document content
        filename: Optional filename
        
    Returns:
        Dictionary with FHIR-formatted codes and metadata
    """
    return _fhir_parser.parse_document(content, filename)


def get_primary_document_code(content: str, filename: str = None) -> Dict[str, Any]:
    """
    Get primary document code in FHIR format.
    
    Returns:
        { 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }
    """
    return _fhir_parser.get_primary_code_only(content, filename)


def extract_lab_test_codes_from_text(content: str) -> List[Dict[str, Any]]:
    """Extract only lab test codes from document content"""
    parser = FHIRDocumentParser()
    return parser._extract_lab_test_codes(content.lower())


def extract_imaging_codes_from_text(content: str) -> List[Dict[str, Any]]:
    """Extract only imaging codes from document content"""
    parser = FHIRDocumentParser()
    return parser._extract_imaging_codes(content.lower())


# Backward compatibility function that replaces the original classify_document
def classify_document_with_fhir_codes(content: str, filename: str = None) -> Tuple[DocumentType, Dict[str, Any]]:
    """
    Enhanced version of classify_document that returns FHIR codes in metadata.
    
    Returns:
        Tuple of (DocumentType, metadata_with_fhir_codes)
    """
    try:
        # Parse with FHIR codes
        fhir_result = parse_document_with_fhir_codes(content, filename)
        
        # Determine DocumentType from primary classification
        doc_type = DocumentType.UNKNOWN
        if fhir_result.get('document_classification'):
            primary_code = fhir_result['document_classification']['code']['coding'][0]
            
            # Map LOINC codes back to DocumentType
            code_to_type = {
                '11502-2': DocumentType.LAB_REPORT,
                '18748-4': DocumentType.RADIOLOGY_REPORT,
                '18842-5': DocumentType.DISCHARGE_SUMMARY,
                '11506-3': DocumentType.CLINICAL_NOTE,
                '11488-4': DocumentType.CONSULTATION,
                '11504-8': DocumentType.OPERATIVE_REPORT,
                '11526-1': DocumentType.PATHOLOGY_REPORT,
                '11492-6': DocumentType.CLINICAL_NOTE,
                # Lab test codes map to LAB_REPORT
                '4548-4': DocumentType.LAB_REPORT,
                '58410-2': DocumentType.LAB_REPORT,
                '51990-0': DocumentType.LAB_REPORT,
                '24323-8': DocumentType.LAB_REPORT,
                '57698-3': DocumentType.LAB_REPORT,
                '3016-3': DocumentType.LAB_REPORT,
                '24356-8': DocumentType.LAB_REPORT
            }
            
            doc_type = code_to_type.get(primary_code['code'], DocumentType.UNKNOWN)
        
        # Build metadata with FHIR codes
        metadata = fhir_result.get('metadata', {})
        metadata['fhir_codes'] = fhir_result.get('extracted_codes', [])
        if fhir_result.get('document_classification'):
            metadata['primary_fhir_code'] = fhir_result['document_classification']['code']
        
        return doc_type, metadata
        
    except Exception:
        # Fallback to basic classification
        return DocumentType.UNKNOWN, {}