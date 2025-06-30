"""
Performance Optimization Script
Adds database indexes and query optimizations to fix slow loading times
"""

from app import app, db
from sqlalchemy import text, Index
from models import Patient, Appointment, MedicalDocument, LabResult
import logging

def add_critical_indexes():
    """Add database indexes for performance optimization"""
    
    with app.app_context():
        try:
            # Add indexes that are critical for performance
            indexes_to_add = [
                # Patient table optimizations
                "CREATE INDEX IF NOT EXISTS idx_patient_last_name ON patient(last_name)",
                "CREATE INDEX IF NOT EXISTS idx_patient_first_name ON patient(first_name)", 
                "CREATE INDEX IF NOT EXISTS idx_patient_mrn ON patient(mrn)",
                "CREATE INDEX IF NOT EXISTS idx_patient_created_at ON patient(created_at)",
                
                # Appointment table optimizations
                "CREATE INDEX IF NOT EXISTS idx_appointment_date ON appointment(appointment_date)",
                "CREATE INDEX IF NOT EXISTS idx_appointment_patient_id ON appointment(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_appointment_status ON appointment(status)",
                "CREATE INDEX IF NOT EXISTS idx_appointment_date_time ON appointment(appointment_date, appointment_time)",
                
                # Medical document optimizations (critical for 570ms query)
                "CREATE INDEX IF NOT EXISTS idx_medical_document_patient_id ON medical_document(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_type ON medical_document(document_type)",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_created_at ON medical_document(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_filename ON medical_document(filename)",
                
                # Lab result optimizations  
                "CREATE INDEX IF NOT EXISTS idx_lab_result_patient_id ON lab_result(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_lab_result_test_date ON lab_result(test_date)",
                
                # Composite indexes for common query patterns
                "CREATE INDEX IF NOT EXISTS idx_patient_name_composite ON patient(last_name, first_name)",
                "CREATE INDEX IF NOT EXISTS idx_appointment_patient_date ON appointment(patient_id, appointment_date)",
            ]
            
            for sql in indexes_to_add:
                try:
                    db.session.execute(text(sql))
                    print(f"✓ Added index: {sql.split('idx_')[1].split(' ON')[0]}")
                except Exception as e:
                    print(f"⚠ Index may already exist: {e}")
            
            db.session.commit()
            print("✓ All performance indexes added successfully")
            
        except Exception as e:
            print(f"❌ Error adding indexes: {e}")
            db.session.rollback()


def optimize_home_page_queries():
    """Add specific optimizations for home page queries"""
    
    with app.app_context():
        try:
            # Add indexes specifically for home page dashboard queries
            home_page_indexes = [
                # For counting queries (SELECT count(*))
                "CREATE INDEX IF NOT EXISTS idx_patient_count ON patient(id) WHERE id IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_appointment_today ON appointment(appointment_date) WHERE appointment_date >= CURRENT_DATE",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_recent ON medical_document(created_at) WHERE created_at >= (CURRENT_DATE - INTERVAL '7 days')",
            ]
            
            for sql in home_page_indexes:
                try:
                    db.session.execute(text(sql))
                    print(f"✓ Added home page index")
                except Exception as e:
                    print(f"⚠ Home page index may already exist: {e}")
            
            db.session.commit()
            print("✓ Home page query optimizations added")
            
        except Exception as e:
            print(f"❌ Error adding home page optimizations: {e}")
            db.session.rollback()


if __name__ == "__main__":
    print("Starting performance optimization...")
    add_critical_indexes()
    optimize_home_page_queries()
    print("Performance optimization complete!")