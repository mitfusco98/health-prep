"""
Test Document to Screening Type Matching System
Validates multi-strategy document matching with confidence scoring
"""

import json
from datetime import datetime, date
from app import app, db
from models import Patient, ScreeningType, MedicalDocument
from document_screening_matcher import DocumentScreeningMatcher, generate_prep_sheet_screening_recommendations


def test_document_screening_matching_system():
    """Test the complete document-to-screening matching system"""
    
    print("TESTING DOCUMENT-TO-SCREENING MATCHING SYSTEM")
    print("=" * 60)
    
    with app.app_context():
        # Step 1: Setup screening types with comprehensive configurations
        setup_comprehensive_screening_configs()
        
        # Step 2: Enhance existing documents with FHIR codes
        enhance_documents_with_codes()
        
        # Step 3: Test individual matching strategies
        test_matching_strategies()
        
        # Step 4: Test prep sheet integration
        test_prep_sheet_integration()
        
        # Step 5: Demonstrate confidence scoring
        demonstrate_confidence_scoring()
        
        print("\n" + "=" * 60)
        print("DOCUMENT-SCREENING MATCHING TEST COMPLETE")


def setup_comprehensive_screening_configs():
    """Setup screening types with comprehensive matching configurations"""
    
    print("\nSetting up comprehensive screening configurations...")
    
    # Enhanced diabetes screening configuration
    diabetes_screening = ScreeningType.query.filter_by(name="Diabetes Management").first()
    if diabetes_screening:
        diabetes_config = {
            "labs": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory",
                    "display": "Laboratory"
                },
                "document_types": ["Lab Report", "HbA1c Results", "Glucose Test", "Laboratory Results"],
                "keywords": ["glucose", "hba1c", "diabetes", "blood sugar", "glycemic", "insulin"],
                "loinc_codes": ["4548-4", "33747-0", "2093-3", "77353-1"],  # HbA1c, glucose, cholesterol
                "cpt_codes": ["83036", "83037", "82947"],  # Glucose tests
                "priority": "high"
            },
            "imaging": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "imaging",
                    "display": "Imaging"
                },
                "document_types": ["Retinal Exam", "Foot X-Ray", "Diabetic Eye Exam"],
                "keywords": ["retinal", "foot", "eye exam", "diabetic retinopathy", "fundus"],
                "cpt_codes": ["92134", "73620", "92014"],  # Retinal exam, foot x-ray, eye exam
                "priority": "medium"
            }
        }
        diabetes_screening.set_document_section_mappings(diabetes_config)
        print("Enhanced: Diabetes Management with LOINC/CPT codes")
    
    # Enhanced hypertension screening
    hypertension_screening = ScreeningType.query.filter_by(name="Hypertension Monitoring").first()
    if hypertension_screening:
        hypertension_config = {
            "vitals": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                },
                "document_types": ["Vital Signs", "Blood Pressure Log", "Cardiovascular Assessment"],
                "keywords": ["blood pressure", "bp", "systolic", "diastolic", "hypertension"],
                "loinc_codes": ["8480-6", "8462-4", "85354-9"],  # Systolic BP, Diastolic BP, BP
                "priority": "high"
            },
            "clinical_notes": {
                "fhir_category": {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "exam",
                    "display": "Exam"
                },
                "document_types": ["Cardiology Note", "Clinical Note", "Cardiovascular Consult"],
                "keywords": ["cardiology", "hypertension", "cardiovascular", "cardiac", "heart"],
                "cpt_codes": ["99213", "99214", "93000"],  # Office visits, ECG
                "priority": "medium"
            }
        }
        hypertension_screening.set_document_section_mappings(hypertension_config)
        print("Enhanced: Hypertension Monitoring with vital signs codes")
    
    # Create cancer screening with comprehensive config
    cancer_screening = ScreeningType.query.filter_by(name="Cancer Risk Screening").first()
    if not cancer_screening:
        cancer_screening = ScreeningType(
            name="Cancer Risk Screening",
            description="Comprehensive cancer screening for high-risk patients",
            default_frequency="Annual",
            is_active=True
        )
        db.session.add(cancer_screening)
        db.session.flush()
    
    cancer_config = {
        "imaging": {
            "fhir_category": {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "imaging",
                "display": "Imaging"
            },
            "document_types": ["Mammogram", "CT Scan", "MRI", "Cancer Screening"],
            "keywords": ["mammogram", "screening", "tumor", "mass", "cancer", "oncology"],
            "loinc_codes": ["36319-2", "44136-0"],  # Mammography, CT
            "cpt_codes": ["77067", "74150", "77084"],  # Mammogram, CT abdomen, DXA
            "priority": "high"
        },
        "labs": {
            "fhir_category": {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            },
            "document_types": ["Tumor Markers", "Cancer Labs", "Oncology Labs"],
            "keywords": ["tumor marker", "cea", "psa", "ca-125", "alpha fetoprotein"],
            "loinc_codes": ["2039-6", "2857-1", "6875-9"],  # CEA, PSA, CA-125
            "priority": "medium"
        }
    }
    cancer_screening.set_document_section_mappings(cancer_config)
    print("Enhanced: Cancer Risk Screening with tumor marker codes")
    
    db.session.commit()
    print("Comprehensive screening configurations complete")


