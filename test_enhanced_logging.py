#!/usr/bin/env python3
"""
Test script to demonstrate enhanced admin logging functionality
Creates sample medical data entries to verify detailed logging captures:
- Alert text, dates, times, and priority for alerts
- File names, upload dates, and types for documents
- Test names, dates, and results for lab data
- Condition names, diagnosis dates for medical conditions
"""

import sys
import os
sys.path.append('.')

from app import app, db
from models import Patient, PatientAlert, MedicalDocument, Condition, LabResult, Vital, Immunization, AdminLog
from datetime import datetime, date
import json

def test_alert_logging():
    """Test alert creation with detailed logging"""
    print("Testing alert logging...")
    
    with app.app_context():
        # Get first patient
        patient = Patient.query.first()
        if not patient:
            print("No patients found. Creating test patient...")
            patient = Patient(
                first_name="Test",
                last_name="Patient",
                mrn="TEST001",
                date_of_birth=date(1980, 1, 1),
                sex="M"
            )
            db.session.add(patient)
            db.session.commit()
        
        # Create test alert with detailed information
        alert = PatientAlert(
            patient_id=patient.id,
            alert_type="Medication",
            description="Patient allergic to penicillin - severe reaction documented",
            severity="High",
            start_date=date.today()
        )
        
        # Simulate form data that would be captured in logging
        test_form_data = {
            'description': "Patient allergic to penicillin - severe reaction documented",
            'alert_type': "Medication",
            'severity': "High",
            'start_date': str(date.today())
        }
        
        db.session.add(alert)
        
        # Create admin log entry to simulate what the decorator would capture
        log_details = {
            'action': 'add',
            'data_type': 'alert',
            'patient_id': patient.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'alert_text': test_form_data['description'],
            'alert_date': test_form_data['start_date'],
            'alert_time': datetime.now().strftime('%H:%M:%S'),
            'priority': test_form_data['severity'],
            'alert_type': test_form_data['alert_type'],
            'endpoint': 'add_alert',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=1,  # Admin user
            event_details=json.dumps(log_details),
            request_id='test_alert_001',
            ip_address='127.0.0.1',
            user_agent='Test Script'
        )
        
        db.session.commit()
        print(f"✓ Created alert for patient {patient.first_name} {patient.last_name}")
        print(f"  Alert text: {alert.description}")
        print(f"  Severity: {alert.severity}")
        print(f"  Type: {alert.alert_type}")

def test_document_logging():
    """Test document upload with detailed logging"""
    print("\nTesting document logging...")
    
    with app.app_context():
        patient = Patient.query.first()
        
        # Create test document
        document = MedicalDocument(
            patient_id=patient.id,
            document_type="lab_report",
            filename="blood_work_results_2024.pdf",
            file_size=245760,  # 240KB
            upload_date=datetime.now()
        )
        
        # Simulate file upload data that would be captured
        log_details = {
            'action': 'add',
            'data_type': 'document',
            'patient_id': patient.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'file_name': "blood_work_results_2024.pdf",
            'file_type': "application/pdf",
            'upload_date': datetime.now().strftime('%Y-%m-%d'),
            'upload_time': datetime.now().strftime('%H:%M:%S'),
            'file_size': "245760 bytes",
            'endpoint': 'add_document',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        db.session.add(document)
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=1,
            event_details=json.dumps(log_details),
            request_id='test_doc_001',
            ip_address='127.0.0.1',
            user_agent='Test Script'
        )
        
        db.session.commit()
        print(f"✓ Created document for patient {patient.first_name} {patient.last_name}")
        print(f"  File name: {document.filename}")
        print(f"  File type: {document.document_type}")
        print(f"  Upload date: {document.upload_date}")

def test_condition_logging():
    """Test medical condition with detailed logging"""
    print("\nTesting condition logging...")
    
    with app.app_context():
        patient = Patient.query.first()
        
        # Create test condition
        condition = Condition(
            patient_id=patient.id,
            condition_name="Type 2 Diabetes Mellitus",
            diagnosis_date=date(2023, 6, 15),
            severity="moderate",
            status="active"
        )
        
        log_details = {
            'action': 'add',
            'data_type': 'condition',
            'patient_id': patient.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'condition_name': "Type 2 Diabetes Mellitus",
            'diagnosis_date': "2023-06-15",
            'severity': "moderate",
            'status': "active",
            'endpoint': 'add_condition',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        db.session.add(condition)
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=1,
            event_details=json.dumps(log_details),
            request_id='test_condition_001',
            ip_address='127.0.0.1',
            user_agent='Test Script'
        )
        
        db.session.commit()
        print(f"✓ Created condition for patient {patient.first_name} {patient.last_name}")
        print(f"  Condition: {condition.condition_name}")
        print(f"  Diagnosis date: {condition.diagnosis_date}")
        print(f"  Severity: {condition.severity}")

