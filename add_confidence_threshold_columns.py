
#!/usr/bin/env python3
"""
Database Migration: Add confidence threshold columns to ChecklistSettings table
Enables confidence-based color coding for document matching
"""

from sqlalchemy import text
from app import app, db

def add_confidence_threshold_columns():
    """Add confidence_high_threshold and confidence_medium_threshold columns to ChecklistSettings table"""
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('checklist_settings')]
            
            if 'confidence_high_threshold' not in columns:
                print("Adding confidence_high_threshold column...")
                db.session.execute(text(
                    "ALTER TABLE checklist_settings ADD COLUMN confidence_high_threshold FLOAT DEFAULT 0.8"
                ))
                
            if 'confidence_medium_threshold' not in columns:
                print("Adding confidence_medium_threshold column...")
                db.session.execute(text(
                    "ALTER TABLE checklist_settings ADD COLUMN confidence_medium_threshold FLOAT DEFAULT 0.5"
                ))
                
            # Commit the changes
            db.session.commit()
            print("✓ Confidence threshold columns added successfully")
            
        except Exception as e:
            print(f"Error adding confidence threshold columns: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    print("Adding confidence threshold columns to ChecklistSettings table...")
    if add_confidence_threshold_columns():
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
