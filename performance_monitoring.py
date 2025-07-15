#!/usr/bin/env python3
"""
Performance Monitoring Utility
Diagnose and monitor performance issues in the healthcare application
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, Optional
from flask import request, g

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor and log performance metrics for route operations"""
    
    def __init__(self):
        self.metrics = {}
        self.slow_threshold = 2.0  # 2 seconds
        
    def log_performance(self, route_name: str, duration: float, details: Optional[Dict[str, Any]] = None):
        """Log performance metrics for a route"""
        
        # Store metrics
        if route_name not in self.metrics:
            self.metrics[route_name] = {
                'total_calls': 0,
                'total_time': 0,
                'max_time': 0,
                'min_time': float('inf'),
                'slow_calls': 0
            }
        
        metrics = self.metrics[route_name]
        metrics['total_calls'] += 1
        metrics['total_time'] += duration
        metrics['max_time'] = max(metrics['max_time'], duration)
        metrics['min_time'] = min(metrics['min_time'], duration)
        
        if duration > self.slow_threshold:
            metrics['slow_calls'] += 1
            logger.warning(f"🐌 Slow route {route_name}: {duration:.2f}s {details or ''}")
        else:
            logger.info(f"⚡ Route {route_name}: {duration:.2f}s")
            
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for all monitored routes"""
        report = {}
        
        for route_name, metrics in self.metrics.items():
            if metrics['total_calls'] > 0:
                avg_time = metrics['total_time'] / metrics['total_calls']
                slow_percentage = (metrics['slow_calls'] / metrics['total_calls']) * 100
                
                report[route_name] = {
                    'avg_time': round(avg_time, 2),
                    'max_time': round(metrics['max_time'], 2),
                    'min_time': round(metrics['min_time'], 2),
                    'total_calls': metrics['total_calls'],
                    'slow_calls': metrics['slow_calls'],
                    'slow_percentage': round(slow_percentage, 1)
                }
        
        return report

# Global monitor instance
performance_monitor = PerformanceMonitor()

def monitor_performance(route_name: Optional[str] = None):
    """Decorator to monitor route performance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Use provided route name or function name
            name = route_name or f.__name__
            
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log performance
                performance_monitor.log_performance(name, duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.log_performance(name, duration, {'error': str(e)})
                raise
                
        return decorated_function
    return decorator

def diagnose_screening_performance():
    """Diagnose specific performance issues with screening routes"""
    try:
        from app import app, db
        from models import Screening, Patient, ScreeningType
        
        with app.app_context():
            start_time = time.time()
            
            # Test 1: Basic screening count
            screening_count = Screening.query.count()
            count_time = time.time() - start_time
            
            # Test 2: Unoptimized query (what we had before)
            start_time = time.time()
            unoptimized = Screening.query.join(Patient).order_by(Screening.due_date.asc()).all()
            unoptimized_time = time.time() - start_time
            
            # Test 3: Optimized query (what we have now)
            start_time = time.time()
            optimized = (
                Screening.query
                .join(Patient)
                .join(ScreeningType, Screening.screening_type_id == ScreeningType.id)
                .filter(ScreeningType.is_active == True)
                .options(
                    db.joinedload(Screening.patient),
                    db.joinedload(Screening.screening_type),
                    db.selectinload(Screening.documents)
                )
                .order_by(Screening.due_date.asc().nullslast())
                .limit(1000)
                .all()
            )
            optimized_time = time.time() - start_time
            
            # Calculate improvement
            improvement = ((unoptimized_time - optimized_time) / unoptimized_time * 100) if unoptimized_time > 0 else 0
            
            report = {
                'screening_count': screening_count,
                'count_query_time': round(count_time, 2),
                'unoptimized_query_time': round(unoptimized_time, 2),
                'optimized_query_time': round(optimized_time, 2),
                'performance_improvement': round(improvement, 1),
                'records_returned_unoptimized': len(unoptimized),
                'records_returned_optimized': len(optimized)
            }
            
            logger.info(f"Screening Performance Diagnosis: {report}")
            return report
            
    except Exception as e:
        logger.error(f"Performance diagnosis failed: {e}")
        return {'error': str(e)}

def get_performance_report():
    """Get current performance report"""
    return performance_monitor.get_performance_report()

def reset_performance_metrics():
    """Reset all performance metrics"""
    performance_monitor.metrics = {}
    logger.info("Performance metrics reset")