def enhance_documents_with_codes():
    """Enhance existing documents with FHIR codes for testing"""
    
    print("\nEnhancing documents with FHIR codes...")
    
    # Get sample documents and enhance with codes
    documents = MedicalDocument.query.limit(4).all()
    
    for i, document in enumerate(documents):
        if not document.doc_metadata:
            # Add FHIR codes based on document type
            fhir_metadata = {}
            
            if document.document_type == "Lab Report" or "lab" in (document.filename or "").lower():
                fhir_metadata = {
                    "fhir_primary_code": {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "4548-4",
                                "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
                            }]
                        }
                    },
                    "section": "labs",
                    "keywords": ["glucose", "hba1c", "diabetes"]
                }
            elif document.document_type == "Radiology Report" or "imaging" in (document.filename or "").lower():
                fhir_metadata = {
                    "fhir_primary_code": {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "36319-2",
                                "display": "Mammography of breast"
                            }]
                        }
                    },
                    "section": "imaging",
                    "keywords": ["mammogram", "breast", "screening"]
                }
            
            if fhir_metadata:
                document.doc_metadata = json.dumps(fhir_metadata)
                print(f"Enhanced: {document.filename or document.document_name} with FHIR codes")
    
    db.session.commit()
    print("Document enhancement complete")


def test_matching_strategies():
    """Test individual matching strategies"""
    
    print("\nTesting individual matching strategies...")
    
    matcher = DocumentScreeningMatcher()
    
    # Get a sample document for testing
    test_document = MedicalDocument.query.first()
    if not test_document:
        print("No documents available for testing")
        return
    
    print(f"\nTesting with document: {test_document.filename or test_document.document_name}")
    print(f"Document type: {test_document.document_type}")
    
    # Test Strategy 1: FHIR code matching
    print("\n1. FHIR Code Matching:")
    fhir_matches = matcher._match_by_fhir_codes(test_document)
    for match in fhir_matches:
        print(f"   ✓ {match.screening_name} (confidence: {match.confidence:.2f})")
        print(f"     Matched codes: {match.matched_codes}")
        print(f"     Source: {match.match_source}")
    
    # Test Strategy 2: Keyword matching
    print("\n2. Keyword Matching:")
    keyword_matches = matcher._match_by_keywords(test_document)
    for match in keyword_matches:
        print(f"   ✓ {match.screening_name} (confidence: {match.confidence:.2f})")
        print(f"     Matched keywords: {match.matched_keywords}")
    
    # Test Strategy 3: User-defined keywords
    print("\n3. User-defined Keyword Matching:")
    user_matches = matcher._match_by_user_keywords(test_document)
    for match in user_matches:
        print(f"   ✓ {match.screening_name} (confidence: {match.confidence:.2f})")
        print(f"     Matched keywords: {match.matched_keywords}")
    
    # Test Strategy 4: AI fuzzy matching
    print("\n4. AI Fuzzy Matching:")
    fuzzy_matches = matcher._match_by_ai_fuzzy(test_document)
    for match in fuzzy_matches:
        print(f"   ✓ {match.screening_name} (confidence: {match.confidence:.2f})")
        print(f"     Fuzzy score: {match.metadata.get('fuzzy_score', 0):.2f}")
    
    # Test combined matching
    print("\n5. Combined Matching (All Strategies):")
    all_matches = matcher.match_document_to_screenings(test_document, enable_ai_fuzzy=True)
    for match in all_matches:
        print(f"   ✓ {match.screening_name}")
        print(f"     Confidence: {match.confidence:.2f}")
        print(f"     Source: {match.match_source}")
        print(f"     Codes: {match.matched_codes}")
        print(f"     Keywords: {match.matched_keywords}")
    
    # Generate match summary
    summary = matcher.get_match_summary(all_matches)
    print(f"\nMatch Summary:")
    print(f"   Total matches: {summary['total_matches']}")
    print(f"   High confidence: {summary['high_confidence_matches']}")
    print(f"   Medium confidence: {summary['medium_confidence_matches']}")
    print(f"   Low confidence: {summary['low_confidence_matches']}")
    print(f"   Best match: {summary['best_match'].screening_name if summary['best_match'] else 'None'}")
    print(f"   Match sources: {summary['match_sources']}")


