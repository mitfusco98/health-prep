
"""
Script to generate sample admin log data for testing
"""
from app import app, db
from models import AdminLog, User
from datetime import datetime, timedelta
import uuid
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_logs():
    """Generate sample admin log entries"""
    try:
        with app.app_context():
            # Get admin user
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                logger.error("Admin user not found. Please create admin user first.")
                return
            
            # Sample event types and details
            sample_events = [
                {
                    'event_type': 'login_success',
                    'user_id': admin_user.id,
                    'event_details': {
                        'username': 'admin',
                        'is_admin': True,
                        'login_method': 'web_form'
                    }
                },
                {
                    'event_type': 'login_fail',
                    'user_id': None,
                    'event_details': {
                        'attempted_username': 'wronguser',
                        'login_method': 'web_form',
                        'reason': 'invalid_credentials'
                    }
                },
                {
                    'event_type': 'admin_dashboard_access',
                    'user_id': admin_user.id,
                    'event_details': {
                        'action': 'admin_dashboard_viewed',
                        'username': 'admin'
                    }
                },
                {
                    'event_type': 'validation_error',
                    'user_id': admin_user.id,
                    'event_details': {
                        'action': 'add_patient',
                        'form_errors': {'mrn': ['This field is required.']},
                        'form_data_fields': ['first_name', 'last_name', 'mrn']
                    }
                },
                {
                    'event_type': 'patient_created',
                    'user_id': admin_user.id,
                    'event_details': {
                        'action': 'patient_created',
                        'patient_mrn': 'MRN001',
                        'patient_name': 'John Doe'
                    }
                }
            ]
            
            # Generate logs for the past week
            base_time = datetime.now()
            for i in range(15):  # Generate 15 log entries
                # Choose random event
                event = random.choice(sample_events)
                
                # Create timestamp going back in time
                hours_ago = random.randint(1, 168)  # Random time in past week
                timestamp = base_time - timedelta(hours=hours_ago)
                
                # Create log entry
                log_entry = AdminLog(
                    timestamp=timestamp,
                    user_id=event['user_id'],
                    event_type=event['event_type'],
                    event_details=str(event['event_details']).replace("'", '"'),  # Convert to JSON-like string
                    request_id=str(uuid.uuid4()),
                    ip_address=f"10.0.0.{random.randint(1, 255)}",
                    user_agent="Mozilla/5.0 (Sample User Agent)"
                )
                
                db.session.add(log_entry)
            
            db.session.commit()
            logger.info("Sample admin logs generated successfully")
            print("Sample admin logs generated successfully!")
            
            # Show count of logs
            total_logs = AdminLog.query.count()
            print(f"Total admin logs in database: {total_logs}")
            
    except Exception as e:
        logger.error(f"Error generating sample logs: {str(e)}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    generate_sample_logs()
