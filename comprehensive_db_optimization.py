
#!/usr/bin/env python3
"""
Comprehensive database optimization script to fix all slow queries
"""

from app import app, db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def optimize_all_database_queries():
    """Add all missing indexes to optimize slow queries"""
    
    with app.app_context():
        try:
            # Check if we're using PostgreSQL or SQLite
            is_postgresql = str(db.engine.url).startswith('postgresql')
            print(f"Database type: {'PostgreSQL' if is_postgresql else 'SQLite'}")
            
            # Core table indexes that are definitely missing
            all_indexes = [
                # Medical document indexes (579ms query fix)
                "CREATE INDEX IF NOT EXISTS idx_medical_document_patient_id ON medical_document(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_document_date ON medical_document(document_date);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_document_type ON medical_document(document_type);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_created_at ON medical_document(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_patient_date ON medical_document(patient_id, document_date);",
                "CREATE INDEX IF NOT EXISTS idx_medical_document_patient_type ON medical_document(patient_id, document_type);",
                
                # Patient table indexes (127ms query fix)
                "CREATE INDEX IF NOT EXISTS idx_patient_mrn ON patient(mrn);",
                "CREATE INDEX IF NOT EXISTS idx_patient_name ON patient(first_name, last_name);",
                "CREATE INDEX IF NOT EXISTS idx_patient_created_at ON patient(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_patient_last_first ON patient(last_name, first_name);",
                
                # Appointment table indexes (63ms query fix)
                "CREATE INDEX IF NOT EXISTS idx_appointment_date ON appointment(appointment_date);",
                "CREATE INDEX IF NOT EXISTS idx_appointment_patient_id ON appointment(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_appointment_datetime ON appointment(appointment_date, appointment_time);",
                "CREATE INDEX IF NOT EXISTS idx_appointment_status ON appointment(status);",
                
                # Lab result indexes (68ms query fix)
                "CREATE INDEX IF NOT EXISTS idx_lab_result_patient_id ON lab_result(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_lab_result_test_date ON lab_result(test_date);",
                "CREATE INDEX IF NOT EXISTS idx_lab_result_test_name ON lab_result(test_name);",
                
                # EHR connection indexes (127ms query fix)
                "CREATE INDEX IF NOT EXISTS idx_ehr_connection_name ON ehr_connection(name);",
                "CREATE INDEX IF NOT EXISTS idx_ehr_connection_vendor ON ehr_connection(vendor);",
                
                # Additional commonly queried tables
                "CREATE INDEX IF NOT EXISTS idx_visit_patient_id ON visit(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_visit_date ON visit(visit_date);",
                "CREATE INDEX IF NOT EXISTS idx_condition_patient_id ON condition(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_condition_active ON condition(is_active);",
                "CREATE INDEX IF NOT EXISTS idx_vital_patient_id ON vital(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_vital_date ON vital(date);",
                "CREATE INDEX IF NOT EXISTS idx_screening_patient_id ON screening(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_screening_due_date ON screening(due_date);",
                "CREATE INDEX IF NOT EXISTS idx_patient_alert_patient_id ON patient_alert(patient_id);",
                "CREATE INDEX IF NOT EXISTS idx_patient_alert_active ON patient_alert(is_active);",
            ]
            
            success_count = 0
            skip_count = 0
            
            for index_sql in all_indexes:
                try:
                    print(f"Creating index: {index_sql}")
                    db.session.execute(text(index_sql))
                    db.session.commit()
                    success_count += 1
                    print("✓ Success")
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        print("⚡ Already exists - skipping")
                        skip_count += 1
                    else:
                        print(f"❌ Failed: {str(e)}")
                    db.session.rollback()
                    continue
                    
            print(f"\n📊 Index Creation Summary:")
            print(f"✅ Successfully created: {success_count}")
            print(f"⚡ Already existed: {skip_count}")
            print(f"🎯 Total processed: {len(all_indexes)}")
            print("\n🚀 Database optimization completed!")
            
            # Update table statistics for better query planning
            if is_postgresql:
                try:
                    print("\n📈 Updating PostgreSQL table statistics...")
                    stat_updates = [
                        "ANALYZE medical_document;",
                        "ANALYZE patient;", 
                        "ANALYZE appointment;",
                        "ANALYZE lab_result;",
                        "ANALYZE ehr_connection;"
                    ]
                    
                    for stat_sql in stat_updates:
                        db.session.execute(text(stat_sql))
                        print(f"✓ {stat_sql}")
                    
                    db.session.commit()
                    print("✅ Statistics updated successfully!")
                    
                except Exception as e:
                    print(f"⚠️  Could not update statistics: {str(e)}")
                    db.session.rollback()
            
        except Exception as e:
            print(f"❌ Critical error during optimization: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    optimize_all_database_queries()
