import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, g
from models import User
import logging

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(hours=24)

def generate_jwt_token(user_id, username, is_admin=False):
    """
    Generate a JWT token for a user

    Args:
        user_id: User's database ID
        username: User's username
        is_admin: Whether the user has admin privileges

    Returns:
        str: JWT token
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'exp': datetime.utcnow() + JWT_EXPIRATION_DELTA,
        'iat': datetime.utcnow(),
        'iss': 'healthprep-app'
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def decode_jwt_token(token):
    """
    Decode and verify a JWT token

    Args:
        token: JWT token string

    Returns:
        dict: Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None

def jwt_required(f):
    """
    Decorator to require valid JWT token for route access

    Usage:
        @app.route('/protected')
        @jwt_required
        def protected_route():
            # Access current user via g.current_user
            return jsonify({'user': g.current_user.username})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # First try to get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                # Expected format: "Bearer <token>"
                parts = auth_header.split(' ')
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                else:
                    return jsonify({'error': 'Invalid Authorization header format. Expected: Bearer <token>'}), 401
            except Exception as e:
                logger.error(f"Error parsing Authorization header: {str(e)}")
                return jsonify({'error': 'Invalid Authorization header'}), 401

        # If no Authorization header, try to get token from cookie
        if not token:
            token = request.cookies.get('auth_token')

        if not token:
            return jsonify({'error': 'Authorization token is required'}), 401

        # Decode the token
        payload = decode_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Get the user from the database
        user = User.query.get(payload.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401

        # Make user available in the request context
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function

def optional_jwt(f):
    """
    Decorator that makes JWT authentication optional
    If a valid token is provided, g.current_user will be set
    If no token or invalid token, g.current_user will be None
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.current_user = None

        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                parts = auth_header.split(' ')
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                    payload = decode_jwt_token(token)
                    if payload:
                        user = User.query.get(payload.get('user_id'))
                        if user:
                            g.current_user = user
            except Exception as e:
                logger.warning(f"Error processing optional JWT: {str(e)}")

        return f(*args, **kwargs)

    return decorated_function

def admin_required(f):
    """
    Decorator to require admin privileges (must be used with jwt_required)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({'error': 'Authentication required'}), 401

        if not g.current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403

        return f(*args, **kwargs)

    return decorated_function

def refresh_token(current_token):
    """
    Generate a new token with extended expiration

    Args:
        current_token: Current valid JWT token

    Returns:
        str: New JWT token or None if current token is invalid
    """
    payload = decode_jwt_token(current_token)
    if not payload:
        return None

    user = User.query.get(payload.get('user_id'))
    if not user:
        return None

    return generate_jwt_token(user.id, user.username)

