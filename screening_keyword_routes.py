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
        manager = ScreeningKeywordManager()
        config = manager.get_keyword_config(screening_id)

        if config:
            keywords = [rule.to_dict() for rule in config.keyword_rules]
            return jsonify({
                'success': True,
                'keywords': keywords,
                'screening_name': config.screening_name,
                'fallback_enabled': config.fallback_enabled,
                'confidence_threshold': config.confidence_threshold
            })
        else:
            return jsonify({
                'success': True,
                'keywords': [],
                'screening_name': '',
                'fallback_enabled': True,
                'confidence_threshold': 0.3
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
        keywords = data.get('keywords', [])

        # Validate screening type exists
        screening_type = ScreeningType.query.get(screening_id)
        if not screening_type:
            return jsonify({
                'success': False,
                'message': 'Screening type not found'
            }), 404

        manager = ScreeningKeywordManager()

        # Clear existing keywords
        config = manager.get_keyword_config(screening_id)
        if config:
            config.keyword_rules = []

        # Add new keywords
        success_count = 0
        for keyword_data in keywords:
            try:
                success = manager.add_keyword_rule(
                    screening_type_id=screening_id,
                    keyword=keyword_data.get('keyword', ''),
                    section=keyword_data.get('section', 'general'),
                    weight=keyword_data.get('weight', 1.0),
                    case_sensitive=keyword_data.get('case_sensitive', False),
                    exact_match=keyword_data.get('exact_match', False),
                    description=keyword_data.get('description', '')
                )
                if success:
                    success_count += 1
            except Exception as e:
                print(f"Error adding keyword {keyword_data.get('keyword')}: {str(e)}")
                continue

        return jsonify({
            'success': True,
            'message': f'Successfully saved {success_count} keywords',
            'keywords_saved': success_count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/<int:screening_id>/suggestions/<section>', methods=['GET'])
def get_keyword_suggestions(screening_id, section):
    """Get keyword suggestions for a specific section"""
    try:
        manager = ScreeningKeywordManager()
        suggestions = manager.suggest_keywords_for_section(section)

        return jsonify({
            'success': True,
            'section': section,
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/screening-keywords/<int:screening_id>/test', methods=['POST'])
def test_keyword_matching(screening_id):
    """Test keyword matching against a sample document"""
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        content = data.get('content', '')
        section = data.get('section', 'general')

        manager = ScreeningKeywordManager()
        matches = manager.match_document_with_keywords(filename, content, section)

        # Filter to only show matches for this screening type
        screening_matches = [
            match for match in matches 
            if match['screening_type_id'] == screening_id
        ]

        return jsonify({
            'success': True,
            'matches': screening_matches,
            'total_matches': len(matches)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500