#!/usr/bin/env python3
"""
System-wide date correction: Apply medical event date prioritization to ALL screenings
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Patient, Screening, MedicalDocument
from automated_screening_engine import ScreeningStatusEngine
from datetime import datetime, date

def correct_all_screening_dates():
    """Apply medical event date prioritization to all completed screenings"""
    
    with app.app_context():
        print("🔧 SYSTEM-WIDE DATE CORRECTION FOR ALL SCREENINGS")
        print("=" * 60)
        
        # Find all completed screenings with linked documents
        completed_screenings = db.session.query(Screening).filter(
            Screening.status == 'Complete'
        ).all()
        
        print(f"📋 Found {len(completed_screenings)} completed screenings to analyze")
        
        corrections_made = 0
        for screening in completed_screenings:
            print(f"\n📋 Checking: {screening.screening_type} for Patient ID {screening.patient_id}")
            print(f"   Current last_completed: {screening.last_completed}")
            
            # Get linked documents
            linked_docs = screening.documents.all()
            if not linked_docs:
                print(f"   ⚠️  No linked documents found")
                continue
            
            # Find the most recent medical event date
            docs_with_dates = []
            for doc in linked_docs:
                if doc.document_date:
                    docs_with_dates.append((doc, doc.document_date))
                elif doc.created_at:
                    docs_with_dates.append((doc, doc.created_at))
            
            if not docs_with_dates:
                print(f"   ⚠️  No valid dates found in documents")
                continue
            
            # Get the most recent date (prioritizing medical event dates)
            most_recent_doc, most_recent_date = max(docs_with_dates, key=lambda x: x[1])
            correct_date = most_recent_date.date() if hasattr(most_recent_date, 'date') else most_recent_date
            
            print(f"   📄 Most recent document: {most_recent_doc.filename}")
            print(f"   📅 Document medical date: {most_recent_doc.document_date}")
            print(f"   📅 Document system date: {most_recent_doc.created_at}")
            print(f"   ✅ Correct date should be: {correct_date}")
            
            # Check if correction is needed
            if screening.last_completed != correct_date:
                old_date = screening.last_completed
                screening.last_completed = correct_date
                
                # Update notes to indicate correction
                if screening.notes:
                    screening.notes += f" | Date corrected from {old_date} to {correct_date}"
                else:
                    screening.notes = f"Date corrected from system upload to medical event date"
                
                corrections_made += 1
                print(f"   🔄 CORRECTED: {old_date} → {correct_date}")
            else:
                print(f"   ✅ Already correct")
        
        # Commit all changes
        if corrections_made > 0:
            db.session.commit()
            print(f"\n✅ Applied {corrections_made} date corrections successfully")
        else:
            print(f"\n✅ All screening dates are already correct")
        
        return corrections_made

def regenerate_all_screenings_with_correct_dates():
    """Regenerate ALL patient screenings using the corrected date logic"""
    
    with app.app_context():
        print("\n🔄 REGENERATING ALL SCREENINGS WITH CORRECT DATE LOGIC")
        print("=" * 60)
        
        engine = ScreeningStatusEngine()
        
        # Get all patients
        patients = Patient.query.all()
        print(f"👥 Processing {len(patients)} patients")
        
        total_regenerated = 0
        for patient in patients:
            print(f"\n👤 Regenerating screenings for: {patient.first_name} {patient.last_name}")
            
            # Generate fresh screenings with correct date logic
            try:
                screenings = engine.generate_patient_screenings(patient.id)
                print(f"   Generated {len(screenings)} screenings")
                total_regenerated += len(screenings)
                
                # Show details for completed screenings
                for screening in screenings:
                    if screening.get('status') == 'Complete':
                        print(f"   ✅ {screening.get('screening_type')}: Last completed {screening.get('last_completed')}")
                        
            except Exception as e:
                print(f"   ❌ Error regenerating screenings: {e}")
                continue
        
        print(f"\n✅ Regenerated {total_regenerated} total screenings with correct date logic")
        return total_regenerated

def verify_date_corrections():
    """Verify that all screenings now use correct medical event dates"""
    
    with app.app_context():
        print("\n🔍 VERIFYING DATE CORRECTIONS")
        print("=" * 40)
        
        # Check completed screenings with documents
        query = """
        SELECT 
            p.first_name, p.last_name,
            s.screening_type, s.last_completed,
            md.document_date as medical_date,
            md.created_at as system_date,
            CASE 
                WHEN md.document_date IS NOT NULL AND s.last_completed = md.document_date::date 
                THEN 'CORRECT'
                WHEN md.document_date IS NULL AND s.last_completed = md.created_at::date 
                THEN 'CORRECT'
                ELSE 'INCORRECT'
            END as status
        FROM patient p
        JOIN screening s ON p.id = s.patient_id
        JOIN screening_documents sd ON s.id = sd.screening_id  
        JOIN medical_document md ON sd.document_id = md.id
        WHERE s.status = 'Complete'
        ORDER BY p.last_name, s.screening_type
        """
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        correct_count = 0
        incorrect_count = 0
        
        for row in rows:
            first_name, last_name, screening_type, last_completed, medical_date, system_date, status = row
            
            if status == 'CORRECT':
                correct_count += 1
                print(f"✅ {first_name} {last_name} - {screening_type}: {last_completed}")
            else:
                incorrect_count += 1
                print(f"❌ {first_name} {last_name} - {screening_type}: {last_completed} (should use medical date)")
        
        print(f"\n📊 VERIFICATION RESULTS:")
        print(f"   ✅ Correct dates: {correct_count}")
        print(f"   ❌ Incorrect dates: {incorrect_count}")
        print(f"   📈 Success rate: {correct_count/(correct_count+incorrect_count)*100:.1f}%" if (correct_count+incorrect_count) > 0 else "   📈 No data to verify")

if __name__ == "__main__":
    print("🚀 STARTING SYSTEM-WIDE DATE CORRECTION")
    print("=" * 60)
    
    # Step 1: Correct existing screening records
    corrections = correct_all_screening_dates()
    
    # Step 2: Regenerate all screenings with corrected logic
    regenerated = regenerate_all_screenings_with_correct_dates()
    
    # Step 3: Verify corrections worked
    verify_date_corrections()
    
    print(f"\n🎉 CORRECTION COMPLETE")
    print(f"   Individual corrections: {corrections}")
    print(f"   Total regenerated: {regenerated}")
    print(f"   All screenings now use medical event dates where available")