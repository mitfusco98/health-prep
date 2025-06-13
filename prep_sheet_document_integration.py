"""
Prep Sheet Document Integration
Integrates the document-screening matching system into prep sheet generation
"""

import json
from typing import Dict, List, Any
from datetime import datetime

from document_screening_matcher import DocumentScreeningMatcher, generate_prep_sheet_screening_recommendations
from fhir_document_section_mapper import DocumentSectionMapper


def enhance_prep_sheet_with_document_matching(patient_id: int, existing_prep_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Enhance prep sheet with intelligent document-to-screening matching
    
    Args:
        patient_id: Patient ID
        existing_prep_data: Existing prep sheet data to enhance
        
    Returns:
        Enhanced prep sheet data with document-based screening recommendations
    """
    if existing_prep_data is None:
        existing_prep_data = {}
    
    # Generate document-based screening recommendations
    document_recommendations = generate_prep_sheet_screening_recommendations(
        patient_id, 
        enable_ai_fuzzy=True
    )
    
    # Add document matching results to prep sheet
    existing_prep_data['document_based_screenings'] = {
        'enabled': True,
        'document_count': document_recommendations['document_count'],
        'recommendations': document_recommendations['screening_recommendations'],
        'document_matches': document_recommendations['document_matches'],
        'summary': document_recommendations['summary'],
        'confidence_analysis': _analyze_recommendation_confidence(document_recommendations),
        'generation_metadata': document_recommendations['generation_metadata']
    }
    
    # Merge with existing screening recommendations
    if 'screening_recommendations' not in existing_prep_data:
        existing_prep_data['screening_recommendations'] = []
    
    # Add high-confidence document-based recommendations to main list
    high_confidence_recs = [
        rec for rec in document_recommendations['screening_recommendations']
        if rec['confidence'] >= 0.8
    ]
    
    for rec in high_confidence_recs:
        prep_recommendation = {
            'type': 'document_based',
            'screening_name': rec['screening_name'],
            'confidence': rec['confidence'],
            'priority': rec['recommendation_priority'],
            'source': 'Document Analysis',
            'matched_codes': rec['matched_codes'],
            'matched_keywords': rec['matched_keywords'],
            'supporting_documents': rec['total_document_matches'],
            'match_sources': rec['match_sources']
        }
        existing_prep_data['screening_recommendations'].append(prep_recommendation)
    
    return existing_prep_data


def _analyze_recommendation_confidence(recommendations: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze confidence distribution and patterns"""
    recs = recommendations['screening_recommendations']
    
    if not recs:
        return {'analysis': 'No recommendations to analyze'}
    
    # Confidence distribution
    confidence_scores = [rec['confidence'] for rec in recs]
    avg_confidence = sum(confidence_scores) / len(confidence_scores)
    max_confidence = max(confidence_scores)
    min_confidence = min(confidence_scores)
    
    # Source analysis
    source_counts = {}
    for rec in recs:
        for source in rec['match_sources']:
            source_counts[source] = source_counts.get(source, 0) + 1
    
    return {
        'average_confidence': avg_confidence,
        'max_confidence': max_confidence, 
        'min_confidence': min_confidence,
        'confidence_range': max_confidence - min_confidence,
        'source_distribution': source_counts,
        'high_confidence_count': sum(1 for score in confidence_scores if score >= 0.8),
        'reliable_recommendations': avg_confidence >= 0.6
    }


def generate_document_matching_summary(patient_id: int) -> Dict[str, Any]:
    """
    Generate a comprehensive summary of document matching results for display
    
    Args:
        patient_id: Patient ID
        
    Returns:
        Summary data for prep sheet display
    """
    recommendations = generate_prep_sheet_screening_recommendations(patient_id, enable_ai_fuzzy=True)
    
    if recommendations['document_count'] == 0:
        return {
            'status': 'no_documents',
            'message': 'No documents available for analysis',
            'recommendations': []
        }
    
    if recommendations['summary']['total_matches'] == 0:
        return {
            'status': 'no_matches',
            'message': f"Analyzed {recommendations['document_count']} documents but found no screening matches",
            'recommendations': []
        }
    
    # Create formatted summary
    formatted_recommendations = []
    
    for rec in recommendations['screening_recommendations']:
        # Determine match quality
        if rec['confidence'] >= 0.8:
            quality = 'high'
            quality_desc = 'Strong match'
        elif rec['confidence'] >= 0.5:
            quality = 'medium' 
            quality_desc = 'Good match'
        else:
            quality = 'low'
            quality_desc = 'Possible match'
        
        # Format match sources
        source_descriptions = {
            'fhir_code': 'Medical codes (LOINC/CPT/SNOMED)',
            'filename_keyword': 'Document keywords',
            'user_keyword': 'User-defined terms',
            'ai_fuzzy': 'AI pattern matching'
        }
        
        formatted_sources = [
            source_descriptions.get(source, source) 
            for source in rec['match_sources']
        ]
        
        formatted_recommendations.append({
            'screening_name': rec['screening_name'],
            'confidence': rec['confidence'],
            'confidence_percent': int(rec['confidence'] * 100),
            'quality': quality,
            'quality_description': quality_desc,
            'priority': rec['recommendation_priority'],
            'matched_documents': rec['total_document_matches'],
            'match_sources': formatted_sources,
            'evidence': {
                'codes': rec['matched_codes'][:3],  # Show first 3 codes
                'keywords': rec['matched_keywords'][:5],  # Show first 5 keywords
                'has_more_codes': len(rec['matched_codes']) > 3,
                'has_more_keywords': len(rec['matched_keywords']) > 5
            }
        })
    
    return {
        'status': 'success',
        'document_count': recommendations['document_count'],
        'total_matches': recommendations['summary']['total_matches'],
        'unique_screenings': recommendations['summary']['unique_screenings'],
        'recommendations': formatted_recommendations,
        'analysis_summary': f"Found {recommendations['summary']['unique_screenings']} relevant screenings from {recommendations['document_count']} documents"
    }


# Example integration with existing prep sheet generation
def example_prep_sheet_integration():
    """Example of how to integrate document matching into existing prep sheet workflow"""
    
    # This would be called from your existing prep sheet generation code
    def generate_enhanced_prep_sheet(patient_id: int):
        # Your existing prep sheet logic here
        prep_data = {
            'patient_id': patient_id,
            'generated_at': datetime.now().isoformat(),
            # ... other existing prep sheet data
        }
        
        # Enhance with document-based recommendations
        enhanced_prep_data = enhance_prep_sheet_with_document_matching(patient_id, prep_data)
        
        # Add document matching summary for display
        document_summary = generate_document_matching_summary(patient_id)
        enhanced_prep_data['document_analysis'] = document_summary
        
        return enhanced_prep_data


# Template data structure for prep sheet display
PREP_SHEET_TEMPLATE_DATA = {
    'document_based_screenings': {
        'enabled': True,
        'document_count': 4,
        'recommendations': [
            {
                'screening_type_id': 1,
                'screening_name': 'Diabetes Management',
                'confidence': 0.85,
                'confidence_percent': 85,
                'recommendation_priority': 'high',
                'total_document_matches': 2,
                'match_sources': ['Medical codes (LOINC/CPT/SNOMED)', 'Document keywords'],
                'matched_codes': ['4548-4', '33747-0'],
                'matched_keywords': ['glucose', 'hba1c', 'diabetes']
            }
        ],
        'summary': {
            'total_matches': 3,
            'unique_screenings': 2,
            'high_confidence_count': 1,
            'medium_confidence_count': 1,
            'low_confidence_count': 0
        },
        'confidence_analysis': {
            'average_confidence': 0.75,
            'reliable_recommendations': True,
            'source_distribution': {
                'fhir_code': 1,
                'filename_keyword': 2,
                'user_keyword': 1
            }
        }
    },
    'document_analysis': {
        'status': 'success',
        'document_count': 4,
        'analysis_summary': 'Found 2 relevant screenings from 4 documents',
        'recommendations': [
            {
                'screening_name': 'Diabetes Management',
                'confidence_percent': 85,
                'quality': 'high',
                'quality_description': 'Strong match',
                'matched_documents': 2,
                'evidence': {
                    'codes': ['4548-4', '33747-0'],
                    'keywords': ['glucose', 'hba1c', 'diabetes'],
                    'has_more_codes': False,
                    'has_more_keywords': True
                }
            }
        ]
    }
}