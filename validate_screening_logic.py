#!/usr/bin/env python3
"""
Diagnostic utility to validate screening logic and document relationships
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Screening, MedicalDocument, Patient
from sqlalchemy import func

def main():
    """Main function to validate screening logic"""
    with app.app_context():
        print("🔍 SCREENING LOGIC VALIDATION REPORT")
        print("=" * 50)
        
        # Check Complete screenings without documents
        print("\n📊 COMPLETE SCREENINGS WITHOUT DOCUMENTS:")
        complete_screenings = Screening.query.filter_by(status='Complete').all()
        invalid_count = 0
        
        for screening in complete_screenings:
            doc_count = screening.document_count
            if doc_count == 0:
                invalid_count += 1
                print(f"  ❌ Screening {screening.id} ({screening.screening_type}) - Patient: {screening.patient.first_name} {screening.patient.last_name}")
        
        if invalid_count == 0:
            print("  ✅ No invalid Complete screenings found!")
        else:
            print(f"  ⚠️  Found {invalid_count} invalid Complete screenings")
        
        # Status distribution
        print("\n📈 STATUS DISTRIBUTION:")
        status_counts = db.session.query(
            Screening.status, 
            func.count(Screening.id)
        ).group_by(Screening.status).all()
        
        for status, count in status_counts:
            print(f"  {status}: {count}")
        
        # Document relationship health
        print("\n🔗 DOCUMENT RELATIONSHIP HEALTH:")
        total_screenings = Screening.query.count()
        screenings_with_docs = db.session.query(Screening.id).join(
            db.text('screening_documents'), 
            db.text('screening.id = screening_documents.screening_id')
        ).distinct().count()
        
        print(f"  Total screenings: {total_screenings}")
        print(f"  Screenings with documents: {screenings_with_docs}")
        print(f"  Screenings without documents: {total_screenings - screenings_with_docs}")
        
        # Complete screenings analysis
        print("\n✅ COMPLETE SCREENINGS ANALYSIS:")
        complete_count = Screening.query.filter_by(status='Complete').count()
        complete_with_docs = 0
        
        for screening in Screening.query.filter_by(status='Complete').all():
            if screening.document_count > 0:
                complete_with_docs += 1
        
        print(f"  Total Complete screenings: {complete_count}")
        print(f"  Complete with documents: {complete_with_docs}")
        print(f"  Complete without documents: {complete_count - complete_with_docs}")
        
        if complete_count == complete_with_docs:
            print("  ✅ All Complete screenings have documents - LOGIC IS CORRECT!")
        else:
            print("  ❌ Some Complete screenings lack documents - LOGIC ERROR DETECTED!")
        
        # Sample Complete screenings with documents
        print("\n📄 SAMPLE COMPLETE SCREENINGS WITH DOCUMENTS:")
        sample_complete = Screening.query.filter_by(status='Complete').limit(5).all()
        for screening in sample_complete:
            docs = screening.get_valid_documents_with_access_check()
            print(f"  {screening.screening_type} (Patient: {screening.patient.first_name} {screening.patient.last_name}) - {len(docs)} docs")
            for doc in docs[:2]:  # Show first 2 docs
                print(f"    - {doc.filename or doc.document_name}")

if __name__ == "__main__":
    main()