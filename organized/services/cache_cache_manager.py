
import redis
import json
import time
import logging
from flask import request
from functools import wraps

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self.memory_cache_timestamps = {}
        
    def init_app(self, app):
        """Initialize cache with Flask app"""
        try:
            # Try to connect to Redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Redis not available, using memory cache: {e}")
            self.redis_client = None
    
    def get(self, key):
        """Get value from cache"""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                
        # Fallback to memory cache
        if key in self.memory_cache:
            timestamp = self.memory_cache_timestamps.get(key, 0)
            if time.time() - timestamp < 300:  # 5 minute TTL
                return self.memory_cache[key]
            else:
                del self.memory_cache[key]
                del self.memory_cache_timestamps[key]
        
        return None
    
    def set(self, key, value, timeout=300):
        """Set value in cache"""
        if self.redis_client:
            try:
                self.redis_client.setex(key, timeout, json.dumps(value))
                return
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                
        # Fallback to memory cache
        self.memory_cache[key] = value
        self.memory_cache_timestamps[key] = time.time()
        
        # Clean up old entries
        if len(self.memory_cache) > 1000:
            current_time = time.time()
            expired_keys = [
                k for k, ts in self.memory_cache_timestamps.items()
                if current_time - ts > 300
            ]
            for k in expired_keys:
                self.memory_cache.pop(k, None)
                self.memory_cache_timestamps.pop(k, None)
    
    def delete(self, key):
        """Delete key from cache"""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
                
        self.memory_cache.pop(key, None)
        self.memory_cache_timestamps.pop(key, None)
    
    def clear_pattern(self, pattern):
        """Clear keys matching pattern"""
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis pattern delete error: {e}")
                
        # For memory cache, remove keys that match pattern
        keys_to_remove = []
        for key in self.memory_cache.keys():
            if pattern.replace('*', '') in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.memory_cache.pop(key, None)
            self.memory_cache_timestamps.pop(key, None)
    
    def clear_all(self):
        """Clear all cache"""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis flush error: {e}")
                
        self.memory_cache.clear()
        self.memory_cache_timestamps.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        if self.redis_client:
            try:
                info = self.redis_client.info()
                return {
                    'type': 'redis',
                    'used_memory': info.get('used_memory_human', 'Unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            except Exception as e:
                logger.error(f"Redis stats error: {e}")
        
        return {
            'type': 'memory',
            'total_keys': len(self.memory_cache),
            'memory_usage': f"{len(str(self.memory_cache))} bytes (estimated)"
        }

# Global cache manager instance
cache_manager = CacheManager()

def cache_route(timeout=300, vary_on=None):
    """
    Decorator to cache route responses
    
    Args:
        timeout: Cache timeout in seconds (default: 300)
        vary_on: List of request parameters to include in cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_parts = [
                func.__name__,
                request.method,
                request.path
            ]
            
            # Add query parameters if specified
            if vary_on:
                for param in vary_on:
                    if param in request.args:
                        cache_key_parts.append(f"{param}={request.args[param]}")
                    elif param in kwargs:
                        cache_key_parts.append(f"{param}={kwargs[param]}")
            
            cache_key = "|".join(cache_key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)
            
            # Only cache successful responses
            if hasattr(result, 'status_code') and result.status_code == 200:
                cache_manager.set(cache_key, result.get_json(), timeout)
            elif isinstance(result, tuple) and len(result) == 2 and result[1] == 200:
                cache_manager.set(cache_key, result[0], timeout)
            
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern):
    """Invalidate cache entries matching pattern"""
    cache_manager.clear_pattern(pattern)
    logger.debug(f"Invalidated cache pattern: {pattern}")

def invalidate_patient_cache(patient_id=None):
    """Invalidate patient-related cache entries"""
    patterns = [
        'api_patients*',
        'patients*',
        'home_dashboard*'
    ]
    
    if patient_id:
        patterns.extend([
            f'patient_detail_{patient_id}*',
            f'api_patients_{patient_id}*'
        ])
    
    for pattern in patterns:
        invalidate_cache_pattern(pattern)

def invalidate_appointment_cache(patient_id=None, date=None):
    """Invalidate appointment-related cache entries"""
    patterns = [
        'appointments*',
        'todays_appointments*',
        'home_dashboard*',
        'api_appointments*'
    ]

    if patient_id:
        patterns.append(f'patient_detail_{patient_id}*')
        patterns.append(f'patient_appointments_{patient_id}*')
        patterns.append(f'api_patients_{patient_id}*')

    if date:
        patterns.append(f'appointments_{date}*')
        patterns.append(f'api_appointments*date={date}*')

    for pattern in patterns:
        invalidate_cache_pattern(pattern)

def invalidate_api_cache():
    """Invalidate all API cache entries"""
    patterns = [
        'api_patients*',
        'api_appointments*'
    ]

    for pattern in patterns:
        invalidate_cache_pattern(pattern)
