"""
Database Migration: Add time-based cutoff columns to ChecklistSettings table
Enables filtering of medical data by age (labs, imaging, consults, hospital visits)
"""

from sqlalchemy import text
from app import app, db


def add_checklist_cutoff_columns():
    """Add cutoff columns to ChecklistSettings table"""
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('checklist_settings')]
            
            if 'labs_cutoff_months' not in columns:
                print("Adding labs_cutoff_months column...")
                db.session.execute(text(
                    "ALTER TABLE checklist_settings ADD COLUMN labs_cutoff_months INTEGER DEFAULT 6"
                ))
                
            if 'imaging_cutoff_months' not in columns:
                print("Adding imaging_cutoff_months column...")
                db.session.execute(text(
                    "ALTER TABLE checklist_settings ADD COLUMN imaging_cutoff_months INTEGER DEFAULT 12"
                ))
                
            if 'consults_cutoff_months' not in columns:
                print("Adding consults_cutoff_months column...")
                db.session.execute(text(
                    "ALTER TABLE checklist_settings ADD COLUMN consults_cutoff_months INTEGER DEFAULT 12"
                ))
                
            if 'hospital_cutoff_months' not in columns:
                print("Adding hospital_cutoff_months column...")
                db.session.execute(text(
                    "ALTER TABLE checklist_settings ADD COLUMN hospital_cutoff_months INTEGER DEFAULT 24"
                ))
                
            db.session.commit()
            print("Successfully added checklist cutoff columns!")
            
        except Exception as e:
            print(f"Error adding cutoff columns: {e}")
            db.session.rollback()


if __name__ == "__main__":
    add_checklist_cutoff_columns()
    print("Database migration complete!")