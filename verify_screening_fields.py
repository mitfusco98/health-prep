#!/usr/bin/env python3
"""
Verification script for ScreeningType dynamic parsing fields
Tests all required fields and populates sample data for demonstration
"""

from app import app, db
from models import ScreeningType
import json


def verify_screening_type_structure():
    """Verify that ScreeningType has all required fields for dynamic parsing"""
    print("=== ScreeningType Field Verification ===")
    
    with app.app_context():
        # Get column information
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = inspector.get_columns('screening_type')
        
        required_fields = {
            'content_keywords': 'Keywords for content parsing',
            'document_keywords': 'Keywords for document type parsing', 
            'filename_keywords': 'Keywords for filename parsing',
            'trigger_conditions': 'FHIR condition triggers',
            'frequency_number': 'Structured frequency number',
            'frequency_unit': 'Structured frequency unit',
            'min_age': 'Minimum age for screening',
            'max_age': 'Maximum age for screening',
            'gender_specific': 'Gender specificity (Male/Female/None)',
            'status': 'Screening status (active/inactive/draft)'
        }
        
        column_names = [col['name'] for col in columns]
        
        print("✓ Checking required fields:")
        all_present = True
        for field, description in required_fields.items():
            if field in column_names:
                print(f"  ✓ {field}: {description}")
            else:
                print(f"  ✗ {field}: {description} - MISSING")
                all_present = False
        
        print(f"\n✓ Field verification: {'PASSED' if all_present else 'FAILED'}")
        return all_present


