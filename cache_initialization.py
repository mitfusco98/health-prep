#!/usr/bin/env python3
"""
Cache Initialization for Healthcare Application
Initializes and warms up caches on application startup
"""

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def initialize_healthcare_caches() -> Dict[str, Any]:
    """
    Initialize healthcare caching system on application startup
    Returns initialization status and performance metrics
    """
    startup_stats = {
        'cache_service_initialized': False,
        'cache_warmed': False,
        'initialization_time_ms': 0,
        'cache_stats': {},
        'errors': [],
        'timestamp': datetime.now().isoformat()
    }
    
    start_time = datetime.now()
    
    try:
        # Initialize cache service
        from enhanced_cache_service import get_healthcare_cache_service
        cache_service = get_healthcare_cache_service()
        startup_stats['cache_service_initialized'] = True
        logger.info("✅ Healthcare cache service initialized")
        
        # Warm up frequently accessed caches
        from cached_operations import warm_frequently_accessed_caches
        warm_results = warm_frequently_accessed_caches()
        startup_stats['cache_warmed'] = len([k for k, v in warm_results.items() if v]) > 0
        startup_stats['warm_results'] = warm_results
        
        if startup_stats['cache_warmed']:
            logger.info(f"🔥 Cache warmed successfully: {len([k for k, v in warm_results.items() if v])} caches ready")
        else:
            logger.warning("⚠️ Cache warming had limited success")
        
        # Get initial cache statistics
        startup_stats['cache_stats'] = cache_service.get_cache_statistics()
        
        # Integration with existing intelligent cache manager
        try:
            from intelligent_cache_manager import integrate_cache_with_auto_refresh_manager, warm_cache_on_startup
            
            # Integrate with existing systems
            integrate_cache_with_auto_refresh_manager()
            warm_cache_on_startup()
            
            logger.info("✅ Integrated with existing cache management systems")
            startup_stats['existing_integrations'] = True
            
        except Exception as integration_error:
            logger.warning(f"⚠️ Existing cache integration warning: {integration_error}")
            startup_stats['existing_integrations'] = False
            startup_stats['errors'].append(f"Integration warning: {str(integration_error)}")
        
    except Exception as e:
        error_msg = f"Cache initialization error: {e}"
        logger.error(error_msg)
        startup_stats['errors'].append(error_msg)
        
    finally:
        end_time = datetime.now()
        startup_stats['initialization_time_ms'] = int((end_time - start_time).total_seconds() * 1000)
    
    # Log initialization summary
    if startup_stats['cache_service_initialized']:
        logger.info(f"🚀 Healthcare cache system initialized in {startup_stats['initialization_time_ms']}ms")
    else:
        logger.error("❌ Healthcare cache system initialization failed")
    
    return startup_stats


def add_cache_invalidation_middleware(app):
    """
    Add middleware to handle cache invalidation on data changes
    """
    try:
        @app.before_request
        def cache_invalidation_middleware():
            """Middleware to handle cache invalidation on route changes"""
            from flask import request
            from cached_operations import get_healthcare_cache_service
            
            try:
                cache_service = get_healthcare_cache_service()
                
                # Handle screening type changes
                if 'screening' in request.endpoint and request.method in ['POST', 'PUT', 'DELETE']:
                    # Get screening type ID from URL if available
                    screening_type_id = request.view_args.get('screening_type_id')
                    if screening_type_id:
                        from cached_operations import invalidate_screening_cache
                        invalidate_screening_cache(screening_type_id)
                
                # Handle patient changes
                if 'patient' in request.endpoint and request.method in ['POST', 'PUT', 'DELETE']:
                    patient_id = request.view_args.get('patient_id')
                    if patient_id:
                        from cached_operations import invalidate_patient_cache
                        invalidate_patient_cache(patient_id)
                
                # Handle document repository changes
                if 'document' in request.endpoint and request.method in ['POST', 'PUT', 'DELETE']:
                    # Invalidate document repository cache
                    cache_service.cache_manager.invalidate_by_tag('document_repository')
                
            except Exception as middleware_error:
                # Don't break the request if cache invalidation fails
                logger.debug(f"Cache invalidation middleware warning: {middleware_error}")
        
        logger.info("✅ Cache invalidation middleware added")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add cache invalidation middleware: {e}")
        return False


def monitor_cache_performance(app):
    """
    Add cache performance monitoring
    """
    try:
        @app.after_request
        def cache_performance_monitor(response):
            """Monitor cache performance after each request"""
            try:
                from cached_operations import get_healthcare_cache_service
                cache_service = get_healthcare_cache_service()
                
                # Get cache statistics periodically (every 100 requests)
                import random
                if random.randint(1, 100) == 1:  # 1% sampling
                    stats = cache_service.get_cache_statistics()
                    hit_ratio = stats.get('healthcare_specific', {}).get('active_screening_types_cache_info', {}).get('hit_ratio', 0)
                    
                    if hit_ratio < 0.5:  # Less than 50% hit ratio
                        logger.warning(f"⚠️ Low cache hit ratio detected: {hit_ratio:.2%}")
                    
            except Exception as monitor_error:
                # Don't break the response if monitoring fails
                logger.debug(f"Cache performance monitoring warning: {monitor_error}")
            
            return response
        
        logger.info("✅ Cache performance monitoring added")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add cache performance monitoring: {e}")
        return False


def cleanup_expired_caches():
    """
    Cleanup function for expired cache entries (can be called periodically)
    """
    try:
        from cached_operations import get_healthcare_cache_service
        cache_service = get_healthcare_cache_service()
        
        # This would typically be handled by Redis TTL or LRU cache limits
        # For in-memory caches, we might need custom cleanup logic
        
        stats_before = cache_service.get_cache_statistics()
        
        # Clear any screening types cache to refresh
        cache_service.invalidate_screening_types_cache()
        
        stats_after = cache_service.get_cache_statistics()
        
        logger.info("🧹 Cache cleanup completed")
        return {
            'cleanup_performed': True,
            'stats_before': stats_before,
            'stats_after': stats_after
        }
        
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")
        return {'cleanup_performed': False, 'error': str(e)}