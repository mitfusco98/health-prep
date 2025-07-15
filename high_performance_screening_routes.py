#!/usr/bin/env python3
"""
High-Performance Screening Routes
Integrates the high-performance bulk screening engine with Flask routes
Provides timeout-resistant, high-speed bulk processing endpoints
"""

import logging
import time
from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from datetime import datetime

from high_performance_bulk_screening_engine import (
    process_all_patients_sync, 
    get_bulk_engine,
    trigger_reactive_update_sync
)
from reactive_trigger_middleware import reactive_trigger_manager

logger = logging.getLogger(__name__)

# Create blueprint for high-performance routes
hp_screening_bp = Blueprint('hp_screening', __name__)

@hp_screening_bp.route('/api/bulk-screening/process', methods=['POST'])
def api_bulk_process_screenings():
    """
    API endpoint for high-performance bulk screening processing
    
    POST data:
    - trigger_source: Optional source description
    - max_patients: Optional limit on number of patients to process
    - force: Optional flag to force processing even if load is high
    
    Returns:
    - JSON with processing results and metrics
    """
    try:
        data = request.get_json() or {}
        trigger_source = data.get('trigger_source', 'api_request')
        max_patients = data.get('max_patients')
        force = data.get('force', False)
        
        logger.info(f"🚀 API bulk processing request - source: {trigger_source}")
        
        # Check system load unless forced
        if not force:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > 80 or memory_percent > 85:
                return jsonify({
                    'success': False,
                    'error': 'System load too high for bulk processing',
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'suggestion': 'Try again later or use force=true'
                }), 503
        
        # Run bulk processing
        start_time = time.time()
        result = process_all_patients_sync(trigger_source)
        processing_time = time.time() - start_time
        
        # Add timing information
        result['api_processing_time'] = processing_time
        result['timestamp'] = datetime.now().isoformat()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ API bulk processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@hp_screening_bp.route('/api/bulk-screening/status', methods=['GET'])