def test_prep_sheet_integration():
    """Test prep sheet integration with document matching"""
    
    print("\nTesting prep sheet integration...")
    
    # Get a patient with documents
    patient = Patient.query.first()
    if not patient:
        print("No patients available for testing")
        return
    
    print(f"\nGenerating screening recommendations for: {patient.first_name} {patient.last_name}")
    print(f"Patient ID: {patient.id}, MRN: {patient.mrn}")
    
    # Generate recommendations without AI fuzzy matching
    recommendations_basic = generate_prep_sheet_screening_recommendations(patient.id, enable_ai_fuzzy=False)
    
    print(f"\nBasic Recommendations (no AI fuzzy):")
    print(f"   Documents processed: {recommendations_basic['document_count']}")
    print(f"   Total matches: {recommendations_basic['summary']['total_matches']}")
    print(f"   Unique screenings: {recommendations_basic['summary']['unique_screenings']}")
    
    for rec in recommendations_basic['screening_recommendations']:
        print(f"\n   📋 {rec['screening_name']}")
        print(f"      Confidence: {rec['confidence']:.2f} ({rec['recommendation_priority']} priority)")
        print(f"      Sources: {', '.join(rec['match_sources'])}")
        print(f"      Document matches: {rec['total_document_matches']}")
        if rec['matched_codes']:
            print(f"      Matched codes: {', '.join(rec['matched_codes'])}")
        if rec['matched_keywords']:
            print(f"      Matched keywords: {', '.join(rec['matched_keywords'][:3])}...")
    
    # Generate recommendations with AI fuzzy matching
    recommendations_ai = generate_prep_sheet_screening_recommendations(patient.id, enable_ai_fuzzy=True)
    
    print(f"\nAI-Enhanced Recommendations:")
    print(f"   Documents processed: {recommendations_ai['document_count']}")
    print(f"   Total matches: {recommendations_ai['summary']['total_matches']}")
    print(f"   Unique screenings: {recommendations_ai['summary']['unique_screenings']}")
    
    # Compare results
    basic_count = len(recommendations_basic['screening_recommendations'])
    ai_count = len(recommendations_ai['screening_recommendations'])
    
    print(f"\nComparison:")
    print(f"   Basic matching: {basic_count} screening recommendations")
    print(f"   AI-enhanced: {ai_count} screening recommendations")
    print(f"   AI improvement: {ai_count - basic_count} additional matches")
    
    return recommendations_ai


