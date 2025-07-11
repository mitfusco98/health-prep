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
    """Get keyword configuration for a screening type"""
    try:
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404

        # Get keywords from content_keywords field or return empty list
        keywords = []
        if hasattr(screening_type, 'content_keywords') and screening_type.content_keywords:
            try:
                import json
                keywords = json.loads(screening_type.content_keywords) if isinstance(screening_type.content_keywords, str) else screening_type.content_keywords
            except (json.JSONDecodeError, TypeError):
                keywords = []

        return jsonify({
            'success': True,
            'keywords': keywords,
            'screening_name': screening_type.name,
            'source': 'screening_type_model'
        })

    except Exception as e:
        db.session.rollback()  # Explicitly rollback on error
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/<int:screening_id>', methods=['POST'])
def save_screening_keywords(screening_id):
    """Save keyword configuration for a screening type"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        # Get screening type
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404

        # Get keywords from request
        keywords = data.get('keywords', [])

        # Convert keywords to simple list if they're objects
        keyword_list = []
        for keyword in keywords:
            if isinstance(keyword, dict):
                keyword_list.append(keyword.get('keyword', ''))
            else:
                keyword_list.append(str(keyword))

        # Remove empty keywords
        keyword_list = [k.strip() for k in keyword_list if k.strip()]

        # Save to all keyword fields (this ensures compatibility)
        screening_type.set_content_keywords(keyword_list)
        screening_type.set_filename_keywords(keyword_list)
        screening_type.set_document_keywords(keyword_list)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Keywords saved successfully',
            'keywords': keyword_list
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/<int:screening_id>/suggestions/<section>', methods=['GET'])
def get_keyword_suggestions(screening_id, section):
    """Get keyword suggestions for a section"""
    try:
        # Define common keywords by section
        suggestions = {
            'labs': ['glucose', 'cholesterol', 'hemoglobin', 'hba1c', 'creatinine', 'blood test', 'lab result'],
            'imaging': ['mammogram', 'x-ray', 'ct scan', 'mri', 'ultrasound', 'radiology', 'scan'],
            'procedures': ['colonoscopy', 'biopsy', 'endoscopy', 'surgery', 'procedure'],
            'vitals': ['blood pressure', 'heart rate', 'weight', 'height', 'temperature', 'vital signs'],
            'consults': ['cardiology', 'oncology', 'neurology', 'specialist', 'consultation'],
            'medications': ['insulin', 'metformin', 'lisinopril', 'medication', 'prescription'],
            'general': ['screening', 'test', 'result', 'report', 'medical']
        }

        return jsonify({
            'success': True,
            'suggestions': suggestions.get(section, [])
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


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