#!/usr/bin/env python3
"""
Check all completed screenings to identify which ones need frequency-based filtering
"""

from app import app, db
from models import Patient, Screening, ScreeningType, MedicalDocument
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

def check_completed_screenings():
    with app.app_context():
        # Get all completed screenings
        completed_screenings = Screening.query.filter(
            Screening.status == 'Complete'
        ).all()
        
        print(f"Found {len(completed_screenings)} completed screenings\n")
        
        needs_update = []
        
        for screening in completed_screenings:
            patient = Patient.query.get(screening.patient_id)
            screening_type = screening.screening_type
            
            # Check if this screening has frequency info
            if not screening_type.frequency_number or not screening_type.frequency_unit:
                continue
                
            # Get all matched documents for this screening
            matched_docs = list(screening.documents)
            
            if not matched_docs or not screening.last_completed:
                continue
                
            # Calculate cutoff date (last_completed - frequency)
            last_completed = screening.last_completed
            frequency_num = int(screening_type.frequency_number)
            frequency_unit = screening_type.frequency_unit.lower()
            
            try:
                if frequency_unit in ['year', 'years', 'annually']:
                    cutoff_date = last_completed - relativedelta(years=frequency_num)
                elif frequency_unit in ['month', 'months', 'monthly']:
                    cutoff_date = last_completed - relativedelta(months=frequency_num)
                elif frequency_unit in ['day', 'days', 'daily']:
                    cutoff_date = last_completed - timedelta(days=frequency_num)
                else:
                    continue
            except:
                continue
            
            # Check if any matched documents are before the cutoff
            outdated_docs = []
            for doc in matched_docs:
                doc_date = doc.document_date or doc.created_at.date()
                if isinstance(doc_date, str):
                    continue
                if hasattr(doc_date, 'date'):
                    doc_date = doc_date.date()
                
                if doc_date < cutoff_date:
                    outdated_docs.append(doc)
            
            if outdated_docs:
                print(f"Patient: {patient.first_name} {patient.last_name}")
                print(f"Screening: {screening_type.name}")
                print(f"Last completed: {last_completed}")
                print(f"Frequency: {frequency_num} {frequency_unit}")
                print(f"Cutoff date: {cutoff_date}")
                print(f"Total docs: {len(matched_docs)}, Outdated: {len(outdated_docs)}")
                for doc in outdated_docs:
                    doc_date = doc.document_date or doc.created_at.date()
                    if hasattr(doc_date, 'date'):
                        doc_date = doc_date.date()
                    print(f"  - {doc.document_name} ({doc_date})")
                print()
                
                needs_update.append((patient.id, screening_type.name))
        
        print(f"Total screenings needing update: {len(needs_update)}")
        return needs_update

if __name__ == "__main__":
    check_completed_screenings()