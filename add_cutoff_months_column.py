"""
Database Migration: Add cutoff_months column to ChecklistSettings table
Enables setting a general cutoff period for prep sheet items
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text, inspect

def add_cutoff_months_column():
    """Add cutoff_months column to ChecklistSettings table"""
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('checklist_settings')]
            
            if 'cutoff_months' not in columns:
                print("Adding cutoff_months column...")
                db.session.execute(text(
                    "ALTER TABLE checklist_settings ADD COLUMN cutoff_months INTEGER"
                ))
                db.session.commit()
                print("Successfully added cutoff_months column!")
            else:
                print("cutoff_months column already exists!")
                
        except Exception as e:
            print(f"Error adding cutoff_months column: {e}")
            db.session.rollback()
            return False
        
        return True

if __name__ == '__main__':
    success = add_cutoff_months_column()
    if success:
        print("Database migration complete!")
    else:
        print("Database migration failed!")