def demonstrate_confidence_scoring():
    """Demonstrate confidence scoring across different match types"""
    
    print("\nDemonstrating confidence scoring...")
    
    matcher = DocumentScreeningMatcher()
    
    # Test confidence calculation for different scenarios
    print("\nConfidence Score Analysis:")
    
    # Scenario 1: Perfect FHIR code match
    print("\n1. Perfect FHIR Code Match:")
    fhir_confidence = matcher._calculate_fhir_code_confidence(
        matched_codes=["4548-4", "33747-0"],
        all_document_codes=[
            {"code": "4548-4", "system": "http://loinc.org"},
            {"code": "33747-0", "system": "http://loinc.org"}
        ]
    )
    print(f"   Confidence: {fhir_confidence:.2f} (Expected: High)")
    
    # Scenario 2: Partial FHIR code match
    partial_fhir_confidence = matcher._calculate_fhir_code_confidence(
        matched_codes=["4548-4"],
        all_document_codes=[
            {"code": "4548-4", "system": "http://loinc.org"},
            {"code": "8480-6", "system": "http://loinc.org"},
            {"code": "2093-3", "system": "http://loinc.org"}
        ]
    )
    print(f"   Partial match confidence: {partial_fhir_confidence:.2f} (Expected: Medium)")
    
    # Scenario 3: Strong keyword match with section
    keyword_confidence = matcher._calculate_keyword_confidence(
        matched_keywords=["section:labs", "glucose", "diabetes", "hba1c"],
        document_text="HbA1c glucose diabetes laboratory results",
        detected_section="labs"
    )
    print(f"\n2. Strong Keyword Match:")
    print(f"   Confidence: {keyword_confidence:.2f} (Expected: High)")
    
    # Scenario 4: User keyword fallback
    user_confidence = matcher._calculate_user_keyword_confidence(
        matched_keywords=["direct:diabetes", "user:glucose", "user:insulin"],
        screening_name="Diabetes Management"
    )
    print(f"\n3. User Keyword Fallback:")
    print(f"   Confidence: {user_confidence:.2f} (Expected: Medium)")
    
    print(f"\nConfidence Thresholds:")
    for level, threshold in matcher.confidence_thresholds.items():
        print(f"   {level.capitalize()}: {threshold:.1f} and above")


def validate_structured_results():
    """Validate that results are properly structured"""
    
    print("\nValidating structured results format...")
    
    patient = Patient.query.first()
    if not patient:
        print("No patients available for validation")
        return
    
    recommendations = generate_prep_sheet_screening_recommendations(patient.id, enable_ai_fuzzy=True)
    
    # Validate structure
    required_fields = [
        'patient_id', 'document_count', 'screening_recommendations', 
        'document_matches', 'summary', 'generation_metadata'
    ]
    
    print("Validating top-level structure:")
    for field in required_fields:
        exists = field in recommendations
        print(f"   {field}: {'✓' if exists else '✗'}")
    
    # Validate recommendation structure
    if recommendations['screening_recommendations']:
        rec = recommendations['screening_recommendations'][0]
        rec_fields = [
            'screening_type_id', 'screening_name', 'confidence', 
            'match_sources', 'matched_codes', 'matched_keywords',
            'recommendation_priority'
        ]
        
        print("\nValidating recommendation structure:")
        for field in rec_fields:
            exists = field in rec
            print(f"   {field}: {'✓' if exists else '✗'}")
    
    print(f"\nStructured results validation complete")
    print(f"Ready for prep sheet integration")


if __name__ == "__main__":
    test_document_screening_matching_system()
    validate_structured_results()