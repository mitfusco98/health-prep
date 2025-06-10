import re
from datetime import datetime, date, timedelta

# Import validation functions from shared utilities
from shared_utilities import (
    validate_required_fields,
    validate_string_field,
    validate_email,
    validate_phone,
    validate_date_input as validate_date,
    sanitize_user_input as sanitize_html_input
)

def validate_integer(value, field_name, min_value=None, max_value=None, required=False):
    """Validate integer fields with range constraints"""
    errors = []

    if value is None and not required:
        return errors, None

    if value is None and required:
        errors.append(f'{field_name} is required')
        return errors, None

    try:
        int_value = int(value)

        if min_value is not None and int_value < min_value:
            errors.append(f'{field_name} must be at least {min_value}')

        if max_value is not None and int_value > max_value:
            errors.append(f'{field_name} must be at most {max_value}')

        return errors, int_value
    except (ValueError, TypeError):
        errors.append(f'{field_name} must be a valid integer')
        return errors, None

def validate_choice(value, field_name, choices, required=False):
    """Validate choice fields against allowed values"""
    errors = []

    if not value and not required:
        return errors

    if not value and required:
        errors.append(f'{field_name} is required')
        return errors

    if value not in choices:
        errors.append(f'{field_name} must be one of: {", ".join(choices)}')

    return errors


import pandas as pd
import csv
import io
import json
import re
import os
from datetime import datetime, timedelta, time
from app import db
from models import Patient, Condition, Vital, LabResult, Visit, ImagingStudy, ConsultReport, HospitalSummary, Screening, MedicalDocument, DocumentType, Appointment
from screening_rules import apply_screening_rules
import logging
import trafilatura
from sqlalchemy import func, or_
from sqlalchemy import text

def process_csv_upload(csv_file):
    """
    Process CSV upload and return processed data.
    This is a wrapper around process_csv_data for backward compatibility.
    """
    return process_csv_data(csv_file)

