
#!/usr/bin/env python3

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up environment
os.environ.setdefault('SESSION_SECRET', 'dev-secret-key-change-in-production')
if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'sqlite:///healthcare.db'

from app import app, db
from models import Patient, MedicalDocument

def verify_patient_documents():
    """Verify that patients have documents and they are properly categorized"""
    
    with app.app_context():
        print("=== Document Verification Report ===")
        
        # Get all patients
        patients = Patient.query.all()
        print(f"Found {len(patients)} patients in database")
        
        for patient in patients:
            print(f"\n--- Patient: {patient.first_name} {patient.last_name} (ID: {patient.id}) ---")
            
            # Get all documents for this patient
            documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
            print(f"Total documents: {len(documents)}")
            
            if documents:
                # Categorize documents
                lab_docs = []
                imaging_docs = []
                consult_docs = []
                hospital_docs = []
                other_docs = []
                
                for doc in documents:
                    doc_type = doc.document_type
                    if doc_type in ['LAB_REPORT', 'Lab Report', 'Laboratory Results', 'Lab Result']:
                        lab_docs.append(doc)
                    elif doc_type in ['RADIOLOGY_REPORT', 'Radiology Report', 'Imaging']:
                        imaging_docs.append(doc)
                    elif doc_type in ['CONSULTATION', 'Consultation', 'Consultation Note']:
                        consult_docs.append(doc)
                    elif doc_type in ['DISCHARGE_SUMMARY', 'Hospital Summary']:
                        hospital_docs.append(doc)
                    elif doc_type in ['CLINICAL_NOTE', 'Clinical Note']:
                        # Clinical notes go to consults for display
                        consult_docs.append(doc)
                    else:
                        other_docs.append(doc)
                
                print(f"  Laboratory documents: {len(lab_docs)}")
                for doc in lab_docs:
                    print(f"    - {doc.filename or doc.document_name} ({doc.document_type})")
                
                print(f"  Imaging documents: {len(imaging_docs)}")
                for doc in imaging_docs:
                    print(f"    - {doc.filename or doc.document_name} ({doc.document_type})")
                
                print(f"  Consultation documents: {len(consult_docs)}")
                for doc in consult_docs:
                    print(f"    - {doc.filename or doc.document_name} ({doc.document_type})")
                
                print(f"  Hospital documents: {len(hospital_docs)}")
                for doc in hospital_docs:
                    print(f"    - {doc.filename or doc.document_name} ({doc.document_type})")
                
                if other_docs:
                    print(f"  Other documents: {len(other_docs)}")
                    for doc in other_docs:
                        print(f"    - {doc.filename or doc.document_name} ({doc.document_type})")
            else:
                print("  No documents found")
        
        # Summary
        total_docs = MedicalDocument.query.count()
        print(f"\n=== Summary ===")
        print(f"Total documents in database: {total_docs}")
        
        # Count by type
        doc_types = db.session.query(MedicalDocument.document_type, db.func.count(MedicalDocument.id)).group_by(MedicalDocument.document_type).all()
        print("Documents by type:")
        for doc_type, count in doc_types:
            print(f"  {doc_type}: {count}")

if __name__ == "__main__":
    verify_patient_documents()
