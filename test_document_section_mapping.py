"""
Test Document Section Mapping to FHIR Categories
Validates document section detection and FHIR category assignment during parsing
"""

import json
from datetime import datetime, date
from app import app, db
from models import Patient, ScreeningType, MedicalDocument
from fhir_document_section_mapper import DocumentSectionMapper, setup_default_screening_section_mappings


def test_document_section_mapping_system():
    """Test the complete document section mapping system"""
    
    print("TESTING DOCUMENT SECTION MAPPING SYSTEM")
    print("=" * 55)
    
    with app.app_context():
        # Step 1: Setup screening types with section mappings
        setup_section_mappings()
        
        # Step 2: Test document section detection
        test_section_detection()
        
        # Step 3: Test FHIR category mapping
        test_fhir_category_mapping()
        
        # Step 4: Test screening matching by section
        test_screening_section_matching()
        
        # Step 5: Test with actual documents
        test_with_existing_documents()
        
        print("\n" + "=" * 55)
        print("DOCUMENT SECTION MAPPING TEST COMPLETE")


def setup_section_mappings():
    """Setup screening types with document section mappings"""
    
    print("\nSetting up document section mappings...")
    
    mapper = DocumentSectionMapper()
    
    # Configure diabetes screening with specific section mappings
    diabetes_screening = ScreeningType.query.filter_by(name="Diabetes Management").first()
    if diabetes_screening:
        diabetes_mappings = {
            "labs": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory",
                    "display": "Laboratory"
                },
                "document_types": ["Lab Report", "HbA1c Results", "Glucose Test"],
                "keywords": ["glucose", "hba1c", "diabetes", "blood sugar"],
                "priority": "high"
            },
            "imaging": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "imaging",
                    "display": "Imaging"
                },
                "document_types": ["Retinal Exam", "Foot X-Ray"],
                "keywords": ["retinal", "foot", "eye exam"],
                "priority": "medium"
            }
        }
        diabetes_screening.set_document_section_mappings(diabetes_mappings)
        print("Configured: Diabetes Management with labs and imaging sections")
    
    # Configure hypertension screening
    hypertension_screening = ScreeningType.query.filter_by(name="Hypertension Monitoring").first()
    if hypertension_screening:
        hypertension_mappings = {
            "vitals": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                },
                "document_types": ["Vital Signs", "Blood Pressure Log"],
                "keywords": ["blood pressure", "bp", "vitals"],
                "priority": "high"
            },
            "clinical_notes": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "exam",
                    "display": "Exam"
                },
                "document_types": ["Cardiology Note", "Clinical Note"],
                "keywords": ["cardiology", "hypertension", "cardiovascular"],
                "priority": "medium"
            }
        }
        hypertension_screening.set_document_section_mappings(hypertension_mappings)
        print("Configured: Hypertension Monitoring with vitals and clinical notes sections")
    
    db.session.commit()
    print("Section mapping configuration complete")


def test_section_detection():
    """Test document section detection logic"""
    
    print("\nTesting document section detection...")
    
    mapper = DocumentSectionMapper()
    
    test_documents = [
        {
            "name": "HbA1c_Results_2024.pdf",
            "type": "Lab Report",
            "content": "Hemoglobin A1c results show glucose control",
            "expected": "labs"
        },
        {
            "name": "Blood_Pressure_Log.pdf", 
            "type": "Vital Signs",
            "content": "Blood pressure readings over time",
            "expected": "vitals"
        },
        {
            "name": "Chest_Xray_Report.pdf",
            "type": "Radiology Report", 
            "content": "Chest x-ray shows clear lungs",
            "expected": "imaging"
        },
        {
            "name": "Cardiology_Consultation.pdf",
            "type": "Consultation Note",
            "content": "Cardiology consult for hypertension management",
            "expected": "consults"
        },
        {
            "name": "Unknown_Document.txt",
            "type": "Misc",
            "content": "Generic medical document",
            "expected": "unknown"
        }
    ]
    
    detection_results = []
    
    for doc in test_documents:
        detected_section = mapper.detect_document_section(
            doc["name"], 
            doc["type"],
            doc["content"]
        )
        
        is_correct = detected_section == doc["expected"]
        detection_results.append({
            "document": doc["name"],
            "expected": doc["expected"],
            "detected": detected_section,
            "correct": is_correct
        })
        
        status = "✓" if is_correct else "✗"
        print(f"  {status} {doc['name']}: {detected_section} (expected: {doc['expected']})")
    
    accuracy = sum(1 for r in detection_results if r["correct"]) / len(detection_results)
    print(f"\nSection detection accuracy: {accuracy:.1%}")
    
    return detection_results


