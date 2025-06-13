"""
Medical Document Parser
Extracts dates, filenames, keywords, and infers document types from medical documents
Returns structured metadata with confidence scoring
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass, asdict
from collections import Counter


@dataclass
class DocumentMetadata:
    """Structured document metadata with confidence scoring"""
    filename: str
    extracted_dates: List[str]
    primary_date: Optional[str]
    keywords: List[str]
    document_type: str
    document_category: str
    confidence_score: float
    extracted_providers: List[str]
    extracted_facilities: List[str]
    content_indicators: Dict[str, Any]
    parsing_metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class MedicalDocumentParser:
    """
    Comprehensive medical document parser with intelligent type inference
    """
    
    def __init__(self):
        # Document type patterns with confidence weights
        self.document_patterns = {
            'lab': {
                'keywords': [
                    'laboratory', 'lab results', 'blood test', 'urine test', 'biopsy',
                    'pathology', 'chemistry panel', 'complete blood count', 'cbc',
                    'glucose', 'cholesterol', 'hemoglobin', 'hematocrit', 'platelet',
                    'white blood cell', 'red blood cell', 'creatinine', 'bun',
                    'liver function', 'thyroid function', 'lipid panel',
                    'hemoglobin a1c', 'hba1c', 'psa', 'cea', 'troponin',
                    'electrolytes', 'sodium', 'potassium', 'chloride', 'co2',
                    'microalbumin', 'urinalysis', 'culture', 'sensitivity',
                    'gram stain', 'blood culture', 'urine culture'
                ],
                'filename_patterns': [
                    r'lab.*result', r'blood.*test', r'urine.*test', r'pathology',
                    r'biopsy', r'chemistry', r'cbc', r'lipid', r'glucose',
                    r'hba1c', r'a1c', r'psa', r'culture'
                ],
                'weight': 1.0
            },
            'imaging': {
                'keywords': [
                    'radiology', 'x-ray', 'xray', 'ct scan', 'computed tomography',
                    'mri', 'magnetic resonance', 'ultrasound', 'mammogram',
                    'pet scan', 'nuclear medicine', 'bone scan', 'dexa',
                    'echocardiogram', 'echo', 'ekg', 'electrocardiogram', 'ecg',
                    'stress test', 'cardiac catheterization', 'angiogram',
                    'fluoroscopy', 'barium', 'contrast', 'doppler'
                ],
                'filename_patterns': [
                    r'x.*ray', r'xray', r'ct.*scan', r'mri', r'ultrasound',
                    r'mammogram', r'pet.*scan', r'echo', r'ekg', r'ecg',
                    r'radiology', r'imaging'
                ],
                'weight': 1.0
            },
            'consult': {
                'keywords': [
                    'consultation', 'consult', 'specialist', 'referral',
                    'cardiology', 'neurology', 'orthopedic', 'dermatology',
                    'psychiatry', 'psychology', 'oncology', 'endocrinology',
                    'gastroenterology', 'pulmonology', 'nephrology',
                    'rheumatology', 'hematology', 'infectious disease',
                    'recommendation', 'opinion', 'assessment', 'evaluation'
                ],
                'filename_patterns': [
                    r'consult', r'consultation', r'specialist', r'referral',
                    r'cardiology', r'neurology', r'orthopedic', r'dermatology'
                ],
                'weight': 0.9
            },
            'hospital_summary': {
                'keywords': [
                    'discharge summary', 'admission', 'hospital stay',
                    'inpatient', 'emergency department', 'ed visit',
                    'hospitalization', 'discharge instructions',
                    'admission history', 'hospital course', 'disposition',
                    'length of stay', 'attending physician', 'resident'
                ],
                'filename_patterns': [
                    r'discharge', r'admission', r'hospital', r'inpatient',
                    r'emergency', r'ed.*visit'
                ],
                'weight': 0.9
            },
            'medication': {
                'keywords': [
                    'prescription', 'medication list', 'pharmacy',
                    'drug', 'dosage', 'frequency', 'refill',
                    'medication reconciliation', 'med list',
                    'rx', 'tablet', 'capsule', 'injection', 'oral',
                    'topical', 'inhaler', 'nebulizer'
                ],
                'filename_patterns': [
                    r'medication', r'prescription', r'pharmacy', r'med.*list',
                    r'drug.*list'
                ],
                'weight': 0.8
            },
            'procedure': {
                'keywords': [
                    'procedure note', 'operative report', 'surgery',
                    'procedure', 'operation', 'surgical', 'biopsy',
                    'endoscopy', 'colonoscopy', 'bronchoscopy',
                    'arthroscopy', 'laparoscopy', 'cystoscopy',
                    'pre-operative', 'post-operative', 'anesthesia'
                ],
                'filename_patterns': [
                    r'procedure', r'operative', r'surgery', r'surgical',
                    r'endoscopy', r'colonoscopy', r'biopsy'
                ],
                'weight': 0.9
            },
            'progress_note': {
                'keywords': [
                    'progress note', 'clinic note', 'office visit',
                    'follow up', 'followup', 'visit note',
                    'subjective', 'objective', 'assessment', 'plan',
                    'soap note', 'chief complaint', 'history of present illness',
                    'review of systems', 'physical exam'
                ],
                'filename_patterns': [
                    r'progress', r'clinic.*note', r'office.*visit',
                    r'follow.*up', r'visit.*note', r'soap'
                ],
                'weight': 0.7
            },
            'vital_signs': {
                'keywords': [
                    'vital signs', 'blood pressure', 'heart rate', 'pulse',
                    'temperature', 'respiratory rate', 'oxygen saturation',
                    'height', 'weight', 'bmi', 'body mass index'
                ],
                'filename_patterns': [
                    r'vital.*signs', r'blood.*pressure', r'vitals'
                ],
                'weight': 0.8
            }
        }
        
        # Date patterns with different formats
        self.date_patterns = [
            # MM/DD/YYYY, MM-DD-YYYY, MM.DD.YYYY
            r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b',
            # YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
            r'\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b',
            # Month DD, YYYY
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
            # Mon DD, YYYY (abbreviated)
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})\b',
            # DD Month YYYY
            r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
            # YYYY only
            r'\b(20\d{2})\b'
        ]
        
        # Provider name patterns
        self.provider_patterns = [
            r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Doctor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+M\.?D\.?',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+D\.?O\.?',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+N\.?P\.?',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+P\.?A\.?'
        ]
        
        # Facility name patterns
        self.facility_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Hospital',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Medical\s+Center',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Clinic',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Laboratory',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Radiology'
        ]
    
    def parse_document(self, filename: str, content: str = None) -> DocumentMetadata:
        """
        Parse a medical document and extract structured metadata
        
        Args:
            filename: Document filename
            content: Document text content (optional)
            
        Returns:
            DocumentMetadata with extracted information
        """
        # Initialize parsing data
        parsing_start = datetime.now()
        extracted_dates = []
        keywords = []
        providers = []
        facilities = []
        content_indicators = {}
        
        # Combine filename and content for analysis
        full_text = filename.lower()
        if content:
            full_text += " " + content.lower()
        
        # Extract dates
        extracted_dates = self._extract_dates(full_text)
        primary_date = self._determine_primary_date(extracted_dates)
        
        # Extract keywords
        keywords = self._extract_keywords(full_text)
        
        # Extract providers and facilities
        if content:
            providers = self._extract_providers(content)
            facilities = self._extract_facilities(content)
        
        # Infer document type and category
        document_type, confidence_score = self._infer_document_type(filename, content)
        document_category = self._determine_category(document_type)
        
        # Analyze content indicators
        content_indicators = self._analyze_content_indicators(full_text)
        
        # Create parsing metadata
        parsing_metadata = {
            "parsing_time": (datetime.now() - parsing_start).total_seconds(),
            "content_length": len(content) if content else 0,
            "filename_length": len(filename),
            "total_keywords_found": len(keywords),
            "date_extraction_method": "regex_pattern_matching",
            "type_inference_method": "keyword_and_pattern_matching"
        }
        
        return DocumentMetadata(
            filename=filename,
            extracted_dates=extracted_dates,
            primary_date=primary_date,
            keywords=keywords,
            document_type=document_type,
            document_category=document_category,
            confidence_score=confidence_score,
            extracted_providers=providers,
            extracted_facilities=facilities,
            content_indicators=content_indicators,
            parsing_metadata=parsing_metadata
        )
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text using multiple patterns"""
        dates = []
        
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(0)
                # Normalize date format
                normalized_date = self._normalize_date(date_str)
                if normalized_date and normalized_date not in dates:
                    dates.append(normalized_date)
        
        return sorted(dates, reverse=True)  # Most recent first
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date to YYYY-MM-DD format"""
        try:
            # Handle various date formats
            date_str = date_str.strip()
            
            # Try different parsing approaches
            formats = [
                '%m/%d/%Y', '%m-%d-%Y', '%m.%d.%Y',
                '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
                '%B %d, %Y', '%b %d, %Y',
                '%d %B %Y', '%Y'
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            return None
        except:
            return None
    
    def _determine_primary_date(self, dates: List[str]) -> Optional[str]:
        """Determine the most likely primary date"""
        if not dates:
            return None
        
        # Return the most recent date (first in sorted list)
        return dates[0]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant medical keywords from text"""
        keywords = []
        
        # Collect keywords from all document types
        for doc_type, patterns in self.document_patterns.items():
            for keyword in patterns['keywords']:
                if keyword.lower() in text:
                    keywords.append(keyword)
        
        # Remove duplicates and sort by frequency in text
        keyword_counts = Counter(keywords)
        return [kw for kw, count in keyword_counts.most_common()]
    
    def _extract_providers(self, text: str) -> List[str]:
        """Extract provider names from document content"""
        providers = []
        
        for pattern in self.provider_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                provider_name = match.group(1).strip()
                if provider_name and provider_name not in providers:
                    providers.append(provider_name)
        
        return providers
    
    def _extract_facilities(self, text: str) -> List[str]:
        """Extract facility names from document content"""
        facilities = []
        
        for pattern in self.facility_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                facility_name = match.group(0).strip()
                if facility_name and facility_name not in facilities:
                    facilities.append(facility_name)
        
        return facilities
    
    def _infer_document_type(self, filename: str, content: str = None) -> Tuple[str, float]:
        """Infer document type with confidence scoring"""
        type_scores = {}
        
        # Analyze filename
        filename_lower = filename.lower()
        
        # Analyze content if available
        content_lower = content.lower() if content else ""
        
        # Score each document type
        for doc_type, patterns in self.document_patterns.items():
            score = 0.0
            matches = 0
            
            # Check filename patterns
            for pattern in patterns['filename_patterns']:
                if re.search(pattern, filename_lower):
                    score += 0.5
                    matches += 1
            
            # Check keywords in filename and content
            keyword_matches = 0
            for keyword in patterns['keywords']:
                if keyword in filename_lower:
                    score += 0.3
                    keyword_matches += 1
                elif content and keyword in content_lower:
                    score += 0.1
                    keyword_matches += 1
            
            # Apply weight and normalize
            final_score = (score * patterns['weight']) / max(1, len(patterns['keywords']) * 0.1)
            
            if matches > 0 or keyword_matches > 0:
                type_scores[doc_type] = min(final_score, 1.0)
        
        # Determine best match
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            return best_type[0], best_type[1]
        else:
            return 'other', 0.0
    
    def _determine_category(self, document_type: str) -> str:
        """Determine high-level document category"""
        category_mapping = {
            'lab': 'diagnostic',
            'imaging': 'diagnostic',
            'consult': 'clinical',
            'hospital_summary': 'clinical',
            'medication': 'therapeutic',
            'procedure': 'procedural',
            'progress_note': 'clinical',
            'vital_signs': 'diagnostic',
            'other': 'general'
        }
        
        return category_mapping.get(document_type, 'general')
    
    def _analyze_content_indicators(self, text: str) -> Dict[str, Any]:
        """Analyze content for additional indicators"""
        indicators = {
            'contains_numeric_values': bool(re.search(r'\d+\.?\d*', text)),
            'contains_medical_units': bool(re.search(r'(mg/dl|mmol/l|mg|ml|units|%|bpm|mmhg)', text, re.IGNORECASE)),
            'contains_dates': bool(re.search(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}', text)),
            'contains_time': bool(re.search(r'\d{1,2}:\d{2}', text)),
            'word_count': len(text.split()),
            'sentence_count': len(re.split(r'[.!?]+', text)),
            'uppercase_ratio': len(re.findall(r'[A-Z]', text)) / max(len(text), 1),
            'medical_terminology_density': self._calculate_medical_density(text)
        }
        
        return indicators
    
    def _calculate_medical_density(self, text: str) -> float:
        """Calculate density of medical terminology in text"""
        medical_terms = []
        
        # Collect all medical keywords
        for patterns in self.document_patterns.values():
            medical_terms.extend(patterns['keywords'])
        
        # Count occurrences
        word_count = len(text.split())
        medical_count = sum(1 for term in medical_terms if term in text.lower())
        
        return medical_count / max(word_count, 1)


def parse_medical_document(filename: str, content: str = None) -> Dict[str, Any]:
    """
    Convenience function to parse a medical document
    
    Args:
        filename: Document filename
        content: Document content (optional)
        
    Returns:
        Dictionary with structured metadata
    """
    parser = MedicalDocumentParser()
    metadata = parser.parse_document(filename, content)
    return metadata.to_dict()


def demo_document_parsing():
    """Demonstrate document parsing capabilities"""
    
    # Test documents with different types
    test_documents = [
        {
            'filename': 'Lab_Results_CBC_2024-03-15.pdf',
            'content': 'Complete Blood Count performed on March 15, 2024. Hemoglobin: 14.2 g/dL, Hematocrit: 42.1%, White Blood Cell count: 7,200/μL, Platelet count: 285,000/μL. Dr. Smith, MD reviewed results.'
        },
        {
            'filename': 'Chest_X-Ray_Report_03-20-2024.pdf',
            'content': 'Chest X-ray performed on March 20, 2024 at City Medical Center. Radiology findings: Clear lung fields, normal heart size. No acute findings. Radiologist: Dr. Johnson, MD.'
        },
        {
            'filename': 'Cardiology_Consultation_Note.pdf',
            'content': 'Cardiology consultation performed by Dr. Anderson, MD on March 25, 2024. Patient referred for chest pain evaluation. Recommendation: stress test and echocardiogram. Follow up in 2 weeks.'
        },
        {
            'filename': 'Discharge_Summary_Hospital_Stay.pdf',
            'content': 'Discharge summary for 3-day hospital admission from March 10-13, 2024 at General Hospital. Admitting diagnosis: pneumonia. Discharge medications: amoxicillin 500mg twice daily.'
        }
    ]
    
    print("MEDICAL DOCUMENT PARSING DEMONSTRATION")
    print("=" * 50)
    
    parser = MedicalDocumentParser()
    
    for i, doc in enumerate(test_documents, 1):
        print(f"\n{i}. Parsing: {doc['filename']}")
        print("-" * 40)
        
        metadata = parser.parse_document(doc['filename'], doc['content'])
        
        print(f"Document Type: {metadata.document_type}")
        print(f"Category: {metadata.document_category}")
        print(f"Confidence: {metadata.confidence_score:.2f}")
        print(f"Primary Date: {metadata.primary_date}")
        print(f"Keywords Found: {len(metadata.keywords)}")
        print(f"Top Keywords: {metadata.keywords[:5]}")
        print(f"Providers: {metadata.extracted_providers}")
        print(f"Facilities: {metadata.extracted_facilities}")
        print(f"Content Indicators:")
        for key, value in metadata.content_indicators.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    demo_document_parsing()