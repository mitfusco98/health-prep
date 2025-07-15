#!/usr/bin/env python3
"""
Reactive Trigger Middleware
Automatically triggers high-performance bulk processing for edge cases:
- Document upload/deletion
- Screening type activation/deactivation  
- Keyword changes
- Cutoff setting updates
"""

import logging
from functools import wraps
from typing import Any, Dict, Optional
from flask import request, g
import threading
import asyncio
from datetime import datetime

from high_performance_bulk_screening_engine import trigger_reactive_update_sync

logger = logging.getLogger(__name__)

class ReactiveScreeningTriggerManager:
    """Manages reactive triggers for screening updates"""
    
    def __init__(self):
        self.enabled = True
        self.trigger_queue = []
        self._processing_lock = threading.Lock()
        
    def trigger_document_change(self, patient_id: int, action: str, document_id: Optional[int] = None):
        """Trigger reactive update for document changes"""
        if not self.enabled:
            return
            
        context = {
            'patient_id': patient_id,
            'action': action,  # 'upload' or 'delete'
            'document_id': document_id,
            'timestamp': str(datetime.now())
        }
        
        # Run in background thread to avoid blocking the request
        threading.Thread(
            target=self._process_trigger_async,
            args=('document_upload' if action == 'upload' else 'document_deletion', context),
            daemon=True
        ).start()
        
        logger.info(f"🔄 Triggered reactive update: document {action} for patient {patient_id}")
        
    def trigger_screening_type_change(self, screening_type_id: int, action: str):
        """Trigger reactive update for screening type changes"""
        if not self.enabled:
            return
            
        context = {
            'screening_type_id': screening_type_id,
            'action': action,  # 'activate' or 'deactivate'
            'timestamp': str(datetime.now())
        }
        
        # Run in background thread
        threading.Thread(
            target=self._process_trigger_async,
            args=(f'screening_type_{action}', context),
            daemon=True
        ).start()
        
        logger.info(f"🔄 Triggered reactive update: screening type {action} for {screening_type_id}")
        
    def trigger_keyword_change(self, screening_type_id: int):
        """Trigger reactive update for keyword changes"""
        if not self.enabled:
            return
            
        context = {
            'screening_type_id': screening_type_id,
            'timestamp': str(datetime.now())
        }
        
        # Run in background thread
        threading.Thread(
            target=self._process_trigger_async,
            args=('keyword_change', context),
            daemon=True
        ).start()
        
        logger.info(f"🔄 Triggered reactive update: keyword change for screening type {screening_type_id}")
        
    def trigger_cutoff_change(self):
        """Trigger reactive update for cutoff setting changes"""
        if not self.enabled:
            return
            
        context = {
            'timestamp': str(datetime.now())
        }
        
        # Run in background thread
        threading.Thread(
            target=self._process_trigger_async,
            args=('cutoff_setting_change', context),
            daemon=True
        ).start()
        
        logger.info(f"🔄 Triggered reactive update: cutoff settings changed")
        
    def _process_trigger_async(self, trigger_type: str, context: Dict[str, Any]):
        """Process trigger asynchronously"""
        try:
            with self._processing_lock:
                success = trigger_reactive_update_sync(trigger_type, context)
                if success:
                    logger.info(f"✅ Reactive trigger {trigger_type} completed successfully")
                else:
                    logger.warning(f"⚠️ Reactive trigger {trigger_type} failed")
        except Exception as e:
            logger.error(f"❌ Error processing reactive trigger {trigger_type}: {e}")

# Global trigger manager
reactive_trigger_manager = ReactiveScreeningTriggerManager()

def document_change_trigger(action: str):
    """
    Decorator to automatically trigger screening updates when documents change
    
    Usage:
        @document_change_trigger('upload')
        def upload_document():
            # Document upload logic
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the original function
            result = f(*args, **kwargs)
            
            # Extract patient_id from various sources
            patient_id = None
            document_id = None
            
            # Try to get patient_id from request args/form
            if hasattr(request, 'args') and 'patient_id' in request.args:
                patient_id = int(request.args.get('patient_id'))
            elif hasattr(request, 'form') and 'patient_id' in request.form:
                patient_id = int(request.form.get('patient_id'))
            elif hasattr(request, 'view_args') and 'patient_id' in request.view_args:
                patient_id = int(request.view_args['patient_id'])
            elif hasattr(request, 'view_args') and 'id' in request.view_args:
                # For patient detail routes where id is patient_id
                patient_id = int(request.view_args['id'])
                
            # Try to get document_id
            if hasattr(request, 'view_args') and 'document_id' in request.view_args:
                document_id = int(request.view_args['document_id'])
                
            # Trigger reactive update if we found a patient_id
            if patient_id:
                reactive_trigger_manager.trigger_document_change(patient_id, action, document_id)
                
            return result
        return decorated_function
    return decorator

def screening_type_change_trigger(action: str):
    """
    Decorator to automatically trigger screening updates when screening types change
    
    Usage:
        @screening_type_change_trigger('activate')
        def activate_screening_type():
            # Activation logic
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the original function
            result = f(*args, **kwargs)
            
            # Extract screening_type_id from various sources
            screening_type_id = None
            
            if hasattr(request, 'args') and 'screening_type_id' in request.args:
                screening_type_id = int(request.args.get('screening_type_id'))
            elif hasattr(request, 'form') and 'screening_type_id' in request.form:
                screening_type_id = int(request.form.get('screening_type_id'))
            elif hasattr(request, 'view_args') and 'screening_type_id' in request.view_args:
                screening_type_id = int(request.view_args['screening_type_id'])
            elif hasattr(request, 'view_args') and 'id' in request.view_args:
                screening_type_id = int(request.view_args['id'])
                
            # Trigger reactive update if we found a screening_type_id
            if screening_type_id:
                reactive_trigger_manager.trigger_screening_type_change(screening_type_id, action)
                
            return result
        return decorated_function
    return decorator