def test_fhir_category_mapping():
    """Test FHIR category mapping for document sections"""
    
    print("\nTesting FHIR category mapping...")
    
    mapper = DocumentSectionMapper()
    
    test_sections = ["labs", "imaging", "vitals", "consults", "procedures", "unknown"]
    
    for section in test_sections:
        fhir_category = mapper.get_fhir_category_for_document(section)
        
        print(f"  {section}:")
        print(f"    System: {fhir_category['system']}")
        print(f"    Code: {fhir_category['code']}")
        print(f"    Display: {fhir_category['display']}")
    
    # Test custom mappings from screening types
    diabetes_screening = ScreeningType.query.filter_by(name="Diabetes Management").first()
    if diabetes_screening:
        print(f"\nTesting custom mappings for Diabetes Management:")
        
        labs_category = mapper.get_fhir_category_for_document("labs", diabetes_screening.id)
        imaging_category = mapper.get_fhir_category_for_document("imaging", diabetes_screening.id)
        
        print(f"  Labs category: {labs_category['code']} - {labs_category['display']}")
        print(f"  Imaging category: {imaging_category['code']} - {imaging_category['display']}")


def test_screening_section_matching():
    """Test finding screenings by document section"""
    
    print("\nTesting screening matching by document section...")
    
    mapper = DocumentSectionMapper()
    
    test_sections = ["labs", "vitals", "imaging", "clinical_notes"]
    
    for section in test_sections:
        matching_screenings = mapper.find_screenings_by_document_section(section)
        
        print(f"  {section} section matches {len(matching_screenings)} screenings:")
        for screening in matching_screenings:
            print(f"    - {screening.name}")
            
            # Show which sections this screening type supports
            mappings = screening.get_document_section_mappings()
            supported_sections = list(mappings.keys())
            print(f"      Supports: {', '.join(supported_sections)}")


def test_with_existing_documents():
    """Test section mapping with existing documents in database"""
    
    print("\nTesting with existing documents...")
    
    mapper = DocumentSectionMapper()
    
    # Get sample documents from database
    documents = MedicalDocument.query.limit(5).all()
    
    if not documents:
        print("  No documents found in database")
        return
    
    print(f"  Processing {len(documents)} documents:")
    
    section_counts = {}
    enhanced_documents = []
    
    for doc in documents:
        # Enhance document with FHIR metadata
        enhanced_metadata = mapper.enhance_document_with_fhir_metadata(doc)
        enhanced_documents.append(enhanced_metadata)
        
        section = enhanced_metadata["detected_section"]
        section_counts[section] = section_counts.get(section, 0) + 1
        
        print(f"\n    Document: {doc.filename or doc.document_name}")
        print(f"    Type: {doc.document_type}")
        print(f"    Detected Section: {section}")
        print(f"    FHIR Category: {enhanced_metadata['fhir_category']['code']}")
        print(f"    Confidence: {enhanced_metadata['section_confidence']:.2f}")
        print(f"    Matching Screenings: {len(enhanced_metadata['matching_screenings'])}")
        
        for screening in enhanced_metadata["matching_screenings"]:
            print(f"      - {screening['name']}")
    
    print(f"\n  Section Distribution:")
    for section, count in section_counts.items():
        print(f"    {section}: {count} documents")
    
    # Get overall statistics
    stats = mapper.get_section_statistics()
    print(f"\n  Overall Statistics:")
    print(f"    Total documents: {stats['total_documents']}")
    print(f"    Sections mapped: {stats['sections_mapped']}")
    print(f"    Unmapped documents: {stats['unmapped_documents']}")
    print(f"    Mapping coverage: {stats['mapping_coverage']:.1%}")
    
    return enhanced_documents


def demonstrate_fhir_integration():
    """Demonstrate integration with FHIR object mapping"""
    
    print("\nDemonstrating FHIR integration...")
    
    mapper = DocumentSectionMapper()
    
    # Get a sample document
    document = MedicalDocument.query.first()
    if not document:
        print("  No documents available for FHIR integration test")
        return
    
    # Enhance with section mapping
    enhanced_metadata = mapper.enhance_document_with_fhir_metadata(document)
    
    # Create FHIR-compatible document structure
    fhir_document = {
        "resourceType": "DocumentReference",
        "id": f"document-{document.id}",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "34133-9",
                "display": "Summarization of episode note"
            }],
            "text": document.document_type or "Medical Document"
        },
        "category": [{
            "coding": [enhanced_metadata["fhir_category"]]
        }],
        "subject": {
            "reference": f"Patient/{document.patient_id}"
        },
        "date": document.created_at.isoformat() if document.created_at else datetime.now().isoformat(),
        "content": [{
            "attachment": {
                "title": document.filename or document.document_name,
                "contentType": document.mime_type or "text/plain"
            }
        }],
        # Custom extension with section mapping metadata
        "extension": [{
            "url": "http://example.org/fhir/StructureDefinition/document-section-mapping",
            "valueString": json.dumps({
                "detected_section": enhanced_metadata["detected_section"],
                "section_confidence": enhanced_metadata["section_confidence"],
                "matching_screenings": enhanced_metadata["matching_screenings"]
            })
        }]
    }
    
    print(f"  FHIR DocumentReference created:")
    print(f"    ID: {fhir_document['id']}")
    print(f"    Category: {fhir_document['category'][0]['coding'][0]['display']}")
    print(f"    Section: {enhanced_metadata['detected_section']}")
    print(f"    Confidence: {enhanced_metadata['section_confidence']:.2f}")
    
    return fhir_document


if __name__ == "__main__":
    test_document_section_mapping_system()
    demonstrate_fhir_integration()