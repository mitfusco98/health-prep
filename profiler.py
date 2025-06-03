
import time
import cProfile
import pstats
import io
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
import threading
import json
import logging
from flask import request, g
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

class AppProfiler:
    def __init__(self):
        self.route_stats = defaultdict(list)
        self.db_query_stats = defaultdict(list)
        self.function_stats = defaultdict(list)
        self.lock = threading.Lock()
        self.start_time = time.time()
        
    def profile_route(self, func):
        """Decorator to profile route execution time"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Profile the function
            profiler = cProfile.Profile()
            profiler.enable()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # Convert to ms
                
                # Get function stats
                s = io.StringIO()
                ps = pstats.Stats(profiler, stream=s)
                ps.sort_stats('cumulative')
                ps.print_stats(10)  # Top 10 functions
                
                route_name = func.__name__
                if hasattr(request, 'endpoint'):
                    route_name = request.endpoint or route_name
                
                with self.lock:
                    self.route_stats[route_name].append({
                        'duration_ms': duration,
                        'timestamp': datetime.now().isoformat(),
                        'method': request.method if request else 'Unknown',
                        'profile_data': s.getvalue()
                    })
                    
                    # Keep only last 100 entries per route
                    if len(self.route_stats[route_name]) > 100:
                        self.route_stats[route_name] = self.route_stats[route_name][-100:]
                
                # Log slow routes (>500ms)
                if duration > 500:
                    logger.warning(f"Slow route detected: {route_name} took {duration:.2f}ms")
                    
        return wrapper
    
    def profile_function(self, func_name=None):
        """Decorator to profile individual functions"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = (end_time - start_time) * 1000
                    
                    name = func_name or f"{func.__module__}.{func.__name__}"
                    
                    with self.lock:
                        self.function_stats[name].append({
                            'duration_ms': duration,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # Keep only last 50 entries per function
                        if len(self.function_stats[name]) > 50:
                            self.function_stats[name] = self.function_stats[name][-50:]
            return wrapper
        return decorator
    
    def get_slowest_routes(self, limit=10):
        """Get the slowest routes by average execution time"""
        route_averages = []
        
        with self.lock:
            for route, stats in self.route_stats.items():
                if stats:
                    avg_duration = sum(s['duration_ms'] for s in stats) / len(stats)
                    max_duration = max(s['duration_ms'] for s in stats)
                    min_duration = min(s['duration_ms'] for s in stats)
                    
                    route_averages.append({
                        'route': route,
                        'avg_duration_ms': avg_duration,
                        'max_duration_ms': max_duration,
                        'min_duration_ms': min_duration,
                        'call_count': len(stats),
                        'recent_calls': stats[-5:]  # Last 5 calls
                    })
        
        return sorted(route_averages, key=lambda x: x['avg_duration_ms'], reverse=True)[:limit]
    
    def get_slowest_functions(self, limit=10):
        """Get the slowest functions by average execution time"""
        function_averages = []
        
        with self.lock:
            for func, stats in self.function_stats.items():
                if stats:
                    avg_duration = sum(s['duration_ms'] for s in stats) / len(stats)
                    max_duration = max(s['duration_ms'] for s in stats)
                    
                    function_averages.append({
                        'function': func,
                        'avg_duration_ms': avg_duration,
                        'max_duration_ms': max_duration,
                        'call_count': len(stats)
                    })
        
        return sorted(function_averages, key=lambda x: x['avg_duration_ms'], reverse=True)[:limit]
    
    def get_db_query_stats(self):
        """Get database query statistics"""
        with self.lock:
            return dict(self.db_query_stats)
    
    def record_db_query(self, statement, duration_ms):
        """Record database query execution time"""
        with self.lock:
            # Normalize SQL statement for grouping
            normalized = ' '.join(str(statement).split()[:10])  # First 10 words
            self.db_query_stats[normalized].append({
                'duration_ms': duration_ms,
                'timestamp': datetime.now().isoformat(),
                'full_statement': str(statement)[:500]  # Truncate long queries
            })
            
            # Keep only last 20 entries per query type
            if len(self.db_query_stats[normalized]) > 20:
                self.db_query_stats[normalized] = self.db_query_stats[normalized][-20:]
    
    def generate_report(self):
        """Generate a comprehensive performance report"""
        return {
            'report_generated': datetime.now().isoformat(),
            'uptime_hours': (time.time() - self.start_time) / 3600,
            'slowest_routes': self.get_slowest_routes(),
            'slowest_functions': self.get_slowest_functions(),
            'database_queries': self.get_db_query_stats(),
            'recommendations': self.get_recommendations()
        }
    
    def get_recommendations(self):
        """Generate performance recommendations"""
        recommendations = []
        
        # Check for slow routes
        slow_routes = self.get_slowest_routes(5)
        for route in slow_routes:
            if route['avg_duration_ms'] > 1000:
                recommendations.append({
                    'type': 'slow_route',
                    'severity': 'high',
                    'description': f"Route '{route['route']}' averages {route['avg_duration_ms']:.1f}ms",
                    'suggestion': 'Consider adding caching, optimizing database queries, or reducing middleware overhead'
                })
            elif route['avg_duration_ms'] > 500:
                recommendations.append({
                    'type': 'slow_route',
                    'severity': 'medium',
                    'description': f"Route '{route['route']}' averages {route['avg_duration_ms']:.1f}ms",
                    'suggestion': 'Review database queries and consider pagination for large datasets'
                })
        
        # Check database query patterns
        db_stats = self.get_db_query_stats()
        for query, stats in db_stats.items():
            if stats:
                avg_duration = sum(s['duration_ms'] for s in stats) / len(stats)
                if avg_duration > 100:
                    recommendations.append({
                        'type': 'slow_query',
                        'severity': 'high' if avg_duration > 500 else 'medium',
                        'description': f"Database query averages {avg_duration:.1f}ms: {query}",
                        'suggestion': 'Add database indexes, optimize JOIN operations, or implement query caching'
                    })
        
        return recommendations

# Global profiler instance
profiler = AppProfiler()

# Database query profiling
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if hasattr(context, '_query_start_time'):
        duration = (time.time() - context._query_start_time) * 1000
        profiler.record_db_query(statement, duration)
        
        # Log only extremely slow queries to reduce console noise
        if duration > 1000:  # Increased threshold to 1 second
            logger.warning(f"Slow database query ({duration:.2f}ms): {str(statement)[:100]}...")
