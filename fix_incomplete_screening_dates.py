#!/usr/bin/env python3
"""
Fix Incomplete screenings that incorrectly have last_completed dates
If no documents match screening criteria, there should be no completion date
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Patient, Screening, MedicalDocument
from datetime import datetime, date

def fix_incomplete_screenings_with_dates():
    """Remove last_completed dates from Incomplete screenings with no matched documents"""
    
    with app.app_context():
        print("🔧 FIXING INCOMPLETE SCREENINGS WITH INVALID COMPLETION DATES")
        print("=" * 70)
        
        # Find all Incomplete screenings that have last_completed dates
        incomplete_with_dates = db.session.query(Screening).filter(
            Screening.status == 'Incomplete',
            Screening.last_completed.isnot(None)
        ).all()
        
        print(f"📋 Found {len(incomplete_with_dates)} Incomplete screenings with completion dates")
        
        fixes_applied = 0
        for screening in incomplete_with_dates:
            # Get patient info
            patient = Patient.query.get(screening.patient_id)
            
            print(f"\n📋 Checking: {screening.screening_type} for {patient.first_name} {patient.last_name}")
            print(f"   Status: {screening.status}")
            print(f"   Last Completed: {screening.last_completed}")
            
            # Check if screening has any linked documents
            linked_docs = screening.documents.all()
            print(f"   Linked Documents: {len(linked_docs)}")
            
            if len(linked_docs) == 0:
                # No documents linked - should not have completion date
                print(f"   ❌ ISSUE: Incomplete screening has completion date but no linked documents")
                
                old_date = screening.last_completed
                screening.last_completed = None
                
                # Update notes to explain the fix
                if screening.notes:
                    screening.notes += f" | Removed invalid completion date {old_date} (no matching documents)"
                else:
                    screening.notes = f"Removed invalid completion date {old_date} - no documents fulfill criteria"
                
                fixes_applied += 1
                print(f"   ✅ FIXED: Removed completion date {old_date}")
                
            else:
                # Has documents but marked incomplete - investigate
                print(f"   ⚠️  WARNING: Incomplete screening has {len(linked_docs)} documents")
                for doc in linked_docs:
                    print(f"      - {doc.filename}")
                print(f"   → This may need status review")
        
        # Commit all fixes
        if fixes_applied > 0:
            db.session.commit()
            print(f"\n✅ Applied {fixes_applied} fixes successfully")
        else:
            print(f"\n✅ No fixes needed - all Incomplete screenings are correct")
        
        return fixes_applied

def validate_screening_logic():
    """Validate that screening status and completion dates are consistent"""
    
    with app.app_context():
        print("\n🔍 VALIDATING SCREENING LOGIC CONSISTENCY")
        print("=" * 50)
        
        # Check all screenings for logical consistency
        all_screenings = Screening.query.all()
        
        consistent_count = 0
        inconsistent_count = 0
        
        for screening in all_screenings:
            patient = Patient.query.get(screening.patient_id)
            linked_docs = screening.documents.all()
            
            # Define consistency rules
            is_consistent = True
            issues = []
            
            # Rule 1: Complete status must have documents
            if screening.status == 'Complete' and len(linked_docs) == 0:
                is_consistent = False
                issues.append("Complete status without documents")
            
            # Rule 2: Incomplete status should not have last_completed if no documents
            if screening.status == 'Incomplete' and screening.last_completed and len(linked_docs) == 0:
                is_consistent = False
                issues.append("Incomplete status with completion date but no documents")
            
            # Rule 3: If has documents and last_completed, should not be Incomplete
            if len(linked_docs) > 0 and screening.last_completed and screening.status == 'Incomplete':
                is_consistent = False
                issues.append("Has documents and completion date but marked Incomplete")
            
            if is_consistent:
                consistent_count += 1
            else:
                inconsistent_count += 1
                print(f"❌ {patient.first_name} {patient.last_name} - {screening.screening_type}")
                print(f"   Status: {screening.status}, Documents: {len(linked_docs)}, Last Completed: {screening.last_completed}")
                for issue in issues:
                    print(f"   Issue: {issue}")
        
        print(f"\n📊 VALIDATION RESULTS:")
        print(f"   ✅ Consistent screenings: {consistent_count}")
        print(f"   ❌ Inconsistent screenings: {inconsistent_count}")
        print(f"   📈 Consistency rate: {consistent_count/(consistent_count+inconsistent_count)*100:.1f}%" if (consistent_count+inconsistent_count) > 0 else "   📈 No screenings to validate")

def check_specific_incomplete_cases():
    """Check specific cases of Incomplete screenings with completion dates"""
    
    with app.app_context():
        print("\n🔍 DETAILED ANALYSIS OF INCOMPLETE SCREENINGS WITH DATES")
        print("=" * 60)
        
        # Query for the specific problematic cases
        query = """
        SELECT 
            p.first_name, p.last_name,
            s.screening_type, s.status, s.last_completed,
            COUNT(sd.document_id) as linked_documents,
            s.notes
        FROM patient p
        JOIN screening s ON p.id = s.patient_id
        LEFT JOIN screening_documents sd ON s.id = sd.screening_id
        WHERE s.status = 'Incomplete' 
        AND s.last_completed IS NOT NULL
        GROUP BY p.first_name, p.last_name, s.screening_type, s.status, s.last_completed, s.notes
        ORDER BY p.last_name, s.screening_type
        """
        
        from sqlalchemy import text
        result = db.session.execute(text(query))
        rows = result.fetchall()
        
        if len(rows) == 0:
            print("✅ No Incomplete screenings with completion dates found")
            return
        
        print(f"Found {len(rows)} problematic cases:")
        
        for row in rows:
            first_name, last_name, screening_type, status, last_completed, linked_docs, notes = row
            print(f"\n👤 {first_name} {last_name}")
            print(f"   📋 {screening_type}")
            print(f"   📊 Status: {status}")
            print(f"   📅 Last Completed: {last_completed}")
            print(f"   📄 Linked Documents: {linked_docs}")
            print(f"   📝 Notes: {notes or 'None'}")
            
            if linked_docs == 0:
                print(f"   ❌ PROBLEM: Has completion date but no documents")
            else:
                print(f"   ⚠️  Has documents but marked Incomplete - may need status review")

if __name__ == "__main__":
    print("🚀 STARTING INCOMPLETE SCREENING DATE CORRECTION")
    print("=" * 60)
    
    # Step 1: Check current state
    check_specific_incomplete_cases()
    
    # Step 2: Apply fixes
    fixes = fix_incomplete_screenings_with_dates()
    
    # Step 3: Validate overall logic
    validate_screening_logic()
    
    print(f"\n🎉 CORRECTION COMPLETE")
    print(f"   Fixes applied: {fixes}")
    print(f"   Rule: Incomplete screenings without documents cannot have completion dates")