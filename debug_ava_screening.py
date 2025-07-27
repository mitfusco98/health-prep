#!/usr/bin/env python3
"""
Debug script to check Ava Eichel's Pap Smear screening and document matching
"""

from app import app, db
from models import Patient, MedicalDocument, ScreeningType
from unified_screening_engine import UnifiedScreeningEngine
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_ava_screening():
    with app.app_context():
        # Find Ava Eichel
        ava = Patient.query.filter(Patient.first_name.ilike('%ava%')).first()
        if not ava:
            print("Ava Eichel not found")
            return
        
        print(f"Found patient: {ava.first_name} {ava.last_name} (ID: {ava.id})")
        
        # Find Pap Smear screening type
        pap_smear = ScreeningType.query.filter(ScreeningType.name.ilike('%pap%')).first()
        if not pap_smear:
            print("Pap Smear screening type not found")
            return
            
        print(f"Found screening type: {pap_smear.name} (Frequency: {pap_smear.frequency_number} {pap_smear.frequency_unit})")
        
        # Get all documents for Ava
        documents = MedicalDocument.query.filter_by(patient_id=ava.id).all()
        print(f"\nAva's documents ({len(documents)}):")
        for doc in documents:
            doc_date = doc.document_date or doc.created_at.date()
            print(f"  - {doc.document_name} (ID: {doc.id}) - Date: {doc_date}")
        
        # Test the unified screening engine
        engine = UnifiedScreeningEngine()
        
        # Find matching documents
        matching_docs = engine._find_matching_documents(ava, pap_smear)
        print(f"\nMatching documents for Pap Smear ({len(matching_docs)}):")
        for doc in matching_docs:
            doc_date = doc.document_date or doc.created_at.date()
            print(f"  - {doc.document_name} (ID: {doc.id}) - Date: {doc_date}")
        
        # Generate screening data
        screening_data = engine._generate_screening_data(ava, pap_smear)
        if screening_data:
            print(f"\nScreening status: {screening_data['status']}")
            print(f"Last completed: {screening_data['last_completed']}")
            print(f"Matched document IDs: {screening_data['matched_documents']}")

if __name__ == "__main__":
    debug_ava_screening()