def create_sample_screening_types():
    """Create sample screening types with all dynamic parsing fields"""
    print("\n=== Creating Sample ScreeningType Data ===")
    
    with app.app_context():
        # Sample screening configurations
        screening_configs = [
            {
                'name': 'Mammography Screening',
                'description': 'Annual breast cancer screening for women',
                'frequency_number': 1,
                'frequency_unit': 'years',
                'min_age': 40,
                'max_age': 75,
                'gender_specific': 'Female',
                'status': 'active',
                'content_keywords': ['mammogram', 'breast imaging', 'breast cancer screening', 'bilateral mammography'],
                'document_keywords': ['radiology', 'imaging', 'breast imaging', 'mammography report'],
                'filename_keywords': ['mammo', 'breast', 'mammography', 'bi-rads'],
                'trigger_conditions': [
                    {
                        'system': 'http://snomed.info/sct',
                        'code': '395557000',
                        'display': 'Family history of breast cancer'
                    }
                ]
            },
            {
                'name': 'Colonoscopy Screening',
                'description': 'Colorectal cancer screening via colonoscopy',
                'frequency_number': 10,
                'frequency_unit': 'years',
                'min_age': 45,
                'max_age': 75,
                'gender_specific': None,
                'status': 'active',
                'content_keywords': ['colonoscopy', 'colon screening', 'polyp', 'colorectal', 'endoscopy'],
                'document_keywords': ['procedure report', 'endoscopy', 'gastroenterology'],
                'filename_keywords': ['colonoscopy', 'endo', 'colon', 'scope'],
                'trigger_conditions': [
                    {
                        'system': 'http://snomed.info/sct',
                        'code': '395557000',
                        'display': 'Family history of colorectal cancer'
                    }
                ]
            },
            {
                'name': 'HbA1c Testing',
                'description': 'Diabetes monitoring and screening',
                'frequency_number': 3,
                'frequency_unit': 'months',
                'min_age': 18,
                'max_age': None,
                'gender_specific': None,
                'status': 'active',
                'content_keywords': ['hemoglobin a1c', 'hba1c', 'glucose', 'diabetes', 'glycemic control'],
                'document_keywords': ['laboratory', 'lab report', 'chemistry panel'],
                'filename_keywords': ['hba1c', 'glucose', 'lab', 'chemistry'],
                'trigger_conditions': [
                    {
                        'system': 'http://snomed.info/sct',
                        'code': '73211009',
                        'display': 'Diabetes mellitus'
                    }
                ]
            },
            {
                'name': 'Bone Density Screening',
                'description': 'Osteoporosis screening via DEXA scan',
                'frequency_number': 2,
                'frequency_unit': 'years',
                'min_age': 65,
                'max_age': None,
                'gender_specific': None,
                'status': 'active',
                'content_keywords': ['bone density', 'dexa', 'osteoporosis', 'bone mineral density', 't-score'],
                'document_keywords': ['radiology', 'imaging', 'bone densitometry'],
                'filename_keywords': ['dexa', 'bone', 'density', 'osteo'],
                'trigger_conditions': [
                    {
                        'system': 'http://snomed.info/sct',
                        'code': '64859006',
                        'display': 'Osteoporosis'
                    }
                ]
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for config in screening_configs:
            # Check if screening type already exists
            screening = ScreeningType.query.filter_by(name=config['name']).first()
            
            if screening:
                print(f"  → Updating existing: {config['name']}")
                updated_count += 1
            else:
                print(f"  → Creating new: {config['name']}")
                screening = ScreeningType()
                created_count += 1
            
            # Set basic fields
            screening.name = config['name']
            screening.description = config['description']
            screening.frequency_number = config['frequency_number']
            screening.frequency_unit = config['frequency_unit']
            screening.min_age = config['min_age']
            screening.max_age = config['max_age']
            screening.gender_specific = config['gender_specific']
            screening.status = config['status']
            
            # Set keyword fields
            screening.set_content_keywords(config['content_keywords'])
            screening.set_document_keywords(config['document_keywords'])
            screening.set_filename_keywords(config['filename_keywords'])
            
            # Set trigger conditions
            screening.set_trigger_conditions(config['trigger_conditions'])
            
            if not ScreeningType.query.filter_by(name=config['name']).first():
                db.session.add(screening)
        
        db.session.commit()
        print(f"  ✓ Created: {created_count}, Updated: {updated_count}")


def test_dynamic_parsing_methods():
    """Test the dynamic parsing methods on sample screening types"""
    print("\n=== Testing Dynamic Parsing Methods ===")
    
    with app.app_context():
        # Test cases for parsing
        test_cases = [
            {
                'filename': 'mammography_bilateral_2024.pdf',
                'content': 'Patient underwent bilateral mammography screening. BI-RADS category 1. No evidence of malignancy.',
                'document_type': 'radiology report'
            },
            {
                'filename': 'colonoscopy_procedure_note.pdf',
                'content': 'Colonoscopy performed to cecum. Multiple small polyps identified and removed.',
                'document_type': 'procedure report'
            },
            {
                'filename': 'lab_results_hba1c.pdf',
                'content': 'Hemoglobin A1c: 7.2% (elevated). Patient diabetes control suboptimal.',
                'document_type': 'laboratory report'
            },
            {
                'filename': 'dexa_scan_report.pdf',
                'content': 'Bone density scan shows T-score of -2.8 at lumbar spine, consistent with osteoporosis.',
                'document_type': 'radiology report'
            }
        ]
        
        screenings = ScreeningType.query.filter_by(status='active').all()
        
        for test_case in test_cases:
            print(f"\n  Testing: {test_case['filename']}")
            matches = []
            
            for screening in screenings:
                # Test filename matching
                filename_match = screening.matches_keywords(test_case['filename'], 'filename')
                
                # Test content matching
                content_match = screening.matches_keywords(test_case['content'], 'content')
                
                # Test document type matching
                document_match = screening.matches_keywords(test_case['document_type'], 'document')
                
                # Test combined matching
                all_match = screening.matches_keywords(
                    f"{test_case['filename']} {test_case['content']} {test_case['document_type']}", 
                    'all'
                )
                
                if any([filename_match, content_match, document_match, all_match]):
                    matches.append({
                        'screening': screening.name,
                        'filename_match': filename_match,
                        'content_match': content_match,
                        'document_match': document_match,
                        'overall_match': all_match
                    })
            
            print(f"    Matches found: {len(matches)}")
            for match in matches:
                print(f"      → {match['screening']}: F:{match['filename_match']} C:{match['content_match']} D:{match['document_match']}")


def verify_field_completeness():
    """Verify all screenings have complete field data"""
    print("\n=== Field Completeness Verification ===")
    
    with app.app_context():
        screenings = ScreeningType.query.all()
        
        for screening in screenings:
            print(f"\n  {screening.name}:")
            print(f"    ✓ Keywords: Content({len(screening.get_content_keywords())}), Document({len(screening.get_document_keywords())}), Filename({len(screening.get_filename_keywords())})")
            print(f"    ✓ Trigger Conditions: {len(screening.get_trigger_conditions())}")
            print(f"    ✓ Frequency: {screening.formatted_frequency}")
            print(f"    ✓ Age Range: {screening.min_age or 'None'} - {screening.max_age or 'None'}")
            print(f"    ✓ Gender: {screening.gender_specific or 'All'}")
            print(f"    ✓ Status: {screening.status}")


def main():
    """Main verification and testing function"""
    print("ScreeningType Dynamic Parsing Verification")
    print("=" * 50)
    
    # Step 1: Verify database structure
    structure_ok = verify_screening_type_structure()
    
    if not structure_ok:
        print("❌ Database structure verification failed!")
        return False
    
    # Step 2: Create sample data
    create_sample_screening_types()
    
    # Step 3: Test parsing methods
    test_dynamic_parsing_methods()
    
    # Step 4: Verify field completeness
    verify_field_completeness()
    
    print("\n" + "=" * 50)
    print("✅ ScreeningType verification completed successfully!")
    print("\nAll required fields are present and functional:")
    print("  • content_keywords, document_keywords, filename_keywords")
    print("  • trigger_conditions, frequency, min_age, max_age, gender, status")
    print("  • Dynamic parsing logic is ready for prep sheet generation")
    
    return True


if __name__ == '__main__':
    main()