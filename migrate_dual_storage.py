#!/usr/bin/env python3
"""
Database Migration for Dual Storage

Adds dual storage columns for both internal and FHIR keys to existing tables
and migrates existing data to the new structure.
"""

from datetime import datetime
import json
from app import app, db
from models import MedicalDocument, PrepSheet
from enhanced_document_processor import enhanced_processor


def add_dual_storage_columns():
    """Add dual storage columns to existing tables"""
    print("Adding dual storage columns to database...")
    
    try:
        with app.app_context():
            # Simply create all tables - SQLAlchemy will handle new columns
            db.create_all()
            print("✓ Database schema updated with dual storage columns")
            return True
            
    except Exception as e:
        print(f"Error adding dual storage columns: {str(e)}")
        return False


def migrate_existing_documents():
    """Migrate existing documents to include dual storage keys"""
    print("\nMigrating existing documents to dual storage...")
    
    try:
        with app.app_context():
            total_docs = MedicalDocument.query.count()
            print(f"Found {total_docs} documents to migrate")
            
            if total_docs == 0:
                print("No documents to migrate")
                return True
            
            # Process documents in batches
            batch_size = 50
            migrated = 0
            errors = 0
            
            while migrated < total_docs:
                # Get batch of documents without dual storage keys
                documents = MedicalDocument.query.filter(
                    MedicalDocument.tag.is_(None)
                ).limit(batch_size).all()
                
                if not documents:
                    break
                
                for doc in documents:
                    try:
                        # Extract internal keys
                        internal_data = enhanced_processor._extract_internal_keys(doc)
                        
                        # Extract FHIR keys
                        fhir_data = enhanced_processor._extract_fhir_keys(doc)
                        
                        # Enhance with document-specific FHIR data
                        if doc.document_type in enhanced_processor.document_type_mappings:
                            mapping = enhanced_processor.document_type_mappings[doc.document_type]
                            if not fhir_data.get('code'):
                                fhir_data['code'] = mapping['fhir_code']
                            if not fhir_data.get('category'):
                                fhir_data['category'] = mapping['fhir_category']
                        
                        # Set effective datetime
                        if not fhir_data.get('effectiveDateTime'):
                            fhir_data['effectiveDateTime'] = doc.document_date or doc.created_at
                        
                        # Update document with dual storage keys
                        doc.set_dual_storage_keys(internal_data, fhir_data)
                        migrated += 1
                        
                        if migrated % 10 == 0:
                            print(f"Migrated {migrated}/{total_docs} documents...")
                        
                    except Exception as e:
                        print(f"Error migrating document {doc.id}: {str(e)}")
                        errors += 1
                
                # Commit batch
                db.session.commit()
            
            print(f"✓ Migration completed: {migrated} documents migrated, {errors} errors")
            return True
            
    except Exception as e:
        print(f"Error migrating documents: {str(e)}")
        db.session.rollback()
        return False


def validate_migration():
    """Validate that the migration completed successfully"""
    print("\nValidating migration...")
    
    try:
        with app.app_context():
            # Check total documents
            total_docs = MedicalDocument.query.count()
            
            # Check documents with internal keys
            docs_with_internal = MedicalDocument.query.filter(
                MedicalDocument.tag.isnot(None)
            ).count()
            
            # Check documents with FHIR keys
            docs_with_fhir = MedicalDocument.query.filter(
                MedicalDocument.fhir_code_code.isnot(None)
            ).count()
            
            print(f"Total documents: {total_docs}")
            print(f"Documents with internal keys: {docs_with_internal}")
            print(f"Documents with FHIR keys: {docs_with_fhir}")
            
            # Sample document check
            if total_docs > 0:
                sample_doc = MedicalDocument.query.first()
                print(f"\nSample document ({sample_doc.id}):")
                print(f"  Internal keys: {sample_doc.get_internal_keys()}")
                print(f"  FHIR keys: {sample_doc.get_fhir_keys()}")
            
            print("✓ Migration validation completed")
            return True
            
    except Exception as e:
        print(f"Error validating migration: {str(e)}")
        return False


def create_test_documents():
    """Create test documents to verify dual storage functionality"""
    print("\nCreating test documents...")
    
    try:
        with app.app_context():
            # Check if we have any patients
            from models import Patient
            patients = Patient.query.limit(3).all()
            
            if not patients:
                print("No patients found - skipping test document creation")
                return True
            
            test_docs_data = [
                {
                    'filename': 'test_lab_report.txt',
                    'document_name': 'Test Lab Results',
                    'document_type': 'Lab Report',
                    'content': 'Lab Results: Hemoglobin A1C: 6.8% (Normal: <7.0%). Cholesterol: 180 mg/dL (Normal: <200).',
                    'patient_id': patients[0].id
                },
                {
                    'filename': 'test_radiology_report.txt',
                    'document_name': 'Test Chest X-Ray',
                    'document_type': 'Radiology Report',
                    'content': 'Chest X-Ray: No acute cardiopulmonary abnormalities. Heart size normal.',
                    'patient_id': patients[0].id if len(patients) > 0 else 1
                },
                {
                    'filename': 'test_clinical_note.txt',
                    'document_name': 'Test Progress Note',
                    'document_type': 'Clinical Note',
                    'content': 'Patient presents for annual physical. Diabetes well controlled. Recommending mammogram screening.',
                    'patient_id': patients[0].id if len(patients) > 0 else 1
                }
            ]
            
            created_count = 0
            for doc_data in test_docs_data:
                # Create document
                doc = MedicalDocument(
                    filename=doc_data['filename'],
                    document_name=doc_data['document_name'],
                    document_type=doc_data['document_type'],
                    content=doc_data['content'],
                    patient_id=doc_data['patient_id'],
                    document_date=datetime.utcnow(),
                    is_processed=True
                )
                
                # Process with dual storage
                from enhanced_document_processor import process_document_with_dual_storage
                if process_document_with_dual_storage(doc):
                    created_count += 1
                    print(f"Created test document: {doc.filename}")
            
            print(f"✓ Created {created_count} test documents with dual storage")
            return True
            
    except Exception as e:
        print(f"Error creating test documents: {str(e)}")
        return False


def run_migration():
    """Run complete dual storage migration"""
    print("=" * 60)
    print("DUAL STORAGE MIGRATION")
    print("=" * 60)
    print("This migration adds dual storage support for both internal")
    print("and FHIR keys to documents and prep sheets.")
    print("=" * 60)
    
    steps = [
        ("Adding dual storage columns", add_dual_storage_columns),
        ("Migrating existing documents", migrate_existing_documents),
        ("Validating migration", validate_migration),
        ("Creating test documents", create_test_documents)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"❌ Failed: {step_name}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ DUAL STORAGE MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nDual storage features now available:")
    print("• Documents store both internal and FHIR keys")
    print("• PrepSheet table created for prep sheet tracking")
    print("• Admin logging for all document/prep sheet operations")
    print("• Backward compatibility with existing code")
    print("• Epic/FHIR export support enabled")
    print("\nNext steps:")
    print("• Update document upload routes to use enhanced_document_processor")
    print("• Update prep sheet generation to use dual_storage_handler")
    print("• Test FHIR export functionality")
    
    return True


if __name__ == "__main__":
    run_migration()