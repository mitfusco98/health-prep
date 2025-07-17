"""
Screening Cache Manager
Implements intelligent caching with dependency tracking for screening results
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict

from app import db
from models import ScreeningType, Patient, Screening


@dataclass
class CacheEntry:
    """Represents a cached screening result"""
    patient_id: int
    screening_type_id: int
    screening_data: Dict[str, Any]
    dependencies: Set[str]  # What this cache entry depends on
    created_at: datetime
    last_accessed: datetime
    cache_key: str
    is_valid: bool = True


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_entries: int = 0
    hit_count: int = 0
    miss_count: int = 0
    invalidation_count: int = 0
    memory_usage_mb: float = 0.0
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None


class ScreeningCacheManager:
    """Manages intelligent caching of screening results with dependency tracking"""
    
    def __init__(self, max_cache_size: int = 10000, ttl_hours: int = 24):
        self.cache: Dict[str, CacheEntry] = {}
        self.dependency_index: Dict[str, Set[str]] = {}  # dependency -> cache_keys
        self.patient_index: Dict[int, Set[str]] = {}  # patient_id -> cache_keys
        self.max_cache_size = max_cache_size
        self.ttl_hours = ttl_hours
        self.stats = CacheStats()
        
    def generate_cache_key(self, patient_id: int, screening_type_id: int, context: Dict[str, Any] = None) -> str:
        """Generate a unique cache key for a screening result"""
        key_data = {
            "patient_id": patient_id,
            "screening_type_id": screening_type_id,
            "context": context or {}
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def get_screening_dependencies(self, screening_type_id: int) -> Set[str]:
        """Get all dependencies that affect a screening type"""
        dependencies = set()
        
        try:
            screening_type = ScreeningType.query.get(screening_type_id)
            if screening_type:
                # Add screening type specific dependencies
                dependencies.add(f"screening_type_{screening_type_id}")
                dependencies.add(f"keywords_{screening_type_id}")
                dependencies.add(f"trigger_conditions_{screening_type_id}")
                dependencies.add(f"frequency_{screening_type_id}")
                dependencies.add(f"cutoffs_{screening_type_id}")
                dependencies.add(f"activation_{screening_type_id}")
                
                # Add global dependencies
                dependencies.add("patient_documents")
                dependencies.add("patient_conditions")
                dependencies.add("checklist_settings")
                
        except Exception as e:
            print(f"⚠️ Error getting dependencies for screening type {screening_type_id}: {e}")
            
        return dependencies
        
    def cache_screening_result(
        self, 
        patient_id: int, 
        screening_type_id: int, 
        screening_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """Cache a screening result with dependency tracking"""
        cache_key = self.generate_cache_key(patient_id, screening_type_id, context)
        dependencies = self.get_screening_dependencies(screening_type_id)
        
        # Create cache entry
        entry = CacheEntry(
            patient_id=patient_id,
            screening_type_id=screening_type_id,
            screening_data=screening_data,
            dependencies=dependencies,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            cache_key=cache_key
        )
        
        # Store in cache
        self.cache[cache_key] = entry
        
        # Update indexes
        for dependency in dependencies:
            if dependency not in self.dependency_index:
                self.dependency_index[dependency] = set()
            self.dependency_index[dependency].add(cache_key)
            
        if patient_id not in self.patient_index:
            self.patient_index[patient_id] = set()
        self.patient_index[patient_id].add(cache_key)
        
        # Cleanup if cache is too large
        self._cleanup_cache()
        
        return cache_key
        
    def get_cached_screening(
        self, 
        patient_id: int, 
        screening_type_id: int, 
        context: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a cached screening result if valid"""
        cache_key = self.generate_cache_key(patient_id, screening_type_id, context)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Check if entry is still valid
            if self._is_entry_valid(entry):
                entry.last_accessed = datetime.utcnow()
                self.stats.hit_count += 1
                return entry.screening_data
            else:
                # Remove invalid entry
                self._remove_cache_entry(cache_key)
                
        self.stats.miss_count += 1
        return None
        
    def _is_entry_valid(self, entry: CacheEntry) -> bool:
        """Check if a cache entry is still valid"""
        # Check TTL
        if datetime.utcnow() - entry.created_at > timedelta(hours=self.ttl_hours):
            return False
            
        # Check if entry is marked as invalid
        if not entry.is_valid:
            return False
            
        return True
        
    def invalidate_by_dependency(self, dependency: str) -> int:
        """Invalidate all cache entries that depend on a specific dependency"""
        invalidated_count = 0
        
        if dependency in self.dependency_index:
            cache_keys_to_invalidate = self.dependency_index[dependency].copy()
            
            for cache_key in cache_keys_to_invalidate:
                if cache_key in self.cache:
                    self.cache[cache_key].is_valid = False
                    invalidated_count += 1
                    
            print(f"🗑️ Invalidated {invalidated_count} cache entries for dependency: {dependency}")
            
        self.stats.invalidation_count += invalidated_count
        return invalidated_count
        
    def invalidate_patient_cache(self, patient_id: int) -> int:
        """Invalidate all cache entries for a specific patient"""
        invalidated_count = 0
        
        if patient_id in self.patient_index:
            cache_keys_to_invalidate = self.patient_index[patient_id].copy()
            
            for cache_key in cache_keys_to_invalidate:
                if cache_key in self.cache:
                    self.cache[cache_key].is_valid = False
                    invalidated_count += 1
                    
            print(f"🗑️ Invalidated {invalidated_count} cache entries for patient {patient_id}")
            
        self.stats.invalidation_count += invalidated_count
        return invalidated_count
        
    def invalidate_screening_type(self, screening_type_id: int) -> int:
        """Invalidate all cache entries for a specific screening type"""
        dependency = f"screening_type_{screening_type_id}"
        return self.invalidate_by_dependency(dependency)
        
    def _remove_cache_entry(self, cache_key: str):
        """Remove a cache entry and update indexes"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Remove from dependency index
            for dependency in entry.dependencies:
                if dependency in self.dependency_index:
                    self.dependency_index[dependency].discard(cache_key)
                    if not self.dependency_index[dependency]:
                        del self.dependency_index[dependency]
                        
            # Remove from patient index
            if entry.patient_id in self.patient_index:
                self.patient_index[entry.patient_id].discard(cache_key)
                if not self.patient_index[entry.patient_id]:
                    del self.patient_index[entry.patient_id]
                    
            # Remove from cache
            del self.cache[cache_key]
            
    def _cleanup_cache(self):
        """Remove old or invalid entries to keep cache size manageable"""
        if len(self.cache) <= self.max_cache_size:
            return
            
        # Get entries sorted by last access time (oldest first)
        entries_by_access = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest entries until we're under the limit
        entries_to_remove = len(self.cache) - self.max_cache_size + 100  # Remove extra to avoid frequent cleanups
        
        for i in range(min(entries_to_remove, len(entries_by_access))):
            cache_key = entries_by_access[i][0]
            self._remove_cache_entry(cache_key)
            
        print(f"🧹 Cleaned up {entries_to_remove} old cache entries")
        
    def get_cache_statistics(self) -> CacheStats:
        """Get current cache performance statistics"""
        self.stats.total_entries = len(self.cache)
        
        if self.cache:
            entries = list(self.cache.values())
            self.stats.oldest_entry = min(entry.created_at for entry in entries)
            self.stats.newest_entry = max(entry.created_at for entry in entries)
            
            # Estimate memory usage (rough calculation)
            total_size = sum(len(json.dumps(asdict(entry))) for entry in entries)
            self.stats.memory_usage_mb = total_size / (1024 * 1024)
        else:
            self.stats.oldest_entry = None
            self.stats.newest_entry = None
            self.stats.memory_usage_mb = 0.0
            
        return self.stats
        
    def clear_cache(self) -> int:
        """Clear all cache entries"""
        count = len(self.cache)
        self.cache.clear()
        self.dependency_index.clear()
        self.patient_index.clear()
        self.stats = CacheStats()
        print(f"🧹 Cleared {count} cache entries")
        return count
        
    def get_cache_info_for_patient(self, patient_id: int) -> Dict[str, Any]:
        """Get cache information for a specific patient"""
        if patient_id not in self.patient_index:
            return {"cached_screenings": 0, "cache_keys": []}
            
        cache_keys = self.patient_index[patient_id]
        valid_entries = []
        
        for cache_key in cache_keys:
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                if self._is_entry_valid(entry):
                    valid_entries.append({
                        "screening_type_id": entry.screening_type_id,
                        "created_at": entry.created_at.isoformat(),
                        "last_accessed": entry.last_accessed.isoformat(),
                        "cache_key": cache_key[:8] + "..."  # Truncated for display
                    })
                    
        return {
            "cached_screenings": len(valid_entries),
            "cache_entries": valid_entries
        }


# Global instance
screening_cache_manager = ScreeningCacheManager()