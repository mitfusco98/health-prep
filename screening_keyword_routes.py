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
    """Get keyword configuration for a screening type - simplified to prevent duplication"""
    try:
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404
        
        # Get keywords from ALL keyword fields and combine them properly
        content_keywords = screening_type.get_content_keywords() or []
        document_keywords = screening_type.get_document_keywords() or []
        filename_keywords = screening_type.get_filename_keywords() or []
        
        # Combine all keywords and ensure uniqueness
        all_keywords = []
        all_keywords.extend(content_keywords)
        all_keywords.extend(document_keywords)
        all_keywords.extend(filename_keywords)
        
        # Process to ensure clean unique strings
        unique_keywords = []
        seen_lower = set()
        
        for keyword in all_keywords:
            if keyword and isinstance(keyword, str):
                clean_keyword = keyword.strip()
                if clean_keyword and clean_keyword.lower() not in seen_lower:
                    unique_keywords.append(clean_keyword)
                    seen_lower.add(clean_keyword.lower())
        
        # Debug logging
        print(f"DEBUG: Screening {screening_id} - Content: {len(content_keywords)}, Document: {len(document_keywords)}, Filename: {len(filename_keywords)}, Final unique: {len(unique_keywords)}")
        
        return jsonify({
            'success': True,
            'keywords': unique_keywords,
            'screening_name': screening_type.name
        })

    except Exception as e:
        print(f"ERROR in get_screening_keywords: {str(e)}")
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
        
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404
        
        # Get keywords from request and convert to simple strings
        keywords = data.get('keywords', [])
        keyword_list = []
        
        for keyword in keywords:
            if isinstance(keyword, dict):
                keyword_text = keyword.get('keyword', '')
            else:
                keyword_text = str(keyword)
            
            clean_keyword = keyword_text.strip()
            if clean_keyword:
                keyword_list.append(clean_keyword)
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in keyword_list:
            if keyword.lower() not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword.lower())
        
        # Save only to content_keywords
        screening_type.set_content_keywords(unique_keywords)
        
        # Clear other keyword fields to prevent any legacy duplication
        screening_type.set_filename_keywords([])
        screening_type.set_document_keywords([])
        
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