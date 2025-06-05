
from functools import wraps
from flask import flash, redirect, url_for
import logging

logger = logging.getLogger(__name__)

def with_db_retry(max_retries=2):
    """Decorator to retry database operations with connection recovery"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app import db
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    is_db_error = any(term in error_str for term in [
                        'ssl connection has been closed',
                        'connection closed',
                        'server closed the connection',
                        'operationalerror',
                        'connection pool',
                        'database connection'
                    ])
                    
                    if is_db_error and attempt < max_retries:
                        logger.warning(f"Database connection error on attempt {attempt + 1}, retrying: {str(e)}")
                        try:
                            # Try to recover the connection
                            db.session.rollback()
                            db.session.remove()
                            db.engine.dispose()
                        except:
                            pass
                        continue
                    else:
                        # Re-raise the exception if it's not a DB error or we've exhausted retries
                        raise e
            
            return func(*args, **kwargs)
        return wrapper
    return decorator



import functools
import logging
from app import sanitize_input

def sanitize_db_inputs(func):
    """Decorator to sanitize all inputs before database operations"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Sanitize string arguments
        sanitized_args = []
        for arg in args:
            if isinstance(arg, str):
                sanitized_args.append(sanitize_input(arg, max_length=5000))
            else:
                sanitized_args.append(arg)
        
        # Sanitize string keyword arguments
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                sanitized_kwargs[key] = sanitize_input(value, max_length=5000)
            else:
                sanitized_kwargs[key] = value
        
        return func(*sanitized_args, **sanitized_kwargs)
    return wrapper


"""
Database utility functions for the healthcare application
"""

from functools import wraps
from flask import flash
from app import db


def safe_db_operation(func):
    """
    Decorator to ensure database operations are properly handled.
    This wraps a route function with proper transaction handling.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Call the original function
            result = func(*args, **kwargs)
            
            # If the function returns a response without committing,
            # ensure we don't leave a dangling transaction
            if not getattr(result, '_db_committed', False):
                db.session.commit()
                
            return result
        except Exception as e:
            # Roll back the session if there's an error
            db.session.rollback()
            print(f"Database error in {func.__name__}: {str(e)}")
            flash(f"Database error: {str(e)}", "danger")
            # Re-raise the exception or handle it as needed
            raise
    return wrapper


def fresh_session_operation(func):
    """
    Decorator that ensures a fresh database session is used for the operation.
    This can help resolve issues with stale session states.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Close any existing session
        db.session.close()
        
        try:
            # Call the original function
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # Roll back the session if there's an error
            db.session.rollback()
            print(f"Database error in {func.__name__}: {str(e)}")
            flash(f"Database error: {str(e)}", "danger")
            # Re-raise the exception or handle it as needed
            raise
        finally:
            # Always ensure the session is closed properly
            db.session.close()
    return wrapper