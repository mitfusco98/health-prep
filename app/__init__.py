# Healthcare Application Package
# Re-export main app and db to maintain existing functionality
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, db

__all__ = ['app', 'db']