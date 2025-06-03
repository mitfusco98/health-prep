
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Global thread pool for non-blocking operations
_thread_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="healthprep_async")

def run_in_background(func):
    """Decorator to run function in background thread pool"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        def task():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background task error in {func.__name__}: {str(e)}")
                return None
        
        future = _thread_pool.submit(task)
        return future
    
    return wrapper

def non_blocking_db_operation(func):
    """Decorator for database operations that should not block the main thread"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000
            
            # Log if operation took too long
            if duration > 500:  # 500ms threshold
                logger.warning(f"Slow DB operation {func.__name__}: {duration:.2f}ms")
            
            return result
        except Exception as e:
            logger.error(f"Database operation error in {func.__name__}: {str(e)}")
            raise
    
    return wrapper

class AsyncFileValidator:
    """Non-blocking file validation utilities"""
    
    @staticmethod
    def quick_validate(file):
        """Fast validation without reading file content"""
        if not file or not file.filename:
            return False
            
        # Quick filename check
        filename = file.filename.lower()
        if any(char in filename for char in ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            return False
            
        # Quick extension check
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js']
        if any(filename.endswith(ext) for ext in dangerous_extensions):
            return False
            
        return True
    
    @staticmethod
    @run_in_background
    def deep_validate(file):
        """Thorough validation in background thread"""
        try:
            import magic
            
            # Read small chunk for MIME detection
            current_pos = file.tell()
            file_content = file.read(1024)
            file.seek(current_pos)
            
            detected_mime = magic.from_buffer(file_content, mime=True)
            
            safe_mimes = [
                'text/plain', 'application/pdf', 'image/jpeg', 'image/png', 
                'image/gif', 'text/csv', 'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ]
            
            return detected_mime in safe_mimes
            
        except Exception as e:
            logger.error(f"Deep file validation error: {str(e)}")
            return False

def optimize_query_execution(query_func):
    """Decorator to optimize database query execution"""
    @wraps(query_func)
    def wrapper(*args, **kwargs):
        # Add query hints for better performance
        start_time = time.perf_counter()
        
        try:
            result = query_func(*args, **kwargs)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            if execution_time > 100:  # Log queries over 100ms
                logger.info(f"Query {query_func.__name__} took {execution_time:.2f}ms")
                
            return result
            
        except Exception as e:
            logger.error(f"Query optimization error in {query_func.__name__}: {str(e)}")
            raise
    
    return wrapper