def api_bulk_processing_status():
    """
    Get status of bulk processing engine
    
    Returns:
    - JSON with engine status and performance metrics
    """
    try:
        import psutil
        import asyncio
        
        # Get system metrics
        system_metrics = {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
        
        # Try to get engine status (this requires async context)
        engine_status = {
            'initialized': False,
            'processing_active': False,
            'connection_pool_size': 0,
            'circuit_breaker_trips': 0
        }
        
        try:
            # This is a simplified status check
            # In a real implementation, you'd want to expose more engine metrics
            engine_status['initialized'] = True
        except Exception as e:
            logger.warning(f"Could not get detailed engine status: {e}")
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'system_metrics': system_metrics,
            'engine_status': engine_status,
            'reactive_triggers_enabled': reactive_trigger_manager.enabled
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@hp_screening_bp.route('/api/reactive-trigger', methods=['POST'])
def api_reactive_trigger():
    """
    API endpoint for manual reactive triggers
    
    POST data:
    - trigger_type: Type of trigger (document_upload, screening_type_activation, etc.)
    - context: Context data for the trigger
    
    Returns:
    - JSON with trigger result
    """
    try:
        data = request.get_json() or {}
        trigger_type = data.get('trigger_type')
        context = data.get('context', {})
        
        if not trigger_type:
            return jsonify({
                'success': False,
                'error': 'trigger_type is required'
            }), 400
            
        # Add timestamp to context
        context['timestamp'] = datetime.now().isoformat()
        context['source'] = 'api_manual'
        
        logger.info(f"🔄 Manual reactive trigger: {trigger_type}")
        
        # Process trigger
        success = trigger_reactive_update_sync(trigger_type, context)
        
        return jsonify({
            'success': success,
            'trigger_type': trigger_type,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }), 200 if success else 500
        
    except Exception as e:
        logger.error(f"❌ Reactive trigger error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@hp_screening_bp.route('/admin/bulk-screening-dashboard')
def admin_bulk_screening_dashboard():
    """
    Admin dashboard for monitoring bulk screening operations
    """
    try:
        import psutil
        
        # Get system metrics
        system_info = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
        }
        
        # Get recent processing metrics (this would come from engine logs in real implementation)
        recent_metrics = {
            'last_bulk_run': 'Never',
            'total_patients_processed': 0,
            'average_processing_time': 0,
            'circuit_breaker_trips': 0,
            'reactive_triggers_today': 0
        }
        
        return render_template('admin/bulk_screening_dashboard.html',
            system_info=system_info,
            recent_metrics=recent_metrics,
            reactive_triggers_enabled=reactive_trigger_manager.enabled
        )
        
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")
        flash(f"Error loading dashboard: {e}", "error")
        return redirect(url_for('admin_dashboard'))

def integrate_high_performance_routes(app):
    """
    Integrate high-performance screening routes with the main Flask app
    
    Args:
        app: Flask application instance
    """
    
    # Register the blueprint
    app.register_blueprint(hp_screening_bp)
    
    # Replace the existing bulk refresh route with high-performance version
    @app.route('/screenings/bulk-refresh', methods=['POST'])
    def high_performance_bulk_refresh():
        """
        High-performance replacement for the existing bulk refresh functionality
        Uses the new bulk screening engine instead of the old timeout-prone approach
        """
        try:
            trigger_source = request.form.get('trigger_source', 'manual_web_refresh')
            tab = request.args.get('tab', 'screenings')
            search_query = request.args.get('search', '')
            
            logger.info(f"🚀 High-performance bulk refresh triggered from web interface")
            
            # Check if system is under load
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            if cpu_percent > 85:
                flash("System is currently under high load. Please try again in a few minutes.", "warning")
                redirect_params = {'tab': tab}
                if search_query:
                    redirect_params['search'] = search_query
                return redirect(url_for('screening_list', **redirect_params))
            
            # Run high-performance bulk processing
            start_time = time.time()
            result = process_all_patients_sync(trigger_source)
            processing_time = time.time() - start_time
            
            if result['success']:
                # Create success message with metrics
                success_msg = (
                    f"High-performance refresh completed! "
                    f"Processed {result['processed_patients']}/{result['total_patients']} patients "
                    f"({result['total_screenings_updated']} screenings, "
                    f"{result['total_documents_linked']} document links) "
                    f"in {processing_time:.1f} seconds"
                )
                
                if result['circuit_breaker_trips'] > 0:
                    success_msg += f" (⚡ {result['circuit_breaker_trips']} patients skipped due to issues)"
                    
                flash(success_msg, "success")
            else:
                flash(f"Bulk refresh encountered errors: {result.get('error', 'Unknown error')}", "error")
            
            # Redirect back to remove parameters from URL
            redirect_params = {'tab': tab}
            if search_query:
                redirect_params['search'] = search_query
            return redirect(url_for('screening_list', **redirect_params))
            
        except Exception as e:
            logger.error(f"❌ High-performance bulk refresh error: {e}")
            flash("Bulk refresh system error. Please contact administrator.", "error")
            return redirect(url_for('screening_list'))
    
    logger.info("✅ High-performance screening routes integrated")

# Enhanced refresh function that replaces the problematic demo_routes refresh
def enhanced_screening_refresh(tab='screenings', search_query='', trigger_source='manual_refresh'):
    """
    Enhanced screening refresh that uses the high-performance engine
    This replaces the timeout-prone refresh logic in demo_routes.py
    
    Args:
        tab: Current tab being refreshed
        search_query: Current search query
        trigger_source: What triggered the refresh
        
    Returns:
        Tuple of (success: bool, message: str, metrics: dict)
    """
    try:
        logger.info(f"🔄 Enhanced refresh for tab '{tab}' - source: {trigger_source}")
        
        # Use high-performance bulk processing
        result = process_all_patients_sync(trigger_source)
        
        if result['success']:
            # Create detailed success message based on tab
            if tab == 'types':
                message = (
                    f"Successfully refreshed {result['total_screenings_updated']} screenings "
                    f"for {result['processed_patients']} patients using latest parsing rules "
                    f"from screening types (linked {result['total_documents_linked']} documents)"
                )
            elif tab == 'checklist':
                message = (
                    f"Successfully refreshed {result['total_screenings_updated']} screenings "
                    f"for {result['processed_patients']} patients using current prep sheet settings "
                    f"(linked {result['total_documents_linked']} documents)"
                )
            else:
                message = (
                    f"Successfully refreshed {result['total_screenings_updated']} screenings "
                    f"for {result['processed_patients']} patients based on current parsing logic "
                    f"(linked {result['total_documents_linked']} documents)"
                )
                
            if result['circuit_breaker_trips'] > 0:
                message += f" (⚡ {result['circuit_breaker_trips']} problematic patients skipped)"
                
            return True, message, result
        else:
            return False, f"Refresh failed: {result.get('error', 'Unknown error')}", result
            
    except Exception as e:
        logger.error(f"❌ Enhanced refresh error: {e}")
        return False, f"System error during refresh: {str(e)}", {}

if __name__ == "__main__":
    # Test the high-performance routes
    from flask import Flask
    
    app = Flask(__name__)
    integrate_high_performance_routes(app)
    
    print("High-performance screening routes ready for testing")