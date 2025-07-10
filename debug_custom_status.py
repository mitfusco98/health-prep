#!/usr/bin/env python3
"""
Debug script to test custom status options form submission
"""

from app import app, db
from models import ChecklistSettings

def test_custom_status_rendering():
    """Test how custom status options are rendered"""
    with app.app_context():
        settings = ChecklistSettings.query.first()
        if settings:
            print(f"Database custom_status_options: {settings.custom_status_options}")
            print(f"Custom status list: {settings.custom_status_list}")
            
            # Simulate template rendering
            if settings.custom_status_list:
                print("\nTemplate would render:")
                for i, status in enumerate(settings.custom_status_list):
                    print(f'  <input type="hidden" name="custom_status_options" value="{status}">')
                    
            # Test what form.getlist would return
            print(f"\nform.getlist('custom_status_options') would return:")
            print(f"  {settings.custom_status_list}")
        else:
            print("No settings found")

if __name__ == "__main__":
    test_custom_status_rendering()