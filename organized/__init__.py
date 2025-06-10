"""
Organized Healthcare Application Structure
Complete reorganization of healthcare app into maintainable modules
"""

from .routes import register_organized_blueprints
from .middleware.admin_logging import register_admin_logging_middleware

def init_organized_app(app):
    """Initialize the organized structure with the Flask app"""
    try:
        # Register organized blueprints
        register_organized_blueprints(app)
        
        # Register middleware
        register_admin_logging_middleware(app)
        
        print("✅ Organized healthcare application initialized successfully")
        return True
        
    except ImportError as e:
        print(f"⚠️  Some organized modules not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Error initializing organized app: {e}")
        return False