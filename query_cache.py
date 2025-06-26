"""
Simple Query Caching for Dashboard
Caches expensive queries for short periods to improve performance
"""

import time
from functools import wraps

# Simple in-memory cache
_query_cache = {}
_cache_times = {}

def cache_query(ttl_seconds=60):
    """Cache query results for specified time to live"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            current_time = time.time()
            
            # Check if we have a cached result that's still valid
            if (cache_key in _query_cache and 
                cache_key in _cache_times and 
                current_time - _cache_times[cache_key] < ttl_seconds):
                return _query_cache[cache_key]
            
            # Execute the function and cache the result
            result = func(*args, **kwargs)
            _query_cache[cache_key] = result
            _cache_times[cache_key] = current_time
            
            # Clean up old cache entries (simple cleanup)
            if len(_query_cache) > 100:  # Limit cache size
                oldest_key = min(_cache_times.keys(), key=lambda k: _cache_times[k])
                del _query_cache[oldest_key]
                del _cache_times[oldest_key]
            
            return result
        return wrapper
    return decorator


def clear_cache():
    """Clear all cached queries"""
    global _query_cache, _cache_times
    _query_cache.clear()
    _cache_times.clear()


def get_cache_stats():
    """Get cache statistics"""
    return {
        'cached_queries': len(_query_cache),
        'oldest_entry': min(_cache_times.values()) if _cache_times else None,
        'newest_entry': max(_cache_times.values()) if _cache_times else None
    }