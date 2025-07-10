
#!/usr/bin/env python3
"""
Migration script to update status options from 'sent_incomplete' to 'incomplete'
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import ChecklistSettings

def migrate_status_options():
    """Update existing status options to use 'incomplete' instead of 'sent_incomplete'"""
    
    with app.app_context():
        print("Starting status options migration...")
        
        # Get all checklist settings
        settings = ChecklistSettings.query.all()
        
        for setting in settings:
            if setting.status_options:
                # Replace 'sent_incomplete' with 'incomplete'
                old_options = setting.status_options
                new_options = old_options.replace('sent_incomplete', 'incomplete')
                
                if old_options != new_options:
                    print(f"Updating status options from '{old_options}' to '{new_options}'")
                    setting.status_options = new_options
                else:
                    print(f"No changes needed for setting ID {setting.id}")
            else:
                print(f"Setting ID {setting.id} has no status options set")
        
        # Commit changes
        try:
            db.session.commit()
            print("✓ Status options migration completed successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error during migration: {e}")
            return False
        
        return True

if __name__ == "__main__":
    success = migrate_status_options()
    if success:
        print("\nMigration completed successfully!")
        print("The status option 'sent & incomplete' has been changed to 'incomplete'")
    else:
        print("\nMigration failed!")
        sys.exit(1)
