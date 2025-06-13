"""
Document to Screening Type Matching System
Multi-strategy document matching with confidence scoring for prep sheet generation
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from difflib import SequenceMatcher

from app import db
from models import ScreeningType, MedicalDocument
from fhir_document_section_mapper import DocumentSectionMapper


@dataclass
class MatchResult:
    """Structured result for document-screening matches"""
    screening_type_id: int
    screening_name: str
    match_source: str  # 'fhir_code', 'filename_keyword', 'user_keyword', 'ai_fuzzy'
    confidence: float  # 0.0 to 1.0
    matched_codes: List[str]
    matched_keywords: List[str]
    metadata: Dict[str, Any]


class DocumentScreeningMatcher:
    """
    Advanced document matching system with multiple strategies and confidence scoring
    """
    
    def __init__(self):
        self.section_mapper = DocumentSectionMapper()
        
        # Standard medical coding systems
        self.coding_systems = {
            'loinc': 'http://loinc.org',
            'cpt': 'http://www.ama-assn.org/go/cpt',
            'snomed': 'http://snomed.info/sct',
            'icd10': 'http://hl7.org/fhir/sid/icd-10-cm',
            'user_coding': 'http://example.org/user-coding-system'
        }
        
        # Confidence thresholds
        self.confidence_thresholds = {
            'high': 0.8,
            'medium': 0.5,
            'low': 0.3
        }
    
    def match_document_to_screenings(self, document: MedicalDocument, enable_ai_fuzzy: bool = False) -> List[MatchResult]:
        """
        Match a document to screening types using multiple strategies
        
        Args:
            document: MedicalDocument instance
            enable_ai_fuzzy: Whether to enable AI-based fuzzy matching
            
        Returns:
            List[MatchResult]: Ordered list of matches with confidence scores
        """
        all_matches = []
        
        # Strategy 1: FHIR code matching (LOINC/CPT/SNOMED)
        fhir_matches = self._match_by_fhir_codes(document)
        all_matches.extend(fhir_matches)
        
        # Strategy 2: Filename and section keyword matching
        keyword_matches = self._match_by_keywords(document)
        all_matches.extend(keyword_matches)
        
        # Strategy 3: User-defined keyword fallback
        user_keyword_matches = self._match_by_user_keywords(document)
        all_matches.extend(user_keyword_matches)
        
        # Strategy 4: AI-based fuzzy matching (optional)
        if enable_ai_fuzzy:
            fuzzy_matches = self._match_by_ai_fuzzy(document)
            all_matches.extend(fuzzy_matches)
        
        # Deduplicate and sort by confidence
        unique_matches = self._deduplicate_matches(all_matches)
        return sorted(unique_matches, key=lambda x: x.confidence, reverse=True)
    
    def _match_by_fhir_codes(self, document: MedicalDocument) -> List[MatchResult]:
        """Match document using FHIR codes (LOINC/CPT/SNOMED)"""
        matches = []
        
        # Extract FHIR codes from document metadata
        document_codes = self._extract_document_codes(document)
        
        if not document_codes:
            return matches
        
        # Get all screening types
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        for screening_type in screening_types:
            # Check section mappings for code matches
            section_mappings = screening_type.get_document_section_mappings()
            matched_codes = []
            
            for section, config in section_mappings.items():
                section_codes = config.get('loinc_codes', []) + config.get('cpt_codes', []) + config.get('snomed_codes', [])
                
                for doc_code in document_codes:
                    if doc_code['code'] in section_codes:
                        matched_codes.append(doc_code['code'])
            
            # Check trigger conditions for condition-based codes
            trigger_conditions = screening_type.get_trigger_conditions()
            for trigger in trigger_conditions:
                for doc_code in document_codes:
                    if (doc_code['code'] == trigger.get('code') and 
                        doc_code['system'] == trigger.get('system')):
                        matched_codes.append(doc_code['code'])
            
            if matched_codes:
                confidence = self._calculate_fhir_code_confidence(matched_codes, document_codes)
                
                matches.append(MatchResult(
                    screening_type_id=screening_type.id,
                    screening_name=screening_type.name,
                    match_source='fhir_code',
                    confidence=confidence,
                    matched_codes=matched_codes,
                    matched_keywords=[],
                    metadata={
                        'matching_system': 'FHIR coding',
                        'total_document_codes': len(document_codes),
                        'matched_code_count': len(matched_codes)
                    }
                ))
        
        return matches
    
    def _match_by_keywords(self, document: MedicalDocument) -> List[MatchResult]:
        """Match document using filename and section keywords"""
        matches = []
        
        # Prepare document text for keyword matching
        document_text = self._prepare_document_text(document)
        detected_section = self.section_mapper.detect_document_section(
            document.filename or document.document_name,
            document.document_type,
            document.content[:500] if document.content else None
        )
        
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        for screening_type in screening_types:
            matched_keywords = []
            
            # Check section mappings for keyword matches
            section_mappings = screening_type.get_document_section_mappings()
            
            for section, config in section_mappings.items():
                section_keywords = config.get('keywords', [])
                
                # Direct section match
                if section == detected_section:
                    matched_keywords.extend(['section:' + section])
                
                # Keyword matching in document text
                for keyword in section_keywords:
                    if keyword.lower() in document_text.lower():
                        matched_keywords.append(keyword)
            
            if matched_keywords:
                confidence = self._calculate_keyword_confidence(matched_keywords, document_text, detected_section)
                
                matches.append(MatchResult(
                    screening_type_id=screening_type.id,
                    screening_name=screening_type.name,
                    match_source='filename_keyword',
                    confidence=confidence,
                    matched_codes=[],
                    matched_keywords=matched_keywords,
                    metadata={
                        'matching_system': 'Keyword matching',
                        'detected_section': detected_section,
                        'keyword_count': len(matched_keywords)
                    }
                ))
        
        return matches
    
    def _match_by_user_keywords(self, document: MedicalDocument) -> List[MatchResult]:
        """Match using user-defined keyword fallback"""
        matches = []
        
        document_text = self._prepare_document_text(document)
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        # User-defined fallback keywords for common scenarios
        user_keyword_patterns = {
            'diabetes': ['diabetes', 'diabetic', 'glucose', 'insulin', 'hba1c', 'blood sugar'],
            'hypertension': ['hypertension', 'blood pressure', 'bp', 'cardiovascular'],
            'cancer': ['cancer', 'tumor', 'oncology', 'malignant', 'screening'],
            'cardiology': ['heart', 'cardiac', 'cardiovascular', 'ecg', 'echo'],
            'pulmonary': ['lung', 'respiratory', 'pulmonary', 'chest', 'breathing']
        }
        
        for screening_type in screening_types:
            matched_keywords = []
            
            # Check screening name against user patterns
            screening_name_lower = screening_type.name.lower()
            
            for pattern_category, keywords in user_keyword_patterns.items():
                if pattern_category in screening_name_lower:
                    for keyword in keywords:
                        if keyword in document_text.lower():
                            matched_keywords.append(f"user:{keyword}")
            
            # Direct screening name keyword matching
            screening_words = screening_name_lower.split()
            for word in screening_words:
                if len(word) > 3 and word in document_text.lower():
                    matched_keywords.append(f"direct:{word}")
            
            if matched_keywords:
                confidence = self._calculate_user_keyword_confidence(matched_keywords, screening_type.name)
                
                matches.append(MatchResult(
                    screening_type_id=screening_type.id,
                    screening_name=screening_type.name,
                    match_source='user_keyword',
                    confidence=confidence,
                    matched_codes=[],
                    matched_keywords=matched_keywords,
                    metadata={
                        'matching_system': 'User-defined keywords',
                        'fallback_strategy': True,
                        'keyword_count': len(matched_keywords)
                    }
                ))
        
        return matches
    
    def _match_by_ai_fuzzy(self, document: MedicalDocument) -> List[MatchResult]:
        """AI-based fuzzy matching using text similarity"""
        matches = []
        
        document_text = self._prepare_document_text(document)
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        for screening_type in screening_types:
            # Create screening context text
            screening_context = f"{screening_type.name} {screening_type.description or ''}"
            
            # Calculate text similarity
            similarity = SequenceMatcher(None, document_text.lower(), screening_context.lower()).ratio()
            
            # Use advanced fuzzy matching for medical terms
            fuzzy_score = self._advanced_fuzzy_match(document_text, screening_context)
            
            # Combine similarity scores
            combined_confidence = (similarity * 0.3) + (fuzzy_score * 0.7)
            
            # Only include matches above minimum threshold
            if combined_confidence > 0.2:
                matches.append(MatchResult(
                    screening_type_id=screening_type.id,
                    screening_name=screening_type.name,
                    match_source='ai_fuzzy',
                    confidence=combined_confidence,
                    matched_codes=[],
                    matched_keywords=[],
                    metadata={
                        'matching_system': 'AI fuzzy matching',
                        'text_similarity': similarity,
                        'fuzzy_score': fuzzy_score,
                        'combined_score': combined_confidence
                    }
                ))
        
        return matches
    
    def _extract_document_codes(self, document: MedicalDocument) -> List[Dict[str, str]]:
        """Extract FHIR codes from document metadata"""
        codes = []
        
        # Check document metadata
        if document.doc_metadata:
            try:
                metadata = json.loads(document.doc_metadata)
                
                # Extract FHIR codes from metadata
                if 'fhir_primary_code' in metadata:
                    fhir_code = metadata['fhir_primary_code']
                    if 'code' in fhir_code and 'coding' in fhir_code['code']:
                        for coding in fhir_code['code']['coding']:
                            codes.append({
                                'system': coding.get('system', ''),
                                'code': coding.get('code', ''),
                                'display': coding.get('display', '')
                            })
                
                # Extract from FHIR condition codes
                if 'fhir_condition_code' in metadata:
                    condition_code = metadata['fhir_condition_code']
                    if 'coding' in condition_code:
                        for coding in condition_code['coding']:
                            codes.append({
                                'system': coding.get('system', ''),
                                'code': coding.get('code', ''),
                                'display': coding.get('display', '')
                            })
            
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Use document's FHIR metadata extraction
        try:
            fhir_metadata = document.extract_fhir_metadata()
            if 'code' in fhir_metadata and 'coding' in fhir_metadata['code']:
                for coding in fhir_metadata['code']['coding']:
                    codes.append({
                        'system': coding.get('system', ''),
                        'code': coding.get('code', ''),
                        'display': coding.get('display', '')
                    })
        except Exception:
            pass
        
        return codes
    
    def _prepare_document_text(self, document: MedicalDocument) -> str:
        """Prepare document text for analysis"""
        text_parts = []
        
        if document.filename:
            text_parts.append(document.filename)
        if document.document_name:
            text_parts.append(document.document_name)
        if document.document_type:
            text_parts.append(document.document_type)
        if document.content and not document.is_binary:
            # Sample first 1000 characters for analysis
            text_parts.append(document.content[:1000])
        
        return ' '.join(text_parts)
    
    def _calculate_fhir_code_confidence(self, matched_codes: List[str], all_document_codes: List[Dict[str, str]]) -> float:
        """Calculate confidence for FHIR code matches"""
        if not matched_codes or not all_document_codes:
            return 0.0
        
        # Base confidence from match ratio
        match_ratio = len(matched_codes) / len(all_document_codes)
        base_confidence = min(0.9, match_ratio * 0.8 + 0.2)
        
        # Boost for multiple matches
        if len(matched_codes) > 1:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _calculate_keyword_confidence(self, matched_keywords: List[str], document_text: str, detected_section: str) -> float:
        """Calculate confidence for keyword matches"""
        if not matched_keywords:
            return 0.0
        
        base_confidence = 0.3
        
        # Boost for section matches
        section_matches = [k for k in matched_keywords if k.startswith('section:')]
        if section_matches:
            base_confidence += 0.4
        
        # Boost for multiple keyword matches
        keyword_matches = [k for k in matched_keywords if not k.startswith('section:')]
        base_confidence += min(0.3, len(keyword_matches) * 0.1)
        
        # Boost for document type relevance
        if detected_section != 'unknown':
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _calculate_user_keyword_confidence(self, matched_keywords: List[str], screening_name: str) -> float:
        """Calculate confidence for user-defined keyword matches"""
        if not matched_keywords:
            return 0.0
        
        base_confidence = 0.2
        
        # Boost for direct screening name matches
        direct_matches = [k for k in matched_keywords if k.startswith('direct:')]
        base_confidence += len(direct_matches) * 0.2
        
        # Boost for user pattern matches
        user_matches = [k for k in matched_keywords if k.startswith('user:')]
        base_confidence += len(user_matches) * 0.15
        
        return min(0.8, base_confidence)  # Cap user keyword confidence
    
    def _advanced_fuzzy_match(self, document_text: str, screening_context: str) -> float:
        """Advanced fuzzy matching for medical terminology"""
        # Medical term extraction and matching
        medical_terms = self._extract_medical_terms(document_text)
        screening_terms = self._extract_medical_terms(screening_context)
        
        if not medical_terms or not screening_terms:
            return 0.0
        
        # Calculate term overlap
        common_terms = set(medical_terms) & set(screening_terms)
        if not common_terms:
            return 0.0
        
        # Calculate weighted similarity
        overlap_ratio = len(common_terms) / max(len(medical_terms), len(screening_terms))
        return min(0.9, overlap_ratio * 0.8)
    
    def _extract_medical_terms(self, text: str) -> List[str]:
        """Extract medical terms from text"""
        # Common medical term patterns
        medical_patterns = [
            r'\b[a-z]*diabetes[a-z]*\b',
            r'\b[a-z]*hypertension[a-z]*\b',
            r'\b[a-z]*cardiac[a-z]*\b',
            r'\b[a-z]*glucose[a-z]*\b',
            r'\b[a-z]*cancer[a-z]*\b',
            r'\b[a-z]*screening[a-z]*\b',
            r'\bhba1c\b',
            r'\b[a-z]*pressure[a-z]*\b'
        ]
        
        terms = []
        text_lower = text.lower()
        
        for pattern in medical_patterns:
            matches = re.findall(pattern, text_lower)
            terms.extend(matches)
        
        return list(set(terms))  # Remove duplicates
    
    def _deduplicate_matches(self, matches: List[MatchResult]) -> List[MatchResult]:
        """Remove duplicate matches, keeping highest confidence"""
        unique_matches = {}
        
        for match in matches:
            key = match.screening_type_id
            
            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
                unique_matches[key] = match
        
        return list(unique_matches.values())
    
    def get_match_summary(self, matches: List[MatchResult]) -> Dict[str, Any]:
        """Generate summary statistics for matches"""
        if not matches:
            return {
                'total_matches': 0,
                'high_confidence_matches': 0,
                'medium_confidence_matches': 0,
                'low_confidence_matches': 0,
                'best_match': None,
                'match_sources': {}
            }
        
        # Count by confidence levels
        high_conf = sum(1 for m in matches if m.confidence >= self.confidence_thresholds['high'])
        medium_conf = sum(1 for m in matches if self.confidence_thresholds['medium'] <= m.confidence < self.confidence_thresholds['high'])
        low_conf = sum(1 for m in matches if self.confidence_thresholds['low'] <= m.confidence < self.confidence_thresholds['medium'])
        
        # Count by source
        source_counts = {}
        for match in matches:
            source_counts[match.match_source] = source_counts.get(match.match_source, 0) + 1
        
        return {
            'total_matches': len(matches),
            'high_confidence_matches': high_conf,
            'medium_confidence_matches': medium_conf,
            'low_confidence_matches': low_conf,
            'best_match': matches[0] if matches else None,
            'match_sources': source_counts,
            'average_confidence': sum(m.confidence for m in matches) / len(matches),
            'confidence_thresholds': self.confidence_thresholds
        }


def generate_prep_sheet_screening_recommendations(patient_id: int, enable_ai_fuzzy: bool = False) -> Dict[str, Any]:
    """
    Generate screening recommendations for prep sheet based on document matching
    
    Args:
        patient_id: Patient ID
        enable_ai_fuzzy: Whether to enable AI fuzzy matching
        
    Returns:
        Dict with structured screening recommendations
    """
    matcher = DocumentScreeningMatcher()
    
    # Get patient documents
    documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()
    
    if not documents:
        return {
            'patient_id': patient_id,
            'document_count': 0,
            'screening_recommendations': [],
            'summary': {
                'total_matches': 0,
                'unique_screenings': 0,
                'confidence_distribution': {}
            }
        }
    
    # Match each document to screening types
    all_recommendations = []
    document_matches = {}
    
    for document in documents:
        matches = matcher.match_document_to_screenings(document, enable_ai_fuzzy)
        
        if matches:
            document_matches[document.id] = {
                'document_name': document.filename or document.document_name,
                'document_type': document.document_type,
                'matches': [
                    {
                        'screening_name': match.screening_name,
                        'match_source': match.match_source,
                        'confidence': match.confidence,
                        'matched_codes': match.matched_codes,
                        'matched_keywords': match.matched_keywords,
                        'metadata': match.metadata
                    }
                    for match in matches
                ]
            }
            
            all_recommendations.extend(matches)
    
    # Consolidate recommendations by screening type
    screening_recommendations = {}
    for match in all_recommendations:
        screening_id = match.screening_type_id
        
        if screening_id not in screening_recommendations:
            screening_recommendations[screening_id] = {
                'screening_name': match.screening_name,
                'highest_confidence': match.confidence,
                'match_sources': [match.match_source],
                'supporting_documents': [],
                'total_matches': 1,
                'all_matched_codes': set(match.matched_codes),
                'all_matched_keywords': set(match.matched_keywords)
            }
        else:
            rec = screening_recommendations[screening_id]
            rec['highest_confidence'] = max(rec['highest_confidence'], match.confidence)
            if match.match_source not in rec['match_sources']:
                rec['match_sources'].append(match.match_source)
            rec['total_matches'] += 1
            rec['all_matched_codes'].update(match.matched_codes)
            rec['all_matched_keywords'].update(match.matched_keywords)
    
    # Convert to final format
    final_recommendations = []
    for screening_id, rec in screening_recommendations.items():
        final_recommendations.append({
            'screening_type_id': screening_id,
            'screening_name': rec['screening_name'],
            'confidence': rec['highest_confidence'],
            'match_sources': rec['match_sources'],
            'total_document_matches': rec['total_matches'],
            'matched_codes': list(rec['all_matched_codes']),
            'matched_keywords': list(rec['all_matched_keywords']),
            'recommendation_priority': 'high' if rec['highest_confidence'] >= 0.8 else 'medium' if rec['highest_confidence'] >= 0.5 else 'low'
        })
    
    # Sort by confidence
    final_recommendations.sort(key=lambda x: x['confidence'], reverse=True)
    
    return {
        'patient_id': patient_id,
        'document_count': len(documents),
        'screening_recommendations': final_recommendations,
        'document_matches': document_matches,
        'summary': {
            'total_matches': len(all_recommendations),
            'unique_screenings': len(screening_recommendations),
            'high_confidence_count': sum(1 for r in final_recommendations if r['confidence'] >= 0.8),
            'medium_confidence_count': sum(1 for r in final_recommendations if 0.5 <= r['confidence'] < 0.8),
            'low_confidence_count': sum(1 for r in final_recommendations if r['confidence'] < 0.5)
        },
        'generation_metadata': {
            'generated_at': datetime.now().isoformat(),
            'ai_fuzzy_enabled': enable_ai_fuzzy,
            'matcher_version': '1.0'
        }
    }