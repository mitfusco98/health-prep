
import os
import logging

# Minimal logging setup
logging.basicConfig(level=logging.WARNING)

# Fast imports only
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create lightweight app for cold starts
def create_lightweight_app():
    """Create a minimal Flask app for fast cold starts"""
    app = Flask(__name__)
    
    # Minimal essential config only
    app.config.update({
        'SECRET_KEY': os.environ.get('SESSION_SECRET', 'dev-key'),
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///healthcare.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_pre_ping': False,  # Disable ping for faster startup
            'pool_recycle': -1,      # Disable connection recycling at startup
            'connect_args': {'connect_timeout': 5}  # Fast timeout
        }
    })
    
    # Initialize minimal database
    db = SQLAlchemy(app)
    
    # Single health check route for warming
    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'mode': 'lightweight'}, 200
    
    # Lazy load full app on first real request
    @app.before_request
    def load_full_app():
        from flask import request
        if request.endpoint != 'health_check':
            # Import and setup full application
            from app import app as full_app
            return full_app.dispatch_request()
    
    return app

# Create the app
if __name__ == '__main__':
    app = create_lightweight_app()
    app.run(host='0.0.0.0', port=5000)
else:
    # For gunicorn/production
    app = create_lightweight_app()
