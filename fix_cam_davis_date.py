#!/usr/bin/env python3
"""
Fix Cam Davis's eye exam screening to use the correct document date
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Patient, Screening, MedicalDocument
from datetime import datetime, date

def fix_cam_davis_eye_exam_date():
    """Fix Cam Davis's eye exam screening to show correct last completed date"""
    
    with app.app_context():
        print("🔧 FIXING CAM DAVIS'S EYE EXAM DATE")
        print("=" * 50)
        
        # Find Cam Davis
        cam = Patient.query.filter(
            Patient.first_name.ilike('Cam'),
            Patient.last_name.ilike('Davis')
        ).first()
        
        if not cam:
            print("❌ Cam Davis not found")
            return
        
        print(f"👤 Patient: {cam.first_name} {cam.last_name}")
        
        # Find eye exam screening
        eye_exam_screening = Screening.query.filter_by(
            patient_id=cam.id
        ).filter(
            Screening.screening_type.ilike('%eye%')
        ).first()
        
        if not eye_exam_screening:
            print("❌ Eye exam screening not found")
            return
        
        print(f"📋 Screening: {eye_exam_screening.screening_type}")
        print(f"📅 Current last_completed: {eye_exam_screening.last_completed}")
        print(f"📅 Current status: {eye_exam_screening.status}")
        
        # Get the linked documents
        linked_docs = eye_exam_screening.documents.all()
        print(f"📄 Linked documents: {len(linked_docs)}")
        
        # Find the document with the actual medical event date
        correct_date = None
        for doc in linked_docs:
            print(f"\n📄 Document: {doc.filename}")
            print(f"   System upload date (created_at): {doc.created_at}")
            print(f"   Medical event date (document_date): {doc.document_date}")
            
            if doc.document_date:
                if not correct_date or doc.document_date > correct_date:
                    correct_date = doc.document_date
        
        if correct_date:
            # Convert to date if it's a datetime
            if hasattr(correct_date, 'date'):
                correct_date = correct_date.date()
            
            print(f"\n✅ Found correct medical event date: {correct_date}")
            
            # Update the screening
            old_date = eye_exam_screening.last_completed
            eye_exam_screening.last_completed = correct_date
            
            # Update notes to reflect the correction
            eye_exam_screening.notes = f"Corrected last_completed date from system upload date to actual medical event date"
            
            db.session.commit()
            
            print(f"✅ Updated last_completed:")
            print(f"   Before: {old_date}")
            print(f"   After: {correct_date}")
            print(f"✅ Updated notes to reflect correction")
            
        else:
            print("❌ No document_date found in linked documents")

def test_automated_screening_engine_date_fix():
    """Test that the automated screening engine now uses correct dates"""
    
    with app.app_context():
        print("\n🧪 TESTING AUTOMATED SCREENING ENGINE DATE FIX")
        print("=" * 50)
        
        from automated_screening_engine import ScreeningStatusEngine
        
        # Find Cam Davis again
        cam = Patient.query.filter(
            Patient.first_name.ilike('Cam'),
            Patient.last_name.ilike('Davis')
        ).first()
        
        if not cam:
            print("❌ Cam Davis not found")
            return
        
        engine = ScreeningStatusEngine()
        
        # Generate fresh screenings for Cam
        screenings = engine.generate_patient_screenings(cam.id)
        
        print(f"👤 Generated {len(screenings)} screenings for {cam.first_name} {cam.last_name}")
        
        # Find the eye exam screening
        for screening in screenings:
            if 'eye' in screening.get('screening_type', '').lower():
                print(f"\n📋 Eye Exam Screening:")
                print(f"   Type: {screening.get('screening_type')}")
                print(f"   Status: {screening.get('status')}")
                print(f"   Last Completed: {screening.get('last_completed')}")
                print(f"   Due Date: {screening.get('due_date')}")
                print(f"   Notes: {screening.get('notes')}")
                
                # Verify the date is correct
                if screening.get('last_completed'):
                    try:
                        last_completed_date = datetime.strptime(screening.get('last_completed'), '%Y-%m-%d').date()
                        expected_date = date(2025, 1, 2)  # January 2, 2025
                        
                        if last_completed_date == expected_date:
                            print(f"✅ SUCCESS: Date correctly shows {expected_date}")
                        else:
                            print(f"❌ ISSUE: Expected {expected_date}, got {last_completed_date}")
                    except ValueError as e:
                        print(f"❌ Date parsing error: {e}")

if __name__ == "__main__":
    fix_cam_davis_eye_exam_date()
    test_automated_screening_engine_date_fix()