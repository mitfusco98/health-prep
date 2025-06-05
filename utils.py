import re
from datetime import datetime, date, timedelta

# Required fields validation moved to shared_utilities.py for consistency
from shared_utilities import validate_required_fields

# String field validation moved to shared_utilities.py for consistency
from shared_utilities import validate_string_field

# Email validation moved to shared_utilities.py for consistency
from shared_utilities import validate_email

# Phone validation moved to shared_utilities.py for consistency
from shared_utilities import validate_phone

# Date validation moved to shared_utilities.py for consistency
from shared_utilities import validate_date_input as validate_date

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

def sanitize_html_input(text, max_length=None):
    """Remove potentially dangerous HTML/script content"""
    if not text:
        return text

    # Remove HTML tags and potential script content
    import html
    sanitized = html.escape(str(text).strip())

    # Remove potential XSS patterns
    dangerous_patterns = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe.*?>',
        r'<object.*?>',
        r'<embed.*?>'
    ]

    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

    if max_length:
        sanitized = sanitized[:max_length]

    return sanitized


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

def process_csv_upload(file):
    """Process a CSV file upload containing patient data"""
    result = {
        'success': False,
        'processed': 0,
        'error': None
    }

    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_data = csv.DictReader(stream)

        # Determine the type of data in the CSV
        processed_count = 0

        # Get the first row to check headers (without consuming the iterator)
        headers = csv_data.fieldnames

        if 'mrn' in headers and 'first_name' in headers and 'last_name' in headers:
            # Process as patients data
            for row in csv_data:
                # Check if patient already exists
                existing_patient = Patient.query.filter_by(mrn=row['mrn']).first()

                if existing_patient:
                    # Update existing patient
                    existing_patient.first_name = row.get('first_name', existing_patient.first_name)
                    existing_patient.last_name = row.get('last_name', existing_patient.last_name)

                    if 'date_of_birth' in row and row['date_of_birth']:
                        try:
                            existing_patient.date_of_birth = datetime.strptime(row['date_of_birth'], '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                existing_patient.date_of_birth = datetime.strptime(row['date_of_birth'], '%m/%d/%Y').date()
                            except ValueError:
                                pass  # Keep existing date if format is invalid

                    existing_patient.sex = row.get('sex', existing_patient.sex)
                    existing_patient.phone = row.get('phone', existing_patient.phone)
                    existing_patient.email = row.get('email', existing_patient.email)
                    existing_patient.address = row.get('address', existing_patient.address)
                    existing_patient.insurance = row.get('insurance', existing_patient.insurance)

                    db.session.commit()
                    processed_count += 1

                    # Re-evaluate screening needs
                    evaluate_screening_needs(existing_patient)
                else:
                    # Create new patient
                    try:
                        dob = None
                        if 'date_of_birth' in row and row['date_of_birth']:
                            try:
                                dob = datetime.strptime(row['date_of_birth'], '%Y-%m-%d').date()
                            except ValueError:
                                dob = datetime.strptime(row['date_of_birth'], '%m/%d/%Y').date()

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
                        processed_count += 1

                        # Evaluate screening needs for new patient
                        evaluate_screening_needs(new_patient)
                    except Exception as e:
                        logging.error(f"Error creating patient from CSV: {str(e)}")
                        continue

        elif 'patient_mrn' in headers and 'condition_name' in headers:
            # Process as conditions data
            for row in csv_data:
                patient = Patient.query.filter_by(mrn=row['patient_mrn']).first()
                if patient:
                    # Check if condition already exists for this patient
                    existing_condition = Condition.query.filter_by(
                        patient_id=patient.id,
                        name=row['condition_name']
                    ).first()

                    if not existing_condition:
                        # Parse diagnosed date if available
                        diagnosed_date = None
                        if 'diagnosed_date' in row and row['diagnosed_date']:
                            try:
                                diagnosed_date = datetime.strptime(row['diagnosed_date'], '%Y-%m-%d').date()
                            except ValueError:
                                try:
                                    diagnosed_date = datetime.strptime(row['diagnosed_date'], '%m/%d/%Y').date()
                                except ValueError:
                                    pass

                        # Create new condition
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
                        processed_count += 1

                        # Re-evaluate screening needs
                        evaluate_screening_needs(patient)

        elif 'patient_mrn' in headers and 'test_name' in headers and 'test_date' in headers:
            # Process as lab results data
            for row in csv_data:
                patient = Patient.query.filter_by(mrn=row['patient_mrn']).first()
                if patient:
                    # Parse test date
                    test_date = None
                    if row['test_date']:
                        try:
                            test_date = datetime.strptime(row['test_date'], '%Y-%m-%d')
                        except ValueError:
                            try:
                                test_date = datetime.strptime(row['test_date'], '%m/%d/%Y')
                            except ValueError:
                                continue

                    if test_date:
                        # Create new lab result
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
                        processed_count += 1

        elif 'patient_mrn' in headers and 'visit_date' in headers:
            # Process as visits data
            for row in csv_data:
                patient = Patient.query.filter_by(mrn=row['patient_mrn']).first()
                if patient:
                    # Parse visit date
                    visit_date = None
                    if row['visit_date']:
                        try:
                            visit_date = datetime.strptime(row['visit_date'], '%Y-%m-%d')
                        except ValueError:
                            try:
                                visit_date = datetime.strptime(row['visit_date'], '%m/%d/%Y')
                            except ValueError:
                                continue

                    if visit_date:
                        # Create new visit
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
                        processed_count += 1

        result['success'] = True
        result['processed'] = processed_count

    except Exception as e:
        logging.error(f"Error processing CSV: {str(e)}")
        result['error'] = str(e)

    return result

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

def generate_prep_sheet(patient, recent_vitals, recent_labs, recent_imaging, recent_consults, recent_hospital, active_conditions, screenings, last_visit_date=None, past_appointments=None):
    """
    Generate a preparation sheet summary for a patient

    Args:
        patient: Patient object
        recent_vitals: List of recent Vital objects
        recent_labs: List of recent LabResult objects
        recent_imaging: List of recent ImagingStudy objects
        recent_consults: List of recent ConsultReport objects
        recent_hospital: List of recent HospitalSummary objects
        active_conditions: List of active Condition objects
        screenings: List of Screening objects
        last_visit_date: Date of last visit if available
        past_appointments: List of past appointments (max 3)

    Returns:
        dict: Preparation sheet data
    """
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

def classify_document(content, filename=None):
    """
    Classify a document based on its content and filename.
    Returns a tuple of (DocumentType, metadata_dict)
    """
    # Initialize metadata
    metadata = {}

    # First check if we can determine type from filename
    if filename:
        filename_lower = filename.lower()
        if 'discharge' in filename_lower and 'summary' in filename_lower:
            return DocumentType.DISCHARGE_SUMMARY, metadata
        elif 'radiology' in filename_lower or 'xray' in filename_lower or 'mri' in filename_lower or 'ct' in filename_lower:
            return DocumentType.RADIOLOGY_REPORT, metadata
        elif 'lab' in filename_lower or 'test' in filename_lower or 'result' in filename_lower:
            return DocumentType.LAB_REPORT, metadata
        elif 'medication' in filename_lower or 'med_list' in filename_lower or 'prescription' in filename_lower:
            return DocumentType.MEDICATION_LIST, metadata
        elif 'referral' in filename_lower:
            return DocumentType.REFERRAL, metadata
        elif 'consult' in filename_lower:
            return DocumentType.CONSULTATION, metadata
        elif 'operation' in filename_lower or 'surgical' in filename_lower or 'procedure' in filename_lower:
            return DocumentType.OPERATIVE_REPORT, metadata
        elif 'pathology' in filename_lower:
            return DocumentType.PATHOLOGY_REPORT, metadata

    # If we couldn't determine from filename, check content
    content_lower = content.lower()

    # Look for document headers/sections that might indicate document type
    if re.search(r'discharge\s+summary', content_lower) or re.search(r'discharged\s+from', content_lower):
        return DocumentType.DISCHARGE_SUMMARY, metadata

    elif re.search(r'radiolog(y|ical)|x-?ray|mri|ct scan|ultrasound', content_lower):
        if re.search(r'impression:', content_lower):
            metadata['has_impression'] = True
        return DocumentType.RADIOLOGY_REPORT, metadata

    elif re.search(r'laboratory|lab(\s+)results?|test(\s+)results?', content_lower):
        # Extract test names
        test_names = []
        test_pattern = r'(?:test|lab):\s*([A-Za-z0-9\s]+)'
        matches = re.finditer(test_pattern, content_lower)
        for match in matches:
            if match.group(1).strip():
                test_names.append(match.group(1).strip())

        metadata['test_names'] = test_names
        return DocumentType.LAB_REPORT, metadata

    elif re.search(r'medications?|prescriptions?', content_lower):
        return DocumentType.MEDICATION_LIST, metadata

    elif re.search(r'referr(ed|al)', content_lower):
        return DocumentType.REFERRAL, metadata

    elif re.search(r'consult(ation)?', content_lower):
        return DocumentType.CONSULTATION, metadata

    elif re.search(r'operat(ive|ion)|surgical|procedure', content_lower):
        return DocumentType.OPERATIVE_REPORT, metadata

    elif re.search(r'pathology', content_lower):
        return DocumentType.PATHOLOGY_REPORT, metadata

    # If we can't determine the type, classify as unknown
    return DocumentType.UNKNOWN, metadata

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

def group_documents_by_type(documents):
    """
    Group a list of document objects by their document type.
    Returns a dictionary with readable document type names as keys and lists of document objects as values.
    This is different from get_patient_documents_summary as it works with document objects directly.
    """
    # Define a mapping from enum values to readable names
    type_names = {
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