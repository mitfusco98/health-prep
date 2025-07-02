
#!/usr/bin/env python3
"""
Verify Sample Medical Documents
Check if sample documents were created and are accessible for patients
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Patient, MedicalDocument

def verify_sample_documents():
    """Verify that sample documents exist and are properly accessible"""
    
    with app.app_context():
        print("=== Sample Documents Verification ===\n")
        
        # Get all patients
        patients = Patient.query.all()
        print(f"Found {len(patients)} patients in database\n")
        
        for patient in patients:
            print(f"Patient: {patient.full_name} (ID: {patient.id})")
            
            # Get documents for this patient
            documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
            
            if documents:
                print(f"  📄 Found {len(documents)} documents:")
                for doc in documents:
                    print(f"    - {doc.filename}")
                    print(f"      Type: {doc.document_type}")
                    print(f"      Created: {doc.created_at}")
                    print(f"      Has content: {'Yes' if doc.content else 'No'}")
                    if doc.doc_metadata:
                        print(f"      Has metadata: Yes")
                    print()
            else:
                print("  ❌ No documents found")
            
            print("-" * 50)
        
        # Summary
        total_documents = MedicalDocument.query.count()
        print(f"\n📊 Summary:")
        print(f"Total documents in database: {total_documents}")
        print(f"Total patients: {len(patients)}")
        
        # Check document types
        print(f"\n📋 Document Types:")
        document_types = db.session.query(MedicalDocument.document_type, db.func.count(MedicalDocument.id)).group_by(MedicalDocument.document_type).all()
        for doc_type, count in document_types:
            print(f"  {doc_type}: {count}")

if __name__ == '__main__':
    verify_sample_documents()
