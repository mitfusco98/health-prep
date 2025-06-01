
"""
Logging configuration for different environments (development, production, etc.)
"""
import os
import logging
from structured_logging import setup_structured_logging


def configure_logging(app):
    """Configure logging based on environment"""
    
    # Determine log level from environment - default to WARNING to reduce console clutter
    log_level_str = os.environ.get('LOG_LEVEL', 'WARNING').upper()
    log_level = getattr(logging, log_level_str, logging.WARNING)
    
    # Determine if we're in production
    is_production = os.environ.get('FLASK_ENV', 'development') == 'production'
    
    if is_production:
        # Production: structured JSON logging only
        structured_logger = setup_structured_logging(app, log_level=log_level)
        
        # Configure additional production-specific settings
        app.logger.info("Production logging configuration loaded", extra={
            'event_type': 'system_startup',
            'environment': 'production',
            'log_level': log_level_str
        })
        
    else:
        # Development: hybrid logging (structured + readable console)
        structured_logger = setup_structured_logging(app, log_level=log_level)
        
        # Add a more readable console handler for development
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)
        
        # Add to root logger for development readability
        dev_logger = logging.getLogger('dev_console')
        dev_logger.addHandler(console_handler)
        dev_logger.setLevel(logging.DEBUG)
        
        app.logger.info("Development logging configuration loaded", extra={
            'event_type': 'system_startup',
            'environment': 'development',
            'log_level': log_level_str
        })
    
    return structured_logger


def log_application_startup(app, structured_logger):
    """Log application startup information"""
    startup_info = {
        'event_type': 'application_startup',
        'flask_env': os.environ.get('FLASK_ENV', 'development'),
        'database_url': app.config.get('SQLALCHEMY_DATABASE_URI', '').split('@')[-1] if '@' in app.config.get('SQLALCHEMY_DATABASE_URI', '') else 'sqlite',
        'debug_mode': app.debug,
        'testing_mode': app.testing,
        'csrf_enabled': app.config.get('WTF_CSRF_ENABLED', False),
        'session_lifetime': str(app.config.get('PERMANENT_SESSION_LIFETIME', 'default'))
    }
    
    structured_logger.logger.info(
        "Healthcare management application started",
        extra=startup_info
    )


def log_application_shutdown(structured_logger):
    """Log application shutdown"""
    structured_logger.logger.info(
        "Healthcare management application shutting down",
        extra={
            'event_type': 'application_shutdown',
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0, msg='', args=(), exc_info=None
            ))
        }
    )
