
"""
Secure key management utilities for HealthPrep application
Ensures proper separation between client-side and server-side credentials
"""

import os
import logging
import hashlib
import secrets
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class KeyType(Enum):
    """Types of API keys and their security levels"""
    PUBLIC = "public"          # Safe for client-side use
    ANON = "anon"             # Anonymous keys safe for client-side
    RESTRICTED = "restricted"  # Limited scope, client-safe
    SERVICE = "service"        # Server-only, never expose
    ADMIN = "admin"           # Administrative, never expose
    SECRET = "secret"         # Confidential, never expose

class KeyValidator:
    """Validates and categorizes API keys for security"""
    
    # Patterns that indicate dangerous service-level keys
    SERVICE_PATTERNS = [
        'service_role', 'service_', 'sk_', 'rk_', 'secret_',
        'admin', 'root', 'master', 'super', 'confidential',
        'private', 'bearer_', 'auth_', 'system_'
    ]
    
    # Patterns that indicate safe client-side keys
    SAFE_PATTERNS = [
        'anon', 'public', 'readonly', 'limited', 'client'
    ]
    
    @classmethod
    def classify_key(cls, api_key: str) -> KeyType:
        """Classify an API key based on its content and patterns"""
        if not api_key:
            return KeyType.SECRET
        
        key_lower = api_key.lower()
        
        # Check for explicitly safe patterns first
        for pattern in cls.SAFE_PATTERNS:
            if pattern in key_lower:
                if 'anon' in pattern:
                    return KeyType.ANON
                elif 'public' in pattern:
                    return KeyType.PUBLIC
                else:
                    return KeyType.RESTRICTED
        
        # Check for dangerous patterns
        for pattern in cls.SERVICE_PATTERNS:
            if pattern in key_lower:
                if 'admin' in pattern or 'root' in pattern:
                    return KeyType.ADMIN
                else:
                    return KeyType.SERVICE
        
        # Default to restricted for unrecognized patterns
        return KeyType.RESTRICTED
    
    @classmethod
    def is_client_safe(cls, api_key: str) -> bool:
        """Determine if a key is safe for client-side use"""
        key_type = cls.classify_key(api_key)
        return key_type in [KeyType.PUBLIC, KeyType.ANON, KeyType.RESTRICTED]
    
    @classmethod
    def validate_key_security(cls, api_key: str, context: str = "general") -> Dict[str, any]:
        """Comprehensive key security validation"""
        if not api_key:
            return {
                'valid': False,
                'reason': 'Empty key',
                'client_safe': False,
                'key_type': KeyType.SECRET
            }
        
        key_type = cls.classify_key(api_key)
        client_safe = cls.is_client_safe(api_key)
        
        # Additional length-based checks
        if len(api_key) > 500:
            logger.warning(f"Unusually long API key ({len(api_key)} chars) - likely service key")
            client_safe = False
            key_type = KeyType.SERVICE
        
        # JWT token detection (should never be used as API keys)
        if api_key.startswith('eyJ'):
            logger.error("JWT token detected as API key - security violation")
            return {
                'valid': False,
                'reason': 'JWT token used as API key',
                'client_safe': False,
                'key_type': KeyType.SECRET
            }
        
        return {
            'valid': True,
            'client_safe': client_safe,
            'key_type': key_type,
            'masked_key': cls.mask_key(api_key),
            'context': context
        }
    
    @classmethod
    def mask_key(cls, key: str, show_chars: int = 4) -> str:
        """Safely mask a key for logging/display"""
        if not key:
            return "****"
        
        if len(key) <= show_chars:
            return "*" * len(key)
        
        return key[:show_chars] + "*" * (len(key) - show_chars)

class SecureKeyManager:
    """Manages secure storage and retrieval of API keys"""
    
    def __init__(self):
        self.validator = KeyValidator()
        self._client_safe_keys = {}
        self._load_environment_keys()
    
    def _load_environment_keys(self):
        """Load and validate keys from environment variables"""
        env_keys = {}
        
        for key, value in os.environ.items():
            if any(suffix in key.upper() for suffix in ['_KEY', '_SECRET', '_TOKEN']):
                validation = self.validator.validate_key_security(value, context=key)
                env_keys[key] = validation
                
                if not validation['client_safe']:
                    logger.info(f"Server-only key detected: {key} ({validation['key_type'].value})")
                else:
                    logger.info(f"Client-safe key detected: {key} ({validation['key_type'].value})")
        
        self._environment_keys = env_keys
    
    def get_client_safe_key(self, key_name: str) -> Optional[str]:
        """Get a key only if it's safe for client-side use"""
        if key_name in self._environment_keys:
            key_info = self._environment_keys[key_name]
            if key_info['client_safe']:
                return os.environ.get(key_name)
            else:
                logger.warning(f"Blocked access to server-only key: {key_name}")
                return None
        
        return None
    
    def validate_and_store_key(self, key_name: str, key_value: str) -> bool:
        """Validate and securely store a new API key"""
        validation = self.validator.validate_key_security(key_value, context=key_name)
        
        if not validation['valid']:
            logger.error(f"Invalid key rejected: {key_name} - {validation['reason']}")
            return False
        
        if validation['client_safe']:
            self._client_safe_keys[key_name] = key_value
            logger.info(f"Client-safe key stored: {key_name}")
        else:
            logger.info(f"Server-only key stored: {key_name}")
        
        return True
    
    def get_safe_keys_for_frontend(self) -> Dict[str, str]:
        """Get only keys that are safe to expose to frontend"""
        safe_keys = {}
        
        # Only return explicitly safe keys
        for key_name, key_value in self._client_safe_keys.items():
            if self.validator.is_client_safe(key_value):
                safe_keys[key_name] = key_value
        
        return safe_keys
    
    def audit_key_usage(self) -> List[Dict]:
        """Audit all keys for security compliance"""
        audit_results = []
        
        for key_name, key_info in self._environment_keys.items():
            audit_results.append({
                'key_name': key_name,
                'key_type': key_info['key_type'].value,
                'client_safe': key_info['client_safe'],
                'masked_value': key_info['masked_key'],
                'compliance': 'PASS' if key_info['valid'] else 'FAIL'
            })
        
        return audit_results

# Global key manager instance
key_manager = SecureKeyManager()
