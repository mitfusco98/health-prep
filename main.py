import os

# Set default FLASK_ENV if not provided
if not os.environ.get("FLASK_ENV"):
    os.environ["FLASK_ENV"] = "development"

from app import app, db  # noqa: F401

# Import all route modules
import demo_routes  # noqa: F401
import ehr_routes  # noqa: F401
import checklist_routes  # noqa: F401
import api_routes  # noqa: F401
import performance_routes  # noqa: F401
import screening_keyword_routes  # noqa: F401

# Import modular route files
from routes import patient_routes  # noqa: F401
from routes import appointment_routes  # noqa: F401

# Import service layers for dependency injection
from services import patient_service, appointment_service  # noqa: F401
import logging

# Defer EHR connection initialization for faster startup
if __name__ != "__main__":
    def lazy_load_ehr():
        """Initialize EHR connections in background after startup"""
        import threading
        import time
        
        def init_ehr():
            time.sleep(3)  # Wait 3 seconds after startup
            try:
                from ehr_routes import import_connections_on_startup
                import_connections_on_startup()
                print("EHR connections initialized")
            except Exception as e:
                print(f"Error initializing EHR connections: {e}")
        
        thread = threading.Thread(target=init_ehr, daemon=True)
        thread.start()
    
    lazy_load_ehr()

    # Defer heavy operations to after startup for faster boot
    def init_sample_data():
        """Initialize sample data in background after startup"""
        import threading
        import time
        
        def delayed_init():
            time.sleep(5)  # Wait 5 seconds after startup
            with app.app_context():
                try:
                    from models import Patient, Appointment
                    from datetime import date, time as time_obj
                    import random

                    # Only add sample appointments if we have patients but no appointments for today
                    today = date.today()
                    patients = Patient.query.limit(10).all()  # Limit query for speed
                    today_appointments = Appointment.query.filter_by(
                        appointment_date=today
                    ).limit(1).first()  # Just check if any exist

                    if patients and not today_appointments:
                        # Common appointment reasons
                        appointment_reasons = [
                            "Annual physical",
                            "Follow-up visit",
                            "Blood pressure check",
                            "Medication review",
                            "Diabetes checkup",
                        ]

                        # Create 3 appointments for today (reduced for speed)
                        used_times = []
                        for _ in range(3):
                            patient = random.choice(patients)

                            hour = random.randint(9, 15)
                            minute = random.choice([0, 30])
                            appointment_time = time_obj(hour=hour, minute=minute)

                            if appointment_time not in used_times:
                                used_times.append(appointment_time)
                                appointment = Appointment(
                                    patient_id=patient.id,
                                    appointment_date=today,
                                    appointment_time=appointment_time,
                                    note=random.choice(appointment_reasons),
                                )
                                db.session.add(appointment)

                        db.session.commit()
                        logging.info(f"Added sample appointments for today")
                except Exception as e:
                    logging.error(f"Error adding sample appointments: {e}")
        
        thread = threading.Thread(target=delayed_init, daemon=True)
        thread.start()
    
    # Start background initialization
    init_sample_data()
