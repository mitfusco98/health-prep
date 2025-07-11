#!/usr/bin/env python3
"""
Demo script showing the new DocumentScreeningMatcher storage capabilities
Uses the many-to-many relationship table instead of storing document IDs in notes
"""

from app import app, db
from models import Patient, MedicalDocument, Screening, ScreeningType
from document_screening_matcher import DocumentScreeningMatcher

def demo_document_screening_storage():
    """Demonstrate the new document-screening relationship storage"""
    
    with app.app_context():
        print("=== Document Screening Matcher Storage Demo ===")
        
        # Get a test patient with documents
        patient = Patient.query.first()
        if not patient:
            print("No patients found. Please add some test data first.")
            return
        
        print(f"Patient: {patient.full_name} (ID: {patient.id})")
        
        # Get patient's documents
        documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
        print(f"Documents: {len(documents)}")
        
        if not documents:
            print("No documents found for patient.")
            return
        
        # Initialize matcher
        matcher = DocumentScreeningMatcher()
        
        # Clear existing screening relationships for demo
        print("\nClearing existing screening relationships...")
        existing_screenings = Screening.query.filter_by(patient_id=patient.id).all()
        for screening in existing_screenings:
            screening.documents.delete()  # Clear relationships
        Screening.query.filter_by(patient_id=patient.id).delete()
        db.session.commit()
        
        # Store all matching documents using the new system
        print("\nAnalyzing documents and storing relationships...")
        results = matcher.store_all_matching_documents(patient, documents)
        
        print(f"Results:")
        print(f"  - Total documents analyzed: {results['total_documents']}")
        print(f"  - Relationships created: {results['relationships_created']}")
        print(f"  - Screenings updated: {results['screenings_updated']}")
        if results['errors']:
            print(f"  - Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"    * {error}")
        
        # Show the new relationships
        print("\nScreening relationships created:")
        screenings_with_docs = Screening.query.filter_by(patient_id=patient.id).all()
        
        for screening in screenings_with_docs:
            doc_count = screening.document_count
            print(f"  {screening.screening_type}: {doc_count} documents")
            
            for document in screening.matched_documents[:3]:  # Show first 3
                metadata = screening.get_document_metadata(document)
                confidence = metadata['confidence_score'] if metadata else 'Unknown'
                match_source = metadata['match_source'] if metadata else 'Unknown'
                print(f"    - {document.document_name or document.filename} (confidence: {confidence}, source: {match_source})")
        
        # Test individual document-screening relationship
        print("\nTesting individual relationship storage...")
        if documents and ScreeningType.query.first():
            test_doc = documents[0]
            test_screening_type = ScreeningType.query.first()
            
            # Get match result
            match_result = matcher.match_document_to_screening(test_screening_type, test_doc, patient)
            
            if match_result['matched']:
                print(f"Match found: {test_doc.filename} -> {test_screening_type.name}")
                
                # Store the relationship
                screening = matcher.store_document_screening_relationship(
                    patient, test_screening_type, test_doc, match_result, confidence_score=0.95
                )
                
                if screening:
                    print(f"Relationship stored successfully in screening ID {screening.id}")
                    
                    # Verify the relationship
                    metadata = screening.get_document_metadata(test_doc)
                    if metadata:
                        print(f"Verification: confidence={metadata['confidence_score']}, source={metadata['match_source']}")
                else:
                    print("Failed to store relationship")
            else:
                print(f"No match found: {test_doc.filename} -> {test_screening_type.name}")
        
        print("\n=== Demo completed ===")

if __name__ == "__main__":
    demo_document_screening_storage()