"""
Admin Route Protection Middleware
Restricts access to /admin/* routes to users with admin role
"""

from functools import wraps
from flask import request, session, flash, redirect, url_for
from models import User
from datetime import datetime, timedelta
import logging
from functools import wraps
from flask import session, abort, request, g
from flask_limiter.util import get_remote_address
from structured_logger import log_audit, log_security_event

# Create logger for admin activities
admin_logger = logging.getLogger('admin')

def log_admin_access(action, details=None, user_id=None):
    """Log admin access attempts and actions"""
    log_data = {
        'ip_address': get_remote_address(),
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'session_id': session.get('session_id', 'No session'),
        'endpoint': request.endpoint,
        'user_id': user_id
    }

    if details:
        log_data.update(details)

    # Log as both security and audit event
    log_security_event('admin_access', f"Admin access: {action}", **log_data)
    log_audit('admin_access', 'admin_dashboard', 'attempted', **log_data)

logger = logging.getLogger(__name__)

def admin_required(f):
    """
    Decorator to protect admin routes.
    Requires user to be logged in and have admin role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login'))

        # Get user from database to check admin status
        user = User.query.get(session.get('user_id'))
        if not user:
            session.clear()
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login'))

        # Check if user has admin role
        if not user.is_admin:
            logger.warning(f"Non-admin user {user.username} attempted to access admin route: {request.endpoint}")
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('index'))

        # Log admin access
        logger.info(f"Admin access granted to user {user.username} for route: {request.endpoint}")

        return f(*args, **kwargs)

    return decorated_function

def register_admin_middleware(app):
    """Register admin middleware with Flask app"""

    @app.before_request
    def protect_admin_routes():
        """
        Automatically protect all routes starting with /admin
        """
        # Skip protection for login, static files, and API routes
        if (request.endpoint in ['login', 'static'] or 
            request.path.startswith('/static/') or 
            request.path.startswith('/api/')):
            return

        # Check if this is an admin route
        if request.path.startswith('/admin'):
            # Check if user is logged in
            if not session.get('user_id'):
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('login'))

            # Get user from database to check admin status
            user = User.query.get(session.get('user_id'))
            if not user:
                session.clear()
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('login'))

            # Check if user has admin role
            if not user.is_admin:
                logger.warning(f"Non-admin user {user.username} attempted to access admin route: {request.path}")
                flash('Access denied. Administrator privileges required.', 'error')
                return redirect(url_for('index'))

            # Log admin access
            logger.info(f"Admin middleware: Access granted to user {user.username} for {request.path}")

    logger.info("Admin route protection middleware registered")