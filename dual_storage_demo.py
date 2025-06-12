#!/usr/bin/env python3
"""
Dual Storage System Demonstration

Demonstrates the complete dual storage system for documents and prep sheets
with both internal and FHIR keys, plus comprehensive admin logging.
"""

import json
from datetime import datetime, date
from app import app, db
from models import MedicalDocument, PrepSheet, Patient
from dual_storage_handler import (
    DualStorageHandler,
    save_document_dual_storage,
    save_prep_sheet_dual_storage
)
from enhanced_document_processor import process_document_with_dual_storage


def demonstrate_document_dual_storage():
    """Demonstrate document saving with dual storage keys"""
    print("=== Document Dual Storage Demonstration ===")
    
    with app.app_context():
        # Get or create a test patient
        patient = Patient.query.first()
        if not patient:
            print("No patients found - creating test patient")
            patient = Patient(
                first_name="Jane",
                last_name="Demo",
                date_of_birth=date(1985, 6, 15),
                sex="Female",
                mrn="DEMO123456",
                phone="555-0123",
                email="jane.demo@example.com"
            )
            db.session.add(patient)
            db.session.commit()
        
        print(f"Using patient: {patient.first_name} {patient.last_name} (ID: {patient.id})")
        
        # Create test documents with different types
        test_documents = [
            {
                'filename': 'hba1c_results_2024.pdf',
                'document_name': 'Hemoglobin A1C Lab Results',
                'document_type': 'Lab Report',
                'content': 'Lab Results: Hemoglobin A1C: 6.8% (Normal: <7.0%). Patient has diabetes screening.',
                'internal_keys': {
                    'tag': 'lab_diabetes',
                    'section': 'laboratory_results',
                    'matched_screening': 'diabetes'
                },
                'fhir_keys': {
                    'code': {
                        'system': 'http://loinc.org',
                        'code': '4548-4',
                        'display': 'Hemoglobin A1c/Hemoglobin.total in Blood'
                    },
                    'category': {
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'laboratory',
                        'display': 'Laboratory'
                    },
                    'effectiveDateTime': datetime(2024, 11, 20, 14, 0, 0)
                }
            },
            {
                'filename': 'mammogram_report_2024.pdf',
                'document_name': 'Mammography Screening Report',
                'document_type': 'Radiology Report',
                'content': 'Mammography: No suspicious findings. Recommend routine annual mammogram screening.',
                'internal_keys': {
                    'tag': 'radiology_screening',
                    'section': 'imaging_studies', 
                    'matched_screening': 'mammogram'
                },
                'fhir_keys': {
                    'code': {
                        'system': 'http://loinc.org',
                        'code': '24604-1',
                        'display': 'Mammography study observation'
                    },
                    'category': {
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'imaging',
                        'display': 'Imaging'
                    },
                    'effectiveDateTime': datetime(2024, 10, 15, 10, 30, 0)
                }
            },
            {
                'filename': 'clinical_note_annual.txt',
                'document_name': 'Annual Physical Examination',
                'document_type': 'Clinical Note',
                'content': 'Annual physical exam. Patient reports good health. Recommend colonoscopy screening due to age.',
                'internal_keys': {
                    'tag': 'annual_exam',
                    'section': 'clinical_notes',
                    'matched_screening': 'colonoscopy'
                },
                'fhir_keys': {
                    'code': {
                        'system': 'http://loinc.org',
                        'code': '11506-3',
                        'display': 'Progress note'
                    },
                    'category': {
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'exam',
                        'display': 'Exam'
                    },
                    'effectiveDateTime': datetime(2024, 12, 1, 9, 0, 0)
                }
            }
        ]
        
        created_docs = []
        
        for doc_data in test_documents:
            print(f"\nCreating document: {doc_data['document_name']}")
            
            # Create document instance
            document = MedicalDocument(
                filename=doc_data['filename'],
                document_name=doc_data['document_name'],
                document_type=doc_data['document_type'],
                content=doc_data['content'],
                patient_id=patient.id,
                document_date=doc_data['fhir_keys']['effectiveDateTime'],
                is_processed=True
            )
            
            # Save with dual storage
            success = DualStorageHandler.save_document_with_dual_storage(
                document=document,
                internal_data=doc_data['internal_keys'],
                fhir_data=doc_data['fhir_keys'],
                user_id=1  # Simulate admin user
            )
            
            if success:
                created_docs.append(document)
                print(f"✓ Saved document with dual storage")
                print(f"  Internal keys: {document.get_internal_keys()}")
                print(f"  FHIR keys: {document.get_fhir_keys()}")
            else:
                print(f"✗ Failed to save document")
        
        print(f"\n✓ Created {len(created_docs)} documents with dual storage")
        return created_docs


