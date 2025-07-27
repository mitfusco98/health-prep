#!/usr/bin/env python3
"""
Simple system-wide refresh to apply new frequency-based filtering to all screenings
"""

from app import app
from timeout_safe_refresh import timeout_safe_refresh

def trigger_system_refresh():
    with app.app_context():
        print("Starting system-wide refresh to apply new frequency-based filtering...")
        
        # Use the existing safe_smart_refresh method
        success_count, total_patients, error_message = timeout_safe_refresh.safe_smart_refresh()
        
        print(f"Refresh completed:")
        print(f"  - Processed patients: {total_patients}")
        print(f"  - Successful updates: {success_count}")
        if error_message:
            print(f"  - Error: {error_message}")
        else:
            print(f"  - All screenings updated with new frequency-based filtering")

if __name__ == "__main__":
    trigger_system_refresh()