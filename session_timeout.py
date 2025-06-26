"""
Session Timeout Management
Handles automatic logout after 10 minutes of inactivity across the entire application
"""

import time
from flask import session, request, redirect, url_for, flash, jsonify
from functools import wraps


def init_session_timeout(app):
    """Initialize session timeout functionality"""
    
    @app.before_request
    def check_session_timeout():
        """Check if session has timed out on every request"""
        
        # Skip timeout check for static files and auth endpoints
        if (request.endpoint and 
            (request.endpoint.startswith('static') or 
             request.endpoint in ['jwt_login', 'jwt_register', 'login', 'register'])):
            return
        
        # Skip for API endpoints that might be called programmatically
        if request.path.startswith('/api/') and request.path not in ['/api/cache/clear']:
            return
            
        current_time = time.time()
        
        # If user is logged in, check for timeout
        if 'user_id' in session:
            last_activity = session.get('last_activity', current_time)
            
            # 10 minutes = 600 seconds
            session_timeout = 600
            
            if current_time - last_activity > session_timeout:
                # Session has timed out
                user_id = session.get('user_id')
                session.clear()
                
                # For AJAX requests, return JSON response
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({
                        'error': 'Session timeout',
                        'message': 'Your session has expired due to inactivity. Please log in again.',
                        'redirect': url_for('login')
                    }), 401
                
                # For regular requests, redirect to login with message
                flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                return redirect(url_for('login'))
            
            # Update last activity time
            session['last_activity'] = current_time
            session.permanent = True  # Make session persistent
    
    @app.context_processor
    def inject_session_info():
        """Inject session timeout info into templates"""
        if 'user_id' in session:
            last_activity = session.get('last_activity', time.time())
            time_remaining = 600 - (time.time() - last_activity)  # 10 minutes
            return {
                'session_timeout_remaining': max(0, int(time_remaining)),
                'session_timeout_warning': time_remaining < 120  # Warning at 2 minutes left
            }
        return {}


def extend_session():
    """Manually extend session activity (called by AJAX)"""
    if 'user_id' in session:
        session['last_activity'] = time.time()
        return True
    return False


def get_session_status():
    """Get current session status for frontend"""
    if 'user_id' not in session:
        return {'logged_in': False}
    
    last_activity = session.get('last_activity', time.time())
    time_remaining = 600 - (time.time() - last_activity)
    
    return {
        'logged_in': True,
        'time_remaining': max(0, int(time_remaining)),
        'warning': time_remaining < 120
    }