"""
Standalone FHIR DocumentReference Conversion Test

This script demonstrates the FHIR document conversion functionality
using your actual MedicalDocument model structure.
"""

import json
from datetime import datetime
import os
import sys

# Add the current directory to Python path
sys.path.append('.')

# Set up Flask app context for database access
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')
if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'

from fhir_mapping.document_reference_mapper import DocumentReferenceMapper


class TestMedicalDocument:
    """Test medical document class with your actual model structure"""
    def __init__(self):
        self.id = 789
        self.patient_id = 12345
        self.filename = "lab_results_2024_06_15.pdf"
        self.document_name = "CBC Lab Results"
        self.document_type = "Lab Results"
        self.content = "Complete Blood Count results showing normal values..."
        self.binary_content = None
        self.is_binary = False
        self.mime_type = "application/pdf"
        self.source_system = "LabCorp Integration"
        self.document_date = datetime(2024, 6, 15, 10, 30, 0)
        self.provider = "Dr. Sarah Johnson"
        self.doc_metadata = '{"test_type": "CBC", "lab_id": "LAB-2024-001", "status": "final"}'
        self.is_processed = True
        self.created_at = datetime(2024, 6, 15, 11, 0, 0)
        self.updated_at = datetime(2024, 6, 15, 11, 15, 0)


