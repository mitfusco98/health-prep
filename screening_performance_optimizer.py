#!/usr/bin/env python3
"""
Screening Performance Optimizer
High-performance screening queries with caching and pagination
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from app import db
from models import Screening, Patient, ScreeningType

logger = logging.getLogger(__name__)

class ScreeningPerformanceOptimizer:
    """Optimized screening queries with caching and performance enhancements"""
    
    CACHE_TIMEOUT = 300  # 5 minutes
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100
    
    def __init__(self):
        self.cache_prefix = "screening_opt"
    
    def get_optimized_screenings(self, 
                               page: int = 1, 
                               page_size: int = DEFAULT_PAGE_SIZE,
                               status_filter: str = '',
                               screening_type_filter: str = '',
                               search_query: str = '') -> Dict:
        """
        Get screenings with optimized query, caching, and pagination
        
        Args:
            page: Page number (1-based)
            page_size: Number of results per page
            status_filter: Filter by screening status
            screening_type_filter: Filter by screening type
            search_query: Search in patient names
            
        Returns:
            Dict with screenings, pagination info, and metadata
        """
        # Validate and limit page size
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        offset = (page - 1) * page_size
        
        # Build cache key
        cache_key = f"{self.cache_prefix}:screenings:{page}:{page_size}:{status_filter}:{screening_type_filter}:{search_query}"
        
        # Try cache first
        try:
            from flask import current_app
            if hasattr(current_app, 'cache'):
                cached_result = current_app.cache.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for screenings page {page}")
                    return cached_result
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        # Build optimized query
        try:
            query_result = self._build_optimized_query(
                offset, page_size, status_filter, screening_type_filter, search_query
            )
            
            # Cache the result
            try:
                from flask import current_app
                if hasattr(current_app, 'cache'):
                    current_app.cache.set(cache_key, query_result, timeout=self.CACHE_TIMEOUT)
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")
            
            return query_result
            
        except Exception as e:
            logger.error(f"Optimized screening query failed: {e}")
            # Fallback to simple query
            return self._fallback_query(offset, page_size)
    
    def _build_optimized_query(self, offset: int, page_size: int, 
                             status_filter: str, screening_type_filter: str, 
                             search_query: str) -> Dict:
        """Build the optimized database query"""
        
        # Base query with optimized joins and eager loading
        base_query = (
            db.session.query(Screening)
            .join(Patient, Screening.patient_id == Patient.id)
            .join(ScreeningType, Screening.screening_type == ScreeningType.name)
            .filter(
                and_(
                    ScreeningType.is_active == True,
                    Screening.is_visible == True
                )
            )
            .options(
                joinedload(Screening.patient)  # Eager load patient data
                # Document loading handled separately to avoid relationship issues
            )
        )
        
        # Apply filters
        if status_filter:
            base_query = base_query.filter(Screening.status == status_filter)
        
        if screening_type_filter:
            base_query = base_query.filter(Screening.screening_type == screening_type_filter)
        
        if search_query:
            search_term = f"%{search_query.lower()}%"
            base_query = base_query.filter(
                or_(
                    Patient.first_name.ilike(search_term),
                    Patient.last_name.ilike(search_term),
                    (Patient.first_name + ' ' + Patient.last_name).ilike(search_term)
                )
            )
        
        # Get total count for pagination (use count query for efficiency)
        total_count = base_query.count()
        
        # Apply ordering and pagination
        screenings = (
            base_query
            .order_by(
                # Optimized ordering prioritizing Due status
                db.case(
                    (Screening.status == 'Due', 1),
                    (Screening.status == 'Due Soon', 2),
                    (Screening.status == 'Incomplete', 3),
                    (Screening.status == 'Complete', 4),
                    else_=5
                ),
                Screening.due_date.asc().nullslast(),
                Patient.last_name.asc(),
                Patient.first_name.asc()
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        current_page = (offset // page_size) + 1
        
        return {
            'screenings': screenings,
            'pagination': {
                'current_page': current_page,
                'total_pages': total_pages,
                'total_count': total_count,
                'page_size': page_size,
                'has_next': current_page < total_pages,
                'has_prev': current_page > 1,
                'next_page': current_page + 1 if current_page < total_pages else None,
                'prev_page': current_page - 1 if current_page > 1 else None
            },
            'filters': {
                'status_filter': status_filter,
                'screening_type_filter': screening_type_filter,
                'search_query': search_query
            },
            'metadata': {
                'query_time': datetime.utcnow(),
                'cache_key': f"{self.cache_prefix}:screenings:{current_page}:{page_size}",
                'optimized': True
            }
        }
    
    def _fallback_query(self, offset: int, page_size: int) -> Dict:
        """Fallback simple query when optimized version fails"""
        logger.warning("Using fallback screening query")
        
        try:
            screenings = (
                Screening.query
                .join(Patient)
                .filter(Screening.is_visible == True)
                .order_by(Screening.due_date.asc())
                .offset(offset)
                .limit(page_size)
                .all()
            )
            
            total_count = Screening.query.filter(Screening.is_visible == True).count()
            
            return {
                'screenings': screenings,
                'pagination': {
                    'current_page': (offset // page_size) + 1,
                    'total_pages': (total_count + page_size - 1) // page_size,
                    'total_count': total_count,
                    'page_size': page_size,
                    'has_next': (offset + page_size) < total_count,
                    'has_prev': offset > 0
                },
                'filters': {},
                'metadata': {
                    'query_time': datetime.utcnow(),
                    'optimized': False,
                    'fallback': True
                }
            }
        except Exception as e:
            logger.error(f"Fallback query also failed: {e}")
            return {
                'screenings': [],
                'pagination': {'current_page': 1, 'total_pages': 0, 'total_count': 0},
                'filters': {},
                'metadata': {'error': str(e)}
            }
    
    def get_screening_stats(self) -> Dict:
        """Get cached screening statistics for dashboard"""
        cache_key = f"{self.cache_prefix}:stats"
        
        try:
            from flask import current_app
            if hasattr(current_app, 'cache'):
                cached_stats = current_app.cache.get(cache_key)
                if cached_stats:
                    return cached_stats
        except Exception:
            pass
        
        try:
            # Optimized stats query using SQL aggregation
            stats_query = text("""
                SELECT 
                    s.status,
                    s.screening_type,
                    COUNT(*) as count
                FROM screening s
                JOIN screening_type st ON s.screening_type = st.name
                WHERE st.is_active = true AND s.is_visible = true
                GROUP BY s.status, s.screening_type
                ORDER BY s.status, s.screening_type
            """)
            
            result = db.session.execute(stats_query)
            stats_data = result.fetchall()
            
            # Process into structured format
            stats = {
                'by_status': {},
                'by_type': {},
                'total_count': 0,
                'last_updated': datetime.utcnow()
            }
            
            for row in stats_data:
                status, screening_type, count = row
                
                # By status
                if status not in stats['by_status']:
                    stats['by_status'][status] = 0
                stats['by_status'][status] += count
                
                # By type
                if screening_type not in stats['by_type']:
                    stats['by_type'][screening_type] = {}
                stats['by_type'][screening_type][status] = count
                
                stats['total_count'] += count
            
            # Cache for 2 minutes (stats update more frequently)
            try:
                from flask import current_app
                if hasattr(current_app, 'cache'):
                    current_app.cache.set(cache_key, stats, timeout=120)
            except Exception:
                pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Stats query failed: {e}")
            return {
                'by_status': {},
                'by_type': {},
                'total_count': 0,
                'error': str(e)
            }
    
    def invalidate_cache(self, screening_id: Optional[int] = None):
        """Invalidate screening caches when data changes"""
        try:
            from flask import current_app
            if hasattr(current_app, 'cache'):
                # Clear all screening-related caches
                current_app.cache.delete(f"{self.cache_prefix}:stats")
                
                # Clear paginated cache (brute force for now)
                for page in range(1, 21):  # Clear first 20 pages
                    for page_size in [25, 50, 100]:
                        current_app.cache.delete(f"{self.cache_prefix}:screenings:{page}:{page_size}:::")
                
                logger.info(f"Cache invalidated for screening changes")
            
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

# Global optimizer instance
screening_optimizer = ScreeningPerformanceOptimizer()