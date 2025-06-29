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
        # Force refresh the screening type from database to get latest data
        db.session.expire_all()
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404
        
        # Get keywords from current ScreeningType fields only - use content_keywords as primary source
        keywords = []
        
        try:
            # Use content_keywords as the primary source (most recently updated)
            content_keywords = screening_type.get_content_keywords() or []
            keywords.extend(content_keywords)
            
            # Only add from other sources if content_keywords is empty
            if not keywords:
                filename_keywords = screening_type.get_filename_keywords() or []
                keywords.extend(filename_keywords)
                
                if not keywords:
                    document_keywords = screening_type.get_document_keywords() or []
                    keywords.extend(document_keywords)
            
            # Remove duplicates while preserving order
            unique_keywords = []
            seen = set()
            for keyword in keywords:
                if keyword and keyword.strip() and keyword.lower() not in seen:
                    unique_keywords.append(keyword.strip())
                    seen.add(keyword.lower())
                    
        except Exception as e:
            print(f"Error getting keywords for screening {screening_id}: {e}")
            unique_keywords = []
        
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