import os

# Set default FLASK_ENV if not provided
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'

from app import app, db  # noqa: F401
import demo_routes  # noqa: F401
import ehr_routes  # noqa: F401
import checklist_routes  # noqa: F401
import api_routes  # noqa: F401
import logging

# Initialize EHR connections
if __name__ != '__main__':
    try:
        from ehr_routes import import_connections_on_startup
        import_connections_on_startup()
    except Exception as e:
        print(f"Error initializing EHR connections: {e}")
    
    # Add sample data for today's appointments
    with app.app_context():
        try:
            from models import Patient, Appointment
            from datetime import date, time
            import random
            
            # Only add sample appointments if we have patients but no appointments for today
            today = date.today()
            patients = Patient.query.all()
            today_appointments = Appointment.query.filter_by(appointment_date=today).all()
            
            if patients and not today_appointments:
                # Common appointment reasons
                appointment_reasons = [
                    "Annual physical",
                    "Follow-up visit",
                    "Blood pressure check",
                    "Medication review",
                    "Diabetes checkup",
                    "Lab result discussion",
                    "Preventive care visit"
                ]
                
                # Create 5 appointments for today
                used_times = []
                for _ in range(5):
                    # Get a random patient
                    patient = random.choice(patients)
                    
                    # Generate a time that hasn't been used yet
                    while True:
                        hour = random.randint(8, 16)  # 8 AM to 4 PM
                        minute = random.choice([0, 15, 30, 45])
                        appointment_time = time(hour=hour, minute=minute)
                        
                        # Check if this time is already used
                        if appointment_time not in used_times:
                            used_times.append(appointment_time)
                            break
                    
                    # Create the appointment
                    appointment = Appointment(
                        patient_id=patient.id,
                        appointment_date=today,
                        appointment_time=appointment_time,
                        note=random.choice(appointment_reasons)
                    )
                    
                    db.session.add(appointment)
                
                db.session.commit()
                logging.info(f"Added 5 sample appointments for today")
        except Exception as e:
            logging.error(f"Error adding sample appointments: {e}")
