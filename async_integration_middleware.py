#!/usr/bin/env python3
"""
Async Integration Middleware
Integrates async processing with existing Flask routes and infrastructure
"""

import asyncio
import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import request, g, current_app, jsonify

from async_screening_processor import get_async_processor

logger = logging.getLogger(__name__)

class AsyncIntegrationMiddleware:
    """
    Middleware for integrating async processing with Flask routes
    Handles document uploads, screening updates, and edge case coordination
    """
    
    def __init__(self, app=None):
        self.app = app
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.async_processor = get_async_processor()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        self.app = app
        
        # Register middleware hooks
        app.before_request(self.before_request_handler)
        app.after_request(self.after_request_handler)
        
        # Register async processing routes
        self.register_async_routes(app)
        
        logger.info("✅ Async integration middleware initialized")
    
    def before_request_handler(self):
        """Handle async processing setup before requests"""
        try:
            # Set up async processing context
            g.async_processing_context = {
                'start_time': time.time(),
                'processor': self.async_processor,
                'requires_async': self._requires_async_processing()
            }
            
            # Pre-process async operations if needed
            if g.async_processing_context['requires_async']:
                self._setup_async_operation()
                
        except Exception as e:
            logger.error(f"❌ Before request async processing error: {e}")
    
    def after_request_handler(self, response):
        """Handle async processing after requests"""
        try:
            if hasattr(g, 'async_processing_context') and response.status_code < 400:
                # Process async operations
                if g.async_processing_context['requires_async']:
                    self._process_async_operation(response)
                
                # Add processing metrics to response
                processing_time = time.time() - g.async_processing_context['start_time']
                response.headers['X-Processing-Time'] = str(processing_time)
                
        except Exception as e:
            logger.error(f"❌ After request async processing error: {e}")
        
        return response
    
    def _requires_async_processing(self) -> bool:
        """Check if current request requires async processing"""
        if not request.endpoint:
            return False
        
        # Document upload/delete operations
        if any(keyword in request.endpoint for keyword in ['add_document', 'delete_document', 'upload']):
            return True
        
        # Screening refresh operations
        if 'screening' in request.endpoint and request.method in ['POST', 'PUT', 'DELETE']:
            return True
        
        # Patient demographic updates
        if any(keyword in request.endpoint for keyword in ['edit_patient', 'add_patient']):
            return True
        
        # Screening type keyword updates
        if 'screening_type' in request.endpoint and request.method in ['POST', 'PUT']:
            return True
        
        return False
    
    def _setup_async_operation(self):
        """Set up async operation context"""
        operation_type = self._determine_operation_type()
        
        g.async_operation = {
            'type': operation_type,
            'data': self._extract_operation_data(),
            'subsection': self._determine_medical_subsection(),
            'requires_cache_invalidation': True
        }
    
    def _process_async_operation(self, response):
        """Process async operation after request completion"""
        if not hasattr(g, 'async_operation'):
            return
        
        operation = g.async_operation
        
        # Run async processing in background
        asyncio.create_task(self._run_async_processing(operation))
    
    async def _run_async_processing(self, operation: Dict[str, Any]):
        """Run async processing operation"""
        try:
            processor = self.async_processor
            
            if operation['type'] == 'document_upload':
                result = await processor.process_screening_refresh_trigger({
                    'patient_id': operation['data'].get('patient_id'),
                    'document_id': operation['data'].get('document_id'),
                    'action': 'upload',
                    'subsection': operation['subsection']
                })
                
            elif operation['type'] == 'document_delete':
                result = await processor.process_screening_refresh_trigger({
                    'patient_id': operation['data'].get('patient_id'),
                    'document_id': operation['data'].get('document_id'),
                    'action': 'delete',
                    'subsection': operation['subsection']
                })
                
            elif operation['type'] == 'screening_update':
                result = await processor.process_screening_refresh_trigger({
                    'patient_id': operation['data'].get('patient_id'),
                    'action': 'update',
                    'subsection': operation['subsection']
                })
                
            elif operation['type'] == 'keyword_update':
                result = await processor.process_screening_type_keyword_update(
                    operation['data'].get('screening_type_id'),
                    operation['data'].get('old_keywords', []),
                    operation['data'].get('new_keywords', [])
                )
                
            elif operation['type'] == 'demographic_update':
                result = await processor.process_demographic_mismatch_handling(
                    operation['data'].get('patient_id'),
                    operation['data'].get('demographic_changes', {})
                )
                
            else:
                result = await processor.coordinate_with_edge_case_handler(
                    operation['type'],
                    operation['data']
                )
            
            logger.info(f"✅ Async processing completed: {operation['type']}")
            
        except Exception as e:
            logger.error(f"❌ Async processing error: {e}")
    
    def _determine_operation_type(self) -> str:
        """Determine the type of async operation needed"""
        if not request.endpoint:
            return 'unknown'
        
        # Document operations
        if 'add_document' in request.endpoint:
            return 'document_upload'
        elif 'delete_document' in request.endpoint:
            return 'document_delete'
        
        # Screening operations
        elif 'screening' in request.endpoint:
            return 'screening_update'
        
        # Patient operations
        elif any(keyword in request.endpoint for keyword in ['edit_patient', 'add_patient']):
            return 'demographic_update'
        
        # Screening type operations
        elif 'screening_type' in request.endpoint:
            return 'keyword_update'
        
        return 'generic_update'
    
    def _extract_operation_data(self) -> Dict[str, Any]:
        """Extract operation data from request"""
        data = {}
        
        # Extract from form data
        if request.form:
            data.update(request.form.to_dict())
        
        # Extract from JSON data
        if request.json:
            data.update(request.json)
        
        # Extract from URL parameters
        if request.view_args:
            data.update(request.view_args)
        
        return data
    
    def _determine_medical_subsection(self) -> str:
        """Determine medical subsection from request data"""
        # Check form data for document type
        if request.form and 'document_type' in request.form:
            document_type = request.form['document_type']
            
            if document_type in ['LAB_RESULT', 'LABORATORY_REPORT']:
                return 'laboratories'
            elif document_type in ['RADIOLOGY_REPORT', 'IMAGING_REPORT', 'XRAY_REPORT']:
                return 'imaging'
            elif document_type in ['CONSULTATION_NOTE', 'REFERRAL_LETTER', 'SPECIALIST_REPORT']:
                return 'consults'
            elif document_type in ['HOSPITAL_SUMMARY', 'DISCHARGE_SUMMARY', 'INPATIENT_REPORT']:
                return 'hospital_records'
            else:
                return 'other'
        
        # Check endpoint for hints
        if request.endpoint:
            if 'lab' in request.endpoint:
                return 'laboratories'
            elif 'imaging' in request.endpoint:
                return 'imaging'
            elif 'consult' in request.endpoint:
                return 'consults'
            elif 'hospital' in request.endpoint:
                return 'hospital_records'
        
        return 'other'
    
    def register_async_routes(self, app):
        """Register async processing API routes"""
        
        @app.route('/api/async/process-screening-refresh', methods=['POST'])
        def api_process_screening_refresh():
            """API endpoint for manual screening refresh processing"""
            try:
                data = request.get_json() or {}
                
                # Run async processing
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.async_processor.process_screening_refresh_trigger(data)
                )
                
                loop.close()
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"❌ API screening refresh error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/async/process-keyword-update', methods=['POST'])
        def api_process_keyword_update():
            """API endpoint for keyword update processing"""
            try:
                data = request.get_json() or {}
                
                # Run async processing
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.async_processor.process_screening_type_keyword_update(
                        data.get('screening_type_id'),
                        data.get('old_keywords', []),
                        data.get('new_keywords', [])
                    )
                )
                
                loop.close()
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"❌ API keyword update error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/async/process-demographic-mismatch', methods=['POST'])
        def api_process_demographic_mismatch():
            """API endpoint for demographic mismatch handling"""
            try:
                data = request.get_json() or {}
                
                # Run async processing
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.async_processor.process_demographic_mismatch_handling(
                        data.get('patient_id'),
                        data.get('demographic_changes', {})
                    )
                )
                
                loop.close()
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"❌ API demographic mismatch error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/async/process-cutoff-calculation', methods=['POST'])
        def api_process_cutoff_calculation():
            """API endpoint for cutoff date calculation"""
            try:
                data = request.get_json() or {}
                
                # Run async processing
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.async_processor.process_cutoff_date_calculation(
                        data.get('patient_id'),
                        data.get('screening_type'),
                        data.get('data_type')
                    )
                )
                
                loop.close()
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"❌ API cutoff calculation error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/async/metrics', methods=['GET'])
        def api_async_metrics():
            """Get async processing metrics"""
            try:
                metrics = self.async_processor.get_processing_metrics()
                return jsonify(metrics)
                
            except Exception as e:
                logger.error(f"❌ API metrics error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

# Decorators for async integration

def async_document_processing(func):
    """Decorator for async document processing"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Execute original function
        result = func(*args, **kwargs)
        
        # Trigger async processing if needed
        if hasattr(g, 'async_operation') and g.async_operation['type'] in ['document_upload', 'document_delete']:
            # Async processing will be handled by middleware
            pass
        
        return result
    return wrapper

def async_screening_processing(func):
    """Decorator for async screening processing"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Execute original function
        result = func(*args, **kwargs)
        
        # Trigger async processing if needed
        if hasattr(g, 'async_operation') and g.async_operation['type'] in ['screening_update', 'keyword_update']:
            # Async processing will be handled by middleware
            pass
        
        return result
    return wrapper

def async_demographic_processing(func):
    """Decorator for async demographic processing"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Execute original function
        result = func(*args, **kwargs)
        
        # Trigger async processing if needed
        if hasattr(g, 'async_operation') and g.async_operation['type'] == 'demographic_update':
            # Async processing will be handled by middleware
            pass
        
        return result
    return wrapper

# Integration function

def integrate_async_middleware(app):
    """
    Integrate async processing middleware with Flask app
    
    Args:
        app: Flask application instance
    """
    middleware = AsyncIntegrationMiddleware(app)
    
    logger.info("✅ Async integration middleware integrated")
    return middleware

if __name__ == "__main__":
    # Test the async integration middleware
    from flask import Flask
    
    app = Flask(__name__)
    
    # Test route
    @app.route('/test-async')
    @async_document_processing
    def test_async_route():
        return jsonify({'message': 'Test async processing'})
    
    # Integrate middleware
    integrate_async_middleware(app)
    
    print("Async integration middleware ready for testing")