#!/usr/bin/env python3
"""
Script to add five test patients for bulk deletion testing
"""

from app import app, db
from models import Patient
from datetime import datetime, date
import random

def add_test_patients():
    """Add five test patients to the database"""
    
    # Test patient data
    test_patients = [
        {
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'date_of_birth': date(1985, 3, 15),
            'sex': 'Female',
            'mrn': f'TEST{random.randint(10000, 99999)}',
            'phone': '555-0101',
            'email': 'alice.johnson@test.com',
            'address': '123 Main St, Test City, TC 12345',
            'insurance': 'Blue Cross Blue Shield'
        },
        {
            'first_name': 'Bob',
            'last_name': 'Williams',
            'date_of_birth': date(1992, 7, 22),
            'sex': 'Male',
            'mrn': f'TEST{random.randint(10000, 99999)}',
            'phone': '555-0102',
            'email': 'bob.williams@test.com',
            'address': '456 Oak Ave, Test City, TC 12345',
            'insurance': 'Aetna'
        },
        {
            'first_name': 'Carol',
            'last_name': 'Davis',
            'date_of_birth': date(1978, 11, 8),
            'sex': 'Female',
            'mrn': f'TEST{random.randint(10000, 99999)}',
            'phone': '555-0103',
            'email': 'carol.davis@test.com',
            'address': '789 Pine Rd, Test City, TC 12345',
            'insurance': 'UnitedHealth'
        },
        {
            'first_name': 'David',
            'last_name': 'Miller',
            'date_of_birth': date(1990, 5, 30),
            'sex': 'Male',
            'mrn': f'TEST{random.randint(10000, 99999)}',
            'phone': '555-0104',
            'email': 'david.miller@test.com',
            'address': '321 Elm St, Test City, TC 12345',
            'insurance': 'Cigna'
        },
        {
            'first_name': 'Emma',
            'last_name': 'Wilson',
            'date_of_birth': date(1987, 9, 12),
            'sex': 'Female',
            'mrn': f'TEST{random.randint(10000, 99999)}',
            'phone': '555-0105',
            'email': 'emma.wilson@test.com',
            'address': '654 Maple Dr, Test City, TC 12345',
            'insurance': 'Kaiser Permanente'
        }
    ]
    
    created_patients = []
    
    try:
        for patient_data in test_patients:
            # Check if a patient with this MRN already exists
            existing = Patient.query.filter_by(mrn=patient_data['mrn']).first()
            if existing:
                # Generate a new MRN if there's a conflict
                patient_data['mrn'] = f'TEST{random.randint(10000, 99999)}'
            
            patient = Patient()
            patient.first_name = patient_data['first_name']
            patient.last_name = patient_data['last_name']
            patient.date_of_birth = patient_data['date_of_birth']
            patient.sex = patient_data['sex']
            patient.mrn = patient_data['mrn']
            patient.phone = patient_data['phone']
            patient.email = patient_data['email']
            patient.address = patient_data['address']
            patient.insurance = patient_data['insurance']
            patient.created_at = datetime.now()
            
            db.session.add(patient)
            created_patients.append(patient)
        
        db.session.commit()
        
        print(f"Successfully created {len(created_patients)} test patients:")
        for patient in created_patients:
            print(f"  - {patient.full_name} (MRN: {patient.mrn}, ID: {patient.id})")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating test patients: {str(e)}")
        return False

if __name__ == '__main__':
    with app.app_context():
        add_test_patients()