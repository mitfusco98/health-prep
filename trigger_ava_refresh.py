#!/usr/bin/env python3
"""
Trigger a refresh for Ava Eichel's screenings to update the web interface
"""

from app import app, db
from models import Patient
from timeout_safe_refresh import timeout_safe_refresh
import logging

def trigger_refresh():
    with app.app_context():
        # Find Ava Eichel
        ava = Patient.query.filter(Patient.first_name.ilike('%ava%')).first()
        if not ava:
            print("Ava Eichel not found")
            return
        
        print(f"Triggering refresh for {ava.first_name} {ava.last_name} (ID: {ava.id})")
        
        # Trigger refresh
        success = timeout_safe_refresh._refresh_single_patient(ava.id)
        print(f"Refresh result: {'Success' if success else 'Failed'}")

if __name__ == "__main__":
    trigger_refresh()