#!/usr/bin/env python3
"""
Comprehensive Medical Data Logging Demonstration
Shows enhanced admin logging for all medical data subsections with their specific required fields
"""

import json
from datetime import datetime, date
from app import app, db
from models import AdminLog

def create_comprehensive_medical_logs():
    """Create sample logs for all medical data types with their specific submission requirements"""
    
    with app.app_context():
        print("Creating comprehensive medical data logging examples...")
        
        # 1. Document Upload (file-based submission)
        document_log = {
            'action': 'add',
            'data_type': 'document',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'file_name': 'chest_xray_lateral_view_2024.jpg',
            'file_type': 'image/jpeg',
            'document_type': 'Imaging Report',
            'upload_date': str(date.today()),
            'upload_time': datetime.now().strftime('%H:%M:%S'),
            'file_size': '2485760 bytes',
            'provider': 'Dr. Mitchell Radiology',
            'document_date': '2024-06-08',
            'endpoint': 'add_document',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(document_log),
            request_id='demo_doc_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        # 2. Medical Condition (subject name + diagnosis info)
        condition_log = {
            'action': 'add',
            'data_type': 'condition',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'condition_name': 'Hypertension, Essential',
            'name': 'Hypertension, Essential',
            'diagnosis_date': '2024-03-15',
            'diagnosis_time': '14:30:00',
            'code': 'I10',
            'icd_code': 'I10',
            'is_active': True,
            'status': 'Active',
            'severity': 'Moderate',
            'notes': 'Well-controlled with ACE inhibitor therapy. Patient reports good compliance with medication regimen.',
            'endpoint': 'add_condition',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(condition_log),
            request_id='demo_condition_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        # 3. Immunization (vaccine name + administration details)
        immunization_log = {
            'action': 'add',
            'data_type': 'immunization',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'vaccine_name': 'COVID-19 mRNA Vaccine (Pfizer-BioNTech)',
            'immunization_name': 'COVID-19 mRNA Vaccine (Pfizer-BioNTech)',
            'vaccination_date': str(date.today()),
            'administration_date': str(date.today()),
            'vaccination_time': '10:15:00',
            'administration_time': '10:15:00',
            'dose_number': 3,
            'dose': 3,
            'manufacturer': 'Pfizer-BioNTech',
            'lot_number': 'FN4587',
            'notes': 'Third dose administered as booster. Patient tolerated well, no immediate adverse reactions observed.',
            'endpoint': 'add_immunization',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(immunization_log),
            request_id='demo_immunization_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        # 4. Lab Results (test name + detailed results)
        lab_log = {
            'action': 'add',
            'data_type': 'lab',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'test_name': 'Lipid Panel (Comprehensive)',
            'lab_name': 'Lipid Panel (Comprehensive)',
            'test_date': str(date.today()),
            'lab_date': str(date.today()),
            'test_time': '08:30:00',
            'lab_time': '08:30:00',
            'result_value': 'Total Cholesterol: 195 mg/dL, LDL: 115 mg/dL, HDL: 58 mg/dL, Triglycerides: 110 mg/dL',
            'result': 'Total Cholesterol: 195 mg/dL, LDL: 115 mg/dL, HDL: 58 mg/dL, Triglycerides: 110 mg/dL',
            'unit': 'mg/dL',
            'reference_range': 'Total <200, LDL <100, HDL >40 (M) >50 (F), TG <150',
            'is_abnormal': True,
            'notes': 'LDL slightly elevated. Recommend dietary modification and recheck in 3 months.',
            'endpoint': 'add_lab',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(lab_log),
            request_id='demo_lab_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        # 5. Vital Signs (comprehensive measurements)
        vital_log = {
            'action': 'add',
            'data_type': 'vital',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'vital_date': str(date.today()),
            'date': str(date.today()),
            'vital_time': '09:45:00',
            'time': '09:45:00',
            'blood_pressure': '138/82',
            'blood_pressure_systolic': 138,
            'blood_pressure_diastolic': 82,
            'heart_rate': '72',
            'pulse': 72,
            'temperature': '98.6',
            'weight': '165',
            'height': '165',
            'bmi': '24.2',
            'oxygen_saturation': '98',
            'respiratory_rate': '16',
            'endpoint': 'add_vitals',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(vital_log),
            request_id='demo_vital_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        # 6. Imaging Study (study type + findings)
        imaging_log = {
            'action': 'add',
            'data_type': 'imaging',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'study_type': 'Chest X-Ray (PA and Lateral)',
            'imaging_type': 'Chest X-Ray (PA and Lateral)',
            'study_date': str(date.today()),
            'imaging_date': str(date.today()),
            'study_time': '11:20:00',
            'imaging_time': '11:20:00',
            'body_site': 'Chest',
            'location': 'Chest',
            'findings': 'Clear lung fields bilaterally. No acute cardiopulmonary abnormalities identified. Heart size within normal limits.',
            'impression': 'Normal chest radiograph. No acute findings.',
            'endpoint': 'add_imaging',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(imaging_log),
            request_id='demo_imaging_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        # 7. Consultation Report (specialist + detailed report)
        consult_log = {
            'action': 'add',
            'data_type': 'consult',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'specialist': 'Dr. Amanda Rodriguez',
            'consultant': 'Dr. Amanda Rodriguez',
            'specialty': 'Cardiology',
            'speciality': 'Cardiology',
            'report_date': str(date.today()),
            'consult_date': str(date.today()),
            'report_time': '15:30:00',
            'consult_time': '15:30:00',
            'reason': 'Evaluation of hypertension and cardiovascular risk assessment',
            'referral_reason': 'Evaluation of hypertension and cardiovascular risk assessment',
            'findings': 'Blood pressure well-controlled on current regimen. Echocardiogram shows normal LV function. No signs of target organ damage.',
            'recommendations': 'Continue current antihypertensive therapy. Annual cardiology follow-up. Lifestyle modifications emphasized.',
            'endpoint': 'add_consult',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(consult_log),
            request_id='demo_consult_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        # 8. Hospital Summary (admission + discharge details)
        hospital_log = {
            'action': 'add',
            'data_type': 'hospital',
            'patient_id': 7,
            'patient_name': 'Sarah Johnson',
            'hospital_name': 'Metropolitan General Hospital',
            'facility': 'Metropolitan General Hospital',
            'admission_date': '2024-05-20',
            'admission_time': '14:45:00',
            'discharge_date': '2024-05-22',
            'discharge_time': '10:30:00',
            'admitting_diagnosis': 'Acute exacerbation of chronic obstructive pulmonary disease',
            'discharge_diagnosis': 'COPD exacerbation, resolved',
            'procedures': 'Chest X-ray, arterial blood gas analysis, bronchodilator therapy, corticosteroid administration',
            'discharge_medications': 'Albuterol inhaler, prednisone taper, increased home oxygen',
            'followup_instructions': 'Follow up with pulmonologist in 1 week, primary care in 2 weeks',
            'endpoint': 'add_hospital',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        }
        
        AdminLog.log_event(
            event_type='data_modification',
            user_id=2,
            event_details=json.dumps(hospital_log),
            request_id='demo_hospital_comprehensive_001',
            ip_address='127.0.0.1',
            user_agent='Comprehensive Medical Logging Demo'
        )
        
        db.session.commit()
        print("✓ Comprehensive medical data logging demonstration completed!")
        print("\nCreated detailed log entries for all medical subsections:")
        print("  ✓ Documents (file-based): File names, upload dates/times, provider info")
        print("  ✓ Conditions (subject-based): Condition names, diagnosis dates/times, ICD codes")
        print("  ✓ Immunizations (subject-based): Vaccine names, administration dates/times, lot numbers")
        print("  ✓ Lab Results (test-based): Test names, result values, reference ranges")
        print("  ✓ Vital Signs (measurement-based): All vital parameters with dates/times")
        print("  ✓ Imaging Studies (study-based): Study types, findings, impressions")
        print("  ✓ Consultations (specialist-based): Specialist info, findings, recommendations")
        print("  ✓ Hospital Summaries (admission-based): Admission/discharge details, diagnoses")

if __name__ == '__main__':
    create_comprehensive_medical_logs()