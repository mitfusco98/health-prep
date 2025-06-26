"""
API Routes for Screening Keyword Management
Handles loading and saving user-defined keywords for screening types
"""

from flask import request, jsonify
from app import app, db
from models import ScreeningType
from screening_keyword_manager import ScreeningKeywordManager
import json


@app.route('/api/screening-keywords/<int:screening_id>', methods=['GET'])
def get_screening_keywords(screening_id):
    """Get keyword configuration for a screening type - uses only current manage screening types system"""
    try:
        # Get screening type from current system only
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404
        
        # Get keywords from current ScreeningType fields only
        keywords = []
        
        # Get keywords from filename_keywords field
        filename_keywords = screening_type.get_filename_keywords()
        if filename_keywords:
            keywords.extend(filename_keywords)
        
        # Get keywords from content_keywords field
        content_keywords = screening_type.get_content_keywords()
        if content_keywords:
            keywords.extend(content_keywords)
        
        # Get keywords from document_keywords field
        document_keywords = screening_type.get_document_keywords()
        if document_keywords:
            keywords.extend(document_keywords)
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in keywords:
            if keyword.lower() not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword.lower())
        
        return jsonify({
            'success': True,
            'keywords': unique_keywords,
            'screening_name': screening_type.name,
            'source': 'manage_screening_types'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/<int:screening_id>', methods=['POST'])
def save_screening_keywords(screening_id):
    """Save keyword configuration - redirects to manage screening types system"""
    return jsonify({
        'success': False,
        'message': 'Keyword editing should be done through the manage screening types interface at /screenings?tab=types',
        'redirect_url': '/screenings?tab=types'
    }), 400


@app.route('/api/screening-keywords/<int:screening_id>/suggestions/<section>', methods=['GET'])
def get_keyword_suggestions(screening_id, section):
    """Keyword suggestions - redirect to manage screening types"""
    return jsonify({
        'success': False,
        'message': 'Keyword management should be done through the manage screening types interface',
        'redirect_url': '/screenings?tab=types'
    }), 400


@app.route('/api/screening-keywords/<int:screening_id>/test', methods=['POST'])
def test_keyword_matching(screening_id):
    """Test keyword matching using current screening types system"""
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        content = data.get('content', '')
        
        # Get screening type
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404
        
        # Test matching using DocumentScreeningMatcher
        from document_screening_matcher import DocumentScreeningMatcher
        from models import Patient, MedicalDocument
        
        # Create a test document object
        test_doc = type('TestDoc', (), {
            'id': 999,
            'filename': filename,
            'content': content,
            'extracted_text': content,
            'document_type': None
        })()
        
        # Create a test patient (for demographic matching)
        test_patient = type('TestPatient', (), {
            'id': 999,
            'age': 50,
            'sex': 'M'
        })()
        
        matcher = DocumentScreeningMatcher()
        result = matcher.match_document_to_screening(screening_type, test_doc, test_patient)
        
        return jsonify({
            'success': True,
            'match_result': result,
            'screening_name': screening_type.name
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500