def main():
    """Test the FHIR document conversion functionality"""
    print("=== FHIR DocumentReference Conversion Test ===\n")
    
    # Create test document with your model structure
    document = TestMedicalDocument()
    
    print("Original Medical Document Data:")
    print(f"  ID: {document.id}")
    print(f"  Patient ID: {document.patient_id}")
    print(f"  Filename: {document.filename}")
    print(f"  Document Name: {document.document_name}")
    print(f"  Document Type: {document.document_type}")
    print(f"  MIME Type: {document.mime_type}")
    print(f"  Source System: {document.source_system}")
    print(f"  Document Date: {document.document_date}")
    print(f"  Provider: {document.provider}")
    print(f"  Is Binary: {document.is_binary}")
    print(f"  Is Processed: {document.is_processed}")
    print(f"  Metadata: {document.doc_metadata}")
    print(f"  Created: {document.created_at}")
    print(f"  Updated: {document.updated_at}")
    print()
    
    # Test conversion to FHIR DocumentReference
    try:
        mapper = DocumentReferenceMapper()
        fhir_document = mapper.to_fhir(document)
        
        print("✓ Successfully converted to FHIR DocumentReference resource")
        print("\nFHIR DocumentReference Resource:")
        print(json.dumps(fhir_document, indent=2))
        print()
        
        # Validate FHIR resource
        is_valid = mapper.validate_fhir_document_reference(fhir_document)
        print(f"✓ FHIR validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test conversion back to internal format
        internal_data = mapper.from_fhir(fhir_document)
        print("\n✓ Successfully converted back to internal format")
        print("Converted Internal Data:")
        for key, value in internal_data.items():
            print(f"  {key}: {value}")
        
        # Summary of key FHIR fields
        print("\n=== FHIR DocumentReference Summary ===")
        print(f"Resource Type: {fhir_document.get('resourceType')}")
        print(f"Document ID: {fhir_document.get('id')}")
        print(f"Status: {fhir_document.get('status')}")
        print(f"Doc Status: {fhir_document.get('docStatus')}")
        
        # Type information
        doc_type = fhir_document.get('type', {})
        type_coding = doc_type.get('coding', [{}])[0]
        print(f"Type: {type_coding.get('display', 'Unknown')} ({type_coding.get('code', 'No code')})")
        
        # Category information
        categories = fhir_document.get('category', [])
        if categories:
            category_coding = categories[0].get('coding', [{}])[0]
            print(f"Category: {category_coding.get('display', 'Unknown')}")
        
        # Subject (patient) reference
        subject = fhir_document.get('subject', {})
        print(f"Subject: {subject.get('reference')} ({subject.get('display', 'Unknown patient')})")
        
        # Document date
        print(f"Document Date: {fhir_document.get('date', 'Not specified')}")
        
        # Author/Provider
        authors = fhir_document.get('author', [])
        if authors:
            print(f"Author: {authors[0].get('display', 'Unknown')}")
        
        # Content attachment
        content_list = fhir_document.get('content', [])
        if content_list:
            attachment = content_list[0].get('attachment', {})
            print(f"Title: {attachment.get('title', 'No title')}")
            print(f"Content Type: {attachment.get('contentType', 'Unknown')}")
            print(f"URL: {attachment.get('url', 'No URL')}")
            if attachment.get('size'):
                print(f"Size: {attachment.get('size')} bytes")
        
        # Identifiers
        identifiers = fhir_document.get('identifier', [])
        for identifier in identifiers:
            print(f"Identifier: {identifier.get('value')} ({identifier.get('system', 'Unknown system')})")
        
        print("\n✓ FHIR document conversion test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ FHIR document conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_document_types():
    """Test conversion with different document types"""
    print("\n=== Different Document Type Tests ===\n")
    
    test_types = [
        'Lab Results',
        'Imaging', 
        'Progress Notes',
        'Discharge Summary',
        'Consultation',
        'Operative Note',
        'Pathology',
        'Radiology',
        'Other'
    ]
    
    mapper = DocumentReferenceMapper()
    
    for doc_type in test_types:
        print(f"Testing document type: {doc_type}")
        
        document = TestMedicalDocument()
        document.document_type = doc_type
        document.document_name = f"Test {doc_type} Document"
        document.filename = f"test_{doc_type.lower().replace(' ', '_')}.pdf"
        
        try:
            fhir_document = mapper.to_fhir(document)
            
            # Check type mapping
            type_info = fhir_document.get('type', {})
            type_coding = type_info.get('coding', [{}])[0]
            print(f"  FHIR Type: {type_coding.get('display', 'Unknown')}")
            
            # Check category mapping
            categories = fhir_document.get('category', [])
            if categories:
                category_coding = categories[0].get('coding', [{}])[0]
                print(f"  FHIR Category: {category_coding.get('display', 'Unknown')}")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        
        print()


def test_binary_document():
    """Test with binary document (image/PDF)"""
    print("\n=== Binary Document Test ===\n")
    
    class BinaryDocument:
        def __init__(self):
            self.id = 999
            self.patient_id = 54321
            self.filename = "chest_xray_image.jpg"
            self.document_name = "Chest X-Ray"
            self.document_type = "Imaging"
            self.content = None  # No text content
            self.binary_content = b"fake_binary_image_data_here"
            self.is_binary = True
            self.mime_type = "image/jpeg"
            self.source_system = "Radiology PACS"
            self.document_date = datetime(2024, 6, 20, 14, 0, 0)
            self.provider = "Dr. Michael Chen"
            self.doc_metadata = '{"study_type": "chest_xray", "view": "PA", "technique": "digital"}'
            self.is_processed = True
            self.created_at = datetime(2024, 6, 20, 14, 30, 0)
            self.updated_at = datetime(2024, 6, 20, 14, 45, 0)
    
    document = BinaryDocument()
    
    try:
        mapper = DocumentReferenceMapper()
        fhir_document = mapper.to_fhir(document)
        
        print("✓ Binary document converted successfully")
        
        # Check content attachment for binary
        content_list = fhir_document.get('content', [])
        if content_list:
            attachment = content_list[0].get('attachment', {})
            print(f"Content Type: {attachment.get('contentType')}")
            print(f"Size: {attachment.get('size')} bytes")
            print(f"Title: {attachment.get('title')}")
        
        print("FHIR DocumentReference (binary):")
        print(json.dumps(fhir_document, indent=2)[:1000] + "..." if len(json.dumps(fhir_document)) > 1000 else json.dumps(fhir_document, indent=2))
        
        return True
        
    except Exception as e:
        print(f"✗ Binary document conversion failed: {e}")
        return False


def test_minimal_document():
    """Test with minimal required fields only"""
    print("\n=== Minimal Document Test ===\n")
    
    class MinimalDocument:
        def __init__(self):
            self.id = 123
            self.patient_id = 98765
            self.filename = "basic_note.txt"
            self.document_type = "Other"  # Default type
    
    document = MinimalDocument()
    
    try:
        mapper = DocumentReferenceMapper()
        fhir_document = mapper.to_fhir(document)
        
        print("✓ Minimal document converted successfully")
        print("FHIR DocumentReference (minimal):")
        print(json.dumps(fhir_document, indent=2))
        
        return True
        
    except Exception as e:
        print(f"✗ Minimal document conversion failed: {e}")
        return False


if __name__ == "__main__":
    success1 = main()
    test_different_document_types()
    success2 = test_binary_document()
    success3 = test_minimal_document()
    
    if success1 and success2 and success3:
        print("\n✓ All FHIR document conversion tests passed!")
    else:
        print("\n✗ Some tests failed - check the output above")