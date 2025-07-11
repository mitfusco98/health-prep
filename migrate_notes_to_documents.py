#!/usr/bin/env python3
"""
Migration Script: Convert existing screening notes with document IDs to many-to-many relationships

This script migrates from the old pipe-separated document ID storage in screening.notes
to the new proper many-to-many relationship between Screening and MedicalDocument models.
"""

import re
from app import app, db
from models import Screening, MedicalDocument

def migrate_notes_to_documents():
    """
    Migrate existing screening notes containing document IDs to the new many-to-many relationship
    """
    with app.app_context():
        print("Starting migration from notes to many-to-many document relationships...")
        
        # Get all screenings that have notes containing document IDs
        screenings = Screening.query.filter(Screening.notes.isnot(None)).all()
        
        migrated_count = 0
        error_count = 0
        
        for screening in screenings:
            try:
                # Extract document IDs from notes using regex
                doc_id_pattern = r'Document ID:\s*(\d+)'
                doc_ids = re.findall(doc_id_pattern, screening.notes or '')
                
                if doc_ids:
                    print(f"Processing screening {screening.id} with {len(doc_ids)} document IDs: {doc_ids}")
                    
                    for doc_id_str in doc_ids:
                        try:
                            doc_id = int(doc_id_str)
                            document = MedicalDocument.query.get(doc_id)
                            
                            if document:
                                # Add document to screening using the new relationship
                                screening.add_document(document, confidence_score=1.0, match_source='migrated')
                                print(f"  - Added document {doc_id} to screening {screening.id}")
                            else:
                                print(f"  - Document {doc_id} not found, skipping")
                                
                        except (ValueError, TypeError) as e:
                            print(f"  - Error processing document ID {doc_id_str}: {e}")
                            error_count += 1
                    
                    # Clean up notes by removing document ID references but keeping other content
                    cleaned_notes = re.sub(r'\|\s*Document ID:\s*\d+', '', screening.notes)
                    cleaned_notes = re.sub(r'Document ID:\s*\d+\s*\|?', '', cleaned_notes)
                    cleaned_notes = cleaned_notes.strip(' |')
                    
                    # Only keep the status and due date information in notes
                    screening.notes = cleaned_notes if cleaned_notes else None
                    
                    migrated_count += 1
                    
            except Exception as e:
                print(f"Error processing screening {screening.id}: {e}")
                error_count += 1
                db.session.rollback()
                continue
        
        try:
            db.session.commit()
            print(f"\nMigration completed successfully!")
            print(f"Migrated screenings: {migrated_count}")
            print(f"Errors encountered: {error_count}")
            
            # Verify the migration
            verify_migration()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error committing migration: {e}")

def verify_migration():
    """Verify that the migration was successful"""
    print("\nVerifying migration...")
    
    # Count screenings with document relationships
    screenings_with_docs = db.session.query(Screening).join(Screening.documents).distinct().count()
    print(f"Screenings with document relationships: {screenings_with_docs}")
    
    # Show sample of migrated data
    sample_screenings = Screening.query.join(Screening.documents).limit(5).all()
    
    for screening in sample_screenings:
        doc_count = screening.document_count
        print(f"Screening {screening.id} ({screening.screening_type}): {doc_count} documents")
        for doc in screening.matched_documents[:3]:  # Show first 3 documents
            print(f"  - Document {doc.id}: {doc.document_name or doc.filename}")

def rollback_migration():
    """
    Rollback the migration by moving document relationships back to notes
    WARNING: This will overwrite existing notes content
    """
    print("Rolling back migration...")
    
    with app.app_context():
        screenings = Screening.query.join(Screening.documents).all()
        
        for screening in screenings:
            doc_ids = [str(doc.id) for doc in screening.matched_documents]
            if doc_ids:
                # Recreate the old notes format
                status_note = "✓ Found matching documents" if screening.status == 'Complete' else "❌ No matching documents"
                doc_notes = [f"Document ID: {doc_id}" for doc_id in doc_ids]
                screening.notes = " | ".join([status_note] + doc_notes)
                
                # Clear document relationships
                screening.documents.delete()
        
        db.session.commit()
        print("Migration rolled back successfully")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        migrate_notes_to_documents()