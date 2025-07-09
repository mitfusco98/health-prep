#!/usr/bin/env python3
"""
Create Sample Medical Documents for Testing Screening Logic
Generates properly categorized, sex-specific medical documents to test document-to-screening matching
and demonstrate prep sheet functionality
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
    """Create sample medical documents with proper categorization and sex-specific logic"""
    
    with app.app_context():
        # Get existing patients
        patients = Patient.query.all()
        if not patients:
            print("No patients found. Please add patients first.")
            return
        
        # Laboratory documents (LAB_REPORT)
        lab_documents = [
            {
                'filename': 'lipid_panel_results.pdf',
                'content': 'LIPID PANEL RESULTS\n\nDate: {date}\nTotal cholesterol: 185 mg/dL\nLDL cholesterol: 110 mg/dL\nHDL cholesterol: 55 mg/dL\nTriglycerides: 120 mg/dL\n\nResults within normal limits. Continue current management.',
                'document_type': 'LAB_REPORT',
                'document_name': 'Lipid Panel Results',
                'keywords': ['lipid', 'cholesterol', 'triglycerides']
            },
            {
                'filename': 'a1c_glucose_results.pdf',
                'content': 'HEMOGLOBIN A1C AND GLUCOSE RESULTS\n\nDate: {date}\nHemoglobin A1c: 5.8%\nFasting glucose: 95 mg/dL\nRandom glucose: 110 mg/dL\n\nGlucose control excellent. Continue current diet and exercise.',
                'document_type': 'LAB_REPORT',
                'document_name': 'A1C and Glucose Results',
                'keywords': ['a1c', 'hemoglobin', 'glucose', 'diabetes']
            },
            {
                'filename': 'complete_blood_count.pdf',
                'content': 'COMPLETE BLOOD COUNT (CBC)\n\nDate: {date}\nHemoglobin: 14.2 g/dL\nHematocrit: 42.1%\nWhite Blood Cell count: 7,200/μL\nPlatelet count: 285,000/μL\n\nAll values within normal range.',
                'document_type': 'LAB_REPORT',
                'document_name': 'Complete Blood Count',
                'keywords': ['cbc', 'blood count', 'hemoglobin']
            },
            {
                'filename': 'thyroid_function_tests.pdf',
                'content': 'THYROID FUNCTION PANEL\n\nDate: {date}\nTSH: 2.1 mIU/L\nFree T4: 1.2 ng/dL\nFree T3: 3.1 pg/mL\n\nThyroid function normal.',
                'document_type': 'LAB_REPORT',
                'document_name': 'Thyroid Function Tests',
                'keywords': ['thyroid', 'tsh', 't4', 't3']
            }
        ]
        
        # Imaging documents (RADIOLOGY_REPORT)
        imaging_documents = [
            {
                'filename': 'mammogram_screening.pdf',
                'content': 'MAMMOGRAM SCREENING RESULTS\n\nDate: {date}\nBilateral mammogram performed for routine screening.\nFindings: No suspicious lesions identified.\nBI-RADS Category: 1 (Negative)\nRecommendation: Continue annual mammogram screening.',
                'document_type': 'RADIOLOGY_REPORT',
                'document_name': 'Mammogram Screening',
                'sex_specific': 'female',
                'keywords': ['mammogram', 'breast', 'screening', 'bi-rads']
            },
            {
                'filename': 'dexa_bone_density.pdf',
                'content': 'BONE DENSITY SCAN (DEXA)\n\nDate: {date}\nLumbar spine T-score: -1.2\nFemoral neck T-score: -0.8\nHip T-score: -1.0\n\nBone density within normal range for age. Recommend repeat in 2 years.',
                'document_type': 'RADIOLOGY_REPORT',
                'document_name': 'DEXA Bone Density Scan',
                'keywords': ['dexa', 'bone density', 'osteoporosis', 't-score']
            },
            {
                'filename': 'chest_xray_screening.pdf',
                'content': 'CHEST X-RAY REPORT\n\nDate: {date}\nIndication: Routine screening\nFindings: Clear lung fields bilaterally. Normal heart size and shape. No acute findings.\nImpression: Normal chest X-ray.',
                'document_type': 'RADIOLOGY_REPORT',
                'document_name': 'Chest X-Ray Screening',
                'keywords': ['chest x-ray', 'lung', 'screening']
            },
            {
                'filename': 'ct_colonography.pdf',
                'content': 'CT COLONOGRAPHY (VIRTUAL COLONOSCOPY)\n\nDate: {date}\nIndication: Colorectal cancer screening\nFindings: No polyps or masses identified. Normal colonic anatomy.\nRecommendation: Routine screening in 5 years.',
                'document_type': 'RADIOLOGY_REPORT',
                'document_name': 'CT Colonography',
                'keywords': ['colonography', 'virtual colonoscopy', 'colon', 'screening']
            }
        ]
        
        # Consultation documents (CONSULTATION)
        consultation_documents = [
            {
                'filename': 'cardiology_consultation.pdf',
                'content': 'CARDIOLOGY CONSULTATION\n\nDate: {date}\nReason: Routine cardiac risk assessment\nHistory: Patient with family history of heart disease\nExamination: Normal heart sounds, regular rhythm\nRecommendation: Continue current medications, annual follow-up',
                'document_type': 'CONSULTATION',
                'document_name': 'Cardiology Consultation',
                'keywords': ['cardiology', 'heart', 'cardiac']
            },
            {
                'filename': 'dermatology_skin_check.pdf',
                'content': 'DERMATOLOGY CONSULTATION\n\nDate: {date}\nReason: Annual skin cancer screening\nExamination: Full body skin examination performed\nFindings: No suspicious lesions identified\nRecommendation: Annual skin checks, sun protection',
                'document_type': 'CONSULTATION',
                'document_name': 'Dermatology Skin Check',
                'keywords': ['dermatology', 'skin', 'cancer screening']
            },
            {
                'filename': 'ophthalmology_eye_exam.pdf',
                'content': 'OPHTHALMOLOGY EXAMINATION\n\nDate: {date}\nReason: Routine eye examination\nVisual Acuity: 20/20 both eyes\nIntraocular Pressure: Normal\nFundoscopy: No retinopathy observed\nRecommendation: Annual eye examinations',
                'document_type': 'CONSULTATION',
                'document_name': 'Ophthalmology Eye Exam',
                'keywords': ['ophthalmology', 'eye exam', 'vision', 'retinal']
            },
            {
                'filename': 'gastroenterology_consultation.pdf',
                'content': 'GASTROENTEROLOGY CONSULTATION\n\nDate: {date}\nReason: Colorectal cancer screening discussion\nHistory: Average risk patient, age appropriate for screening\nRecommendation: Colonoscopy scheduling, dietary counseling\nFollow-up: Post-procedure in 2 weeks',
                'document_type': 'CONSULTATION',
                'document_name': 'Gastroenterology Consultation',
                'keywords': ['gastroenterology', 'colonoscopy', 'colon']
            }
        ]
        
        # Hospital documents (DISCHARGE_SUMMARY)
        hospital_documents = [
            {
                'filename': 'preventive_care_admission.pdf',
                'content': 'DISCHARGE SUMMARY - PREVENTIVE CARE UNIT\n\nAdmission Date: {date}\nDischarge Date: {date}\nReason: Comprehensive preventive health assessment\nProcedures: Complete physical exam, routine screenings\nDischarge Instructions: Continue current medications, follow-up appointments scheduled',
                'document_type': 'DISCHARGE_SUMMARY',
                'document_name': 'Preventive Care Admission Summary',
                'keywords': ['preventive', 'comprehensive', 'physical']
            },
            {
                'filename': 'outpatient_procedure_summary.pdf',
                'content': 'OUTPATIENT PROCEDURE SUMMARY\n\nDate: {date}\nProcedure: Routine screening procedures\nAnesthesia: Local/Conscious sedation\nComplications: None\nDisposition: Discharged home in stable condition\nFollow-up: Scheduled as appropriate',
                'document_type': 'DISCHARGE_SUMMARY',
                'document_name': 'Outpatient Procedure Summary',
                'keywords': ['outpatient', 'procedure', 'screening']
            }
        ]
        
        # Female-specific documents
        female_specific_documents = [
            {
                'filename': 'pap_smear_results.pdf',
                'content': 'PAP SMEAR CYTOLOGY REPORT\n\nDate: {date}\nSpecimen: Cervical cytology\nResults: Normal cervical cells (NILM)\nHPV Testing: Negative\nRecommendation: Routine screening in 3 years per guidelines',
                'document_type': 'LAB_REPORT',
                'document_name': 'Pap Smear Results',
                'sex_specific': 'female',
                'keywords': ['pap smear', 'cervical', 'cytology', 'hpv']
            },
            {
                'filename': 'gynecology_consultation.pdf',
                'content': 'GYNECOLOGY CONSULTATION\n\nDate: {date}\nReason: Annual gynecological examination\nExamination: Normal pelvic examination\nBreast examination: Normal\nRecommendations: Continue routine screening, contraception counseling as needed',
                'document_type': 'CONSULTATION',
                'document_name': 'Gynecology Consultation',
                'sex_specific': 'female',
                'keywords': ['gynecology', 'pelvic', 'breast']
            }
        ]
        
        # Male-specific documents
        male_specific_documents = [
            {
                'filename': 'prostate_screening.pdf',
                'content': 'PROSTATE SCREENING RESULTS\n\nDate: {date}\nPSA Level: 1.2 ng/mL\nDigital Rectal Exam: Normal\nProstate size: Normal\nRecommendation: Continue annual screening, repeat PSA in 1 year',
                'document_type': 'LAB_REPORT',
                'document_name': 'Prostate Screening',
                'sex_specific': 'male',
                'keywords': ['prostate', 'psa', 'screening']
            },
            {
                'filename': 'urology_consultation.pdf',
                'content': 'UROLOGY CONSULTATION\n\nDate: {date}\nReason: Prostate health screening\nExamination: Normal genitourinary examination\nProstate: No abnormalities detected\nRecommendations: Annual screening, lifestyle modifications',
                'document_type': 'CONSULTATION',
                'document_name': 'Urology Consultation',
                'sex_specific': 'male',
                'keywords': ['urology', 'prostate', 'genitourinary']
            }
        ]
        
        # Other/miscellaneous documents
        other_documents = [
            {
                'filename': 'vaccination_record.pdf',
                'content': 'VACCINATION RECORD UPDATE\n\nDate: {date}\nInfluenza vaccine: Administered\nCOVID-19 status: Up to date\nTdap: Current (expires 2029)\nAll routine adult vaccinations current per CDC guidelines',
                'document_type': 'OTHER',
                'document_name': 'Vaccination Record',
                'keywords': ['vaccination', 'immunization', 'vaccine']
            },
            {
                'filename': 'nutrition_counseling.pdf',
                'content': 'NUTRITION COUNSELING SESSION\n\nDate: {date}\nDietary Assessment: Mediterranean diet pattern\nBMI: 24.5 (Normal)\nRecommendations: Continue current diet, increase fiber intake\nFollow-up: 6 months',
                'document_type': 'OTHER',
                'document_name': 'Nutrition Counseling',
                'keywords': ['nutrition', 'diet', 'counseling']
            }
        ]
        
        print("Creating sex-specific, properly categorized medical documents...")
        print(f"Found {len(patients)} patients to process")
        
        documents_created = 0
        
        for patient in patients:
            print(f"\nProcessing patient: {patient.full_name} (Sex: {patient.sex})")
            
            # Base documents for all patients
            patient_documents = []
            patient_documents.extend(random.sample(lab_documents, 2))  # 2 lab documents
            patient_documents.extend(random.sample(imaging_documents, 1))  # 1 imaging document  
            patient_documents.extend(random.sample(consultation_documents, 2))  # 2 consultations
            patient_documents.extend(random.sample(hospital_documents, 1))  # 1 hospital document
            patient_documents.extend(random.sample(other_documents, 1))  # 1 other document
            
            # Add sex-specific documents
            if patient.sex and patient.sex.lower() == 'female':
                patient_documents.extend(female_specific_documents)  # Add all female-specific
                # Add mammogram (already in imaging_documents but marked female-specific)
                print(f"  -> Added female-specific documents (pap smear, gynecology, mammogram)")
            elif patient.sex and patient.sex.lower() == 'male':
                patient_documents.extend(male_specific_documents)  # Add all male-specific
                print(f"  -> Added male-specific documents (prostate screening, urology)")
            
            # Filter out sex-specific documents for wrong gender
            filtered_documents = []
            for doc in patient_documents:
                if 'sex_specific' in doc:
                    if patient.sex and patient.sex.lower() == doc['sex_specific']:
                        filtered_documents.append(doc)
                    else:
                        print(f"  -> Skipped {doc['document_name']} (wrong gender)")
                else:
                    filtered_documents.append(doc)
            
            # Create documents for this patient
            for doc_data in filtered_documents:
                # Create document with realistic dates (last 18 months)
                days_ago = random.randint(30, 540)
                document_date = datetime.now() - timedelta(days=days_ago)
                
                # Create metadata dictionary
                metadata = {
                    'medical_data_subsection': doc_data['document_type'],
                    'keywords': doc_data.get('keywords', []),
                    'sex_specific': doc_data.get('sex_specific'),
                    'file_size': random.randint(50000, 200000),
                    'content_type': 'application/pdf',
                    'fhir_document_reference_id': f"doc-{patient.id}-{documents_created + 1}",
                    'status': 'completed',
                    'created_for_demo': True,
                    'notes': f"Generated for screening logic testing - {doc_data['document_type']}"
                }
                
                # Format content with actual date
                formatted_content = doc_data['content'].format(
                    date=document_date.strftime('%B %d, %Y')
                )
                
                new_document = MedicalDocument(
                    patient_id=patient.id,
                    filename=f"{patient.last_name}_{doc_data['filename']}",
                    document_name=doc_data['document_name'],
                    document_type=doc_data['document_type'],  # Now using correct values
                    content=formatted_content,
                    document_date=document_date,
                    source_system="HealthPrep Demo System",
                    provider="Demo Provider",
                    doc_metadata=json.dumps(metadata)
                )
                
                try:
                    db.session.add(new_document)
                    documents_created += 1
                    print(f"  -> Created: {doc_data['document_name']} ({doc_data['document_type']})")
                except Exception as e:
                    print(f"  -> Error creating {doc_data['document_name']}: {e}")
                    db.session.rollback()
                    continue
        
        # Commit all documents
        try:
            db.session.commit()
            print(f"\n✓ Successfully created {documents_created} medical documents")
            print(f"✓ Documents properly categorized by medical data subsection:")
            print(f"  - LAB_REPORT: Laboratory results and tests")
            print(f"  - RADIOLOGY_REPORT: Imaging studies and scans")  
            print(f"  - CONSULTATION: Specialist consultations")
            print(f"  - DISCHARGE_SUMMARY: Hospital and procedure summaries")
            print(f"  - OTHER: Miscellaneous medical documents")
            print(f"✓ Sex-specific logic applied (no inappropriate documents)")
            print(f"✓ Documents designed to test screening logic and prep sheet generation")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error committing documents: {e}")

def show_document_summary():
    """Show summary of created documents by type and patient"""
    with app.app_context():
        patients = Patient.query.all()
        
        print("\n" + "="*60)
        print("DOCUMENT SUMMARY BY PATIENT AND TYPE")
        print("="*60)
        
        for patient in patients:
            documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
            if documents:
                print(f"\n{patient.full_name} ({patient.sex}):")
                
                # Count by type
                type_counts = {}
                for doc in documents:
                    doc_type = doc.document_type or 'UNKNOWN'
                    type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
                
                for doc_type, count in type_counts.items():
                    subsection_name = {
                        'LAB_REPORT': 'Laboratories',
                        'RADIOLOGY_REPORT': 'Imaging', 
                        'CONSULTATION': 'Consults',
                        'DISCHARGE_SUMMARY': 'Hospital Records',
                        'OTHER': 'Other'
                    }.get(doc_type, doc_type)
                    print(f"  - {subsection_name}: {count} documents")

if __name__ == "__main__":
    print("Creating sample medical documents for screening logic testing...")
    create_sample_documents()
    show_document_summary()
    print("\nDocuments are now ready for testing prep sheet generation and screening logic!")