
import redis
import json
import time
import hashlib
from functools import wraps
from datetime import datetime, timedelta
from flask import request, g, session
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, app=None):
        self.app = app
        self.redis_client = None
        self.memory_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
    def init_app(self, app):
        self.app = app
        try:
            # Try to connect to Redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using memory cache: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, prefix, *args, **kwargs):
        """Generate a unique cache key"""
        # Include user context for user-specific caching
        user_id = session.get('user_id', 'anonymous')
        
        # Create key components
        key_parts = [prefix, str(user_id)]
        key_parts.extend(str(arg) for arg in args)
        
        # Add sorted kwargs
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(hashlib.md5(str(sorted_kwargs).encode()).hexdigest()[:8])
        
        return ':'.join(key_parts)
    
    def get(self, key):
        """Get value from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    self.cache_stats['hits'] += 1
                    return json.loads(value)
            else:
                # Fallback to memory cache
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    if entry['expires'] > time.time():
                        self.cache_stats['hits'] += 1
                        return entry['data']
                    else:
                        del self.memory_cache[key]
            
            self.cache_stats['misses'] += 1
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, key, value, ttl=300):
        """Set value in cache with TTL (time to live) in seconds"""
        try:
            if self.redis_client:
                self.redis_client.setex(key, ttl, json.dumps(value))
            else:
                # Fallback to memory cache
                self.memory_cache[key] = {
                    'data': value,
                    'expires': time.time() + ttl
                }
                # Simple cleanup for memory cache
                if len(self.memory_cache) > 1000:
                    self._cleanup_memory_cache()
            
            self.cache_stats['sets'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key):
        """Delete key from cache"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
            
            self.cache_stats['deletes'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern):
        """Delete keys matching pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    self.cache_stats['deletes'] += len(keys)
            else:
                # For memory cache, delete keys that match pattern
                keys_to_delete = [key for key in self.memory_cache.keys() if pattern.replace('*', '') in key]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                self.cache_stats['deletes'] += len(keys_to_delete)
            
            return True
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """Clean up expired entries from memory cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if entry['expires'] <= current_time
        ]
        for key in expired_keys:
            del self.memory_cache[key]
    
    def get_stats(self):
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests,
            'backend': 'redis' if self.redis_client else 'memory',
            'memory_cache_size': len(self.memory_cache) if not self.redis_client else 0
        }

# Global cache manager instance
cache_manager = CacheManager()

def cache_route(prefix, ttl=300, include_user=True, vary_on=None):
    """Decorator for caching route responses"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key_parts = [prefix]
            
            # Add route arguments
            if args:
                cache_key_parts.extend(str(arg) for arg in args)
            
            # Add query parameters if specified
            if vary_on:
                for param in vary_on:
                    value = request.args.get(param)
                    if value:
                        cache_key_parts.append(f"{param}:{value}")
            
            # Add user context if needed
            if include_user:
                user_id = session.get('user_id', 'anonymous')
                cache_key_parts.append(f"user:{user_id}")
            
            cache_key = ':'.join(cache_key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {cache_key}")
            result = f(*args, **kwargs)
            
            # Only cache successful responses
            if hasattr(result, 'status_code'):
                if result.status_code == 200:
                    cache_manager.set(cache_key, result.get_data(as_text=True), ttl)
            else:
                # For JSON responses
                cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return decorated_function
    return decorator

def invalidate_cache_pattern(pattern):
    """Invalidate cache entries matching pattern"""
    cache_manager.delete_pattern(pattern)

def invalidate_patient_cache(patient_id):
    """Invalidate all cache entries for a specific patient"""
    patterns = [
        f"patient_detail:{patient_id}:*",
        f"patient_documents:{patient_id}:*",
        f"prep_sheet:{patient_id}:*",
        "patients_list:*",
        "dashboard:*"
    ]
    for pattern in patterns:
        invalidate_cache_pattern(pattern)

def invalidate_appointment_cache(date=None):
    """Invalidate appointment-related cache entries"""
    patterns = [
        "appointments:*",
        "dashboard:*",
        "all_visits:*"
    ]
    if date:
        patterns.append(f"appointments:{date}:*")
    
    for pattern in patterns:
        invalidate_cache_pattern(pattern)
