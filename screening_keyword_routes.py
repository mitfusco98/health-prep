"""
The code caches API responses to prevent duplicate requests and clears old cache entries to manage memory usage.
"""
from flask import request, jsonify
from app import app, db
from models import ScreeningType
from screening_keyword_manager import ScreeningKeywordManager
import json
import time

# Initialize a simple cache
_request_cache = {}
_cache_timeout = 60  # Cache timeout in seconds


@app.route('/api/screening-keywords/<int:screening_id>', methods=['GET'])
def get_screening_keywords(screening_id):
    """Get keyword configuration for a screening type - simplified to prevent duplication"""
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

    try:
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404

        # Get ONLY unified keywords - completely ignore legacy fields
        unified_keywords = screening_type.get_unified_keywords() or []
        
        # Defensive check: if unified_keywords is somehow still pulling legacy data, force empty
        if not isinstance(unified_keywords, list):
            unified_keywords = []
        
        # Use ONLY unified keywords - absolutely no legacy field access
        all_keywords = unified_keywords

        # Process to ensure clean unique strings with multiple deduplication passes
        unique_keywords = []
        seen_lower = set()

        # First pass: clean and deduplicate by exact match - use all_keywords instead of content_keywords
        cleaned_keywords = []
        for keyword in all_keywords:
            if keyword and isinstance(keyword, str):
                clean_keyword = keyword.strip()
                if clean_keyword and clean_keyword not in cleaned_keywords:
                    cleaned_keywords.append(clean_keyword)

        # Second pass: deduplicate by lowercase to catch case variations
        for keyword in cleaned_keywords:
            if keyword.lower() not in seen_lower:
                unique_keywords.append(keyword)
                seen_lower.add(keyword.lower())

        # Debug logging
        print(f"DEBUG: Screening {screening_id} - All keywords: {len(all_keywords)}, Final unique: {len(unique_keywords)}")

        result = jsonify({
            'success': True,
            'keywords': unique_keywords,
            'screening_name': screening_type.name
        })

        # Cache the result
        _request_cache[cache_key] = (result, current_time)

        # Clean old cache entries
        keys_to_remove = []
        for key, (_, timestamp) in _request_cache.items():
            if current_time - timestamp > _cache_timeout:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del _request_cache[key]

        return result

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

        # Save to unified_keywords field (applies to both content and filenames)
        screening_type.set_unified_keywords(unique_keywords)

        # Clear legacy keyword fields to prevent duplication
        screening_type.set_content_keywords([])
        screening_type.set_filename_keywords([])
        screening_type.set_document_keywords([])

        db.session.commit()

        # Clear cache when keywords are saved
        cache_key = f"screening_keywords_{screening_id}"
        if cache_key in _request_cache:
            del _request_cache[cache_key]
            print(f"DEBUG: Cleared cache for screening keywords {screening_id} after save.")
        
        # Also clear any other cached entries that might be stale
        keys_to_clear = [key for key in _request_cache.keys() if key.startswith('screening_keywords_')]
        for key in keys_to_clear:
            if key != cache_key:  # Don't double-clear the same key
                del _request_cache[key]
        
        if keys_to_clear:
            print(f"DEBUG: Cleared {len(keys_to_clear)} cached keyword entries to prevent stale data.")

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


@app.route('/api/screening-keywords/bulk', methods=['GET'])
def get_all_screening_keywords():
    """Get keywords for all active screening types in a single request"""
    try:
        # Get all active screening types
        screening_types = ScreeningType.query.filter_by(is_active=True).all()

        bulk_data = {}
        for screening_type in screening_types:
            # Get ONLY content keywords - this is the single source of truth
            content_keywords = screening_type.get_content_keywords() or []

            # Ensure we're working with clean data from the start
            if not content_keywords or not isinstance(content_keywords, list):
                unique_keywords = []
            else:
                # Single-pass deduplication with strict validation
                unique_keywords = []
                seen_keywords = set()

                for keyword in content_keywords:
                    # Only process valid string keywords
                    if keyword and isinstance(keyword, str):
                        clean_keyword = keyword.strip()

                        # Skip empty strings and duplicates (case-insensitive)
                        if clean_keyword and clean_keyword.lower() not in seen_keywords:
                            unique_keywords.append(clean_keyword)
                            seen_keywords.add(clean_keyword.lower())

            # Debug logging
            print(f"DEBUG: Screening {screening_type.id} - Raw content: {len(content_keywords)}, Final unique: {len(unique_keywords)}")

            # Additional validation - ensure no duplicates escaped
            final_check = len(unique_keywords) == len(set(k.lower() for k in unique_keywords))
            if not final_check:
                print(f"WARNING: Duplicate keywords detected in final result for screening {screening_type.id}")
                # Emergency deduplication
                temp_seen = set()
                temp_unique = []
                for k in unique_keywords:
                    if k.lower() not in temp_seen:
                        temp_unique.append(k)
                        temp_seen.add(k.lower())
                unique_keywords = temp_unique

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