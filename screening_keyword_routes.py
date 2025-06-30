"""
Screening Keyword Routes - Unified System Only
Handles keyword configuration using ONLY the unified_keywords field.
All legacy keyword fields have been removed.
"""
from flask import request, jsonify
from app import app, db
from models import ScreeningType
import time

# Simple cache for API responses
_request_cache = {}
_cache_timeout = 60


@app.route('/api/screening-keywords/<int:screening_id>', methods=['GET'])
def get_screening_keywords(screening_id):
    """Get keyword configuration for a screening type - unified system only"""
    cache_key = f"screening_keywords_{screening_id}"
    current_time = time.time()

    # Check cache first
    if cache_key in _request_cache:
        result, timestamp = _request_cache[cache_key]
        if current_time - timestamp <= _cache_timeout:
            print(f"DEBUG: Serving screening keywords {screening_id} from cache.")
            return result
        else:
            print(f"DEBUG: Cache expired for screening keywords {screening_id}.")
            del _request_cache[cache_key]

    try:
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404

        # Get ONLY unified keywords - no legacy field access
        unified_keywords = screening_type.get_unified_keywords() or []

        # Ensure we have a clean list
        if not isinstance(unified_keywords, list):
            unified_keywords = []

        # Clean and deduplicate keywords
        unique_keywords = []
        seen_lower = set()

        for keyword in unified_keywords:
            if keyword and isinstance(keyword, str):
                clean_keyword = keyword.strip()
                if clean_keyword and clean_keyword.lower() not in seen_lower:
                    unique_keywords.append(clean_keyword)
                    seen_lower.add(clean_keyword.lower())

        # Debug logging
        print(f"DEBUG: Screening {screening_id} - Unified keywords: {len(unified_keywords)}, Final unique: {len(unique_keywords)}")

        result = jsonify({
            'success': True,
            'keywords': unique_keywords,
            'screening_name': screening_type.name
        })

        # Cache the result
        _request_cache[cache_key] = (result, current_time)

        return result

    except Exception as e:
        print(f"ERROR in get_screening_keywords: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/<int:screening_id>', methods=['POST'])
def save_screening_keywords(screening_id):
    """Save keyword configuration for a screening type - unified system only"""
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

        # Get keywords from request
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

        # Save ONLY to unified_keywords field
        screening_type.set_unified_keywords(unique_keywords)

        # Ensure legacy fields are NULL (should already be cleared)
        screening_type.content_keywords = None
        screening_type.filename_keywords = None
        screening_type.document_keywords = None

        db.session.commit()

        # Clear cache
        cache_key = f"screening_keywords_{screening_id}"
        if cache_key in _request_cache:
            del _request_cache[cache_key]

        print(f"DEBUG: Saved {len(unique_keywords)} keywords for screening {screening_id}")

        return jsonify({
            'success': True,
            'message': 'Keywords saved successfully',
            'keywords': unique_keywords
        })

    except Exception as e:
        db.session.rollback()
        print(f"ERROR in save_screening_keywords: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/bulk', methods=['GET'])
def get_all_screening_keywords():
    """Get keywords for all active screening types - unified system only"""
    try:
        screening_types = ScreeningType.query.filter_by(is_active=True).all()

        bulk_data = {}
        for screening_type in screening_types:
            # Get ONLY unified keywords
            unified_keywords = screening_type.get_unified_keywords() or []

            # Clean and deduplicate
            unique_keywords = []
            seen_keywords = set()

            for keyword in unified_keywords:
                if keyword and isinstance(keyword, str):
                    clean_keyword = keyword.strip()
                    if clean_keyword and clean_keyword.lower() not in seen_keywords:
                        unique_keywords.append(clean_keyword)
                        seen_keywords.add(clean_keyword.lower())

            print(f"DEBUG: Screening {screening_type.id} - Unified: {len(unified_keywords)}, Final unique: {len(unique_keywords)}")

            bulk_data[screening_type.id] = {
                'keywords': unique_keywords,
                'screening_name': screening_type.name
            }

        return jsonify({
            'success': True,
            'data': bulk_data
        })

    except Exception as e:
        print(f"ERROR in get_all_screening_keywords: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/<int:screening_id>/test', methods=['POST'])
def test_keyword_matching(screening_id):
    """Test keyword matching using unified keywords only"""
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        content = data.get('content', '')

        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404

        # Test matching using DocumentScreeningMatcher
        from document_screening_matcher import DocumentScreeningMatcher

        # Create a test document object
        test_doc = type('TestDoc', (), {
            'id': 999,
            'filename': filename,
            'content': content,
            'extracted_text': content,
            'document_type': None
        })()

        # Create a test patient
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


# Clear all cache on module reload
def clear_all_cache():
    """Clear all cached keyword data"""
    global _request_cache
    _request_cache.clear()
    print("DEBUG: Cleared all keyword cache")
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