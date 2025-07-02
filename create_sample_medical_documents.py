#!/usr/bin/env python3
"""
Create Sample Medical Documents for Testing Screening Logic
Adds realistic medical documents for existing patients to test document-to-screening matching
"""

import sys
import os
from datetime import datetime, timedelta
import random
import json

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Patient, MedicalDocument, ScreeningType

def create_sample_documents():
    """Create sample medical documents for testing screening logic"""

    with app.app_context():
        # Get existing patients
        patients = Patient.query.limit(5).all()
        if not patients:
            print("No patients found. Please add patients first.")
            return

        # Sample documents that SHOULD match screening types
        matching_documents = [
            {
                'filename': 'colonoscopy_report_2024.pdf',
                'content': 'COLONOSCOPY REPORT\n\nPatient underwent colonoscopy examination. No polyps found. Recommended follow-up in 10 years. Procedure completed successfully with gastroenterology team.',
                'document_type': 'Report',
                'section': 'Gastroenterology',
                'category': 'Procedure Report'
            },
            {
                'filename': 'mammogram_screening_results.pdf', 
                'content': 'MAMMOGRAM SCREENING RESULTS\n\nBilateral mammogram performed. No suspicious lesions identified. BI-RADS category 1. Recommend routine annual mammogram screening.',
                'document_type': 'Imaging',
                'section': 'Radiology',
                'category': 'Screening'
            },
            {
                'filename': 'pap_smear_cytology.pdf',
                'content': 'PAP SMEAR CYTOLOGY REPORT\n\nCervical cytology specimen examined. Results: Normal cervical cells. No malignant cells identified. Recommend routine screening in 3 years.',
                'document_type': 'Lab Result',
                'section': 'Pathology',
                'category': 'Screening'
            },
            {
                'filename': 'lipid_panel_lab_results.pdf',
                'content': 'LIPID PANEL RESULTS\n\nTotal cholesterol: 185 mg/dL\nLDL: 110 mg/dL\nHDL: 55 mg/dL\nTriglycerides: 120 mg/dL\n\nResults within normal limits.',
                'document_type': 'Lab Result',
                'section': 'Laboratory',
                'category': 'Blood Work'
            },
            {
                'filename': 'eye_exam_optometry.pdf',
                'content': 'COMPREHENSIVE EYE EXAMINATION\n\nOptometry evaluation completed. Visual acuity 20/20 both eyes. No retinopathy observed. Recommend annual eye exam.',
                'document_type': 'Report',
                'section': 'Optometry',
                'category': 'Examination'
            },
            {
                'filename': 'a1c_glucose_test.pdf',
                'content': 'HEMOGLOBIN A1C TEST RESULTS\n\nHbA1c: 5.8%\nFasting glucose: 95 mg/dL\n\nResults indicate good glucose control. Continue current management.',
                'document_type': 'Lab Result',
                'section': 'Laboratory',
                'category': 'Blood Work'
            },
            {
                'filename': 'dexa_scan_bone_density.pdf',
                'content': 'BONE DENSITY SCAN (DEXA)\n\nLumbar spine T-score: -1.2\nFemoral neck T-score: -0.8\n\nBone density within normal range for age. Recommend repeat in 2 years.',
                'document_type': 'Imaging',
                'section': 'Radiology',
                'category': 'Diagnostic'
            },
            {
                'filename': 'vaccination_record_2024.pdf',
                'content': 'VACCINATION RECORD\n\nInfluenza vaccine administered 10/15/2024\nCOVID-19 booster given 09/20/2024\nTdap up to date (last: 2019)\n\nAll routine vaccinations current.',
                'document_type': 'Record',
                'section': 'Immunizations',
                'category': 'Preventive Care'
            }
        ]

        # Sample documents that should NOT match screening types
        non_matching_documents = [
            {
                'filename': 'emergency_room_visit.pdf',
                'content': 'EMERGENCY DEPARTMENT VISIT\n\nChief complaint: Acute abdominal pain. Diagnosis: Appendicitis. Patient admitted for emergency appendectomy.',
                'document_type': 'Report',
                'section': 'Emergency Medicine',
                'category': 'Emergency Care'
            },
            {
                'filename': 'physical_therapy_notes.pdf',
                'content': 'PHYSICAL THERAPY EVALUATION\n\nPatient presents with lower back pain. Range of motion limited. Recommended therapy protocol for 6 weeks.',
                'document_type': 'Note',
                'section': 'Rehabilitation',
                'category': 'Therapy'
            },
            {
                'filename': 'dermatology_consultation.pdf',
                'content': 'DERMATOLOGY CONSULTATION\n\nSkin lesion examination. Benign seborrheic keratosis identified. No treatment required. Follow-up as needed.',
                'document_type': 'Consultation',
                'section': 'Dermatology',
                'category': 'Specialty Care'
            },
            {
                'filename': 'medication_list_current.pdf',
                'content': 'CURRENT MEDICATION LIST\n\n1. Lisinopril 10mg daily\n2. Metformin 500mg twice daily\n3. Atorvastatin 20mg nightly\n\nNo drug interactions noted.',
                'document_type': 'List',
                'section': 'Pharmacy',
                'category': 'Medications'
            },
            {
                'filename': 'orthopedic_xray_knee.pdf',
                'content': 'KNEE X-RAY REPORT\n\nAP and lateral views of the right knee. Mild degenerative changes consistent with osteoarthritis. No fracture identified.',
                'document_type': 'Imaging',
                'section': 'Radiology',
                'category': 'Diagnostic'
            }
        ]

        # Combine all documents
        all_documents = matching_documents + non_matching_documents

        print(f"Creating {len(all_documents)} sample documents for {len(patients)} patients...")

        documents_created = 0

        for i, patient in enumerate(patients):
            # Assign 3-4 documents per patient, mixing matching and non-matching
            num_docs = random.randint(3, 4)
            selected_docs = random.sample(all_documents, num_docs)

            for doc_data in selected_docs:
                # Create document with realistic dates (last 2 years)
                days_ago = random.randint(30, 730)
                upload_date = datetime.now() - timedelta(days=days_ago)

                # Create metadata dictionary
                metadata = {
                    'section': doc_data['section'],
                    'category': doc_data['category'],
                    'file_size': random.randint(50000, 500000),
                    'content_type': 'application/pdf',
                    'fhir_document_reference_id': f"doc-{patient.id}-{documents_created + 1}",
                    'status': 'completed'
                }

                new_document = MedicalDocument(
                    patient_id=patient.id,
                    filename=f"{patient.last_name}_{doc_data['filename']}",
                    document_name=doc_data['filename'].replace('.pdf', '').replace('_', ' ').title(),
                    document_type=doc_data['document_type'],
                    content=doc_data['content'],
                    document_date=upload_date,
                    provider="Sample Provider",
                    doc_metadata=json.dumps(metadata),
                    is_processed=True,
                    mime_type='application/pdf'
                )

                try:
                    db.session.add(new_document)
                    documents_created += 1
                    print(f"  Created: {new_document.filename} for {patient.full_name}")
                except Exception as e:
                    print(f"  Error creating document {doc_data['filename']}: {e}")

        # Commit all documents
        try:
            db.session.commit()
            print(f"\n✓ Successfully created {documents_created} medical documents")

            # Show summary of what was created
            print("\nDocument Summary:")
            print("MATCHING documents (should trigger screenings):")
            for doc in matching_documents:
                print(f"  - {doc['filename']}: Tests {doc['section']} screening")

            print("\nNON-MATCHING documents (should not trigger screenings):")
            for doc in non_matching_documents:
                print(f"  - {doc['filename']}: {doc['section']} - not screening related")

            print(f"\nTotal patients with documents: {len(patients)}")
            print("You can now test the prep sheet screening logic!")

        except Exception as e:
            db.session.rollback()
            print(f"Error committing documents: {e}")

