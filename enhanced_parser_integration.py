"""
Enhanced Document Parser Integration

This module shows how to modify your existing document parser to return extracted tags
in the requested FHIR format: { 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }
"""

import re
import json
from typing import Dict, List, Any

class EnhancedDocumentParser:
    """
    Enhanced version of your DocumentClassifier that returns FHIR-formatted codes
    """
    
    def __init__(self):
        # LOINC codes for lab tests (from filenames and content)
        self.lab_patterns = {
            r'hemoglobin\s+a1?c|hba1c|glycated\s+hemoglobin': {
                'system': 'http://loinc.org',
                'code': '4548-4',
                'display': 'Hemoglobin A1c/Hemoglobin.total in Blood'
            },
            r'complete\s+blood\s+count|cbc': {
                'system': 'http://loinc.org',
                'code': '58410-2',
                'display': 'Complete blood count (hemogram) panel - Blood by Automated count'
            },
            r'basic\s+metabolic\s+panel|bmp': {
                'system': 'http://loinc.org',
                'code': '51990-0',
                'display': 'Basic metabolic panel - Blood'
            },
            r'comprehensive\s+metabolic\s+panel|cmp': {
                'system': 'http://loinc.org',
                'code': '24323-8',
                'display': 'Comprehensive metabolic panel - Blood'
            },
            r'lipid\s+panel|cholesterol\s+panel': {
                'system': 'http://loinc.org',
                'code': '57698-3',
                'display': 'Lipid panel with direct LDL - Serum or Plasma'
            },
            r'thyroid\s+stimulating\s+hormone|tsh': {
                'system': 'http://loinc.org',
                'code': '3016-3',
                'display': 'Thyrotropin [Units/volume] in Serum or Plasma'
            },
            r'glucose|blood\s+sugar': {
                'system': 'http://loinc.org',
                'code': '2339-0',
                'display': 'Glucose [Mass/volume] in Blood'
            },
            r'creatinine': {
                'system': 'http://loinc.org',
                'code': '2160-0',
                'display': 'Creatinine [Mass/volume] in Serum or Plasma'
            }
        }
        
        # LOINC codes for imaging studies
        self.imaging_patterns = {
            r'chest\s+x-?ray|chest\s+radiograph': {
                'system': 'http://loinc.org',
                'code': '36643-5',
                'display': 'Chest X-ray'
            },
            r'ct\s+scan|computed\s+tomography': {
                'system': 'http://loinc.org',
                'code': '18748-4',
                'display': 'Diagnostic imaging study'
            },
            r'mri|magnetic\s+resonance': {
                'system': 'http://loinc.org',
                'code': '18755-9',
                'display': 'MR study'
            },
            r'ultrasound|sonogram': {
                'system': 'http://loinc.org',
                'code': '18760-9',
                'display': 'Ultrasound study'
            }
        }
        
        # Document type patterns
        self.document_patterns = {
            r'discharge\s+summary': {
                'system': 'http://loinc.org',
                'code': '18842-5',
                'display': 'Discharge summary'
            },
            r'progress\s+note': {
                'system': 'http://loinc.org',
                'code': '11506-3',
                'display': 'Progress note'
            },
            r'consultation\s+note|consult': {
                'system': 'http://loinc.org',
                'code': '11488-4',
                'display': 'Consultation note'
            }
        }
    
    def extract_fhir_codes(self, content: str, filename: str = None) -> List[Dict[str, Any]]:
        """
        Extract all FHIR codes from document content and filename.
        
        Returns:
            List of dictionaries in format:
            [{ 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }]
        """
        extracted_codes = []
        content_lower = content.lower() if content else ""
        
        # Check filename patterns
        if filename:
            filename_lower = filename.lower()
            all_patterns = {**self.lab_patterns, **self.imaging_patterns, **self.document_patterns}
            
            for pattern, coding_info in all_patterns.items():
                if re.search(pattern, filename_lower):
                    extracted_codes.append({
                        'code': {
                            'coding': [coding_info]
                        },
                        'source': 'filename',
                        'matched_text': filename
                    })
        
        # Check content patterns
        all_patterns = {**self.lab_patterns, **self.imaging_patterns, **self.document_patterns}
        for pattern, coding_info in all_patterns.items():
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                extracted_codes.append({
                    'code': {
                        'coding': [coding_info]
                    },
                    'source': 'content',
                    'matched_text': match.group(0)
                })
        
        return extracted_codes
    
    def get_primary_fhir_code(self, content: str, filename: str = None) -> Dict[str, Any]:
        """
        Get the primary FHIR code for a document.
        
        Returns:
            Dictionary in format: { 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }
        """
        extracted = self.extract_fhir_codes(content, filename)
        
        if extracted:
            return extracted[0]['code']
        else:
            # Default LOINC code for general clinical document
            return {
                'code': {
                    'coding': [{
                        'system': 'http://loinc.org',
                        'code': '34133-9',
                        'display': 'Summarization of episode note'
                    }]
                }
            }
    
    def parse_document_with_fhir_tags(self, content: str, filename: str = None) -> Dict[str, Any]:
        """
        Enhanced version of your original classify_document function.
        Returns both classification and FHIR codes.
        """
        result = {
            'success': True,
            'document_type': 'Clinical Document',
            'primary_fhir_code': self.get_primary_fhir_code(content, filename),
            'all_fhir_codes': self.extract_fhir_codes(content, filename),
            'metadata': {}
        }
        
        # Simple document type classification based on primary code
        primary_code = result['primary_fhir_code']['code']['coding'][0]['code']
        
        if primary_code in ['4548-4', '58410-2', '51990-0', '24323-8', '57698-3', '3016-3', '2339-0', '2160-0']:
            result['document_type'] = 'Lab Report'
        elif primary_code in ['36643-5', '18748-4', '18755-9', '18760-9']:
            result['document_type'] = 'Imaging Report'
        elif primary_code in ['18842-5']:
            result['document_type'] = 'Discharge Summary'
        elif primary_code in ['11506-3']:
            result['document_type'] = 'Progress Note'
        elif primary_code in ['11488-4']:
            result['document_type'] = 'Consultation'
        
        return result


