
#!/usr/bin/env python3
"""
Update Sample Document Types
Updates existing sample documents to use the correct document types that match the form categories
"""

import sys
import os
from datetime import datetime
import json

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Patient, MedicalDocument

def update_document_types():
    """Update existing sample document types to match form categories"""
    
    with app.app_context():
        # Get all documents
        documents = MedicalDocument.query.all()
        
        if not documents:
            print("No documents found in the database.")
            return
        
        print(f"Updating {len(documents)} documents...")
        
        # Document type mapping based on filename patterns
        type_mapping = {
            # Lab documents
            'colonoscopy': 'LAB_REPORT',
            'hba1c': 'LAB_REPORT', 
            'a1c': 'LAB_REPORT',
            'glucose': 'LAB_REPORT',
            'lipid': 'LAB_REPORT',
            'cholesterol': 'LAB_REPORT',
            'lab': 'LAB_REPORT',
            'blood': 'LAB_REPORT',
            
            # Imaging documents
            'mammogram': 'RADIOLOGY_REPORT',
            'xray': 'RADIOLOGY_REPORT',
            'x-ray': 'RADIOLOGY_REPORT',
            'ct': 'RADIOLOGY_REPORT',
            'mri': 'RADIOLOGY_REPORT',
            'dexa': 'RADIOLOGY_REPORT',
            'scan': 'RADIOLOGY_REPORT',
            'ultrasound': 'RADIOLOGY_REPORT',
            
            # Consultation documents  
            'consultation': 'CONSULTATION',
            'consult': 'CONSULTATION',
            'eye_exam': 'CONSULTATION',
            'optometry': 'CONSULTATION',
            'dermatology': 'CONSULTATION',
            'exam': 'CONSULTATION',
            
            # Clinical notes and other records
            'pap': 'CLINICAL_NOTE',
            'cytology': 'CLINICAL_NOTE',
            'vaccination': 'CLINICAL_NOTE',
            'vaccine': 'CLINICAL_NOTE',
            'immunization': 'CLINICAL_NOTE',
            'emergency': 'DISCHARGE_SUMMARY',
            'therapy': 'CLINICAL_NOTE',
            'medication': 'OTHER',
            'orthopedic': 'CONSULTATION'
        }
        
        updates_made = 0
        
        for doc in documents:
            filename_lower = doc.filename.lower()
            content_lower = (doc.content or '').lower()
            old_type = doc.document_type
            new_type = None
            
            # Check filename and content for keywords
            for keyword, doc_type in type_mapping.items():
                if keyword in filename_lower or keyword in content_lower:
                    new_type = doc_type
                    break
            
            # If no specific match found, use default based on current type
            if not new_type:
                if doc.document_type in ['Report', 'Imaging']:
                    new_type = 'RADIOLOGY_REPORT'
                elif doc.document_type in ['Lab Result', 'Laboratory']:
                    new_type = 'LAB_REPORT'
                elif doc.document_type in ['Consultation', 'Examination']:
                    new_type = 'CONSULTATION'
                elif doc.document_type in ['Record', 'Note', 'List']:
                    new_type = 'CLINICAL_NOTE'
                else:
                    new_type = 'OTHER'
            
            # Update if different
            if new_type != old_type:
                doc.document_type = new_type
                updates_made += 1
                print(f"  Updated {doc.filename}: {old_type} → {new_type}")
        
        # Commit changes
        try:
            db.session.commit()
            print(f"\n✓ Successfully updated {updates_made} documents")
            
            # Show summary by type
            print("\nDocument Summary by Type:")
            for doc_type in ['LAB_REPORT', 'RADIOLOGY_REPORT', 'CONSULTATION', 'CLINICAL_NOTE', 'DISCHARGE_SUMMARY', 'OTHER']:
                count = MedicalDocument.query.filter_by(document_type=doc_type).count()
                if count > 0:
                    print(f"  {doc_type}: {count} documents")
                    
        except Exception as e:
            db.session.rollback()
            print(f"Error updating documents: {e}")

if __name__ == '__main__':
    update_document_types()
