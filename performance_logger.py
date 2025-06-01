
import time
from functools import wraps
from structured_logger import log_performance

def log_execution_time(operation_name=None):
    """Decorator to log execution time of functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                log_performance(op_name, duration_ms, 
                              function=func.__name__, 
                              module=func.__module__)
        return wrapper
    return decorator

def log_database_operation(operation_type):
    """Decorator specifically for database operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                log_performance(f"db_{operation_type}", duration_ms,
                              operation_type=operation_type,
                              function=func.__name__,
                              table=getattr(args[0], '__tablename__', 'unknown') if args else 'unknown')
        return wrapper
    return decorator
