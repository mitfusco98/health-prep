
from sqlalchemy import text
from app import db
import logging

logger = logging.getLogger(__name__)

def add_database_indexes():
    """Add missing database indexes for better query performance"""
    indexes_to_add = [
        # Patient table indexes
        "CREATE INDEX IF NOT EXISTS idx_patient_mrn ON patient(mrn);",
        "CREATE INDEX IF NOT EXISTS idx_patient_name ON patient(first_name, last_name);",
        "CREATE INDEX IF NOT EXISTS idx_patient_created ON patient(created_at);",
        
        # Appointment table indexes
        "CREATE INDEX IF NOT EXISTS idx_appointment_date ON appointment(appointment_date);",
        "CREATE INDEX IF NOT EXISTS idx_appointment_patient ON appointment(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_appointment_datetime ON appointment(appointment_date, appointment_time);",
        
        # Visit table indexes
        "CREATE INDEX IF NOT EXISTS idx_visit_patient ON visit(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_visit_date ON visit(visit_date);",
        
        # Condition table indexes
        "CREATE INDEX IF NOT EXISTS idx_condition_patient ON condition(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_condition_active ON condition(is_active);",
        
        # Vital table indexes
        "CREATE INDEX IF NOT EXISTS idx_vital_patient ON vital(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_vital_date ON vital(date);",
        
        # Lab result indexes
        "CREATE INDEX IF NOT EXISTS idx_lab_patient ON lab_result(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_lab_date ON lab_result(test_date);",
        
        # Screening indexes
        "CREATE INDEX IF NOT EXISTS idx_screening_patient ON screening(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_screening_due ON screening(due_date);",
        
        # Alert indexes
        "CREATE INDEX IF NOT EXISTS idx_alert_patient ON patient_alert(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_alert_active ON patient_alert(is_active);",
        
        # Admin log indexes
        "CREATE INDEX IF NOT EXISTS idx_admin_log_timestamp ON admin_log(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_admin_log_user ON admin_log(user_id);",
    ]
    
    try:
        with db.engine.connect() as conn:
            for index_sql in indexes_to_add:
                try:
                    conn.execute(text(index_sql))
                    logger.info(f"Successfully created index: {index_sql}")
                except Exception as e:
                    logger.warning(f"Could not create index (may already exist): {e}")
            
            conn.commit()
            logger.info("Database index optimization completed")
            
    except Exception as e:
        logger.error(f"Error adding database indexes: {e}")

def analyze_slow_queries():
    """Analyze and report on potentially slow queries"""
    import time
    
    slow_query_checks = [
        {
            'name': 'Patients without MRN index usage',
            'query': "SELECT COUNT(*) FROM patient WHERE mrn LIKE '%test%';",
            'description': 'This query may not use the MRN index if LIKE pattern starts with %'
        },
        {
            'name': 'Appointments without date range',
            'query': "SELECT COUNT(*) FROM appointment WHERE appointment_date > CURRENT_DATE - INTERVAL '30 days';",
            'description': 'Date range queries should use proper indexes'
        },
        {
            'name': 'Medical documents query optimization',
            'query': "SELECT COUNT(*) FROM medical_document LIMIT 1000;",
            'description': 'Large document tables need pagination and indexing'
        }
    ]
    
    results = []
    try:
        with db.engine.connect() as conn:
            for check in slow_query_checks:
                start_time = time.time()
                try:
                    result = conn.execute(text(check['query']))
                    count = result.scalar()
                    duration = (time.time() - start_time) * 1000
                    
                    results.append({
                        'name': check['name'],
                        'duration_ms': duration,
                        'result_count': count,
                        'description': check['description'],
                        'query': check['query']
                    })
                    
                except Exception as e:
                    results.append({
                        'name': check['name'],
                        'error': str(e),
                        'description': check['description']
                    })
                    
    except Exception as e:
        logger.error(f"Error analyzing slow queries: {e}")
        
    return results

if __name__ == '__main__':
    from app import app
    with app.app_context():
        print("Adding database indexes...")
        add_database_indexes()
        print("\nAnalyzing query performance...")
        results = analyze_slow_queries()
        for result in results:
            print(f"\n{result['name']}:")
            if 'duration_ms' in result:
                print(f"  Duration: {result['duration_ms']:.1f}ms")
                print(f"  Results: {result['result_count']}")
            if 'error' in result:
                print(f"  Error: {result['error']}")
            print(f"  Description: {result['description']}")