def keyword_change_trigger(f):
    """
    Decorator to automatically trigger screening updates when keywords change
    
    Usage:
        @keyword_change_trigger
        def update_keywords():
            # Keyword update logic
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Execute the original function
        result = f(*args, **kwargs)
        
        # Extract screening_type_id from various sources
        screening_type_id = None
        
        if hasattr(request, 'args') and 'screening_type_id' in request.args:
            screening_type_id = int(request.args.get('screening_type_id'))
        elif hasattr(request, 'form') and 'screening_type_id' in request.form:
            screening_type_id = int(request.form.get('screening_type_id'))
        elif hasattr(request, 'view_args') and 'screening_type_id' in request.view_args:
            screening_type_id = int(request.view_args['screening_type_id'])
        elif hasattr(request, 'view_args') and 'id' in request.view_args:
            screening_type_id = int(request.view_args['id'])
            
        # Trigger reactive update if we found a screening_type_id
        if screening_type_id:
            reactive_trigger_manager.trigger_keyword_change(screening_type_id)
            
        return result
    return decorated_function

def cutoff_change_trigger(f):
    """
    Decorator to automatically trigger screening updates when cutoff settings change
    
    Usage:
        @cutoff_change_trigger
        def update_cutoff_settings():
            # Cutoff update logic
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Execute the original function
        result = f(*args, **kwargs)
        
        # Trigger reactive update for cutoff changes
        reactive_trigger_manager.trigger_cutoff_change()
        
        return result
    return decorated_function

# Integration functions for existing routes
def integrate_reactive_triggers_with_routes(app):
    """
    Integrate reactive triggers with existing Flask routes
    Call this function to automatically add triggers to existing routes
    """
    
    # Document upload/deletion routes
    document_routes = [
        'add_document', 'upload_document', 'delete_document', 
        'add_lab_result', 'add_imaging', 'add_consult', 'add_hospital_summary'
    ]
    
    # Screening type management routes
    screening_type_routes = [
        'activate_screening_type', 'deactivate_screening_type',
        'update_screening_type', 'edit_screening_type'
    ]
    
    # Keyword management routes  
    keyword_routes = [
        'update_keywords', 'edit_screening_keywords', 'manage_parsing_rules'
    ]
    
    # Cutoff setting routes
    cutoff_routes = [
        'update_checklist_settings', 'update_cutoff_settings'
    ]
    
    # Apply decorators to existing routes
    for endpoint_name in document_routes:
        if endpoint_name in app.view_functions:
            # Determine action based on route name
            action = 'upload' if any(word in endpoint_name for word in ['add', 'upload']) else 'delete'
            app.view_functions[endpoint_name] = document_change_trigger(action)(app.view_functions[endpoint_name])
            logger.info(f"✅ Added document change trigger to {endpoint_name}")
            
    for endpoint_name in screening_type_routes:
        if endpoint_name in app.view_functions:
            # Determine action based on route name  
            action = 'activate' if 'activate' in endpoint_name else 'deactivate' if 'deactivate' in endpoint_name else 'update'
            app.view_functions[endpoint_name] = screening_type_change_trigger(action)(app.view_functions[endpoint_name])
            logger.info(f"✅ Added screening type change trigger to {endpoint_name}")
            
    for endpoint_name in keyword_routes:
        if endpoint_name in app.view_functions:
            app.view_functions[endpoint_name] = keyword_change_trigger(app.view_functions[endpoint_name])
            logger.info(f"✅ Added keyword change trigger to {endpoint_name}")
            
    for endpoint_name in cutoff_routes:
        if endpoint_name in app.view_functions:
            app.view_functions[endpoint_name] = cutoff_change_trigger(app.view_functions[endpoint_name])
            logger.info(f"✅ Added cutoff change trigger to {endpoint_name}")
            
    logger.info("🔄 Reactive trigger middleware integration complete")

# Utility functions for manual triggering
def manual_trigger_document_change(patient_id: int, action: str, document_id: Optional[int] = None):
    """Manually trigger document change update"""
    reactive_trigger_manager.trigger_document_change(patient_id, action, document_id)

def manual_trigger_screening_type_change(screening_type_id: int, action: str):
    """Manually trigger screening type change update"""
    reactive_trigger_manager.trigger_screening_type_change(screening_type_id, action)

def manual_trigger_keyword_change(screening_type_id: int):
    """Manually trigger keyword change update"""
    reactive_trigger_manager.trigger_keyword_change(screening_type_id)

def manual_trigger_cutoff_change():
    """Manually trigger cutoff change update"""
    reactive_trigger_manager.trigger_cutoff_change()

def disable_reactive_triggers():
    """Disable reactive triggers (for testing or maintenance)"""
    reactive_trigger_manager.enabled = False
    logger.info("⚠️ Reactive triggers disabled")

def enable_reactive_triggers():
    """Enable reactive triggers"""
    reactive_trigger_manager.enabled = True
    logger.info("✅ Reactive triggers enabled")