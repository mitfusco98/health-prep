#!/usr/bin/env python3
"""
Cache Reactive Triggers
Provides decorators and middleware for automatic cache invalidation
"""

import logging
from functools import wraps
from typing import Dict, Any, Optional
from flask import request, g
from datetime import datetime

from intelligent_cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

def cache_invalidation_trigger(trigger_type: str, context_extractor: callable = None):
    """
    Decorator to automatically trigger cache invalidation after route execution
    
    Args:
        trigger_type: Type of cache invalidation trigger
        context_extractor: Function to extract context from request/response
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            try:
                # Extract context for cache invalidation
                context = {}
                if context_extractor:
                    context = context_extractor(request, result, *args, **kwargs)
                
                # Add default context
                context.update({
                    'timestamp': datetime.now().isoformat(),
                    'endpoint': request.endpoint,
                    'method': request.method
                })
                
                # Trigger cache invalidation
                cache_mgr = get_cache_manager()
                cache_mgr.trigger_invalidation(trigger_type, context)
                
            except Exception as e:
                logger.error(f"❌ Cache invalidation trigger error: {e}")
                
            return result
        return wrapper
    return decorator

def screening_type_context_extractor(req, result, *args, **kwargs):
    """Extract screening type context from request"""
    context = {}
    
    # Extract screening type ID from various sources
    if 'screening_type_id' in kwargs:
        context['screening_type_id'] = kwargs['screening_type_id']
    elif hasattr(req, 'form') and 'screening_type_id' in req.form:
        context['screening_type_id'] = req.form['screening_type_id']
    elif hasattr(req, 'json') and req.json and 'screening_type_id' in req.json:
        context['screening_type_id'] = req.json['screening_type_id']
    
    # Extract action from method
    if req.method == 'POST':
        context['action'] = 'create_or_update'
    elif req.method == 'PUT':
        context['action'] = 'update'
    elif req.method == 'DELETE':
        context['action'] = 'delete'
    
    return context

def patient_context_extractor(req, result, *args, **kwargs):
    """Extract patient context from request"""
    context = {}
    
    # Extract patient ID from various sources
    if 'patient_id' in kwargs:
        context['patient_id'] = kwargs['patient_id']
    elif hasattr(req, 'form') and 'patient_id' in req.form:
        context['patient_id'] = req.form['patient_id']
    elif hasattr(req, 'json') and req.json and 'patient_id' in req.json:
        context['patient_id'] = req.json['patient_id']
    
    # Extract action from method
    if req.method == 'POST':
        context['action'] = 'create_or_update'
    elif req.method == 'PUT':
        context['action'] = 'update'
    elif req.method == 'DELETE':
        context['action'] = 'delete'
    
    return context

def document_context_extractor(req, result, *args, **kwargs):
    """Extract document context from request"""
    context = {}
    
    # Extract document ID from various sources
    if 'document_id' in kwargs:
        context['document_id'] = kwargs['document_id']
    elif hasattr(req, 'form') and 'document_id' in req.form:
        context['document_id'] = req.form['document_id']
    
    # Extract patient ID
    if 'patient_id' in kwargs:
        context['patient_id'] = kwargs['patient_id']
    elif hasattr(req, 'form') and 'patient_id' in req.form:
        context['patient_id'] = req.form['patient_id']
    
    # Extract action from method
    if req.method == 'POST':
        context['action'] = 'upload'
    elif req.method == 'PUT':
        context['action'] = 'update'
    elif req.method == 'DELETE':
        context['action'] = 'delete'
    
    return context

# Pre-defined decorators for common use cases
screening_type_cache_trigger = cache_invalidation_trigger(
    'screening_type_status_change', 
    screening_type_context_extractor
)

patient_cache_trigger = cache_invalidation_trigger(
    'patient_demographic_change',
    patient_context_extractor
)

document_cache_trigger = cache_invalidation_trigger(
    'document_type_change',
    document_context_extractor
)

# Route-specific cache invalidation middleware
def integrate_cache_triggers_with_routes(app):
    """
    Integrate cache invalidation triggers with existing routes
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request_cache_handling():
        """Handle cache invalidation before requests"""
        # Mark batch operations
        if request.endpoint and any(keyword in request.endpoint for keyword in ['bulk', 'batch', 'mass']):
            cache_mgr = get_cache_manager()
            cache_mgr.trigger_invalidation('batch_operation_start', {
                'endpoint': request.endpoint,
                'method': request.method
            })
            g.batch_operation_started = True
        else:
            g.batch_operation_started = False
    
    @app.after_request
    def after_request_cache_handling(response):
        """Handle cache invalidation after requests"""
        try:
            if hasattr(g, 'batch_operation_started') and g.batch_operation_started:
                # End batch operation
                cache_mgr = get_cache_manager()
                cache_mgr.trigger_invalidation('batch_operation_end', {
                    'endpoint': request.endpoint,
                    'method': request.method
                })
            
            # Route-specific cache invalidation
            if request.endpoint and response.status_code < 400:
                cache_mgr = get_cache_manager()
                
                # Screening type routes
                if 'screening_type' in request.endpoint:
                    cache_mgr.trigger_invalidation('screening_type_status_change', {
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'change_type': 'status'
                    })
                
                # Patient routes
                elif any(keyword in request.endpoint for keyword in ['patient', 'add_patient', 'edit_patient']):
                    patient_id = request.form.get('patient_id') or request.view_args.get('patient_id')
                    cache_mgr.trigger_invalidation('patient_demographic_change', {
                        'patient_id': patient_id,
                        'endpoint': request.endpoint,
                        'method': request.method
                    })
                
                # Document routes
                elif any(keyword in request.endpoint for keyword in ['document', 'add_document', 'upload']):
                    patient_id = request.form.get('patient_id') or request.view_args.get('patient_id')
                    document_id = request.form.get('document_id') or request.view_args.get('document_id')
                    cache_mgr.trigger_invalidation('document_type_change', {
                        'patient_id': patient_id,
                        'document_id': document_id,
                        'endpoint': request.endpoint,
                        'method': request.method
                    })
                
                # Screening routes
                elif 'screening' in request.endpoint:
                    cache_mgr.trigger_invalidation('medical_data_subsection_update', {
                        'endpoint': request.endpoint,
                        'method': request.method
                    })
                    
        except Exception as e:
            logger.error(f"❌ After request cache handling error: {e}")
        
        return response
    
    logger.info("✅ Cache reactive triggers integrated with routes")

if __name__ == "__main__":
    # Test the cache reactive triggers
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/test')
    @screening_type_cache_trigger
    def test_route():
        return "Test route with cache invalidation"
    
    integrate_cache_triggers_with_routes(app)
    
    print("Cache reactive triggers ready for testing")