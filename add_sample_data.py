import random
from datetime import datetime, timedelta
from app import app, db
from models import (Patient, Condition, Vital, Visit, LabResult, ImagingStudy, 
                    ConsultReport, HospitalSummary, Screening, DocumentType, MedicalDocument,
                    Appointment)
from utils import evaluate_screening_needs

# Custom functions
def random_date(start_date, end_date):
    """Generate a random date between start_date and end_date"""
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def random_past_date(years_ago_min=1, years_ago_max=5):
    """Generate a random date in the past"""
    today = datetime.now()
    years_ago_min_date = today - timedelta(days=365 * years_ago_min)
    years_ago_max_date = today - timedelta(days=365 * years_ago_max)
    return random_date(years_ago_max_date, years_ago_min_date)

def random_future_date(days_ahead_min=1, days_ahead_max=60):
    """Generate a random date in the future"""
    today = datetime.now()
    days_ahead_min_date = today + timedelta(days=days_ahead_min)
    days_ahead_max_date = today + timedelta(days=days_ahead_max)
    return random_date(days_ahead_min_date, days_ahead_max_date)

def add_demo_patients():
    # Sample Patients
    patients_data = [
        {
            'first_name': 'John',
            'last_name': 'Smith',
            'date_of_birth': datetime(1975, 5, 15),
            'sex': 'Male',
            'mrn': 'MRN100001',
            'phone': '555-123-4567',
            'email': 'john.smith@example.com',
            'address': '123 Main St, Anytown, USA',
            'insurance': 'Blue Cross Blue Shield'
        },
        {
            'first_name': 'Emma',
            'last_name': 'Johnson',
            'date_of_birth': datetime(1982, 8, 22),
            'sex': 'Female',
            'mrn': 'MRN100002',
            'phone': '555-234-5678',
            'email': 'emma.johnson@example.com',
            'address': '456 Elm St, Somewhere, USA',
            'insurance': 'Aetna'
        },
        {
            'first_name': 'Michael',
            'last_name': 'Williams',
            'date_of_birth': datetime(1968, 12, 10),
            'sex': 'Male',
            'mrn': 'MRN100003',
            'phone': '555-345-6789',
            'email': 'michael.williams@example.com',
            'address': '789 Oak St, Nowhere, USA',
            'insurance': 'United Healthcare'
        },
        {
            'first_name': 'Sophia',
            'last_name': 'Miller',
            'date_of_birth': datetime(1995, 3, 30),
            'sex': 'Female',
            'mrn': 'MRN100004',
            'phone': '555-456-7890',
            'email': 'sophia.miller@example.com',
            'address': '321 Pine St, Everywhere, USA',
            'insurance': 'Cigna'
        },
        {
            'first_name': 'Robert',
            'last_name': 'Davis',
            'date_of_birth': datetime(1950, 9, 5),
            'sex': 'Male',
            'mrn': 'MRN100005',
            'phone': '555-567-8901',
            'email': 'robert.davis@example.com',
            'address': '654 Cedar St, Somewhere, USA',
            'insurance': 'Medicare'
        },
        {
            'first_name': 'Olivia',
            'last_name': 'Garcia',
            'date_of_birth': datetime(1988, 7, 17),
            'sex': 'Female',
            'mrn': 'MRN100006',
            'phone': '555-678-9012',
            'email': 'olivia.garcia@example.com',
            'address': '987 Maple St, Anywhere, USA',
            'insurance': 'Humana'
        },
        {
            'first_name': 'William',
            'last_name': 'Rodriguez',
            'date_of_birth': datetime(1972, 4, 20),
            'sex': 'Male',
            'mrn': 'MRN100007',
            'phone': '555-789-0123',
            'email': 'william.rodriguez@example.com',
            'address': '159 Birch St, Nowhere, USA',
            'insurance': 'Medicaid'
        },
        {
            'first_name': 'Ava',
            'last_name': 'Brown',
            'date_of_birth': datetime(1990, 10, 8),
            'sex': 'Female',
            'mrn': 'MRN100008',
            'phone': '555-890-1234',
            'email': 'ava.brown@example.com',
            'address': '753 Walnut St, Somewhere, USA',
            'insurance': 'Kaiser Permanente'
        },
        {
            'first_name': 'James',
            'last_name': 'Martinez',
            'date_of_birth': datetime(1958, 1, 25),
            'sex': 'Male',
            'mrn': 'MRN100009',
            'phone': '555-901-2345',
            'email': 'james.martinez@example.com',
            'address': '852 Spruce St, Anywhere, USA',
            'insurance': 'TRICARE'
        },
        {
            'first_name': 'Charlotte',
            'last_name': 'Taylor',
            'date_of_birth': datetime(1985, 6, 12),
            'sex': 'Female',
            'mrn': 'MRN100010',
            'phone': '555-012-3456',
            'email': 'charlotte.taylor@example.com',
            'address': '426 Aspen St, Everywhere, USA',
            'insurance': 'Anthem'
        }
    ]
    
    # Common Conditions
    conditions_data = [
        ('Hypertension', 'I10', True),
        ('Type 2 Diabetes', 'E11.9', True),
        ('Asthma', 'J45.909', True),
        ('Hyperlipidemia', 'E78.5', True),
        ('Obesity', 'E66.9', True),
        ('Depression', 'F32.9', True),
        ('Anxiety Disorder', 'F41.9', True),
        ('Osteoarthritis', 'M19.90', True),
        ('GERD', 'K21.9', True),
        ('Hypothyroidism', 'E03.9', True),
        ('Migraine', 'G43.909', True),
        ('Sleep Apnea', 'G47.30', True),
        ('Allergic Rhinitis', 'J30.9', False),
        ('Iron Deficiency Anemia', 'D50.9', False),
        ('Atrial Fibrillation', 'I48.91', True)
    ]
    
    # Lab Tests
    lab_tests = [
        ('Hemoglobin A1C', '%', '4.0-5.6', lambda: round(random.uniform(4.0, 8.0), 1)),
        ('Fasting Glucose', 'mg/dL', '70-99', lambda: random.randint(70, 180)),
        ('Total Cholesterol', 'mg/dL', '<200', lambda: random.randint(120, 280)),
        ('LDL Cholesterol', 'mg/dL', '<100', lambda: random.randint(60, 180)),
        ('HDL Cholesterol', 'mg/dL', '>40', lambda: random.randint(30, 80)),
        ('Triglycerides', 'mg/dL', '<150', lambda: random.randint(50, 300)),
        ('Hemoglobin', 'g/dL', '12.0-15.5', lambda: round(random.uniform(10.0, 17.0), 1)),
        ('White Blood Cell Count', 'K/uL', '4.5-11.0', lambda: round(random.uniform(3.0, 15.0), 1)),
        ('Platelets', 'K/uL', '150-450', lambda: random.randint(100, 500)),
        ('TSH', 'mIU/L', '0.4-4.0', lambda: round(random.uniform(0.1, 8.0), 2)),
        ('Creatinine', 'mg/dL', '0.6-1.2', lambda: round(random.uniform(0.5, 2.0), 1)),
        ('eGFR', 'mL/min', '>60', lambda: random.randint(30, 120)),
        ('ALT', 'U/L', '7-56', lambda: random.randint(5, 100)),
        ('AST', 'U/L', '10-40', lambda: random.randint(8, 80)),
        ('Vitamin D', 'ng/mL', '30-100', lambda: random.randint(15, 120))
    ]
    
    # Imaging Studies
    imaging_types = [
        ('X-Ray', ['Chest', 'Lumbar Spine', 'Knee', 'Ankle', 'Wrist']),
        ('MRI', ['Brain', 'Lumbar Spine', 'Shoulder', 'Knee', 'Hip']),
        ('CT', ['Chest', 'Abdomen', 'Pelvis', 'Head', 'Sinus']),
        ('Ultrasound', ['Abdomen', 'Thyroid', 'Breast', 'Pelvic', 'Carotid']),
        ('Mammogram', ['Breast']),
        ('DEXA', ['Bone Density']),
        ('PET', ['Whole Body'])
    ]
    
    # Visit Types
    visit_types = [
        'Annual Physical',
        'Follow-up',
        'Urgent',
        'Specialist Consult',
        'Telemedicine'
    ]
    
    # Specialties
    specialties = [
        ('Cardiology', 'Dr. Robert Chen'),
        ('Gastroenterology', 'Dr. Sarah Johnson'),
        ('Endocrinology', 'Dr. Michael Peterson'),
        ('Neurology', 'Dr. Jessica Lee'),
        ('Orthopedics', 'Dr. David Wilson'),
        ('Dermatology', 'Dr. Emily Martinez'),
        ('Pulmonology', 'Dr. Thomas Brown'),
        ('Nephrology', 'Dr. Maria Rodriguez'),
        ('Rheumatology', 'Dr. James Taylor'),
        ('Urology', 'Dr. Lisa Garcia')
    ]
    
    # Hospitals
    hospitals = [
        'Memorial Hospital',
        'University Medical Center',
        'Community General Hospital',
        'Regional Medical Center',
        'St. Mary\'s Hospital'
    ]
    
    # Create patients
    created_patients = []
    for patient_data in patients_data:
        patient = Patient(**patient_data)
        db.session.add(patient)
        created_patients.append(patient)
    
    db.session.commit()
    
    # Create data for each patient
    for patient in created_patients:
        # Add 1-3 conditions
        num_conditions = random.randint(1, 3)
        selected_conditions = random.sample(conditions_data, num_conditions)
        
        for condition_name, condition_code, is_active in selected_conditions:
            diagnosed_date = random_past_date(1, 5)
            condition = Condition(
                patient_id=patient.id,
                name=condition_name,
                code=condition_code,
                diagnosed_date=diagnosed_date,
                is_active=is_active,
                notes=f"Diagnosed by Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])}"
            )
            db.session.add(condition)
        
        # Add vital signs
        height = random.uniform(150, 190)  # cm
        weight = random.uniform(50, 110)   # kg
        bmi = round(weight / ((height/100) ** 2), 1)
        
        vital = Vital(
            patient_id=patient.id,
            date=datetime.now() - timedelta(days=random.randint(0, 60)),
            height=height,
            weight=weight,
            temperature=round(random.uniform(36.0, 37.5), 1),
            blood_pressure_systolic=random.randint(110, 160),
            blood_pressure_diastolic=random.randint(60, 95),
            pulse=random.randint(60, 100),
            respiratory_rate=random.randint(12, 20),
            oxygen_saturation=random.randint(95, 100)
        )
        db.session.add(vital)
        
        # Add lab results (3-6 random tests)
        num_labs = random.randint(3, 6)
        selected_labs = random.sample(lab_tests, num_labs)
        
        for test_name, unit, reference_range, value_func in selected_labs:
            result_value = value_func()
            
            # Determine if abnormal based on reference range
            is_abnormal = False
            if '-' in reference_range:
                low, high = reference_range.split('-')
                is_abnormal = result_value < float(low) or result_value > float(high)
            elif '<' in reference_range:
                high = float(reference_range.replace('<', ''))
                is_abnormal = result_value >= high
            elif '>' in reference_range:
                low = float(reference_range.replace('>', ''))
                is_abnormal = result_value <= low
                
            lab = LabResult(
                patient_id=patient.id,
                test_name=test_name,
                test_date=datetime.now() - timedelta(days=random.randint(1, 90)),
                result_value=str(result_value),
                unit=unit,
                reference_range=reference_range,
                is_abnormal=is_abnormal,
                notes="Standard laboratory test"
            )
            db.session.add(lab)
        
        # Add imaging study (0-1 per patient)
        if random.random() < 0.7:  # 70% chance
            imaging_type, body_sites = random.choice(imaging_types)
            body_site = random.choice(body_sites)
            
            imaging = ImagingStudy(
                patient_id=patient.id,
                study_type=imaging_type,
                body_site=body_site,
                study_date=datetime.now() - timedelta(days=random.randint(1, 120)),
                findings=f"Study performed due to {random.choice(['pain', 'swelling', 'routine screening', 'follow-up'])}. " +
                         f"{random.choice(['No significant abnormalities detected.', 'Minor degenerative changes noted.', 'Normal for age.', 'Incidental finding of no clinical significance.'])}",
                impression="No acute process identified."
            )
            db.session.add(imaging)
        
        # Add specialist consult (0-1 per patient)
        if random.random() < 0.5:  # 50% chance
            specialty, specialist = random.choice(specialties)
            
            consult = ConsultReport(
                patient_id=patient.id,
                specialist=specialist,
                specialty=specialty,
                report_date=datetime.now() - timedelta(days=random.randint(1, 150)),
                reason=f"Evaluation of {random.choice(['persistent symptoms', 'abnormal test results', 'chronic condition management', 'new diagnosis'])}",
                findings=f"Patient presents with {random.choice(['mild', 'moderate', 'significant'])} symptoms. " +
                        f"{random.choice(['Physical exam unremarkable.', 'Laboratory studies reviewed.', 'Imaging results discussed.'])}",
                recommendations=f"{random.choice(['Continue current management.', 'Adjust medication regimen.', 'Follow up in 3 months.', 'Additional testing recommended.'])}"
            )
            db.session.add(consult)
        
        # Add hospital stay (0-1 per patient, less common)
        if random.random() < 0.2:  # 20% chance
            admission_date = datetime.now() - timedelta(days=random.randint(30, 180))
            discharge_date = admission_date + timedelta(days=random.randint(1, 10))
            
            hospital = HospitalSummary(
                patient_id=patient.id,
                admission_date=admission_date,
                discharge_date=discharge_date,
                hospital_name=random.choice(hospitals),
                admitting_diagnosis=random.choice(["Chest Pain", "Pneumonia", "Diabetic Ketoacidosis", "Gastrointestinal Bleeding", "COPD Exacerbation"]),
                discharge_diagnosis=random.choice(["Acute Coronary Syndrome", "Community Acquired Pneumonia", "Controlled Diabetes", "Gastritis", "Stable COPD"]),
                procedures=f"{random.choice(['Diagnostic testing', 'Interventional procedure', 'Therapeutic management', 'No invasive procedures'])}",
                discharge_medications=f"{random.choice(['Continue home medications.', 'Added 2 new medications.', 'Discontinued 1 medication.', 'No changes to medication regimen.'])}",
                followup_instructions=f"Follow up with {random.choice(['primary care', 'specialist', 'both primary care and specialist'])} within {random.choice(['1 week', '2 weeks', '1 month'])}"
            )
            db.session.add(hospital)
        
        # Add 1-3 office visits
        num_visits = random.randint(1, 3)
        for _ in range(num_visits):
            visit_date = datetime.now() - timedelta(days=random.randint(1, 200))
            
            visit = Visit(
                patient_id=patient.id,
                visit_date=visit_date,
                visit_type=random.choice(visit_types),
                provider=f"Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])}",
                reason=random.choice(["Annual physical", "Follow-up for chronic condition", "Acute illness", "Preventive care", "Medication review"]),
                notes=f"{random.choice(['Patient doing well.', 'Symptoms improving.', 'New concerns addressed.', 'Routine visit with no acute issues.'])}"
            )
            db.session.add(visit)
            
        # Add a future visit for some patients
        if random.random() < 0.4:  # 40% chance
            future_visit = Visit(
                patient_id=patient.id,
                visit_date=random_future_date(7, 60),
                visit_type=random.choice(visit_types),
                provider=f"Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])}",
                reason=random.choice(["Follow-up", "Annual physical", "Preventive care", "Chronic disease management"]),
                notes="Scheduled appointment"
            )
            db.session.add(future_visit)
        
    # Commit all changes
    db.session.commit()
    
    # Add screening recommendations
    for patient in created_patients:
        evaluate_screening_needs(patient)
    
    db.session.commit()
    
    print(f"Created {len(created_patients)} patients with sample medical data")


