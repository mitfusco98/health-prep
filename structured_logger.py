
import json
import logging
import traceback
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, session, g, has_request_context
from flask_limiter.util import get_remote_address

class StructuredLogger:
    """Structured logging utility that outputs JSON-formatted logs for machine parsing"""
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        
    def _get_base_context(self) -> Dict[str, Any]:
        """Get base context information for all log entries"""
        import os
        import uuid
        
        context = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'healthprep',
            'environment': os.environ.get('ENVIRONMENT', 'production'),
            'correlation_id': str(uuid.uuid4()),
            'log_version': '1.0',
            'process_id': os.getpid(),
            'thread_id': str(threading.current_thread().ident) if hasattr(threading, 'current_thread') else 'unknown'
        }
        
        # Add request context if available
        if has_request_context():
            try:
                context.update({
                    'request_id': session.get('session_id', 'unknown'),
                    'ip_address': get_remote_address(),
                    'method': request.method,
                    'path': request.path,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'session_id': session.get('session_id')
                })
                
                # Add user context if available
                if hasattr(g, 'current_user') and g.current_user:
                    context['user_id'] = g.current_user.id
                    context['username'] = g.current_user.username
                    
            except Exception:
                # Don't fail logging if context extraction fails
                pass
                
        return context
    
    def _log_structured(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None, 
                       exc_info: bool = False, **kwargs):
        """Internal method to create structured log entries"""
        log_entry = self._get_base_context()
        log_entry.update({
            'level': level.upper(),
            'message': message,
            'logger': self.logger.name,
            'log_type': 'application',
            'severity': self._map_severity(level),
            'source': {
                'file': kwargs.get('filename', 'unknown'),
                'function': kwargs.get('function', 'unknown'),
                'line': kwargs.get('line_number', 0)
            }
        })
        
        # Add any extra data under a structured namespace
        if extra_data:
            log_entry['event_data'] = extra_data
            
        # Add metrics if present
        if 'duration_ms' in kwargs:
            log_entry['metrics'] = {
                'duration_ms': kwargs.pop('duration_ms'),
                'operation': kwargs.get('operation', 'unknown')
            }
            
        # Add any additional keyword arguments under structured fields
        if kwargs:
            log_entry['additional_fields'] = {k: v for k, v in kwargs.items() 
                                            if k not in ['filename', 'function', 'line_number', 'operation']}
        
        # Add exception information if requested
        if exc_info:
            log_entry['exception'] = {
                'type': str(type(exc_info).__name__) if isinstance(exc_info, Exception) else 'Exception',
                'message': str(exc_info) if isinstance(exc_info, Exception) else 'Unknown exception',
                'traceback': traceback.format_exc(),
                'stack_hash': abs(hash(traceback.format_exc())) % (10 ** 8)
            }
        
        # Add tags for easier filtering
        log_entry['tags'] = self._generate_tags(level, kwargs)
        
        # Convert to JSON string with consistent formatting
        json_message = json.dumps(log_entry, default=str, separators=(',', ':'), sort_keys=True)
        
        # Log at appropriate level
        getattr(self.logger, level.lower())(json_message)
    
    def _map_severity(self, level: str) -> int:
        """Map log level to numeric severity for machine processing"""
        severity_map = {
            'debug': 0,
            'info': 1,
            'warning': 2,
            'error': 3,
            'critical': 4
        }
        return severity_map.get(level.lower(), 1)
    
    def _generate_tags(self, level: str, kwargs: Dict[str, Any]) -> list:
        """Generate tags for easier log filtering and aggregation"""
        tags = [level.lower()]
        
        if 'event_category' in kwargs:
            tags.append(f"category:{kwargs['event_category']}")
        
        if 'operation' in kwargs:
            tags.append(f"operation:{kwargs['operation']}")
        
        if has_request_context():
            tags.append("has_request_context")
            if request.method:
                tags.append(f"method:{request.method.lower()}")
            if request.endpoint:
                tags.append(f"endpoint:{request.endpoint}")
        
        return tags
    
    def info(self, message: str, **kwargs):
        """Log info level message"""
        self._log_structured('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        self._log_structured('warning', message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error level message"""
        self._log_structured('error', message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """Log critical level message"""
        self._log_structured('critical', message, exc_info=exc_info, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        self._log_structured('debug', message, **kwargs)
    
    def security_event(self, event_type: str, message: str, **kwargs):
        """Log security-related events with special tagging"""
        kwargs['event_category'] = 'security'
        kwargs['security_event_type'] = event_type
        self._log_structured('warning', message, **kwargs)
    
    def performance_event(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics"""
        kwargs['event_category'] = 'performance'
        kwargs['operation'] = operation
        kwargs['duration_ms'] = duration_ms
        self._log_structured('info', f"Performance: {operation} took {duration_ms}ms", **kwargs)
    
    def business_event(self, event_type: str, message: str, **kwargs):
        """Log business logic events"""
        kwargs['event_category'] = 'business'
        kwargs['business_event_type'] = event_type
        self._log_structured('info', message, **kwargs)
    
    def audit_event(self, action: str, resource: str, result: str, **kwargs):
        """Log audit trail events"""
        kwargs['event_category'] = 'audit'
        kwargs['action'] = action
        kwargs['resource'] = resource
        kwargs['result'] = result
        self._log_structured('info', f"Audit: {action} on {resource} - {result}", **kwargs)

# Create global structured logger instance
structured_logger = StructuredLogger('healthprep')

# Convenience functions for common use cases
def log_security_event(event_type: str, message: str, **kwargs):
    """Log security events"""
    structured_logger.security_event(event_type, message, **kwargs)

def log_performance(operation: str, duration_ms: float, **kwargs):
    """Log performance metrics"""
    structured_logger.performance_event(operation, duration_ms, **kwargs)

def log_business_event(event_type: str, message: str, **kwargs):
    """Log business events"""
    structured_logger.business_event(event_type, message, **kwargs)

def log_audit(action: str, resource: str, result: str, **kwargs):
    """Log audit events"""
    structured_logger.audit_event(action, resource, result, **kwargs)

def log_error(message: str, exc_info: bool = False, **kwargs):
    """Log error with structured format"""
    structured_logger.error(message, exc_info=exc_info, **kwargs)

def log_info(message: str, **kwargs):
    """Log info with structured format"""
    structured_logger.info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Log warning with structured format"""
    structured_logger.warning(message, **kwargs)
