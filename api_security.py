
"""
API Security middleware to prevent exposure of sensitive credentials
"""

from flask import request, jsonify, g
from functools import wraps
import logging
from key_management import key_manager, KeyType

logger = logging.getLogger(__name__)

def validate_api_credentials(f):
    """Decorator to validate API credentials are appropriate for the context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if request contains any API keys
        api_key = None
        
        # Check various sources for API keys
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                api_key = auth_header[7:]
            elif auth_header.startswith('ApiKey '):
                api_key = auth_header[7:]
        
        if 'X-API-Key' in request.headers:
            api_key = request.headers['X-API-Key']
        
        if request.json and 'api_key' in request.json:
            api_key = request.json['api_key']
        
        # Validate the key if present
        if api_key:
            validation = key_manager.validator.validate_key_security(api_key, context=request.endpoint)
            
            if not validation['valid']:
                logger.warning(f"Invalid API key rejected: {validation['reason']}")
                return jsonify({'error': 'Invalid API credentials'}), 401
            
            if not validation['client_safe']:
                logger.error(f"Service-level key blocked in API request: {validation['key_type'].value}")
                return jsonify({'error': 'Service-level credentials not allowed in API requests'}), 403
            
            # Store validated key info in request context
            g.api_key_info = validation
        
        return f(*args, **kwargs)
    
    return decorated_function

def block_sensitive_credentials(f):
    """Decorator to specifically block service and admin level credentials"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check all request data for sensitive patterns
        sensitive_patterns = [
            'service_role', 'admin_key', 'root_key', 'master_key',
            'eyJ',  # JWT tokens
            'sk_',  # Stripe-style service keys
            'rk_',  # Restricted keys
        ]
        
        # Check request body
        if request.json:
            for key, value in request.json.items():
                if isinstance(value, str):
                    for pattern in sensitive_patterns:
                        if pattern in value.lower():
                            logger.error(f"Blocked sensitive credential pattern: {pattern}")
                            return jsonify({'error': 'Service-level credentials detected and blocked'}), 403
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                if isinstance(value, str):
                    for pattern in sensitive_patterns:
                        if pattern in value.lower():
                            logger.error(f"Blocked sensitive credential pattern: {pattern}")
                            return jsonify({'error': 'Service-level credentials detected and blocked'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def audit_credential_usage():
    """Audit function to check for credential security compliance"""
    audit_results = key_manager.audit_key_usage()
    
    violations = [result for result in audit_results if result['compliance'] == 'FAIL']
    
    if violations:
        logger.warning(f"Credential security violations detected: {len(violations)} issues")
        for violation in violations:
            logger.warning(f"Violation: {violation['key_name']} - {violation['key_type']}")
    
    return {
        'total_keys': len(audit_results),
        'violations': len(violations),
        'compliance_rate': (len(audit_results) - len(violations)) / len(audit_results) * 100,
        'details': audit_results
    }
