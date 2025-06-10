#!/usr/bin/env python3
"""
Demonstrate enhanced admin logging functionality
Shows how detailed information is captured for alerts and medical data
"""

import sys
import os

sys.path.append(".")

from app import app, db
from models import PatientAlert, AdminLog
from datetime import datetime, date
import json


def create_sample_alert_log():
    """Create a sample alert log entry with enhanced details"""
    with app.app_context():
        # Create a comprehensive log entry showing enhanced alert logging
        log_details = {
            "action": "add",
            "data_type": "alert",
            "patient_id": 5,
            "patient_name": "John Doe",
            "alert_text": "Patient allergic to penicillin - severe anaphylactic reaction documented in 2023",
            "alert_date": str(date.today()),
            "alert_time": datetime.now().strftime("%H:%M:%S"),
            "priority": "High",
            "alert_type": "Allergy",
            "endpoint": "add_alert",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
            "form_changes": {
                "alert_description": "Patient allergic to penicillin",
                "alert_severity": "High",
                "alert_type": "Allergy",
            },
        }

        AdminLog.log_event(
            event_type="data_modification",
            user_id=2,
            event_details=json.dumps(log_details),
            request_id="demo_alert_001",
            ip_address="127.0.0.1",
            user_agent="Enhanced Logging Demo",
        )

        # Document upload example
        doc_log_details = {
            "action": "add",
            "data_type": "document",
            "patient_id": 5,
            "patient_name": "John Doe",
            "file_name": "lab_results_hemoglobin_a1c_2024.pdf",
            "file_type": "application/pdf",
            "upload_date": datetime.now().strftime("%Y-%m-%d"),
            "upload_time": datetime.now().strftime("%H:%M:%S"),
            "file_size": "156720 bytes",
            "endpoint": "add_document",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
        }

        AdminLog.log_event(
            event_type="data_modification",
            user_id=2,
            event_details=json.dumps(doc_log_details),
            request_id="demo_doc_001",
            ip_address="127.0.0.1",
            user_agent="Enhanced Logging Demo",
        )

        # Lab result example
        lab_log_details = {
            "action": "add",
            "data_type": "lab",
            "patient_id": 5,
            "patient_name": "John Doe",
            "test_name": "Comprehensive Metabolic Panel",
            "test_date": str(date.today()),
            "test_time": datetime.now().strftime("%H:%M:%S"),
            "result_value": "Glucose: 145 mg/dL (High)",
            "endpoint": "add_lab",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
        }

        AdminLog.log_event(
            event_type="data_modification",
            user_id=2,
            event_details=json.dumps(lab_log_details),
            request_id="demo_lab_001",
            ip_address="127.0.0.1",
            user_agent="Enhanced Logging Demo",
        )

        # Condition example
        condition_log_details = {
            "action": "add",
            "data_type": "condition",
            "patient_id": 5,
            "patient_name": "John Doe",
            "condition_name": "Type 2 Diabetes Mellitus",
            "diagnosis_date": "2023-08-15",
            "severity": "Moderate",
            "status": "Active",
            "endpoint": "add_condition",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
        }

        AdminLog.log_event(
            event_type="data_modification",
            user_id=2,
            event_details=json.dumps(condition_log_details),
            request_id="demo_condition_001",
            ip_address="127.0.0.1",
            user_agent="Enhanced Logging Demo",
        )

        # Vital signs example
        vital_log_details = {
            "action": "add",
            "data_type": "vital",
            "patient_id": 5,
            "patient_name": "John Doe",
            "vital_date": str(date.today()),
            "vital_time": datetime.now().strftime("%H:%M:%S"),
            "blood_pressure": "142/88",
            "heart_rate": "78",
            "temperature": "98.4",
            "weight": "185",
            "endpoint": "add_vitals",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
        }

        AdminLog.log_event(
            event_type="data_modification",
            user_id=2,
            event_details=json.dumps(vital_log_details),
            request_id="demo_vital_001",
            ip_address="127.0.0.1",
            user_agent="Enhanced Logging Demo",
        )

        # Immunization example
        immunization_log_details = {
            "action": "add",
            "data_type": "immunization",
            "patient_id": 5,
            "patient_name": "John Doe",
            "vaccine_name": "Influenza Vaccine (Quadrivalent)",
            "vaccination_date": str(date.today()),
            "vaccination_time": datetime.now().strftime("%H:%M:%S"),
            "lot_number": "FL2024A",
            "endpoint": "add_immunization",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
        }

        AdminLog.log_event(
            event_type="data_modification",
            user_id=2,
            event_details=json.dumps(immunization_log_details),
            request_id="demo_immunization_001",
            ip_address="127.0.0.1",
            user_agent="Enhanced Logging Demo",
        )

        db.session.commit()
        print("Enhanced logging demonstration completed!")
        print("Created sample log entries showing detailed information capture:")
        print("✓ Alert with text, date, time, and priority")
        print("✓ Document with file name, upload date/time, and size")
        print("✓ Lab result with test name, date, time, and results")
        print("✓ Medical condition with diagnosis date and severity")
        print("✓ Vital signs with measurement date and time")
        print("✓ Immunization with vaccine name, date, and lot number")


if __name__ == "__main__":
    create_sample_alert_log()