class CSVProcessor:
    """Handles different types of CSV imports with clear separation of concerns"""
    
    def __init__(self):
        self.processors = {
            'patients': self._process_patients_csv,
            'conditions': self._process_conditions_csv,
            'lab_results': self._process_lab_results_csv,
            'visits': self._process_visits_csv
        }
    
    def process(self, csv_file):
        """Main entry point for CSV processing"""
        try:
            csv_data = csv.DictReader(io.StringIO(csv_file.decode('utf-8')))
            headers = [header.lower() for header in csv_data.fieldnames]
            
            # Validate basic requirements
            if not self._validate_basic_headers(headers):
                return {'success': False, 'error': 'Invalid CSV format - missing required columns'}
            
            # Determine CSV type and process
            csv_type = self._determine_csv_type(headers)
            if csv_type not in self.processors:
                return {'success': False, 'error': f'Unsupported CSV format: {csv_type}'}
            
            # Re-read CSV data for processing
            csv_data = csv.DictReader(io.StringIO(csv_file.decode('utf-8')))
            return self.processors[csv_type](csv_data)
            
        except Exception as e:
            logging.error(f"Error processing CSV: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _validate_basic_headers(self, headers):
        """Validate that CSV has minimum required headers"""
        has_mrn = any(header in headers for header in ['mrn', 'patient_mrn'])
        has_data = any(header in headers for header in ['first_name', 'condition_name', 'test_name', 'visit_date'])
        return has_mrn and has_data
    
    def _determine_csv_type(self, headers):
        """Determine the type of CSV based on headers"""
        if 'mrn' in headers and 'first_name' in headers and 'last_name' in headers:
            return 'patients'
        elif 'patient_mrn' in headers and 'condition_name' in headers:
            return 'conditions'
        elif 'patient_mrn' in headers and 'test_name' in headers and 'test_date' in headers:
            return 'lab_results'
        elif 'patient_mrn' in headers and 'visit_date' in headers:
            return 'visits'
        return 'unknown'
    
    def _process_patients_csv(self, csv_data):
        """Process patient data CSV"""
        processed_count = 0
        
        for row in csv_data:
            try:
                patient = self._create_or_update_patient(row)
                if patient:
                    processed_count += 1
                    evaluate_screening_needs(patient)
            except Exception as e:
                logging.error(f"Error processing patient row: {str(e)}")
                continue
        
        return {'success': True, 'processed': processed_count}
    
    def _process_conditions_csv(self, csv_data):
        """Process conditions data CSV"""
        processed_count = 0
        
        for row in csv_data:
            try:
                if self._create_condition_for_patient(row):
                    processed_count += 1
            except Exception as e:
                logging.error(f"Error processing condition row: {str(e)}")
                continue
        
        return {'success': True, 'processed': processed_count}
    
    def _process_lab_results_csv(self, csv_data):
        """Process lab results data CSV"""
        processed_count = 0
        
        for row in csv_data:
            try:
                if self._create_lab_result_for_patient(row):
                    processed_count += 1
            except Exception as e:
                logging.error(f"Error processing lab result row: {str(e)}")
                continue
        
        return {'success': True, 'processed': processed_count}
    
    def _process_visits_csv(self, csv_data):
        """Process visits data CSV"""
        processed_count = 0
        
        for row in csv_data:
            try:
                if self._create_visit_for_patient(row):
                    processed_count += 1
            except Exception as e:
                logging.error(f"Error processing visit row: {str(e)}")
                continue
        
        return {'success': True, 'processed': processed_count}
    
    def _create_or_update_patient(self, row):
        """Create or update a patient from CSV row"""
        existing_patient = Patient.query.filter_by(mrn=row['mrn']).first()
        
        if existing_patient:
            return self._update_existing_patient(existing_patient, row)
        else:
            return self._create_new_patient(row)
    
    def _update_existing_patient(self, patient, row):
        """Update existing patient with new data"""
        patient.first_name = row.get('first_name', patient.first_name)
        patient.last_name = row.get('last_name', patient.last_name)
        
        if 'date_of_birth' in row and row['date_of_birth']:
            patient.date_of_birth = self._parse_date(row['date_of_birth'])
        
        patient.sex = row.get('sex', patient.sex)
        patient.phone = row.get('phone', patient.phone)
        patient.email = row.get('email', patient.email)
        patient.address = row.get('address', patient.address)
        patient.insurance = row.get('insurance', patient.insurance)
        
        db.session.commit()
        return patient
    
    def _create_new_patient(self, row):
        """Create new patient from CSV row"""
        dob = self._parse_date(row.get('date_of_birth'))
        
        new_patient = Patient(
            first_name=row.get('first_name', ''),
            last_name=row.get('last_name', ''),
            date_of_birth=dob,
            sex=row.get('sex', ''),
            mrn=row['mrn'],
            phone=row.get('phone', ''),
            email=row.get('email', ''),
            address=row.get('address', ''),
            insurance=row.get('insurance', '')
        )
        
        db.session.add(new_patient)
        db.session.commit()
        return new_patient
    
    def _create_condition_for_patient(self, row):
        """Create condition for patient from CSV row"""
        patient = Patient.query.filter_by(mrn=row['patient_mrn']).first()
        if not patient:
            return False
        
        # Check if condition already exists
        existing_condition = Condition.query.filter_by(
            patient_id=patient.id,
            name=row['condition_name']
        ).first()
        
        if existing_condition:
            return False
        
        diagnosed_date = self._parse_date(row.get('diagnosed_date'))
        
        condition = Condition(
            patient_id=patient.id,
            name=row['condition_name'],
            code=row.get('code', ''),
            diagnosed_date=diagnosed_date,
            is_active=row.get('is_active', 'true').lower() in ('true', 'yes', '1'),
            notes=row.get('notes', '')
        )
        
        db.session.add(condition)
        db.session.commit()
        evaluate_screening_needs(patient)
        return True
    
    def _create_lab_result_for_patient(self, row):
        """Create lab result for patient from CSV row"""
        patient = Patient.query.filter_by(mrn=row['patient_mrn']).first()
        if not patient:
            return False
        
        test_date = self._parse_date(row.get('test_date'))
        if not test_date:
            return False
        
        lab_result = LabResult(
            patient_id=patient.id,
            test_name=row['test_name'],
            test_date=test_date,
            result_value=row.get('result_value', ''),
            unit=row.get('unit', ''),
            reference_range=row.get('reference_range', ''),
            is_abnormal=row.get('is_abnormal', 'false').lower() in ('true', 'yes', '1'),
            notes=row.get('notes', '')
        )
        
        db.session.add(lab_result)
        db.session.commit()
        return True
    
    def _create_visit_for_patient(self, row):
        """Create visit for patient from CSV row"""
        patient = Patient.query.filter_by(mrn=row['patient_mrn']).first()
        if not patient:
            return False
        
        visit_date = self._parse_date(row.get('visit_date'))
        if not visit_date:
            return False
        
        visit = Visit(
            patient_id=patient.id,
            visit_date=visit_date,
            visit_type=row.get('visit_type', 'Office Visit'),
            provider=row.get('provider', ''),
            reason=row.get('reason', ''),
            notes=row.get('notes', '')
        )
        
        db.session.add(visit)
        db.session.commit()
        return True
    
    def _parse_date(self, date_str):
        """Parse date string with multiple format support"""
        if not date_str:
            return None
        
        formats = ['%Y-%m-%d', '%m/%d/%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

# Create global processor instance
_csv_processor = CSVProcessor()

def process_csv_data(csv_file):
    """
    Process CSV data using the new processor class.
    Maintains backward compatibility with existing interface.
    """
    return _csv_processor.process(csv_file)

def evaluate_screening_needs(patient):
    """Evaluate and update screening recommendations for a patient"""
    # Get patient's active conditions
    conditions = Condition.query.filter_by(patient_id=patient.id, is_active=True).all()
    condition_names = [c.name.lower() for c in conditions]

    # Apply screening rules based on demographics and conditions
    screening_recommendations = apply_screening_rules(patient, condition_names)

    # Update or create screenings in database
    for rec in screening_recommendations:
        # Check if this screening already exists
        existing = Screening.query.filter_by(
            patient_id=patient.id,
            screening_type=rec['type']
        ).first()

        if existing:
            # Update existing screening
            existing.due_date = rec['due_date']
            existing.frequency = rec['frequency']
            existing.priority = rec['priority']
            existing.notes = rec.get('notes', existing.notes)
        else:
            # Create new screening recommendation
            screening = Screening(
                patient_id=patient.id,
                screening_type=rec['type'],
                due_date=rec['due_date'],
                last_completed=rec.get('last_completed'),
                frequency=rec['frequency'],
                priority=rec['priority'],
                notes=rec.get('notes', '')
            )
            db.session.add(screening)

    db.session.commit()

class PatientPrepData:
    """Container for all patient data needed for prep sheet generation"""
    
    def __init__(self, patient):
        self.patient = patient
        self.recent_vitals = []
        self.recent_labs = []
        self.recent_imaging = []
        self.recent_consults = []
        self.recent_hospital = []
        self.active_conditions = []
        self.screenings = []
        self.last_visit_date = None
        self.past_appointments = []
    
    @classmethod
    def from_patient_id(cls, patient_id):
        """Factory method to create PrepData from patient ID"""
        from models import Patient, Vital, LabResult, ImagingStudy, ConsultReport, HospitalSummary, Condition, Screening, Appointment
        
        patient = Patient.query.get(patient_id)
        if not patient:
            return None
        
        prep_data = cls(patient)
        
        # Load recent data (last 6 months)
        six_months_ago = datetime.now() - timedelta(days=180)
        
        prep_data.recent_vitals = Vital.query.filter(
            Vital.patient_id == patient_id,
            Vital.date >= six_months_ago
        ).order_by(Vital.date.desc()).limit(5).all()
        
        prep_data.recent_labs = LabResult.query.filter(
            LabResult.patient_id == patient_id,
            LabResult.test_date >= six_months_ago
        ).order_by(LabResult.test_date.desc()).limit(10).all()
        
        prep_data.active_conditions = Condition.query.filter(
            Condition.patient_id == patient_id,
            Condition.is_active == True
        ).all()
        
        prep_data.screenings = Screening.query.filter(
            Screening.patient_id == patient_id
        ).all()
        
        return prep_data

class PrepSheetGenerator:
    """Generates preparation sheets with clear separation of concerns"""
    
    def __init__(self):
        self.alert_generators = [
            self._generate_lab_alerts,
            self._generate_hospital_alerts,
            self._generate_screening_alerts
        ]
        
        self.action_generators = [
            self._generate_screening_actions,
            self._generate_condition_monitoring_actions
        ]
    
    def generate(self, prep_data):
        """Generate preparation sheet from patient data"""
        prep_sheet = {
            'summary': self._generate_summary(prep_data),
            'alerts': self._generate_all_alerts(prep_data),
            'action_items': self._generate_all_actions(prep_data),
            'past_appointments': prep_data.past_appointments or []
        }
        return prep_sheet
    
    def _generate_summary(self, prep_data):
        """Generate patient summary text"""
        patient = prep_data.patient
        age_str = f"{patient.age} year old" if patient.age else ""
        
        # Build condition summary
        condition_names = [c.name for c in prep_data.active_conditions[:3]]
        condition_str = ", ".join(condition_names)
        if len(prep_data.active_conditions) > 3:
            condition_str += f", and {len(prep_data.active_conditions) - 3} other conditions"
        
        # Build base summary
        if condition_str:
            summary = f"{patient.full_name} is a {age_str} {patient.sex.lower()} with {condition_str}."
        else:
            summary = f"{patient.full_name} is a {age_str} {patient.sex.lower()} with no documented active conditions."
        
        # Add last visit information
        if prep_data.last_visit_date:
            days_since = (datetime.now().date() - prep_data.last_visit_date.date()).days
            summary += f" Last visit was {days_since} days ago on {prep_data.last_visit_date.strftime('%Y-%m-%d')}."
        
        return summary
    
    def _generate_all_alerts(self, prep_data):
        """Generate all alerts from different sources"""
        alerts = []
        for generator in self.alert_generators:
            alerts.extend(generator(prep_data))
        return alerts
    
    def _generate_all_actions(self, prep_data):
        """Generate all action items from different sources"""
        actions = []
        for generator in self.action_generators:
            actions.extend(generator(prep_data))
        return actions
    
    def _generate_lab_alerts(self, prep_data):
        """Generate alerts for abnormal lab results"""
        alerts = []
        for lab in prep_data.recent_labs:
            if lab.is_abnormal:
                alerts.append({
                    'description': f"Abnormal {lab.test_name}",
                    'date': lab.test_date,
                    'details': f"Result: {lab.result_value} {lab.unit} (Reference range: {lab.reference_range})"
                })
        return alerts
    
    def _generate_hospital_alerts(self, prep_data):
        """Generate alerts for recent hospitalizations"""
        alerts = []
        for stay in prep_data.recent_hospital:
            days_hospitalized = (stay.discharge_date - stay.admission_date).days if stay.discharge_date else 'ongoing'
            alerts.append({
                'description': f"Recent hospitalization",
                'date': stay.admission_date,
                'details': f"Admitted to {stay.hospital_name} for {days_hospitalized} days with {stay.admitting_diagnosis}"
            })
        return alerts
    
    def _generate_screening_alerts(self, prep_data):
        """Generate alerts for overdue screenings"""
        alerts = []
        today = datetime.now().date()
        
        for screening in prep_data.screenings:
            if screening.due_date and screening.due_date < today:
                days_overdue = (today - screening.due_date).days
                alerts.append({
                    'description': f"Overdue {screening.screening_type}",
                    'date': screening.due_date,
                    'details': f"Overdue by {days_overdue} days. Priority: {screening.priority}"
                })
        return alerts
    
    def _generate_screening_actions(self, prep_data):
        """Generate action items for due screenings"""
        actions = []
        today = datetime.now().date()
        
        for screening in prep_data.screenings:
            if screening.due_date and screening.due_date <= today + timedelta(days=90):
                actions.append({
                    'description': f"Schedule {screening.screening_type}",
                    'priority': screening.priority,
                    'details': f"Due by {screening.due_date.strftime('%Y-%m-%d')}. Frequency: {screening.frequency}"
                })
        return actions
    
    def _generate_condition_monitoring_actions(self, prep_data):
        """Generate monitoring actions based on active conditions"""
        actions = []
        condition_monitoring = {
            'diabetes': {'test': 'Check A1C', 'priority': 'High', 'details': 'Routine monitoring for diabetes management'},
            'pre-diabetes': {'test': 'Check A1C', 'priority': 'High', 'details': 'Routine monitoring for diabetes management'},
            'hypertension': {'test': 'Check blood pressure', 'priority': 'High', 'details': 'Routine monitoring for hypertension management'},
            'high blood pressure': {'test': 'Check blood pressure', 'priority': 'High', 'details': 'Routine monitoring for hypertension management'},
            'hyperlipidemia': {'test': 'Check lipid panel', 'priority': 'Medium', 'details': 'Routine monitoring for hyperlipidemia management'},
            'high cholesterol': {'test': 'Check lipid panel', 'priority': 'Medium', 'details': 'Routine monitoring for hyperlipidemia management'}
        }
        
        for condition in prep_data.active_conditions:
            condition_key = condition.name.lower()
            if condition_key in condition_monitoring:
                monitoring = condition_monitoring[condition_key]
                actions.append({
                    'description': monitoring['test'],
                    'priority': monitoring['priority'],
                    'details': monitoring['details']
                })
        
        return actions

# Global generator instance
_prep_sheet_generator = PrepSheetGenerator()

def generate_prep_sheet(patient, recent_vitals=None, recent_labs=None, recent_imaging=None, recent_consults=None, recent_hospital=None, active_conditions=None, screenings=None, last_visit_date=None, past_appointments=None, include_full_data=False):
    """
    Generate a preparation sheet summary for a patient
    Maintains backward compatibility with existing interface.
    """
    # Create prep data container from individual parameters
    prep_data = PatientPrepData(patient)
    # Use lightweight data by default, full data only when requested
    prep_data.recent_vitals = recent_vitals or []
    prep_data.recent_labs = (recent_labs or [])[:5] if not include_full_data else (recent_labs or [])
    prep_data.recent_imaging = (recent_imaging or [])[:3] if not include_full_data else (recent_imaging or [])
    prep_data.recent_consults = (recent_consults or [])[:3] if not include_full_data else (recent_consults or [])
    prep_data.recent_hospital = (recent_hospital or [])[:2] if not include_full_data else (recent_hospital or [])
    prep_data.active_conditions = (active_conditions or [])[:10] if not include_full_data else (active_conditions or [])
    prep_data.screenings = (screenings or [])[:10] if not include_full_data else (screenings or [])
    prep_data.last_visit_date = last_visit_date
    prep_data.past_appointments = (past_appointments or [])[:5] if not include_full_data else (past_appointments or [])
    
    return _prep_sheet_generator.generate(prep_data)
    # Initialize prep sheet data
    prep_sheet = {
        'summary': '',
        'alerts': [],
        'action_items': [],
        'past_appointments': past_appointments or []
    }

    # Create patient summary
    age_str = f"{patient.age} year old" if patient.age else ""
    condition_str = ", ".join([c.name for c in active_conditions[:3]])
    if len(active_conditions) > 3:
        condition_str += f", and {len(active_conditions) - 3} other conditions"

    if condition_str:
        prep_sheet['summary'] = f"{patient.full_name} is a {age_str} {patient.sex.lower()} with {condition_str}."
    else:
        prep_sheet['summary'] = f"{patient.full_name} is a {age_str} {patient.sex.lower()} with no documented active conditions."

    # Add information about last visit
    if last_visit_date:
        days_since = (datetime.now().date() - last_visit_date.date()).days
        prep_sheet['summary'] += f" Last visit was {days_since} days ago on {last_visit_date.strftime('%Y-%m-%d')}."

    # Add alerts based on recent data
    # Abnormal lab results
    for lab in recent_labs:
        if lab.is_abnormal:
            prep_sheet['alerts'].append({
                'description': f"Abnormal {lab.test_name}",
                'date': lab.test_date,
                'details': f"Result: {lab.result_value} {lab.unit} (Reference range: {lab.reference_range})"
            })

    # Recent hospital stays
    for stay in recent_hospital:
        days_hospitalized = (stay.discharge_date - stay.admission_date).days if stay.discharge_date else 'ongoing'
        prep_sheet['alerts'].append({
            'description': f"Recent hospitalization",
            'date': stay.admission_date,
            'details': f"Admitted to {stay.hospital_name} for {days_hospitalized} days with {stay.admitting_diagnosis}"
        })

    # Overdue screenings
    today = datetime.now().date()
    for screening in screenings:
        if screening.due_date and screening.due_date < today:
            days_overdue = (today - screening.due_date).days
            prep_sheet['alerts'].append({
                'description': f"Overdue {screening.screening_type}",
                'date': screening.due_date,
                'details': f"Overdue by {days_overdue} days. Priority: {screening.priority}"
            })

    # Add action items
    # Due screenings
    for screening in screenings:
        if screening.due_date and screening.due_date <= today + timedelta(days=90):
            prep_sheet['action_items'].append({
                'description': f"Schedule {screening.screening_type}",
                'priority': screening.priority,
                'details': f"Due by {screening.due_date.strftime('%Y-%m-%d')}. Frequency: {screening.frequency}"
            })

    # Laboratory monitoring for conditions
    for condition in active_conditions:
        if condition.name.lower() in ['diabetes', 'pre-diabetes']:
            prep_sheet['action_items'].append({
                'description': "Check A1C",
                'priority': "High",
                'details': "Routine monitoring for diabetes management"
            })
        elif condition.name.lower() in ['hypertension', 'high blood pressure']:
            prep_sheet['action_items'].append({
                'description': "Check blood pressure",
                'priority': "High",
                'details': "Routine monitoring for hypertension management"
            })
        elif condition.name.lower() in ['hyperlipidemia', 'high cholesterol']:
            prep_sheet['action_items'].append({
                'description': "Check lipid panel",
                'priority': "Medium",
                'details': "Routine monitoring for hyperlipidemia management"
            })

    return prep_sheet

def process_document_upload(content, filename, source_system="HealthPrep"):
    """Process a document content and classify it based on content and filename"""
    result = {
        'success': False,
        'document_type': None,
        'metadata': {},
        'error': None
    }

    try:
        # Classify document based on content and filename
        doc_type, metadata = classify_document(content, filename)

        # Return document type and metadata only
        result['success'] = True
        result['document_type'] = doc_type.value
        result['metadata'] = metadata

    except Exception as e:
        logging.error(f"Error processing document upload: {str(e)}")
        result['error'] = str(e)

    return result

class DocumentClassifier:
    """Strategy pattern for document classification"""
    
    def __init__(self):
        # Filename pattern lookup
        self.filename_patterns = {
            ('discharge', 'summary'): DocumentType.DISCHARGE_SUMMARY,
            ('radiology', 'xray', 'mri', 'ct'): DocumentType.RADIOLOGY_REPORT,
            ('lab', 'test', 'result'): DocumentType.LAB_REPORT,
            ('medication', 'med_list', 'prescription'): DocumentType.MEDICATION_LIST,
            ('referral',): DocumentType.REFERRAL,
            ('consult',): DocumentType.CONSULTATION,
            ('operation', 'surgical', 'procedure'): DocumentType.OPERATIVE_REPORT,
            ('pathology',): DocumentType.PATHOLOGY_REPORT,
        }
        
        # Content pattern strategies
        self.content_strategies = [
            self._classify_discharge_summary,
            self._classify_radiology_report,
            self._classify_lab_report,
            self._classify_medication_list,
            self._classify_referral,
            self._classify_consultation,
            self._classify_operative_report,
            self._classify_pathology_report,
        ]
    
    def classify(self, content, filename=None):
        """
        Classify a document based on its content and filename.
        Returns a tuple of (DocumentType, metadata_dict)
        """
        metadata = {}
        
        # Try filename classification first
        if filename:
            doc_type = self._classify_by_filename(filename)
            if doc_type:
                return doc_type, metadata
        
        # Try content classification strategies
        content_lower = content.lower()
        for strategy in self.content_strategies:
            result = strategy(content_lower, metadata)
            if result:
                return result
        
        # Default to unknown
        return DocumentType.UNKNOWN, metadata
    
    def _classify_by_filename(self, filename):
        """Classify document by filename patterns"""
        filename_lower = filename.lower()
        
        for keywords, doc_type in self.filename_patterns.items():
            if any(keyword in filename_lower for keyword in keywords):
                return doc_type
        
        return None
    
    def _classify_discharge_summary(self, content_lower, metadata):
        if re.search(r'discharge\s+summary', content_lower) or re.search(r'discharged\s+from', content_lower):
            return DocumentType.DISCHARGE_SUMMARY, metadata
        return None
    
    def _classify_radiology_report(self, content_lower, metadata):
        if re.search(r'radiolog(y|ical)|x-?ray|mri|ct scan|ultrasound', content_lower):
            if re.search(r'impression:', content_lower):
                metadata['has_impression'] = True
            return DocumentType.RADIOLOGY_REPORT, metadata
        return None
    
    def _classify_lab_report(self, content_lower, metadata):
        if re.search(r'laboratory|lab(\s+)results?|test(\s+)results?', content_lower):
            # Extract test names
            test_names = []
            test_pattern = r'(?:test|lab):\s*([A-Za-z0-9\s]+)'
            matches = re.finditer(test_pattern, content_lower)
            for match in matches:
                if match.group(1).strip():
                    test_names.append(match.group(1).strip())
            
            metadata['test_names'] = test_names
            return DocumentType.LAB_REPORT, metadata
        return None
    
    def _classify_medication_list(self, content_lower, metadata):
        if re.search(r'medications?|prescriptions?', content_lower):
            return DocumentType.MEDICATION_LIST, metadata
        return None
    
    def _classify_referral(self, content_lower, metadata):
        if re.search(r'referr(ed|al)', content_lower):
            return DocumentType.REFERRAL, metadata
        return None
    
    def _classify_consultation(self, content_lower, metadata):
        if re.search(r'consult(ation)?', content_lower):
            return DocumentType.CONSULTATION, metadata
        return None
    
    def _classify_operative_report(self, content_lower, metadata):
        if re.search(r'operat(ive|ion)|surgical|procedure', content_lower):
            return DocumentType.OPERATIVE_REPORT, metadata
        return None
    
    def _classify_pathology_report(self, content_lower, metadata):
        if re.search(r'pathology', content_lower):
            return DocumentType.PATHOLOGY_REPORT, metadata
        return None

# Global classifier instance
_document_classifier = DocumentClassifier()

def classify_document(content, filename=None):
    """
    Classify a document based on its content and filename.
    Returns a tuple of (DocumentType, metadata_dict)
    """
    return _document_classifier.classify(content, filename)

def process_document(document_id):
    """
    Process a document to extract key information based on its type.
    Updates the document with extracted provider information and sets is_processed flag.
    """
    document = MedicalDocument.query.get(document_id)
    if not document:
        logging.error(f"Document with ID {document_id} not found")
        return False

    content = document.content
    doc_type = document.document_type
    metadata = json.loads(document.doc_metadata) if document.doc_metadata else {}

    # Extract provider information - common in most medical documents
    provider_match = re.search(r'provider|physician|doctor|attending|surgeon:\s*([A-Za-z\s\.,]+)', content.lower())
    if provider_match:
        document.provider = provider_match.group(1).strip()

    # Process specific document types differently
    if doc_type == DocumentType.DISCHARGE_SUMMARY.value:
        # Extract discharge diagnoses
        diagnoses = []
        diag_pattern = r'diagnos(is|es):\s*([A-Za-z0-9\s\.,]+)'
        diag_match = re.search(diag_pattern, content.lower())
        if diag_match:
            diagnoses_text = diag_match.group(2).strip()
            diagnoses = [d.strip() for d in re.split(r'[,;]', diagnoses_text) if d.strip()]
            metadata['diagnoses'] = diagnoses

        # Look for hospital information
        hospital_match = re.search(r'hospital:\s*([A-Za-z0-9\s\.,]+)', content.lower())
        if hospital_match:
            metadata['hospital'] = hospital_match.group(1).strip()

    elif doc_type == DocumentType.LAB_REPORT.value:
        # Try to extract individual test results
        results = []
        result_pattern = r'([A-Za-z\s]+):\s*([\d\.]+)\s*([A-Za-z/%]+)?'
        for match in re.finditer(result_pattern, content):
            test_name = match.group(1).strip()
            value = match.group(2).strip()
            unit = match.group(3).strip() if match.group(3) else ""
            results.append({
                'test': test_name,
                'value': value,
                'unit': unit
            })

        if results:
            metadata['results'] = results

    # Update the document metadata and mark as processed
    document.doc_metadata = json.dumps(metadata)
    document.is_processed = True
    db.session.commit()

    return True

def extract_document_text_from_url(url):
    """
    Extract text content from a URL using trafilatura

    Args:
        url: URL to extract content from

    Returns:
        str: Extracted text content or empty string if extraction failed
    """
    try:
        # Download content
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""

        # Extract main text content from HTML
        text = trafilatura.extract(downloaded)
        return text or ""
    except Exception as e:
        logging.error(f"Error extracting text from URL {url}: {str(e)}")
        return ""

def get_patient_documents_summary(patient_id):
    """
    Get a summary of all documents for a patient, organized by type.
    Returns a dictionary with document types as keys and lists of documents as values.
    """
    documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()

    # Group documents by type
    grouped_docs = {}
    for doc in documents:
        if doc.document_type not in grouped_docs:
            grouped_docs[doc.document_type] = []

        # Add basic document info
        doc_info = {
            'id': doc.id,
            'filename': doc.filename,
            'document_name': doc.document_name if hasattr(doc, 'document_name') else doc.filename,
            'date': doc.document_date,
            'provider': doc.provider,
            'source': doc.source_system
        }

        # Add key info from metadata if available
        if doc.doc_metadata:
            try:
                metadata = json.loads(doc.doc_metadata)
                if 'diagnoses' in metadata:
                    doc_info['diagnoses'] = metadata['diagnoses']
                if 'results' in metadata:
                    doc_info['results'] = metadata['results']
                if 'has_impression' in metadata:
                    doc_info['has_impression'] = metadata['has_impression']
            except json.JSONDecodeError:
                pass

        grouped_docs[doc.document_type].append(doc_info)

    return grouped_docs

class DocumentTypeMapper:
    """Lookup object for document type display names and metadata"""
    
    TYPE_DISPLAY_NAMES = {
        DocumentType.DISCHARGE_SUMMARY.value: 'Hospital Discharge',
        DocumentType.OPERATIVE_REPORT.value: 'Operative Report',
        DocumentType.PATHOLOGY_REPORT.value: 'Pathology Report',
        DocumentType.RADIOLOGY_REPORT.value: 'Imaging Study',
        DocumentType.LAB_REPORT.value: 'Lab Report',
        DocumentType.CONSULTATION.value: 'Consult Report',
        DocumentType.MEDICATION_LIST.value: 'Medication List',
        DocumentType.REFERRAL.value: 'Referral',
        DocumentType.UNKNOWN.value: 'Other Documents'
    }
    
    @classmethod
    def get_display_name(cls, doc_type_value):
        """Get readable display name for document type"""
        return cls.TYPE_DISPLAY_NAMES.get(doc_type_value, 'Other Documents')
    
    @classmethod
    def get_all_display_names(cls):
        """Get all available display names"""
        return cls.TYPE_DISPLAY_NAMES

# Global mapper instance
_document_type_mapper = DocumentTypeMapper()

def group_documents_by_type(documents):
    """
    Group a list of document objects by their document type.
    Returns a dictionary with readable document type names as keys and lists of document objects as values.
    This is different from get_patient_documents_summary as it works with document objects directly.
    """
    type_names = _document_type_mapper.get_all_display_names()

    # Group documents by type
    grouped_docs = {}
    for doc in documents:
        # Get the readable name for this document type
        doc_type_name = type_names.get(doc.document_type, 'Other Documents')

        # Initialize the group if needed
        if doc_type_name not in grouped_docs:
            grouped_docs[doc_type_name] = []

        # Enhance the document object with metadata
        doc_info = {
            'id': doc.id,
            'filename': doc.filename,
            'document_name': doc.document_name if hasattr(doc, 'document_name') else doc.filename,
            'document_date': doc.document_date,
            'provider': doc.provider,
            'source': doc.source_system,
            'document_type': doc.document_type,
            'diagnoses': [],
            'results': []
        }

        # Extract metadata if available
        if doc.doc_metadata:
            try:
                metadata = json.loads(doc.doc_metadata)
                if 'diagnoses' in metadata:
                    doc_info['diagnoses'] = metadata['diagnoses']
                if 'results' in metadata:
                    doc_info['results'] = metadata['results']
                if 'hospital' in metadata:
                    doc_info['hospital'] = metadata['hospital']
            except Exception as e:
                logging.error(f"Error parsing document metadata: {e}")

        grouped_docs[doc_type_name].append(doc_info)

    # Sort documents within each group by date (newest first)
    for doc_type in grouped_docs:
        grouped_docs[doc_type] = sorted(
            grouped_docs[doc_type], 
            key=lambda x: x['document_date'] if x['document_date'] else datetime.min,
            reverse=True
        )

    return grouped_docs

def process_document_advanced(document_id):
    """
    More advanced document processing to extract metadata, key information, and update the document.
    This is called after a document has been successfully saved to the database.

    Args:
        document_id: The ID of the document to process

    Returns:
        bool: True if successful, False otherwise
    """
    from models import MedicalDocument, DocumentType
    import logging

    try:
        # Get the document from the database
        document = MedicalDocument.query.get(document_id)
        if not document:
            return False

        # Get existing metadata
        try:
            metadata = json.loads(document.doc_metadata) if document.doc_metadata else {}
        except json.JSONDecodeError:
            metadata = {}

        # Extract document text
        content = document.content

        # Extract key information based on document type
        extracted_data = {}

        if document.document_type == DocumentType.LAB_REPORT.value:
            # Extract lab test results, reference ranges, etc.
            extracted_data = extract_lab_data(content)
        elif document.document_type == DocumentType.RADIOLOGY_REPORT.value:
            # Extract imaging findings, impressions, etc.
            extracted_data = extract_imaging_data(content)
        elif document.document_type == DocumentType.CONSULTATION.value:
            # Extract consultation recommendations, specialist info, etc.
            extracted_data = extract_consult_data(content)
        elif document.document_type == DocumentType.DISCHARGE_SUMMARY.value:
            # Extract hospital info, diagnosis, discharge instructions, etc.
            extracted_data = extract_hospital_data(content)

        # Update metadata with extracted data
        metadata.update(extracted_data)

        # Save updated metadata
        document.doc_metadata = json.dumps(metadata)
        db.session.commit()

        return True
    except Exception as e:
        # Log the error but continue
        import logging
        logging.error(f"Error processing document {document_id}: {str(e)}")
        return False

def extract_lab_data(content):
    """Extract lab-specific data from document content"""
    # This is a simple version - in a real implementation, use NLP or regex
    # to identify test results, ranges, etc.
    data = {
        'results': []
    }

    # Look for common lab result patterns
    if "WBC" in content or "WHITE BLOOD CELL" in content.upper():
        data['results'].append({"test": "WBC", "found": True})
    if "HGB" in content or "HEMOGLOBIN" in content.upper():
        data['results'].append({"test": "Hemoglobin", "found": True})
    if "GLUCOSE" in content.upper():
        data['results'].append({"test": "Glucose", "found": True})

    return data

def extract_imaging_data(content):
    """Extract imaging-specific data from document content"""
    data = {
        'has_impression': False,
        'study_type': 'Unknown'
    }

    # Check if there's an impression section
    if "IMPRESSION:" in content.upper():
        data['has_impression'] = True

    # Determine study type
    if any(x in content.upper() for x in ["XRAY", "X-RAY", "RADIOGRAPH"]):
        data['study_type'] = "X-Ray"
    elif "MRI" in content.upper() or "MAGNETIC RESONANCE" in content.upper():
        data['study_type'] = "MRI"
    elif "CT" in content.upper() or "COMPUTED TOMOGRAPHY" in content.upper():
        data['study_type'] = "CT Scan"
    elif "ULTRASOUND" in content.upper() or "SONOGRAM" in content.upper():
        data['study_type'] = "Ultrasound"

    return data

def extract_consult_data(content):
    """Extract consultation-specific data from document content"""
    data = {
        'has_recommendations': False,
        'specialty': 'Unknown'
    }

    # Check for recommendations
    if any(x in content.upper() for x in ["RECOMMENDATION", "RECOMMEND", "ADVISED"]):
        data['has_recommendations'] = True

    # Try to determine specialty
    specialties = {
        "CARDIO": "Cardiology",
        "NEURO": "Neurology",
        "ORTHO": "Orthopedics",
        "GASTRO": "Gastroenterology",
        "DERMATOL": "Dermatology",
        "ONCOL": "Oncology",
        "ENDOCRIN": "Endocrinology"
    }

    for key, value in specialties.items():
        if key in content.upper():
            data['specialty'] = value
            break

    return data

def extract_hospital_data(content):
    """Extract hospital summary-specific data from document content"""
    data = {
        'hospital': 'Unknown',
        'has_discharge_instructions': False
    }

    # Check for discharge instructions
    if any(x in content.upper() for x in ["DISCHARGE INSTRUCTION", "FOLLOW-UP", "FOLLOW UP"]):
        data['has_discharge_instructions'] = True

    # Try to find hospital name - in real app would use more sophisticated methods
    content_upper = content.upper()
    if "HOSPITAL" in content_upper:
        # Simple approach - look for lines with 'hospital' and get the context
        lines = content.split('\n')
        for line in lines:
            if "HOSPITAL" in line.upper() and len(line) < 100:  # Avoid extremely long lines
                data['hospital'] = line.strip()
                break

    return data


def get_next_available_mrn():
    """Generate the next available MRN"""
    try:
        # Get the highest current MRN number using parameterized query
        result = db.session.execute(text("SELECT MAX(CAST(SUBSTRING(mrn FROM :pattern) AS INTEGER)) FROM patient WHERE mrn ~ :regex_pattern"), 
                                  {"pattern": '[0-9]+', "regex_pattern": '^[0-9]+$'})
        max_mrn = result.scalar()

        if max_mrn is None:
            # If no numeric MRNs exist, start from 1000
            return "1000"
        else:
            # Return the next number
            return str(max_mrn + 1)
    except Exception as e:
        # If there's any error, generate a random MRN
        import random
        return str(random.randint(10000, 99999))