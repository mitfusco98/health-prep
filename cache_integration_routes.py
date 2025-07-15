#!/usr/bin/env python3
"""
Cache Integration Routes
Provides admin and API endpoints for cache management
"""

import logging
from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from datetime import datetime
from typing import Dict, Any

from intelligent_cache_manager import get_cache_manager, warm_cache_on_startup

logger = logging.getLogger(__name__)

# Create blueprint for cache management routes
cache_integration_bp = Blueprint('cache_integration', __name__)

@cache_integration_bp.route('/admin/cache/stats', methods=['GET'])
def admin_cache_stats():
    """Admin endpoint to get cache statistics"""
    try:
        cache_mgr = get_cache_manager()
        stats = cache_mgr.get_stats()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'cache_stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Cache stats error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@cache_integration_bp.route('/admin/cache/clear', methods=['POST'])
def admin_cache_clear():
    """Admin endpoint to clear all cache"""
    try:
        cache_mgr = get_cache_manager()
        success = cache_mgr.clear_all()
        
        if success:
            flash("Cache cleared successfully", "success")
        else:
            flash("Failed to clear cache", "error")
            
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        logger.error(f"❌ Cache clear error: {e}")
        flash(f"Cache clear error: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

@cache_integration_bp.route('/admin/cache/warmup', methods=['POST'])
def admin_cache_warmup():
    """Admin endpoint to warm up cache"""
    try:
        success = warm_cache_on_startup()
        
        if success:
            flash("Cache warmed up successfully", "success")
        else:
            flash("Failed to warm up cache", "error")
            
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        logger.error(f"❌ Cache warmup error: {e}")
        flash(f"Cache warmup error: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

@cache_integration_bp.route('/admin/cache/invalidate-tag', methods=['POST'])
def admin_cache_invalidate_tag():
    """Admin endpoint to invalidate cache by tag"""
    try:
        tag = request.form.get('tag')
        if not tag:
            flash("Tag is required", "error")
            return redirect(url_for('admin_dashboard'))
            
        cache_mgr = get_cache_manager()
        count = cache_mgr.invalidate_by_tag(tag)
        
        flash(f"Invalidated {count} cache entries for tag '{tag}'", "success")
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        logger.error(f"❌ Cache tag invalidation error: {e}")
        flash(f"Cache invalidation error: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

@cache_integration_bp.route('/api/cache/trigger-invalidation', methods=['POST'])
def api_cache_trigger_invalidation():
    """API endpoint to trigger cache invalidation"""
    try:
        data = request.get_json() or {}
        trigger_type = data.get('trigger_type')
        context = data.get('context', {})
        
        if not trigger_type:
            return jsonify({
                'success': False,
                'error': 'trigger_type is required'
            }), 400
            
        cache_mgr = get_cache_manager()
        cache_mgr.trigger_invalidation(trigger_type, context)
        
        return jsonify({
            'success': True,
            'message': f'Cache invalidation triggered for {trigger_type}',
            'trigger_type': trigger_type,
            'context': context
        }), 200
        
    except Exception as e:
        logger.error(f"❌ API cache invalidation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cache_integration_bp.route('/api/cache/screening-types', methods=['GET'])
def api_cache_screening_types():
    """API endpoint to get cached screening types"""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        cache_mgr = get_cache_manager()
        screening_types = cache_mgr.cache_screening_types(active_only=active_only)
        
        return jsonify({
            'success': True,
            'screening_types': screening_types,
            'active_only': active_only,
            'count': len(screening_types)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ API screening types cache error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cache_integration_bp.route('/api/cache/patient-demographics/<int:patient_id>', methods=['GET'])
def api_cache_patient_demographics(patient_id: int):
    """API endpoint to get cached patient demographics"""
    try:
        cache_mgr = get_cache_manager()
        demographics = cache_mgr.cache_patient_demographics(patient_id)
        
        if demographics is None:
            return jsonify({
                'success': False,
                'error': 'Patient not found'
            }), 404
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'demographics': demographics
        }), 200
        
    except Exception as e:
        logger.error(f"❌ API patient demographics cache error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def integrate_cache_routes(app):
    """
    Integrate cache management routes with the main Flask app
    
    Args:
        app: Flask application instance
    """
    
    # Register the blueprint
    app.register_blueprint(cache_integration_bp)
    
    # Initialize cache integrations
    try:
        from intelligent_cache_manager import (
            integrate_cache_with_auto_refresh_manager,
            integrate_cache_with_reactive_triggers,
            warm_cache_on_startup
        )
        
        # Integrate with existing systems
        integrate_cache_with_auto_refresh_manager()
        integrate_cache_with_reactive_triggers()
        
        # Warm up cache on startup
        warm_cache_on_startup()
        
        logger.info("✅ Cache integration routes initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Cache integration initialization error: {e}")
    
    # Add cache invalidation to existing routes
    @app.before_request
    def cache_invalidation_middleware():
        """Middleware to handle cache invalidation on route changes"""
        cache_mgr = get_cache_manager()
        
        # Handle screening type changes
        if request.endpoint == 'screening_types' and request.method == 'POST':
            cache_mgr.trigger_invalidation('screening_type_status_change', {
                'change_type': 'status',
                'timestamp': datetime.now().isoformat()
            })
        
        # Handle document uploads
        elif request.endpoint == 'add_document' and request.method == 'POST':
            patient_id = request.form.get('patient_id')
            if patient_id:
                cache_mgr.trigger_invalidation('document_type_change', {
                    'patient_id': int(patient_id),
                    'action': 'upload',
                    'timestamp': datetime.now().isoformat()
                })
        
        # Handle patient demographic changes
        elif request.endpoint in ['edit_patient', 'add_patient'] and request.method == 'POST':
            patient_id = request.form.get('patient_id') or request.view_args.get('patient_id')
            if patient_id:
                cache_mgr.trigger_invalidation('patient_demographic_change', {
                    'patient_id': int(patient_id),
                    'action': 'update',
                    'timestamp': datetime.now().isoformat()
                })
    
    logger.info("✅ Cache integration routes integrated")

if __name__ == "__main__":
    # Test the cache integration routes
    from flask import Flask
    
    app = Flask(__name__)
    integrate_cache_routes(app)
    
    print("Cache integration routes ready for testing")