# Global parser instance
enhanced_parser = EnhancedDocumentParser()

def extract_tags_from_document(content: str, filename: str = None) -> Dict[str, Any]:
    """
    Main function to extract tags from document in FHIR format.
    
    Args:
        content: Document text content
        filename: Optional filename
        
    Returns:
        Primary FHIR code in format: { 'code': { 'coding': [{ ... }] } }
    """
    return enhanced_parser.get_primary_fhir_code(content, filename)

def get_all_document_codes(content: str, filename: str = None) -> List[Dict[str, Any]]:
    """
    Get all FHIR codes found in document.
    
    Returns:
        List of FHIR codes
    """
    return enhanced_parser.extract_fhir_codes(content, filename)

def enhanced_classify_document(content: str, filename: str = None) -> Dict[str, Any]:
    """
    Enhanced document classification with FHIR codes.
    
    Returns:
        Complete document analysis with FHIR tags
    """
    return enhanced_parser.parse_document_with_fhir_tags(content, filename)


# Example usage and integration with your existing system
def demonstrate_enhanced_parser():
    """Show how the enhanced parser works with real examples"""
    
    examples = [
        {
            'content': 'Laboratory results show elevated Hemoglobin A1C at 7.2%',
            'filename': 'hba1c_lab_results_2024.pdf'
        },
        {
            'content': 'Complete Blood Count shows normal white cell count',
            'filename': 'cbc_report.pdf'
        },
        {
            'content': 'Chest X-ray demonstrates clear lung fields',
            'filename': 'chest_xray_pa_lateral.pdf'
        },
        {
            'content': 'Progress note: Patient doing well post-surgery',
            'filename': 'daily_progress_note.docx'
        }
    ]
    
    print("Enhanced Document Parser - FHIR Code Extraction")
    print("=" * 50)
    
    for i, example in enumerate(examples, 1):
        print(f"\nExample {i}:")
        print(f"Content: {example['content']}")
        print(f"Filename: {example['filename']}")
        
        # Get primary FHIR code
        primary_code = extract_tags_from_document(example['content'], example['filename'])
        print("Primary FHIR Code:")
        print(json.dumps(primary_code, indent=2))
        
        # Get complete analysis
        analysis = enhanced_classify_document(example['content'], example['filename'])
        print(f"Document Type: {analysis['document_type']}")
        print(f"Total FHIR codes found: {len(analysis['all_fhir_codes'])}")
        print()


if __name__ == "__main__":
    demonstrate_enhanced_parser()