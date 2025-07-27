#!/usr/bin/env python3
"""
System-wide refresh to apply new frequency-based filtering to all completed screenings
"""

from app import app, db
from models import Patient, Screening
from timeout_safe_refresh import timeout_safe_refresh
import logging

def refresh_all_completed_screenings():
    with app.app_context():
        # Get all patients with completed screenings
        completed_screenings = db.session.query(Screening).filter(
            Screening.status == 'Complete'
        ).all()
        
        print(f"Found {len(completed_screenings)} completed screenings")
        
        # Get unique patient IDs from completed screenings
        patient_ids = set(screening.patient_id for screening in completed_screenings)
        print(f"Refreshing {len(patient_ids)} patients with completed screenings")
        
        success_count = 0
        error_count = 0
        
        for patient_id in patient_ids:
            try:
                patient = Patient.query.get(patient_id)
                if patient:
                    print(f"Refreshing {patient.first_name} {patient.last_name} (ID: {patient_id})")
                    success = timeout_safe_refresh._refresh_single_patient(patient_id)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        print(f"  - Failed to refresh patient {patient_id}")
                else:
                    print(f"Patient {patient_id} not found")
                    error_count += 1
            except Exception as e:
                print(f"Error refreshing patient {patient_id}: {e}")
                error_count += 1
        
        print(f"\nRefresh complete:")
        print(f"  - Success: {success_count} patients")
        print(f"  - Errors: {error_count} patients")

if __name__ == "__main__":
    refresh_all_completed_screenings()