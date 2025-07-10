#!/usr/bin/env python3
"""
Database Migration: Replace 'priority' column with 'status' column in Screening table
Supports automated screening status determination: 'Due', 'Due Soon', 'Incomplete', 'Complete'
"""

from app import app, db
from models import Screening

def migrate_priority_to_status():
    """Replace priority column with status column in Screening table"""
    with app.app_context():
        try:
            # Check if status column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('screening')]
            
            if 'status' not in columns:
                print("Adding 'status' column to Screening table...")
                # Add status column using SQLAlchemy 2.0 syntax
                with db.engine.connect() as conn:
                    conn.execute(db.text("ALTER TABLE screening ADD COLUMN status VARCHAR(20) DEFAULT 'Incomplete'"))
                    conn.commit()
                
                # Migrate existing priority values to appropriate status values
                print("Migrating existing priority values to status...")
                
                # Map priority to status (this is a reasonable conversion)
                priority_to_status_map = {
                    'High': 'Due',
                    'Medium': 'Due Soon', 
                    'Low': 'Incomplete'
                }
                
                # Update existing records
                with db.engine.connect() as conn:
                    for old_priority, new_status in priority_to_status_map.items():
                        conn.execute(db.text(f"""
                            UPDATE screening 
                            SET status = :new_status 
                            WHERE priority = :old_priority
                        """), {"new_status": new_status, "old_priority": old_priority})
                    
                    # Set any remaining NULL priorities to 'Incomplete'
                    conn.execute(db.text("UPDATE screening SET status = 'Incomplete' WHERE priority IS NULL OR priority = ''"))
                    conn.commit()
                
                print("Migration of priority values completed.")
            else:
                print("Status column already exists.")
            
            # Check if priority column exists and drop it
            if 'priority' in columns:
                print("Dropping 'priority' column...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE screening DROP COLUMN priority'))
                    conn.commit()
                print("Priority column dropped successfully.")
            else:
                print("Priority column already removed.")
                
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            raise

def clear_existing_screenings():
    """Clear all existing screening records to prepare for automated generation"""
    with app.app_context():
        try:
            count = db.session.query(Screening).count()
            print(f"Found {count} existing screening records")
            
            if count > 0:
                print("Clearing existing screening records...")
                db.session.query(Screening).delete()
                db.session.commit()
                print(f"Cleared {count} screening records")
            else:
                print("No existing screening records to clear")
                
        except Exception as e:
            print(f"Error clearing screenings: {e}")
            raise

if __name__ == "__main__":
    print("=== Screening System Migration ===")
    print("This will:")
    print("1. Replace 'priority' column with 'status' column")
    print("2. Clear existing manual screening records") 
    print("3. Prepare for automated screening generation")
    
    # Auto-proceed for non-interactive execution
    migrate_priority_to_status()
    clear_existing_screenings()
    print("\n✓ Migration completed - system ready for automated screening generation")