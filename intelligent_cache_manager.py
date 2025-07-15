#!/usr/bin/env python3
"""
Intelligent Cache Manager with Real-Time Invalidation
Integrates with automated edge case handling for coordinated cache updates
"""

import logging
import json
import time
import threading
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
import hashlib
import os

# Try Redis first, fall back to in-memory
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app import app
from models import Patient, ScreeningType, MedicalDocument

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    tags: Set[str] = None
    version: int = 1
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = set()

@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    invalidations: int = 0
    evictions: int = 0
    
    @property
    def hit_ratio(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

class IntelligentCacheManager:
    """
    Intelligent cache manager with real-time invalidation and edge case handling
    """
    
    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        self.redis_url = redis_url or os.environ.get('REDIS_URL')
        self.default_ttl = default_ttl
        self.redis_client = None
        self.local_cache = {}  # Fallback in-memory cache
        self.cache_stats = CacheStats()
        self.invalidation_callbacks = {}
        self.tag_registry = {}  # Maps tags to cache keys
        self.lock = threading.RLock()
        
        # Initialize Redis connection
        self._initialize_redis()
        
        # Cache invalidation triggers
        self.invalidation_triggers = {
            'screening_type_keyword_change': self._invalidate_screening_type_cache,
            'screening_type_status_change': self._invalidate_screening_type_cache,
            'document_type_change': self._invalidate_document_cache,
            'patient_demographic_change': self._invalidate_patient_cache,
            'medical_data_subsection_update': self._invalidate_medical_data_cache,
            'batch_operation_start': self._handle_batch_operation_start,
            'batch_operation_end': self._handle_batch_operation_end,
        }
        
        # Batch operation tracking
        self.batch_operation_active = False
        self.batch_invalidations = set()
        
    def _initialize_redis(self):
        """Initialize Redis connection if available"""
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Redis initialization failed, using in-memory cache: {e}")
                self.redis_client = None
        else:
            logger.info("📝 Using in-memory cache (Redis not available)")
            
    def get(self, key: str, default=None) -> Any:
        """Get value from cache with automatic deserialization"""
        with self.lock:
            self.cache_stats.total_requests += 1
            
            try:
                # Try Redis first
                if self.redis_client:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        entry_data = json.loads(cached_data)
                        entry = CacheEntry(**entry_data)
                        
                        # Check expiration
                        if entry.expires_at and datetime.fromisoformat(entry.expires_at) < datetime.now():
                            self.redis_client.delete(key)
                            self.cache_stats.cache_misses += 1
                            return default
                        
                        self.cache_stats.cache_hits += 1
                        return entry.value
                
                # Fall back to local cache
                if key in self.local_cache:
                    entry = self.local_cache[key]
                    
                    # Check expiration
                    if entry.expires_at and entry.expires_at < datetime.now():
                        del self.local_cache[key]
                        self.cache_stats.cache_misses += 1
                        return default
                    
                    self.cache_stats.cache_hits += 1
                    return entry.value
                
                self.cache_stats.cache_misses += 1
                return default
                
            except Exception as e:
                logger.error(f"❌ Cache get error for key {key}: {e}")
                self.cache_stats.cache_misses += 1
                return default
                
    def set(self, key: str, value: Any, ttl: int = None, tags: Set[str] = None) -> bool:
        """Set value in cache with optional TTL and tags"""
        with self.lock:
            try:
                ttl = ttl or self.default_ttl
                expires_at = datetime.now() + timedelta(seconds=ttl)
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    expires_at=expires_at,
                    tags=tags or set()
                )
                
                # Store in Redis
                if self.redis_client:
                    entry_data = asdict(entry)
                    entry_data['created_at'] = entry.created_at.isoformat()
                    entry_data['expires_at'] = entry.expires_at.isoformat()
                    entry_data['tags'] = list(entry.tags)
                    
                    self.redis_client.setex(key, ttl, json.dumps(entry_data))
                
                # Store in local cache as backup
                self.local_cache[key] = entry
                
                # Update tag registry
                if tags:
                    for tag in tags:
                        if tag not in self.tag_registry:
                            self.tag_registry[tag] = set()
                        self.tag_registry[tag].add(key)
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Cache set error for key {key}: {e}")
                return False
                
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            try:
                # Delete from Redis
                if self.redis_client:
                    self.redis_client.delete(key)
                
                # Delete from local cache
                if key in self.local_cache:
                    entry = self.local_cache[key]
                    del self.local_cache[key]
                    
                    # Remove from tag registry
                    for tag in entry.tags:
                        if tag in self.tag_registry:
                            self.tag_registry[tag].discard(key)
                            if not self.tag_registry[tag]:
                                del self.tag_registry[tag]
                
                self.cache_stats.evictions += 1
                return True
                
            except Exception as e:
                logger.error(f"❌ Cache delete error for key {key}: {e}")
                return False
                
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag"""
        with self.lock:
            if self.batch_operation_active:
                # Store invalidations for batch processing
                self.batch_invalidations.add(tag)
                return 0
                
            invalidated_count = 0
            
            try:
                if tag in self.tag_registry:
                    keys_to_delete = self.tag_registry[tag].copy()
                    for key in keys_to_delete:
                        if self.delete(key):
                            invalidated_count += 1
                    
                    logger.info(f"🔄 Invalidated {invalidated_count} cache entries for tag: {tag}")
                    
                self.cache_stats.invalidations += invalidated_count
                return invalidated_count
                
            except Exception as e:
                logger.error(f"❌ Cache invalidation error for tag {tag}: {e}")
                return 0
                
    def clear_all(self) -> bool:
        """Clear all cache entries"""
        with self.lock:
            try:
                # Clear Redis
                if self.redis_client:
                    self.redis_client.flushdb()
                
                # Clear local cache
                self.local_cache.clear()
                self.tag_registry.clear()
                
                logger.info("🧹 All cache entries cleared")
                return True
                
            except Exception as e:
                logger.error(f"❌ Cache clear error: {e}")
                return False
                
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return {
            'total_requests': self.cache_stats.total_requests,
            'cache_hits': self.cache_stats.cache_hits,
            'cache_misses': self.cache_stats.cache_misses,
            'hit_ratio': self.cache_stats.hit_ratio,
            'invalidations': self.cache_stats.invalidations,
            'evictions': self.cache_stats.evictions,
            'cache_size': len(self.local_cache),
            'redis_available': self.redis_client is not None,
            'batch_operation_active': self.batch_operation_active
        }
        
    # Specialized cache methods for screening types
    def cache_screening_types(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Cache screening types with real-time invalidation support"""
        cache_key = f"screening_types:active={active_only}"
        
        cached_types = self.get(cache_key)
        if cached_types is not None:
            return cached_types
            
        # Generate fresh data
        with app.app_context():
            query = ScreeningType.query
            if active_only:
                query = query.filter_by(is_active=True)
            
            screening_types = query.order_by(ScreeningType.name).all()
            
            # Convert to serializable format
            types_data = []
            for st in screening_types:
                type_data = {
                    'id': st.id,
                    'name': st.name,
                    'is_active': getattr(st, 'is_active', True),
                    'description': getattr(st, 'description', ''),
                    'default_frequency': getattr(st, 'default_frequency', ''),
                    'frequency_number': getattr(st, 'frequency_number', None),
                    'frequency_unit': getattr(st, 'frequency_unit', None),
                    'keywords': getattr(st, 'keywords', ''),
                    'trigger_conditions': getattr(st, 'trigger_conditions', ''),
                    'min_age': getattr(st, 'min_age', None),
                    'max_age': getattr(st, 'max_age', None),
                    'gender_specific': getattr(st, 'gender_specific', None),
                    'document_types': getattr(st, 'document_types', ''),
                    'filename_keywords': getattr(st, 'filename_keywords', ''),
                    'content_keywords': getattr(st, 'content_keywords', '')
                }
                types_data.append(type_data)
            
            # Cache with appropriate tags
            tags = {'screening_types', 'active_screening_types' if active_only else 'all_screening_types'}
            self.set(cache_key, types_data, ttl=1800, tags=tags)  # 30 minute TTL
            
            logger.info(f"📦 Cached {len(types_data)} screening types (active_only={active_only})")
            return types_data
            
    def cache_patient_demographics(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """Cache patient demographics for screening eligibility"""
        cache_key = f"patient_demographics:{patient_id}"
        
        cached_demo = self.get(cache_key)
        if cached_demo is not None:
            return cached_demo
            
        # Generate fresh data
        with app.app_context():
            patient = Patient.query.get(patient_id)
            if not patient:
                return None
                
            demo_data = {
                'id': patient.id,
                'age': patient.age,
                'sex': patient.sex,
                'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                'conditions': [c.condition_name for c in patient.conditions] if hasattr(patient, 'conditions') else []
            }
            
            # Cache with patient-specific tag
            tags = {'patient_demographics', f'patient_{patient_id}'}
            self.set(cache_key, demo_data, ttl=3600, tags=tags)  # 1 hour TTL
            
            return demo_data
            
    def cache_document_types(self) -> List[str]:
        """Cache available document types"""
        cache_key = "document_types"
        
        cached_types = self.get(cache_key)
        if cached_types is not None:
            return cached_types
            
        # Generate fresh data
        with app.app_context():
            # Get unique document types from database
            result = MedicalDocument.query.with_entities(MedicalDocument.document_type).distinct().all()
            document_types = [row[0] for row in result if row[0]]
            
            # Cache with document tag
            tags = {'document_types'}
            self.set(cache_key, document_types, ttl=7200, tags=tags)  # 2 hour TTL
            
            logger.info(f"📦 Cached {len(document_types)} document types")
            return document_types
            
    # Invalidation trigger handlers
    def _invalidate_screening_type_cache(self, context: Dict[str, Any]):
        """Handle screening type cache invalidation"""
        screening_type_id = context.get('screening_type_id')
        change_type = context.get('change_type', 'unknown')
        
        logger.info(f"🔄 Invalidating screening type cache - ID: {screening_type_id}, Type: {change_type}")
        
        # Invalidate screening type caches
        self.invalidate_by_tag('screening_types')
        self.invalidate_by_tag('active_screening_types')
        self.invalidate_by_tag('all_screening_types')
        
        # Invalidate specific screening type if ID provided
        if screening_type_id:
            self.invalidate_by_tag(f'screening_type_{screening_type_id}')
            
    def _invalidate_document_cache(self, context: Dict[str, Any]):
        """Handle document cache invalidation"""
        document_id = context.get('document_id')
        patient_id = context.get('patient_id')
        
        logger.info(f"🔄 Invalidating document cache - Document: {document_id}, Patient: {patient_id}")
        
        # Invalidate document type cache
        self.invalidate_by_tag('document_types')
        
        # Invalidate patient-specific caches
        if patient_id:
            self.invalidate_by_tag(f'patient_{patient_id}')
            
    def _invalidate_patient_cache(self, context: Dict[str, Any]):
        """Handle patient demographic cache invalidation"""
        patient_id = context.get('patient_id')
        
        logger.info(f"🔄 Invalidating patient cache - Patient: {patient_id}")
        
        if patient_id:
            self.invalidate_by_tag(f'patient_{patient_id}')
            self.invalidate_by_tag('patient_demographics')
            
    def _invalidate_medical_data_cache(self, context: Dict[str, Any]):
        """Handle medical data subsection cache invalidation"""
        patient_id = context.get('patient_id')
        data_type = context.get('data_type')
        
        logger.info(f"🔄 Invalidating medical data cache - Patient: {patient_id}, Type: {data_type}")
        
        if patient_id:
            self.invalidate_by_tag(f'patient_{patient_id}')
            
        if data_type:
            self.invalidate_by_tag(f'medical_data_{data_type}')
            
    def _handle_batch_operation_start(self, context: Dict[str, Any]):
        """Handle start of batch operation"""
        logger.info("🔄 Batch operation started - deferring cache invalidations")
        with self.lock:
            self.batch_operation_active = True
            self.batch_invalidations.clear()
            
    def _handle_batch_operation_end(self, context: Dict[str, Any]):
        """Handle end of batch operation"""
        logger.info("🔄 Batch operation ended - processing deferred invalidations")
        with self.lock:
            self.batch_operation_active = False
            
            # Process all deferred invalidations
            for tag in self.batch_invalidations:
                self.invalidate_by_tag(tag)
                
            self.batch_invalidations.clear()
            
    def trigger_invalidation(self, trigger_type: str, context: Dict[str, Any]):
        """Trigger cache invalidation for specific events"""
        if trigger_type in self.invalidation_triggers:
            try:
                self.invalidation_triggers[trigger_type](context)
            except Exception as e:
                logger.error(f"❌ Cache invalidation trigger error ({trigger_type}): {e}")
        else:
            logger.warning(f"⚠️ Unknown cache invalidation trigger: {trigger_type}")

# Global cache manager instance
cache_manager = None

def get_cache_manager() -> IntelligentCacheManager:
    """Get or create the global cache manager"""
    global cache_manager
    
    if cache_manager is None:
        cache_manager = IntelligentCacheManager()
        
    return cache_manager

# Decorator for automatic caching
def cached(ttl: int = 3600, tags: Set[str] = None, key_prefix: str = ""):
    """
    Decorator for automatic function result caching
    
    Args:
        ttl: Time to live in seconds
        tags: Cache tags for invalidation
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            
            # Add arguments to key
            if args:
                key_parts.append(str(hash(args)))
            if kwargs:
                key_parts.append(str(hash(tuple(sorted(kwargs.items())))))
                
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache
            cache_mgr = get_cache_manager()
            cached_result = cache_mgr.get(cache_key)
            
            if cached_result is not None:
                return cached_result
                
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_mgr.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
            
        return wrapper
    return decorator

# Integration functions
def integrate_cache_with_auto_refresh_manager():
    """Integrate cache manager with auto refresh manager"""
    try:
        from automated_edge_case_handler import AutomatedScreeningRefreshManager
        
        # Add cache invalidation to refresh manager
        original_refresh = AutomatedScreeningRefreshManager.refresh_patient_screenings
        
        def enhanced_refresh(self, patient_id: int, trigger_source: str = "unknown"):
            # Invalidate patient-specific caches before refresh
            cache_mgr = get_cache_manager()
            cache_mgr.trigger_invalidation('patient_demographic_change', {'patient_id': patient_id})
            
            # Call original refresh
            result = original_refresh(self, patient_id, trigger_source)
            
            # Invalidate related caches after refresh
            cache_mgr.trigger_invalidation('medical_data_subsection_update', {'patient_id': patient_id})
            
            return result
            
        # Replace method with enhanced version
        AutomatedScreeningRefreshManager.refresh_patient_screenings = enhanced_refresh
        
        logger.info("✅ Cache manager integrated with auto refresh manager")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cache integration error: {e}")
        return False

def integrate_cache_with_reactive_triggers():
    """Integrate cache manager with reactive trigger middleware"""
    try:
        from reactive_trigger_middleware import reactive_trigger_manager
        
        # Add cache invalidation callbacks
        original_trigger_document_change = reactive_trigger_manager.trigger_document_change
        original_trigger_screening_type_change = reactive_trigger_manager.trigger_screening_type_change
        original_trigger_keyword_change = reactive_trigger_manager.trigger_keyword_change
        
        def enhanced_trigger_document_change(patient_id: int, action: str, document_id: Optional[int] = None):
            # Trigger cache invalidation
            cache_mgr = get_cache_manager()
            cache_mgr.trigger_invalidation('document_type_change', {
                'patient_id': patient_id,
                'document_id': document_id,
                'action': action
            })
            
            # Call original trigger
            return original_trigger_document_change(patient_id, action, document_id)
            
        def enhanced_trigger_screening_type_change(screening_type_id: int, action: str):
            # Trigger cache invalidation
            cache_mgr = get_cache_manager()
            cache_mgr.trigger_invalidation('screening_type_status_change', {
                'screening_type_id': screening_type_id,
                'action': action,
                'change_type': 'status'
            })
            
            # Call original trigger
            return original_trigger_screening_type_change(screening_type_id, action)
            
        def enhanced_trigger_keyword_change(screening_type_id: int):
            # Trigger cache invalidation
            cache_mgr = get_cache_manager()
            cache_mgr.trigger_invalidation('screening_type_keyword_change', {
                'screening_type_id': screening_type_id,
                'change_type': 'keyword'
            })
            
            # Call original trigger
            return original_trigger_keyword_change(screening_type_id)
            
        # Replace methods with enhanced versions
        reactive_trigger_manager.trigger_document_change = enhanced_trigger_document_change
        reactive_trigger_manager.trigger_screening_type_change = enhanced_trigger_screening_type_change
        reactive_trigger_manager.trigger_keyword_change = enhanced_trigger_keyword_change
        
        logger.info("✅ Cache manager integrated with reactive triggers")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cache reactive integration error: {e}")
        return False

# Cache warming functions
def warm_cache_on_startup():
    """Warm up the cache with frequently accessed data"""
    try:
        cache_mgr = get_cache_manager()
        
        # Warm up screening types cache
        cache_mgr.cache_screening_types(active_only=True)
        cache_mgr.cache_screening_types(active_only=False)
        
        # Warm up document types cache
        cache_mgr.cache_document_types()
        
        logger.info("🔥 Cache warmed up successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cache warmup error: {e}")
        return False

if __name__ == "__main__":
    # Test the cache manager
    cache_mgr = IntelligentCacheManager()
    
    # Test basic operations
    cache_mgr.set("test_key", {"test": "value"}, ttl=60, tags={"test"})
    result = cache_mgr.get("test_key")
    print(f"Cache test result: {result}")
    
    # Test tag invalidation
    cache_mgr.invalidate_by_tag("test")
    result = cache_mgr.get("test_key")
    print(f"After invalidation: {result}")
    
    # Test statistics
    stats = cache_mgr.get_stats()
    print(f"Cache stats: {stats}")