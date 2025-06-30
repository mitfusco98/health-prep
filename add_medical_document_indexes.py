
#!/usr/bin/env python3
"""
Add database indexes to fix slow medical_document queries
Run this script to optimize database performance
"""

from app import app, db
from sqlalchemy import text
import logging

def add_medical_document_indexes():
    """Add indexes to medical_document table for performance optimization"""
    
    with app.app_context():
        try:
            # Add indexes for commonly queried columns
            indexes_to_add = [
                "CREATE INDEX IF NOT EXISTS idx_medical_document_patient_id ON medical_document(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_document_date ON medical_document(document_date);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_document_type ON medical_document(document_type);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_created_at ON medical_document(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_patient_date ON medical_document(patient_id, document_date);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_patient_type ON medical_document(patient_id, document_type);"
            ]
            
            for index_sql in indexes_to_add:
                print(f"Creating index: {index_sql}")
                db.session.execute(text(index_sql))
                
            db.session.commit()
            print("✓ All medical_document indexes created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating indexes: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    add_medical_document_indexes()
