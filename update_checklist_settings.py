#!/usr/bin/env python3
"""
Script to update the checklist_settings table with a new custom_status_options column
"""
from app import app, db
from sqlalchemy import Column, Text
from sqlalchemy.exc import OperationalError

def add_custom_status_column():
    """Add custom_status_options column to checklist_settings table"""
    with app.app_context():
        print("Adding custom_status_options column to checklist_settings table...")
        try:
            # Execute raw SQL to add the column using proper SQLAlchemy text() function
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE checklist_settings ADD COLUMN IF NOT EXISTS custom_status_options TEXT'))
            db.session.commit()
            print("Column added successfully!")
        except OperationalError as e:
            db.session.rollback()
            print(f"Error adding column: {e}")
            
        # Migrate 'custom' setting from status_options to custom_status_options if needed
        from models import ChecklistSettings
        settings = ChecklistSettings.query.first()
        if settings:
            if 'custom' in settings.status_options_list:
                # Remove 'custom' from status_options
                options = settings.status_options_list
                if 'custom' in options:
                    options.remove('custom')
                settings.status_options = ','.join(options)
                db.session.commit()
                print("Removed 'custom' option from status_options")
            
            # Initialize custom_status_options with some default values if empty
            if not settings.custom_status_options:
                settings.custom_status_options = "Needs Follow Up,Patient Declined,Ordered"
                db.session.commit()
                print("Added default custom status options")
        else:
            print("No checklist settings found in database")

if __name__ == "__main__":
    add_custom_status_column()
    print("Database update complete!")