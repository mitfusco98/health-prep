from flask import request, jsonify
from werkzeug.security import check_password_hash
from app import app, db, csrf
from models import User
from jwt_utils import generate_jwt_token, jwt_required, refresh_token
import logging

logger = logging.getLogger(__name__)

@app.route('/api/auth/login', methods=['POST'])
@csrf.exempt
def jwt_login():
    """
    JWT-based login endpoint

    Expected JSON payload:
    {
        "username": "user@example.com",
        "password": "password123"
    }

    Returns:
    {
        "access_token": "jwt_token_here",
        "user": {
            "id": 1,
            "username": "user@example.com",
            "is_admin": false
        }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password are required'}), 400

        # Validate field types and lengths
        if not isinstance(data['username'], str) or not isinstance(data['password'], str):
            return jsonify({'error': 'Username and password must be strings'}), 400

        username = data['username'].strip()
        password = data['password']

        # Validate username format and length
        if len(username) < 3 or len(username) > 100:
            return jsonify({'error': 'Username must be 3-100 characters long'}), 400

        # Validate password length
        if len(password) < 6 or len(password) > 200:
            return jsonify({'error': 'Password must be 6-200 characters long'}), 400

        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for username: {username}")
            return jsonify({'error': 'Invalid username or password'}), 401

        # Generate JWT token with admin role
        access_token = generate_jwt_token(user.id, user.username, user.is_admin)

        logger.info(f"Successful JWT login for user: {user.username}")

        response = jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin
            }
        })

        # Set the JWT token as an HTTP-only cookie
        response.set_cookie(
            'auth_token',
            access_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            path='/'
        )

        return response, 200

    except Exception as e:
        import traceback
        import uuid
        
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"JWT Login Error [{error_id}]:")
        logger.error(f"Username attempted: {data.get('username', 'unknown') if 'data' in locals() else 'unknown'}")
        logger.error(f"Remote Address: {request.remote_addr}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Stack Trace:\n{traceback.format_exc()}")
        
        return jsonify({
            'error': 'Authentication service temporarily unavailable',
            'error_id': error_id
        }), 500

@app.route('/api/auth/register', methods=['POST'])
@csrf.exempt
def jwt_register():
    """
    JWT-based registration endpoint

    Expected JSON payload:
    {
        "username": "newuser",
        "email": "user@example.com",
        "password": "password123"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Validate field types
        for field in required_fields:
            if not isinstance(data[field], str):
                return jsonify({'error': f'{field} must be a string'}), 400

        username = data['username'].strip()
        email = data['email'].strip()
        password = data['password']

        # Validate username
        if len(username) < 3 or len(username) > 50:
            return jsonify({'error': 'Username must be 3-50 characters long'}), 400

        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            return jsonify({'error': 'Username can only contain letters, numbers, dots, hyphens, and underscores'}), 400

        # Validate email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email) or len(email) > 254:
            return jsonify({'error': 'Invalid email format'}), 400

        # Validate password
        if len(password) < 6 or len(password) > 200:
            return jsonify({'error': 'Password must be 6-200 characters long'}), 400

        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            return jsonify({'error': 'Username or email already exists'}), 409

        # Create new user
        new_user = User(
            username=username,
            email=email,
            is_admin=False
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Generate JWT token for the new user
        access_token = generate_jwt_token(new_user.id, new_user.username)

        logger.info(f"New user registered: {new_user.username}")

        response = jsonify({
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'is_admin': new_user.is_admin
            }
        })

        # Set the JWT token as an HTTP-only cookie
        response.set_cookie(
            'auth_token',
            access_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            path='/'
        )

        return response, 201

    except Exception as e:
        import traceback
        import uuid
        
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"JWT Registration Error [{error_id}]:")
        logger.error(f"Username attempted: {data.get('username', 'unknown') if 'data' in locals() else 'unknown'}")
        logger.error(f"Email attempted: {data.get('email', 'unknown') if 'data' in locals() else 'unknown'}")
        logger.error(f"Remote Address: {request.remote_addr}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Stack Trace:\n{traceback.format_exc()}")
        
        db.session.rollback()
        return jsonify({
            'error': 'Registration service temporarily unavailable',
            'error_id': error_id
        }), 500

@app.route('/api/auth/refresh', methods=['POST'])
@csrf.exempt
@jwt_required
def jwt_refresh():
    """
    Refresh JWT token endpoint
    Requires a valid JWT token in Authorization header

    Returns:
    {
        "access_token": "new_jwt_token_here"
    }
    """
    try:
        # Get current token from the cookie
        token = request.cookies.get('auth_token')

        if not token:
            return jsonify({'error': 'Current token required'}), 400

        # Generate new token
        new_token = refresh_token(token)

        if not new_token:
            return jsonify({'error': 'Unable to refresh token'}), 400
        
        response = jsonify({})
        response.set_cookie(
            'auth_token',
            new_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            path='/'
        )

        return response, 200

    except Exception as e:
        import traceback
        import uuid
        
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"JWT Refresh Error [{error_id}]:")
        logger.error(f"Remote Address: {request.remote_addr}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Stack Trace:\n{traceback.format_exc()}")
        
        return jsonify({
            'error': 'Token refresh service temporarily unavailable',
            'error_id': error_id
        }), 500

@app.route('/api/auth/verify', methods=['GET'])
@csrf.exempt
@jwt_required
def jwt_verify():
    """
    Verify JWT token and return user information

    Returns:
    {
        "user": {
            "id": 1,
            "username": "user@example.com",
            "is_admin": false
        },
        "valid": true
    }
    """
    try:
        from flask import g

        return jsonify({
            'valid': True,
            'user': {
                'id': g.current_user.id,
                'username': g.current_user.username,
                'email': g.current_user.email,
                'is_admin': g.current_user.is_admin
            }
        }), 200

    except Exception as e:
        import traceback
        import uuid
        
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"JWT Verification Error [{error_id}]:")
        logger.error(f"Remote Address: {request.remote_addr}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Stack Trace:\n{traceback.format_exc()}")
        
        return jsonify({
            'error': 'Token verification service temporarily unavailable',
            'error_id': error_id
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
@csrf.exempt
def jwt_logout():
    """
    Logout endpoint that clears the HTTP-only cookie
    """
    try:
        response = jsonify({
            'success': True,
            'message': 'Logout successful'
        })

        # Clear the HTTP-only cookie
        response.set_cookie(
            'auth_token',
            '',
            max_age=0,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            path='/'
        )

        return response, 200

    except Exception as e:
        import traceback
        import uuid
        
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"JWT Logout Error [{error_id}]:")
        logger.error(f"Remote Address: {request.remote_addr}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Stack Trace:\n{traceback.format_exc()}")
        
        return jsonify({
            'error': 'Logout service temporarily unavailable',
            'error_id': error_id
        }), 500