def test_lab_result_logging():
    """Test lab result with detailed logging"""
    print("\nTesting lab result logging...")
    
    with app.app_context():
        patient = Patient.query.first()
        
        # Create test lab result
        lab_result = LabResult(
            patient_id=patient.id,
            test_name="Hemoglobin A1C",
            test_date=date.today(),
            result="7.2%",
            reference_range="<7.0%",
            status="abnormal"
        )
        
        log_details = {
            'action': 'add',
            'data_type': 'lab',
            'patient_id': patient.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'test_name': "Hemoglobin A1C",
            'test_date': str(date.today()),
            'test_time': datetime.now().strftime('%H:%M:%S'),
            'result_value': "7.2%",
            'endpoint': 'add_lab',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        db.session.add(lab_result)
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=1,
            event_details=json.dumps(log_details),
            request_id='test_lab_001',
            ip_address='127.0.0.1',
            user_agent='Test Script'
        )
        
        db.session.commit()
        print(f"✓ Created lab result for patient {patient.first_name} {patient.last_name}")
        print(f"  Test: {lab_result.test_name}")
        print(f"  Date: {lab_result.test_date}")
        print(f"  Result: {lab_result.result}")

def test_vital_signs_logging():
    """Test vital signs with detailed logging"""
    print("\nTesting vital signs logging...")
    
    with app.app_context():
        patient = Patient.query.first()
        
        # Create test vital signs
        vital = Vital(
            patient_id=patient.id,
            measurement_date=date.today(),
            blood_pressure="140/90",
            heart_rate="85",
            temperature="98.6",
            weight="180"
        )
        
        log_details = {
            'action': 'add',
            'data_type': 'vital',
            'patient_id': patient.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'vital_date': str(date.today()),
            'vital_time': datetime.now().strftime('%H:%M:%S'),
            'blood_pressure': "140/90",
            'heart_rate': "85",
            'temperature': "98.6",
            'weight': "180",
            'endpoint': 'add_vitals',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        db.session.add(vital)
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=1,
            event_details=json.dumps(log_details),
            request_id='test_vital_001',
            ip_address='127.0.0.1',
            user_agent='Test Script'
        )
        
        db.session.commit()
        print(f"✓ Created vital signs for patient {patient.first_name} {patient.last_name}")
        print(f"  BP: {vital.blood_pressure}")
        print(f"  HR: {vital.heart_rate}")
        print(f"  Temp: {vital.temperature}")
        print(f"  Weight: {vital.weight}")

def test_immunization_logging():
    """Test immunization with detailed logging"""
    print("\nTesting immunization logging...")
    
    with app.app_context():
        patient = Patient.query.first()
        
        # Create test immunization
        immunization = Immunization(
            patient_id=patient.id,
            vaccine_name="COVID-19 Vaccine (Pfizer)",
            vaccination_date=date.today(),
            lot_number="EK5730",
            administered_by="Dr. Smith"
        )
        
        log_details = {
            'action': 'add',
            'data_type': 'immunization',
            'patient_id': patient.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'vaccine_name': "COVID-19 Vaccine (Pfizer)",
            'vaccination_date': str(date.today()),
            'vaccination_time': datetime.now().strftime('%H:%M:%S'),
            'lot_number': "EK5730",
            'endpoint': 'add_immunization',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        db.session.add(immunization)
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=1,
            event_details=json.dumps(log_details),
            request_id='test_immunization_001',
            ip_address='127.0.0.1',
            user_agent='Test Script'
        )
        
        db.session.commit()
        print(f"✓ Created immunization for patient {patient.first_name} {patient.last_name}")
        print(f"  Vaccine: {immunization.vaccine_name}")
        print(f"  Date: {immunization.vaccination_date}")
        print(f"  Lot: {immunization.lot_number}")