def add_sample_appointments():
    """Add sample appointments for today's date"""
    from datetime import time, date
    
    # Get all patients
    patients = Patient.query.all()
    if not patients:
        print("No patients found. Please add demo patients first.")
        return
    
    # Today's date
    today = date.today()
    
    # Clear any existing appointments for today to avoid duplicates
    existing_appointments = Appointment.query.filter_by(appointment_date=today).all()
    for appointment in existing_appointments:
        db.session.delete(appointment)
    
    # Create 5-8 appointments for today at different times
    num_appointments = random.randint(5, 8)
    used_times = []
    
    # Common appointment reasons
    appointment_reasons = [
        "Annual physical",
        "Follow-up visit",
        "Blood pressure check",
        "Medication review",
        "Chronic disease management",
        "Diabetes checkup",
        "Lab result discussion",
        "Respiratory symptoms",
        "Preventive care visit",
        "Vaccination"
    ]
    
    # Generate time slots between 8:00 AM and 5:00 PM
    for _ in range(num_appointments):
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
    print(f"Added {num_appointments} sample appointments for today")


# Run the functions with Flask app context
with app.app_context():
    # Only add demo patients if none exist
    if Patient.query.count() == 0:
        add_demo_patients()
    
    # Add sample appointments for today
    add_sample_appointments()