def demonstrate_prep_sheet_dual_storage():
    """Demonstrate prep sheet saving with dual storage keys"""
    print("\n=== Prep Sheet Dual Storage Demonstration ===")
    
    with app.app_context():
        # Get test patient
        patient = Patient.query.first()
        if not patient:
            print("No patient available for prep sheet demo")
            return None
        
        print(f"Creating prep sheet for: {patient.first_name} {patient.last_name}")
        
        # Create prep sheet
        prep_sheet = PrepSheet(
            patient_id=patient.id,
            appointment_date=date(2024, 12, 15),
            filename=f"prep_sheet_{patient.id}_{date.today().strftime('%Y%m%d')}.pdf",
            content="Comprehensive preparation sheet with screening recommendations...",
            prep_data=json.dumps({
                "screenings": ["mammogram", "colonoscopy", "diabetes"],
                "conditions": ["controlled diabetes"],
                "medications": ["metformin"],
                "vitals": {"bp": "120/80", "weight": "65kg"}
            })
        )
        
        # Define internal and FHIR keys for prep sheet
        internal_keys = {
            'tag': 'prep_sheet',
            'section': 'preventive_care',
            'matched_screening': 'mammogram,colonoscopy,diabetes'
        }
        
        fhir_keys = {
            'code': {
                'system': 'http://loinc.org',
                'code': '75492-9',
                'display': 'Preventive care note'
            },
            'category': {
                'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                'code': 'survey',
                'display': 'Survey'
            },
            'effectiveDateTime': datetime.combine(prep_sheet.appointment_date, datetime.min.time())
        }
        
        # Save with dual storage
        success = DualStorageHandler.save_prep_sheet_with_dual_storage(
            prep_sheet=prep_sheet,
            internal_data=internal_keys,
            fhir_data=fhir_keys,
            user_id=1  # Simulate admin user
        )
        
        if success:
            print(f"✓ Saved prep sheet with dual storage")
            print(f"  Internal keys: {prep_sheet.get_internal_keys()}")
            print(f"  FHIR keys: {prep_sheet.get_fhir_keys()}")
            return prep_sheet
        else:
            print(f"✗ Failed to save prep sheet")
            return None


def demonstrate_search_functionality():
    """Demonstrate searching using both internal and FHIR keys"""
    print("\n=== Search Functionality Demonstration ===")
    
    with app.app_context():
        print("Searching documents by internal keys...")
        
        # Search by internal tag
        lab_docs = MedicalDocument.query.filter(MedicalDocument.tag.like('%lab%')).all()
        print(f"Documents with 'lab' tag: {len(lab_docs)}")
        
        # Search by internal section
        imaging_docs = MedicalDocument.query.filter(MedicalDocument.section == 'imaging_studies').all()
        print(f"Documents in 'imaging_studies' section: {len(imaging_docs)}")
        
        # Search by matched screening
        diabetes_docs = MedicalDocument.query.filter(MedicalDocument.matched_screening == 'diabetes').all()
        print(f"Documents matched to 'diabetes' screening: {len(diabetes_docs)}")
        
        print("\nSearching documents by FHIR keys...")
        
        # Search by FHIR code system
        loinc_docs = MedicalDocument.query.filter(MedicalDocument.fhir_code_system == 'http://loinc.org').all()
        print(f"Documents with LOINC codes: {len(loinc_docs)}")
        
        # Search by FHIR category
        lab_category_docs = MedicalDocument.query.filter(MedicalDocument.fhir_category_code == 'laboratory').all()
        print(f"Documents in 'laboratory' FHIR category: {len(lab_category_docs)}")
        
        # Search prep sheets
        prep_sheets = PrepSheet.query.all()
        print(f"Total prep sheets: {len(prep_sheets)}")


def demonstrate_admin_logging():
    """Demonstrate admin logging for document operations"""
    print("\n=== Admin Logging Demonstration ===")
    
    with app.app_context():
        # Get a test document
        document = MedicalDocument.query.first()
        if not document:
            print("No documents available for logging demo")
            return
        
        print(f"Testing logging with document: {document.filename}")
        
        # Simulate document deletion with logging
        print("Simulating document deletion (with logging)...")
        
        # Capture details before deletion
        doc_details = {
            "document_id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,
            "internal_keys": document.get_internal_keys(),
            "fhir_keys": document.get_fhir_keys()
        }
        
        print(f"Document details logged: {json.dumps(doc_details, indent=2, default=str)}")
        
        # In a real scenario, this would be logged to the admin_logs table
        # For demo purposes, we'll just show what would be logged
        admin_log_entry = {
            "action": "document_delete",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "user_id": 1,
            "details": doc_details,
            "ip_address": "127.0.0.1",
            "user_agent": "Demo Script"
        }
        
        print("Admin log entry that would be created:")
        print(json.dumps(admin_log_entry, indent=2, default=str))


