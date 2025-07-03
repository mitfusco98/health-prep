#!/usr/bin/env python3
"""
Database Migration: Add screening_cutoffs column to ChecklistSettings table
Enables individual cutoff settings for each screening type
"""
import os
from app import app, db
from models import ChecklistSettings

def add_screening_cutoffs_column():
    """Add screening_cutoffs column to ChecklistSettings table"""
    try:
        with app.app_context():
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('checklist_settings')]
            
            if 'screening_cutoffs' not in columns:
                print("Adding screening_cutoffs column to checklist_settings table...")
                
                # Add the column using modern SQLAlchemy syntax
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE checklist_settings ADD COLUMN screening_cutoffs TEXT'))
                    conn.commit()
                
                print("✓ screening_cutoffs column added successfully")
            else:
                print("✓ screening_cutoffs column already exists")
                
    except Exception as e:
        print(f"Error adding screening_cutoffs column: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Adding screening_cutoffs column to ChecklistSettings table...")
    if add_screening_cutoffs_column():
        print("Migration completed successfully!")
    else:
        print("Migration failed!")