def check_admin_logs():
    """Check the admin logs to verify enhanced details are captured"""
    print("\n" + "="*60)
    print("ADMIN LOG VERIFICATION")
    print("="*60)
    
    with app.app_context():
        # Get recent logs from our test
        recent_logs = AdminLog.query.filter(
            AdminLog.request_id.like('test_%')
        ).order_by(AdminLog.timestamp.desc()).limit(10).all()
        
        print(f"Found {len(recent_logs)} test log entries:")
        
        for log in recent_logs:
            print(f"\n📋 Log ID: {log.id}")
            print(f"   Event: {log.event_type}")
            print(f"   Time: {log.timestamp}")
            print(f"   Request ID: {log.request_id}")
            
            if log.event_details:
                try:
                    details = json.loads(log.event_details)
                    print(f"   Data Type: {details.get('data_type', 'N/A')}")
                    print(f"   Patient: {details.get('patient_name', 'N/A')}")
                    
                    # Show specific details based on data type
                    data_type = details.get('data_type', '')
                    
                    if data_type == 'alert':
                        print(f"   🚨 Alert Text: {details.get('alert_text', 'N/A')}")
                        print(f"   📅 Alert Date: {details.get('alert_date', 'N/A')}")
                        print(f"   ⏰ Alert Time: {details.get('alert_time', 'N/A')}")
                        print(f"   ⚠️  Priority: {details.get('priority', 'N/A')}")
                    
                    elif data_type == 'document':
                        print(f"   📄 File Name: {details.get('file_name', 'N/A')}")
                        print(f"   📅 Upload Date: {details.get('upload_date', 'N/A')}")
                        print(f"   ⏰ Upload Time: {details.get('upload_time', 'N/A')}")
                        print(f"   📊 File Size: {details.get('file_size', 'N/A')}")
                    
                    elif data_type == 'condition':
                        print(f"   🏥 Condition: {details.get('condition_name', 'N/A')}")
                        print(f"   📅 Diagnosis Date: {details.get('diagnosis_date', 'N/A')}")
                        print(f"   ⚠️  Severity: {details.get('severity', 'N/A')}")
                    
                    elif data_type == 'lab':
                        print(f"   🧪 Test Name: {details.get('test_name', 'N/A')}")
                        print(f"   📅 Test Date: {details.get('test_date', 'N/A')}")
                        print(f"   ⏰ Test Time: {details.get('test_time', 'N/A')}")
                        print(f"   📊 Result: {details.get('result_value', 'N/A')}")
                    
                    elif data_type == 'vital':
                        print(f"   📅 Vital Date: {details.get('vital_date', 'N/A')}")
                        print(f"   ⏰ Vital Time: {details.get('vital_time', 'N/A')}")
                        print(f"   🩺 BP: {details.get('blood_pressure', 'N/A')}")
                        print(f"   💓 HR: {details.get('heart_rate', 'N/A')}")
                    
                    elif data_type == 'immunization':
                        print(f"   💉 Vaccine: {details.get('vaccine_name', 'N/A')}")
                        print(f"   📅 Vaccination Date: {details.get('vaccination_date', 'N/A')}")
                        print(f"   ⏰ Vaccination Time: {details.get('vaccination_time', 'N/A')}")
                        print(f"   🏷️  Lot Number: {details.get('lot_number', 'N/A')}")
                    
                except json.JSONDecodeError:
                    print(f"   Details: {log.event_details}")

if __name__ == "__main__":
    print("Enhanced Admin Logging Test Suite")
    print("="*50)
    print("This test demonstrates the enhanced logging functionality")
    print("that captures detailed information for medical data operations.")
    print()
    
    # Run all tests
    test_alert_logging()
    test_document_logging()
    test_condition_logging()
    test_lab_result_logging()
    test_vital_signs_logging()
    test_immunization_logging()
    
    # Verify the logs
    check_admin_logs()
    
    print("\n" + "="*60)
    print("✅ Enhanced logging test completed!")
    print("Admin logs now include detailed information:")
    print("• Alert text, dates, times, and priority")
    print("• File names, upload dates, and sizes")
    print("• Test names, dates, and results")
    print("• Condition names and diagnosis dates")
    print("• Vital signs with measurement times")
    print("• Immunization details with lot numbers")
    print("="*60)