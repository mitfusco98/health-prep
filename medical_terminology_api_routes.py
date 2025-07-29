"""
Medical Terminology API Routes
Provides REST endpoints for standardized medical terminology,
autocomplete suggestions, and validation.
"""

from flask import Blueprint, request, jsonify
from medical_terminology_standardizer import medical_standardizer
import logging

# Import CSRF protection for exemptions
try:
    from flask_wtf.csrf import CSRFProtect, exempt
    csrf_exempt = exempt
except ImportError:
    # Fallback if CSRF is not available
    def csrf_exempt(f):
        return f

# Create blueprint for medical terminology API
terminology_api = Blueprint('terminology_api', __name__, url_prefix='/api/terminology')

@terminology_api.route('/screening/suggestions', methods=['GET'])
def get_screening_suggestions():
    """Get autocomplete suggestions for screening type names"""
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 suggestions
        
        if not query or len(query) < 2:
            return jsonify({'suggestions': []})
        
        suggestions = medical_standardizer.get_screening_suggestions(query, limit)
        
        return jsonify({
            'suggestions': suggestions,
            'query': query,
            'count': len(suggestions)
        })
        
    except Exception as e:
        logging.error(f"Error getting screening suggestions: {e}")
        return jsonify({'error': 'Failed to get suggestions'}), 500

@terminology_api.route('/condition/suggestions', methods=['GET'])
def get_condition_suggestions():
    """Get autocomplete suggestions for medical condition names"""
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)
        
        if not query or len(query) < 2:
            return jsonify({'suggestions': []})
        
        suggestions = medical_standardizer.get_condition_suggestions(query, limit)
        
        return jsonify({
            'suggestions': suggestions,
            'query': query,
            'count': len(suggestions)
        })
        
    except Exception as e:
        logging.error(f"Error getting condition suggestions: {e}")
        return jsonify({'error': 'Failed to get suggestions'}), 500

@terminology_api.route('/screening/validate', methods=['POST'])
@csrf_exempt  # Exempt from CSRF since this is an AJAX API endpoint
def validate_screening_input():
    """Validate screening type input and provide suggestions"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name', '')
        trigger_conditions = data.get('trigger_conditions', [])
        
        validation_result = medical_standardizer.validate_screening_input(name, trigger_conditions)
        
        return jsonify(validation_result)
        
    except Exception as e:
        logging.error(f"Error validating screening input: {e}")
        return jsonify({'error': 'Validation failed'}), 500

@terminology_api.route('/screening/normalize', methods=['POST'])
def normalize_screening_name():
    """Normalize a screening name to its canonical form"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name', '')
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        canonical_name, confidence = medical_standardizer.normalize_screening_name(name)
        
        return jsonify({
            'original': name,
            'canonical': canonical_name,
            'confidence': confidence,
            'normalized': confidence >= 0.8
        })
        
    except Exception as e:
        logging.error(f"Error normalizing screening name: {e}")
        return jsonify({'error': 'Normalization failed'}), 500

@terminology_api.route('/condition/normalize', methods=['POST'])
def normalize_condition_name():
    """Normalize a condition name to its canonical form"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name', '')
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        canonical_name, confidence = medical_standardizer.normalize_condition_name(name)
        
        return jsonify({
            'original': name,
            'canonical': canonical_name,
            'confidence': confidence,
            'normalized': confidence >= 0.7
        })
        
    except Exception as e:
        logging.error(f"Error normalizing condition name: {e}")
        return jsonify({'error': 'Normalization failed'}), 500

@terminology_api.route('/screening/variants', methods=['GET'])
def get_screening_variants():
    """Get all variants of a screening type"""
    try:
        name = request.args.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Name parameter is required'}), 400
        
        variants = medical_standardizer.detect_variants(name)
        
        return jsonify({
            'base_name': name,
            'variants': variants,
            'count': len(variants)
        })
        
    except Exception as e:
        logging.error(f"Error getting screening variants: {e}")
        return jsonify({'error': 'Failed to get variants'}), 500

@terminology_api.route('/standards/screenings', methods=['GET'])
def get_screening_standards():
    """Get all standardized screening type definitions"""
    try:
        category = request.args.get('category', '').strip()
        
        standards = medical_standardizer.screening_standards
        
        if category:
            # Filter by category
            filtered = {k: v for k, v in standards.items() if v.get('category') == category}
            return jsonify({'standards': filtered, 'category': category})
        
        return jsonify({'standards': standards})
        
    except Exception as e:
        logging.error(f"Error getting screening standards: {e}")
        return jsonify({'error': 'Failed to get standards'}), 500

@terminology_api.route('/standards/conditions', methods=['GET'])
def get_condition_standards():
    """Get all standardized medical condition definitions"""
    try:
        category = request.args.get('category', '').strip()
        
        standards = medical_standardizer.condition_standards
        
        if category:
            # Filter by category
            filtered = {k: v for k, v in standards.items() if v.get('category') == category}
            return jsonify({'standards': filtered, 'category': category})
        
        return jsonify({'standards': standards})
        
    except Exception as e:
        logging.error(f"Error getting condition standards: {e}")
        return jsonify({'error': 'Failed to get standards'}), 500