"""
Test script for the extended ScreeningType model functionality
Creates sample screening types with the new fields to verify integration
"""

import os
import sys
from app import app, db
from models import ScreeningType

def create_sample_screening_types():
    """Create sample screening types with extended fields"""
    
    with app.app_context():
        try:
            # Sample screening types with all new fields
            sample_screenings = [
                {
                    "name": "Comprehensive Mammogram",
                    "description": "Breast cancer screening with digital mammography and tomosynthesis",
                    "frequency_months": 12,
                    "min_age": 40,
                    "max_age": 74,
                    "gender": "Female",
                    "document_section": "imaging",
                    "keywords": ["mammogram", "breast imaging", "tomosynthesis", "breast cancer screening"],
                    "filename_keywords": ["mammo", "breast", "tomo"],
                    "trigger_conditions": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "395557000",
                            "display": "Family history of malignant neoplasm of breast"
                        }
                    ]
                },
                {
                    "name": "HbA1c Diabetes Monitoring",
                    "description": "Hemoglobin A1c test for diabetes management and screening",
                    "frequency_months": 6,
                    "min_age": 35,
                    "max_age": None,
                    "gender": None,
                    "document_section": "labs",
                    "keywords": ["hba1c", "hemoglobin a1c", "diabetes", "glucose"],
                    "filename_keywords": ["hba1c", "a1c", "diabetes"],
                    "trigger_conditions": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": "E11.9",
                            "display": "Type 2 diabetes mellitus without complications"
                        }
                    ]
                },
                {
                    "name": "Prostate Cancer Screening",
                    "description": "PSA test and digital rectal exam for prostate cancer screening",
                    "frequency_months": 12,
                    "min_age": 50,
                    "max_age": 70,
                    "gender": "Male",
                    "document_section": "labs",
                    "keywords": ["psa", "prostate specific antigen", "prostate cancer", "digital rectal exam"],
                    "filename_keywords": ["psa", "prostate"],
                    "trigger_conditions": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "428262008",
                            "display": "Family history of prostate cancer"
                        }
                    ]
                }
            ]
            
            created_count = 0
            
            for screening_data in sample_screenings:
                # Check if screening already exists
                existing = ScreeningType.query.filter_by(name=screening_data["name"]).first()
                
                if existing:
                    print(f"⚠ Screening type '{screening_data['name']}' already exists, updating...")
                    screening_type = existing
                else:
                    print(f"✓ Creating new screening type: {screening_data['name']}")
                    screening_type = ScreeningType()
                    created_count += 1
                
                # Set basic fields
                screening_type.name = screening_data["name"]
                screening_type.description = screening_data["description"]
                screening_type.frequency_months = screening_data["frequency_months"]
                screening_type.min_age = screening_data["min_age"]
                screening_type.max_age = screening_data["max_age"]
                screening_type.gender = screening_data["gender"]
                screening_type.document_section = screening_data["document_section"]
                screening_type.is_active = True
                
                # Set keywords
                screening_type.set_keywords(screening_data["keywords"])
                screening_type.set_filename_keywords(screening_data["filename_keywords"])
                
                # Set trigger conditions
                screening_type.set_trigger_conditions(screening_data["trigger_conditions"])
                
                if not existing:
                    db.session.add(screening_type)
            
            db.session.commit()
            print(f"\n✓ Successfully created {created_count} new screening types")
            
            # Test the new methods
            print("\n=== Testing New Methods ===")
            
            for screening_type in ScreeningType.query.filter_by(is_active=True).all():
                print(f"\nScreening: {screening_type.name}")
                print(f"  - Formatted Frequency: {screening_type.formatted_frequency}")
                print(f"  - Keywords: {screening_type.get_keywords()}")
                print(f"  - Filename Keywords: {screening_type.get_filename_keywords()}")
                print(f"  - Trigger Conditions: {len(screening_type.get_trigger_conditions())} conditions")
                print(f"  - Document Section: {screening_type.document_section}")
                
                # Test keyword matching
                test_content = "Patient needs mammogram breast cancer screening"
                if screening_type.matches_content_keywords(test_content):
                    print(f"  ✓ Matches test content: '{test_content}'")
                
                test_filename = "mammo_results_2024.pdf"
                if screening_type.matches_filename_keywords(test_filename):
                    print(f"  ✓ Matches test filename: '{test_filename}'")
            
        except Exception as e:
            print(f"✗ Error creating sample screening types: {str(e)}")
            db.session.rollback()
            raise

def test_parsing_integration():
    """Test the screening parser integration"""
    
    with app.app_context():
        try:
            from screening_parser import get_screening_parser
            
            parser = get_screening_parser()
            
            # Test document parsing
            test_content = "Patient underwent mammogram for breast cancer screening. Results show normal tissue."
            test_filename = "mammo_report_2024.pdf"
            
            matches = parser.parse_document(
                content=test_content,
                filename=test_filename,
                document_section="imaging"
            )
            
            print(f"\n=== Document Parsing Test ===")
            print(f"Test content: {test_content}")
            print(f"Test filename: {test_filename}")
            print(f"Document section: imaging")
            print(f"Found {len(matches)} matches:")
            
            for match in matches:
                print(f"  - {match['screening_type'].name}")
                print(f"    Score: {match['match_score']}")
                print(f"    Confidence: {match['confidence']:.2f}")
                print(f"    Reasons: {', '.join(match['match_reasons'])}")
            
        except Exception as e:
            print(f"✗ Error testing parsing integration: {str(e)}")

if __name__ == "__main__":
    print("Testing extended ScreeningType functionality...")
    create_sample_screening_types()
    test_parsing_integration()
    print("\n✓ Testing completed successfully!")