def show_document_summary():
    """Show summary of existing documents for testing"""
    with app.app_context():
        documents = MedicalDocument.query.join(Patient).all()

        if not documents:
            print("No documents found in the database.")
            return

        print(f"\nExisting Medical Documents ({len(documents)} total):")
        print("-" * 80)

        for doc in documents:
            # Check if content might match screening keywords
            content_lower = (doc.content or '').lower()
            filename_lower = doc.filename.lower()

            potential_matches = []
            screening_keywords = [
                ('Colonoscopy', ['colonoscopy', 'colo', 'gastroentero']),
                ('Mammogram', ['mammogram', 'mammo', 'breast']),
                ('Pap Smear', ['pap', 'cervical']),
                ('Lipid Panel', ['hdl', 'ldl', 'lipid', 'cholesterol']),
                ('Eye Exam', ['eye exam', 'optometry', 'vision']),
                ('A1c', ['a1c', 'glucose', 'sugar']),
                ('Bone Density', ['dexa', 'dxa', 'bone density']),
                ('Vaccination', ['vaccination', 'vaccine', 'immunization'])
            ]

            for screening_name, keywords in screening_keywords:
                if any(keyword in content_lower or keyword in filename_lower for keyword in keywords):
                    potential_matches.append(screening_name)

            match_str = f" → Matches: {', '.join(potential_matches)}" if potential_matches else " → No matches"

            print(f"{doc.patient.full_name}: {doc.filename}{match_str}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'summary':
        show_document_summary()
    else:
        create_sample_documents()