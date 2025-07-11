"""
Document Screening Matcher
Matches medical documents to screening types using patient profile and document metadata/content
Uses ScreeningType rules from /screenings?tab=types
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
import re
import json
from models import ScreeningType, Patient, MedicalDocument, Screening
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
        filename_keywords = screening_type.get_filename_keywords()
        if not filename_keywords:
            return False, "No filename keywords defined"
        
        filename = document.filename.lower() if document.filename else ""
        matched_keywords = []
        
        for keyword in filename_keywords:
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
        content_keywords = screening_type.get_content_keywords()
        if not content_keywords:
            return False, "No content keywords defined"
        
        # Combine searchable text from document
        searchable_text = ""
        if document.content:
            searchable_text += document.content.lower()
        
        if not searchable_text.strip():
            return False, "No document content available for matching"
        
        matched_keywords = []
        for keyword in content_keywords:
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
        document_keywords = screening_type.get_document_keywords()
        if not document_keywords:
            return False, "No document section keywords defined"
        
        # Get document section - check metadata first, then document_type
        document_section = ""
        
        # Try to extract section from metadata
        if document.doc_metadata:
            try:
                import json
                metadata = json.loads(document.doc_metadata)
                if 'section' in metadata:
                    document_section = metadata['section'].lower()
                elif 'category' in metadata:
                    document_section = metadata['category'].lower()
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Fallback to document_type if no section found
        if not document_section and document.document_type:
            document_section = document.document_type.lower()
        
        if not document_section:
            return False, "No document section available for matching"
        
        matched_keywords = []
        for keyword in document_keywords:
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
                    'last_match': max(matches, key=lambda x: x['document_id'])['notes'] if matches else 'No matches',
                    'priority': 'high' if len(matches) > 1 else 'normal'
                }
                recommendations['recommendations'].append(recommendation)
        
        return recommendations
    
    def store_document_screening_relationship(
        self,
        patient: Patient,
        screening_type: ScreeningType,
        document: MedicalDocument,
        match_result: Dict[str, Any],
        confidence_score: float = 1.0
    ) -> Optional[Screening]:
        """
        Store a document-screening relationship in the many-to-many table
        
        Args:
            patient: Patient object
            screening_type: ScreeningType object 
            document: MedicalDocument object
            match_result: Result from match_document_to_screening
            confidence_score: Confidence score for the match (0.0 to 1.0)
            
        Returns:
            Screening object or None if operation failed
        """
        try:
            # Find existing screening or create new one
            screening = Screening.query.filter_by(
                patient_id=patient.id,
                screening_type=screening_type.name
            ).first()
            
            if not screening:
                # Create new screening record
                screening = Screening(
                    patient_id=patient.id,
                    screening_type=screening_type.name,
                    status='Incomplete',  # Will be updated by automated engine
                    frequency=screening_type.formatted_frequency or 'As needed',
                    notes=self._generate_clean_notes(match_result),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(screening)
                db.session.flush()  # Get the ID
            
            # Add document relationship using the new many-to-many table
            screening.add_document(
                document,
                confidence_score=confidence_score,
                match_source=match_result.get('match_method', 'automated')
            )
            
            db.session.commit()
            return screening
            
        except Exception as e:
            db.session.rollback()
            print(f"Error storing document-screening relationship: {e}")
            return None
    
    def store_all_matching_documents(
        self,
        patient: Patient,
        documents: List[MedicalDocument] = None
    ) -> Dict[str, Any]:
        """
        Find all document matches for a patient and store relationships in the database
        
        Args:
            patient: Patient object
            documents: Optional list of documents (if None, fetches all patient documents)
            
        Returns:
            Dict with storage results and statistics
        """
        if documents is None:
            documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
        
        results = {
            'patient_id': patient.id,
            'total_documents': len(documents),
            'relationships_created': 0,
            'screenings_updated': 0,
            'errors': []
        }
        
        try:
            for document in documents:
                # Find matching screenings for this document
                matches = self.find_matching_screenings(document, patient)
                
                for match in matches:
                    if match['matched']:
                        # Get the screening type
                        screening_type = ScreeningType.query.get(match['screening_id'])
                        if not screening_type:
                            continue
                        
                        # Calculate confidence score
                        confidence = self._calculate_match_confidence_from_result(match, document)
                        
                        # Store the relationship
                        screening = self.store_document_screening_relationship(
                            patient, screening_type, document, match, confidence
                        )
                        
                        if screening:
                            results['relationships_created'] += 1
                            results['screenings_updated'] += 1
                        else:
                            results['errors'].append(f"Failed to store relationship for {screening_type.name}")
            
            return results
            
        except Exception as e:
            results['errors'].append(f"General error: {str(e)}")
            return results
    
    def _generate_clean_notes(self, match_result: Dict[str, Any]) -> str:
        """
        Generate clean notes without document IDs (those are now in relationships)
        
        Args:
            match_result: Match result dictionary
            
        Returns:
            Clean notes string
        """
        notes = match_result.get('notes', '')
        
        # Remove any document ID references from notes
        notes = re.sub(r'\|\s*Document ID:\s*\d+', '', notes)
        notes = re.sub(r'Document ID:\s*\d+\s*\|?', '', notes)
        notes = notes.strip(' |')
        
        # Add match method information if not present
        if match_result.get('match_method') and 'matched' not in notes.lower():
            method_desc = self._format_match_source(match_result['match_method'])
            notes = f"Matched via {method_desc}. {notes}" if notes else f"Matched via {method_desc}"
        
        return notes or "Document match found"
    
    def _calculate_match_confidence_from_result(self, match_result: Dict, document: MedicalDocument) -> float:
        """Calculate confidence from match result and document"""
        base_confidence = {
            'content': 0.9,
            'filename': 0.7, 
            'keywords': 0.6
        }
        
        confidence = base_confidence.get(match_result.get('match_method'), 0.5)
        
        # Adjust based on match quality indicators
        notes = match_result.get('notes', '')
        if 'keywords matched:' in notes:
            keyword_count = notes.count(',') + 1
            if keyword_count > 1:
                confidence = min(confidence + (keyword_count * 0.05), 1.0)
        
        return round(confidence, 2)
    
    def remove_document_from_screenings(
        self,
        document: MedicalDocument,
        patient: Patient = None
    ) -> Dict[str, Any]:
        """
        Remove a document from all screening relationships
        
        Args:
            document: MedicalDocument to remove
            patient: Optional patient object for validation
            
        Returns:
            Dict with removal results
        """
        results = {
            'document_id': document.id,
            'relationships_removed': 0,
            'errors': []
        }
        
        try:
            # Get all screenings that reference this document
            screenings_with_doc = Screening.query.join(Screening.documents).filter(
                MedicalDocument.id == document.id
            ).all()
            
            for screening in screenings_with_doc:
                # Validate patient if provided
                if patient and screening.patient_id != patient.id:
                    continue
                
                # Remove document from screening
                screening.remove_document(document)
                results['relationships_removed'] += 1
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            results['errors'].append(f"Error removing document relationships: {str(e)}")
            return results


def generate_prep_sheet_screening_recommendations(
    patient_id: int, 
    enable_ai_fuzzy: bool = True,
    include_confidence_scores: bool = True
) -> Dict[str, Any]:
    """
    Generate comprehensive prep sheet screening recommendations with document matching
    
    Args:
        patient_id: Patient ID
        enable_ai_fuzzy: Enable fuzzy/AI matching (currently uses keyword matching)
        include_confidence_scores: Include confidence scoring for matches
        
    Returns:
        Dict containing:
            - screening_recommendations: List of screening recommendations with document matches
            - document_matches: Detailed document matching results
            - summary: Summary statistics
            - generation_metadata: Generation details
    """
    from models import Patient, MedicalDocument, ScreeningType
    from checklist_routes import get_or_create_settings
    
    try:
        # Get patient and related data
        patient = Patient.query.get(patient_id)
        if not patient:
            return _empty_screening_recommendations_response(f"Patient {patient_id} not found")
        
        # Get patient's documents
        documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()
        
        # Get checklist settings to determine which screenings to include
        checklist_settings = get_or_create_settings()
        content_sources = checklist_settings.content_sources_list if checklist_settings else ['age_based', 'existing_screenings']
        
        # Get active screening types from prep sheet settings
        active_screening_types = _get_active_screening_types_for_prep_sheet(patient, content_sources)
        
        # Initialize matcher
        matcher = DocumentScreeningMatcher()
        
        # Generate recommendations for each screening type
        screening_recommendations = []
        all_document_matches = []
        
        for screening_type in active_screening_types:
            recommendation = _analyze_screening_with_documents(
                screening_type, patient, documents, matcher, include_confidence_scores
            )
            screening_recommendations.append(recommendation)
            
            # Collect document matches for this screening
            if recommendation.get('document_matches'):
                all_document_matches.extend(recommendation['document_matches'])
        
        # Generate summary statistics
        summary = _generate_screening_summary(screening_recommendations, documents)
        
        # Prepare response
        response = {
            'patient_id': patient_id,
            'patient_name': patient.full_name,
            'document_count': len(documents),
            'screening_recommendations': screening_recommendations,
            'document_matches': all_document_matches,
            'summary': summary,
            'generation_metadata': {
                'generated_at': datetime.now().isoformat(),
                'method': 'document_screening_matcher',
                'fuzzy_matching_enabled': enable_ai_fuzzy,
                'confidence_scoring_enabled': include_confidence_scores,
                'content_sources': content_sources,
                'total_screening_types_analyzed': len(active_screening_types)
            }
        }
        
        return response
        
    except Exception as e:
        return _empty_screening_recommendations_response(f"Error generating recommendations: {str(e)}")


def _get_active_screening_types_for_prep_sheet(patient: Patient, content_sources: List[str]) -> List[ScreeningType]:
    """Get active screening types based on prep sheet settings and patient criteria"""
    from models import ScreeningType, Screening
    
    screening_types = set()
    
    # Age-based screenings
    if 'age_based' in content_sources:
        age_based = ScreeningType.query.filter(
            ScreeningType.is_active == True,
            ScreeningType.status == 'active'
        ).all()
        
        for st in age_based:
            # Check age criteria
            if st.min_age and patient.age < st.min_age:
                continue
            if st.max_age and patient.age > st.max_age:
                continue
            
            # Check gender criteria
            if st.gender_specific and patient.sex.lower() != st.gender_specific.lower():
                continue
                
            screening_types.add(st)
    
    # Existing screenings in database
    if 'existing_screenings' in content_sources:
        existing_screenings = Screening.query.filter_by(patient_id=patient.id).all()
        for screening in existing_screenings:
            screening_type = ScreeningType.query.filter_by(
                name=screening.screening_type, 
                is_active=True
            ).first()
            if screening_type:
                screening_types.add(screening_type)
    
    # Gender-based screenings (additional logic)
    if 'gender_based' in content_sources:
        gender_specific = ScreeningType.query.filter(
            ScreeningType.is_active == True,
            ScreeningType.gender_specific == patient.sex.lower()
        ).all()
        screening_types.update(gender_specific)
    
    # Condition-based screenings (if conditions exist)
    if 'condition_based' in content_sources:
        from models import Condition
        patient_conditions = Condition.query.filter_by(patient_id=patient.id).all()
        if patient_conditions:
            # Add screening types that match patient conditions
            condition_triggered = ScreeningType.query.filter(
                ScreeningType.is_active == True,
                ScreeningType.trigger_conditions.isnot(None)
            ).all()
            
            for st in condition_triggered:
                if _patient_matches_trigger_conditions(patient_conditions, st):
                    screening_types.add(st)
    
    return list(screening_types)


def _patient_matches_trigger_conditions(patient_conditions: List, screening_type: ScreeningType) -> bool:
    """Check if patient conditions match screening type trigger conditions"""
    if not screening_type.trigger_conditions:
        return False
    
    try:
        trigger_conditions = json.loads(screening_type.trigger_conditions) if isinstance(screening_type.trigger_conditions, str) else screening_type.trigger_conditions
        if not trigger_conditions:
            return False
        
        patient_condition_names = [c.name.lower() for c in patient_conditions]
        
        for trigger in trigger_conditions:
            trigger_name = trigger.get('condition', '').lower()
            if any(trigger_name in condition for condition in patient_condition_names):
                return True
        
        return False
        
    except (json.JSONDecodeError, AttributeError):
        return False


def _analyze_screening_with_documents(
    screening_type: ScreeningType, 
    patient: Patient, 
    documents: List, 
    matcher: DocumentScreeningMatcher,
    include_confidence: bool = True
) -> Dict[str, Any]:
    """Analyze a screening type against patient documents to generate recommendation"""
    
    # Basic screening info
    recommendation = {
        'screening_type_id': screening_type.id,
        'screening_name': screening_type.name,
        'screening_description': screening_type.description,
        'frequency': screening_type.formatted_frequency or 'As recommended',
        'document_matches': [],
        'best_match': None,
        'match_confidence': 0.0,
        'match_sources': [],
        'recommendation_status': 'no_documents',
        'status_notes': ''
    }
    
    if not documents:
        recommendation['status_notes'] = 'No documents available for analysis'
        return recommendation
    
    # Analyze each document for matches
    document_matches = []
    best_match = None
    highest_confidence = 0.0
    
    for document in documents:
        match_result = matcher.match_document_to_screening(screening_type, document, patient)
        
        if match_result['matched']:
            # Calculate confidence score
            confidence = _calculate_match_confidence(match_result, screening_type, document)
            
            document_match = {
                'document_id': document.id,
                'document_name': document.filename or 'Unnamed Document',
                'document_type': document.document_type.value if hasattr(document.document_type, 'value') else str(document.document_type),
                'match_method': match_result['match_method'],
                'match_confidence': confidence,
                'match_confidence_percent': int(confidence * 100),
                'match_source': _format_match_source(match_result['match_method']),
                'match_notes': match_result['notes'],
                'status': match_result['status']
            }
            
            document_matches.append(document_match)
            
            # Track best match
            if confidence > highest_confidence:
                highest_confidence = confidence
                best_match = document_match
    
    # Update recommendation with results
    recommendation['document_matches'] = document_matches
    recommendation['best_match'] = best_match
    recommendation['match_confidence'] = highest_confidence
    
    if document_matches:
        # Determine recommendation status and notes
        if highest_confidence >= 0.8:
            recommendation['recommendation_status'] = 'high_confidence'
            recommendation['status_notes'] = f"Strong match found: {best_match['document_name']} ({best_match['match_source']})"
        elif highest_confidence >= 0.6:
            recommendation['recommendation_status'] = 'medium_confidence'
            recommendation['status_notes'] = f"Possible match: {best_match['document_name']} ({best_match['match_source']})"
        else:
            recommendation['recommendation_status'] = 'low_confidence'
            recommendation['status_notes'] = f"Weak match: {best_match['document_name']} ({best_match['match_source']})"
        
        # Collect unique match sources
        recommendation['match_sources'] = list(set([m['match_source'] for m in document_matches]))
    else:
        recommendation['recommendation_status'] = 'no_matches'
        recommendation['status_notes'] = 'No document matches found for this screening'
    
    return recommendation


def _calculate_match_confidence(match_result: Dict, screening_type: ScreeningType, document) -> float:
    """Calculate confidence score for a document match"""
    base_confidence = {
        'content': 0.9,      # Content matches are most reliable
        'filename': 0.7,     # Filename matches are moderately reliable  
        'keywords': 0.6      # Section/keyword matches are less reliable
    }
    
    confidence = base_confidence.get(match_result['match_method'], 0.5)
    
    # Adjust confidence based on additional factors
    
    # Boost confidence if multiple keyword matches
    if 'keywords matched:' in match_result['notes']:
        keyword_count = match_result['notes'].count(',') + 1
        if keyword_count > 1:
            confidence = min(confidence + (keyword_count * 0.05), 1.0)
    
    # Boost confidence for exact document type matches
    if hasattr(document, 'document_type') and screening_type.name.lower() in str(document.document_type).lower():
        confidence = min(confidence + 0.1, 1.0)
    
    # Reduce confidence for very old documents
    if hasattr(document, 'created_at'):
        days_old = (datetime.now() - document.created_at).days
        if days_old > 365:  # Older than 1 year
            confidence *= 0.9
        elif days_old > 730:  # Older than 2 years
            confidence *= 0.8
    
    return round(confidence, 2)


def _format_match_source(match_method: str) -> str:
    """Format match source for display"""
    source_map = {
        'content': 'Document content',
        'filename': 'Filename keywords',
        'keywords': 'Document section/keywords'
    }
    return source_map.get(match_method, match_method)


def _generate_screening_summary(recommendations: List[Dict], documents: List) -> Dict[str, Any]:
    """Generate summary statistics for screening recommendations"""
    total_screenings = len(recommendations)
    matched_screenings = len([r for r in recommendations if r['document_matches']])
    high_confidence = len([r for r in recommendations if r['match_confidence'] >= 0.8])
    medium_confidence = len([r for r in recommendations if 0.6 <= r['match_confidence'] < 0.8])
    low_confidence = len([r for r in recommendations if 0.3 <= r['match_confidence'] < 0.6])
    
    return {
        'total_screenings_analyzed': total_screenings,
        'screenings_with_matches': matched_screenings,
        'match_percentage': round((matched_screenings / total_screenings * 100) if total_screenings > 0 else 0, 1),
        'high_confidence_matches': high_confidence,
        'medium_confidence_matches': medium_confidence,
        'low_confidence_matches': low_confidence,
        'total_documents_analyzed': len(documents),
        'average_confidence': round(
            sum([r['match_confidence'] for r in recommendations if r['match_confidence'] > 0]) / 
            max(matched_screenings, 1), 2
        ) if matched_screenings > 0 else 0.0
    }


def _empty_screening_recommendations_response(error_message: str) -> Dict[str, Any]:
    """Return empty response structure for error cases"""
    return {
        'patient_id': None,
        'patient_name': None,
        'document_count': 0,
        'screening_recommendations': [],
        'document_matches': [],
        'summary': {
            'total_screenings_analyzed': 0,
            'screenings_with_matches': 0,
            'match_percentage': 0,
            'high_confidence_matches': 0,
            'medium_confidence_matches': 0,
            'low_confidence_matches': 0,
            'total_documents_analyzed': 0,
            'average_confidence': 0.0
        },
        'generation_metadata': {
            'generated_at': datetime.now().isoformat(),
            'method': 'document_screening_matcher',
            'error': error_message
        }
    }


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