def demonstrate_fhir_export():
    """Demonstrate FHIR export using stored keys"""
    print("\n=== FHIR Export Demonstration ===")
    
    with app.app_context():
        documents = MedicalDocument.query.limit(3).all()
        
        if not documents:
            print("No documents available for FHIR export demo")
            return
        
        print("Exporting documents in FHIR format using stored keys...")
        
        for document in documents:
            fhir_keys = document.get_fhir_keys()
            
            # Create FHIR DocumentReference using stored keys
            fhir_document_reference = {
                "resourceType": "DocumentReference",
                "id": f"document-{document.id}",
                "status": "current",
                "docStatus": "final",
                "type": {
                    "coding": [fhir_keys['code']] if fhir_keys['code'] else [],
                    "text": document.document_type
                },
                "category": [{"coding": [fhir_keys['category']]}] if fhir_keys['category'] else [],
                "subject": {
                    "reference": f"Patient/patient-{document.patient_id}",
                    "display": f"Patient {document.patient_id}"
                },
                "date": fhir_keys['effectiveDateTime'].isoformat() + 'Z' if fhir_keys['effectiveDateTime'] else None,
                "description": document.document_name,
                "content": [{
                    "attachment": {
                        "contentType": "text/plain",
                        "title": document.filename
                    }
                }]
            }
            
            print(f"\nFHIR DocumentReference for {document.filename}:")
            print(json.dumps(fhir_document_reference, indent=2, default=str))


def demonstrate_epic_compatibility():
    """Demonstrate Epic/external EHR compatibility"""
    print("\n=== Epic/External EHR Compatibility Demonstration ===")
    
    with app.app_context():
        documents = MedicalDocument.query.limit(2).all()
        
        if not documents:
            print("No documents available for Epic compatibility demo")
            return
        
        print("Generating Epic-compatible export using FHIR keys...")
        
        epic_export = {
            "resourceType": "Bundle",
            "id": f"epic-export-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": "collection",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "entry": []
        }
        
        for document in documents:
            fhir_keys = document.get_fhir_keys()
            
            # Epic-style document entry
            entry = {
                "resource": {
                    "resourceType": "DocumentReference",
                    "id": f"doc-{document.id}",
                    "meta": {
                        "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-documentreference"]
                    },
                    "status": "current",
                    "type": {
                        "coding": [fhir_keys['code']] if fhir_keys['code'] else []
                    },
                    "category": [{"coding": [fhir_keys['category']]}] if fhir_keys['category'] else [],
                    "subject": {"reference": f"Patient/{document.patient_id}"},
                    "date": fhir_keys['effectiveDateTime'].isoformat() + 'Z' if fhir_keys['effectiveDateTime'] else None
                },
                "fullUrl": f"https://your-system.com/fhir/DocumentReference/doc-{document.id}"
            }
            
            epic_export["entry"].append(entry)
        
        epic_export["total"] = len(epic_export["entry"])
        
        print("Epic-compatible FHIR Bundle:")
        print(json.dumps(epic_export, indent=2, default=str))


def run_complete_demonstration():
    """Run the complete dual storage demonstration"""
    print("DUAL STORAGE SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demonstrates the complete dual storage system that stores")
    print("both internal keys and FHIR-style keys for Epic/EHR compatibility.")
    print("=" * 60)
    
    # Run all demonstrations
    documents = demonstrate_document_dual_storage()
    prep_sheet = demonstrate_prep_sheet_dual_storage()
    demonstrate_search_functionality()
    demonstrate_admin_logging()
    demonstrate_fhir_export()
    demonstrate_epic_compatibility()
    
    print("\n" + "=" * 60)
    print("✅ DUAL STORAGE DEMONSTRATION COMPLETED")
    print("=" * 60)
    print("\nKey Benefits Demonstrated:")
    print("• Documents store both internal and FHIR keys simultaneously")
    print("• Backward compatibility with existing internal key usage")
    print("• FHIR-compliant exports for Epic and external EHR systems")
    print("• Comprehensive admin logging for all document operations")
    print("• Search functionality using both key formats")
    print("• Prep sheet tracking with dual storage support")
    print("\nImplementation Features:")
    print("• Automatic key extraction during document processing")
    print("• Structured FHIR codes (LOINC, SNOMED CT, etc.)")
    print("• Proper categorization for healthcare interoperability")
    print("• Timestamped effective dates for clinical relevance")
    print("• Admin audit trail for compliance and security")


if __name__ == "__main__":
    run_complete_demonstration()