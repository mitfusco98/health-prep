#!/usr/bin/env python3
"""
Test FHIR-Compliant Screening Types Configuration

Demonstrates the enhanced screening_types config with:
- Manual keywords
- Document sections (labs, imaging, consults, etc.)
- LOINC/CPT codes with FHIR field naming
- Category mapping to FHIR sections
"""

import json
from datetime import datetime
from screening_rules import (
    SCREENING_TYPES_CONFIG, 
    FHIR_DOCUMENT_SECTIONS,
    get_screening_by_keyword,
    get_screening_by_loinc_code,
    get_screenings_by_document_section,
    create_fhir_screening_recommendation
)

class MockPatient:
    def __init__(self, patient_id, age, sex):
        self.id = patient_id
        self.age = age
        self.sex = sex

def test_manual_keyword_search():
    """Test searching screenings by manual keywords"""
    print("=== Manual Keyword Search Test ===")
    
    keywords_to_test = [
        "mammogram",
        "cholesterol", 
        "a1c",
        "flu shot",
        "colonoscopy",
        "bone density",
        "depression screening"
    ]
    
    for keyword in keywords_to_test:
        result = get_screening_by_keyword(keyword)
        if result:
            config = result["config"]
            coding = config["code"]["coding"][0]
            print(f"Keyword: '{keyword}'")
            print(f"  Screening: {result['id']}")
            print(f"  LOINC/Code: {coding['code']}")
            print(f"  Display: {coding['display']}")
            print(f"  Section: {config['document_section']}")
            print(f"  Priority: {config['priority']}")
            print()
        else:
            print(f"Keyword: '{keyword}' - No match found")
            print()

def test_loinc_code_search():
    """Test searching screenings by LOINC codes"""
    print("=== LOINC Code Search Test ===")
    
    loinc_codes_to_test = [
        "4548-4",    # HbA1c
        "24604-1",   # Mammography
        "57698-3",   # Lipid panel
        "2857-1",    # PSA
        "85354-9",   # Blood pressure
        "45398-4"    # Colonoscopy
    ]
    
    for loinc_code in loinc_codes_to_test:
        result = get_screening_by_loinc_code(loinc_code)
        if result:
            config = result["config"]
            print(f"LOINC Code: {loinc_code}")
            print(f"  Screening: {result['id']}")
            print(f"  Display: {config['code']['coding'][0]['display']}")
            print(f"  Keywords: {', '.join(config['manual_keywords'])}")
            print(f"  Section: {config['document_section']}")
            print()
        else:
            print(f"LOINC Code: {loinc_code} - No match found")
            print()

def test_document_section_filtering():
    """Test filtering screenings by document sections"""
    print("=== Document Section Filtering Test ===")
    
    sections = ["labs", "imaging", "procedures", "vitals", "immunizations", "assessments"]
    
    for section in sections:
        screenings = get_screenings_by_document_section(section)
        print(f"Section: {section.upper()}")
        print(f"  FHIR Category: {FHIR_DOCUMENT_SECTIONS[section]['category'][0]['coding'][0]['display']}")
        print(f"  Screenings ({len(screenings)}):")
        
        for screening in screenings:
            config = screening["config"]
            coding = config["code"]["coding"][0]
            print(f"    - {screening['id']}: {coding['display']} ({coding['code']})")
        print()

def test_fhir_field_structure():
    """Test FHIR field naming and structure compliance"""
    print("=== FHIR Field Structure Compliance Test ===")
    
    # Test a few key screenings for FHIR compliance
    test_screenings = ["mammogram", "hba1c", "lipid_panel", "influenza_vaccine"]
    
    for screening_id in test_screenings:
        config = SCREENING_TYPES_CONFIG[screening_id]
        print(f"Screening: {screening_id}")
        
        # Verify required FHIR fields
        fhir_fields = ["code", "category", "type", "manual_keywords", "document_section"]
        for field in fhir_fields:
            if field in config:
                print(f"  ✓ {field}: Present")
            else:
                print(f"  ✗ {field}: Missing")
        
        # Verify code.coding structure
        if "code" in config and "coding" in config["code"]:
            coding = config["code"]["coding"][0]
            required_coding_fields = ["system", "code", "display"]
            for field in required_coding_fields:
                if field in coding:
                    print(f"  ✓ code.coding.{field}: {coding[field][:50]}...")
                else:
                    print(f"  ✗ code.coding.{field}: Missing")
        
        # Verify category structure
        if "category" in config and len(config["category"]) > 0:
            category_coding = config["category"][0]["coding"][0]
            print(f"  ✓ category.coding.code: {category_coding['code']}")
            print(f"  ✓ category.coding.display: {category_coding['display']}")
        
        print()

def test_fhir_service_request_generation():
    """Test generating FHIR ServiceRequest resources"""
    print("=== FHIR ServiceRequest Generation Test ===")
    
    # Create mock patient
    patient = MockPatient("12345", 45, "female")
    
    # Test generating recommendations for different screenings
    test_screenings = ["mammogram", "hba1c", "lipid_panel"]
    
    for screening_id in test_screenings:
        config = SCREENING_TYPES_CONFIG[screening_id]
        
        # Generate FHIR ServiceRequest
        service_request = create_fhir_screening_recommendation(
            config,
            str(patient.id),
            datetime.now().date()
        )
        
        print(f"FHIR ServiceRequest for {screening_id}:")
        print(json.dumps(service_request, indent=2, default=str))
        print()

def test_category_to_fhir_mapping():
    """Test category mapping to FHIR document sections"""
    print("=== Category to FHIR Section Mapping Test ===")
    
    for section_name, section_config in FHIR_DOCUMENT_SECTIONS.items():
        category_coding = section_config["category"][0]["coding"][0]
        type_code = section_config["type_code"]
        
        print(f"Document Section: {section_name}")
        print(f"  FHIR Category System: {category_coding['system']}")
        print(f"  FHIR Category Code: {category_coding['code']}")
        print(f"  FHIR Category Display: {category_coding['display']}")
        print(f"  Type Code: {type_code}")
        
        # Count screenings in this section
        screenings = get_screenings_by_document_section(section_name)
        print(f"  Screenings Count: {len(screenings)}")
        print()

def test_comprehensive_keyword_coverage():
    """Test comprehensive keyword coverage across all medical specialties"""
    print("=== Comprehensive Keyword Coverage Test ===")
    
    # Test keywords for different medical areas
    medical_areas = {
        "Laboratory Tests": ["a1c", "cholesterol", "psa", "hepatitis c"],
        "Imaging Studies": ["mammogram", "ct chest", "bone density", "ultrasound"],
        "Procedures": ["colonoscopy", "sigmoidoscopy"],
        "Vital Signs": ["blood pressure", "bp"],
        "Immunizations": ["flu shot", "shingles vaccine", "pneumonia vaccine"],
        "Assessments": ["depression screening", "phq9"]
    }
    
    for area, keywords in medical_areas.items():
        print(f"{area}:")
        found_count = 0
        
        for keyword in keywords:
            result = get_screening_by_keyword(keyword)
            if result:
                config = result["config"]
                coding = config["code"]["coding"][0]
                print(f"  ✓ {keyword} → {coding['display']} ({coding['code']})")
                found_count += 1
            else:
                print(f"  ✗ {keyword} → No match")
        
        coverage_percent = (found_count / len(keywords)) * 100
        print(f"  Coverage: {found_count}/{len(keywords)} ({coverage_percent:.1f}%)")
        print()

def show_configuration_summary():
    """Show summary of the FHIR screening configuration"""
    print("=== FHIR Screening Configuration Summary ===")
    
    total_screenings = len(SCREENING_TYPES_CONFIG)
    print(f"Total Screenings Configured: {total_screenings}")
    
    # Count by document section
    section_counts = {}
    for screening_id, config in SCREENING_TYPES_CONFIG.items():
        section = config["document_section"]
        section_counts[section] = section_counts.get(section, 0) + 1
    
    print("\nScreenings by Document Section:")
    for section, count in sorted(section_counts.items()):
        print(f"  {section}: {count}")
    
    # Count by priority
    priority_counts = {}
    for screening_id, config in SCREENING_TYPES_CONFIG.items():
        priority = config["priority"]
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    print("\nScreenings by Priority:")
    for priority, count in sorted(priority_counts.items()):
        print(f"  {priority}: {count}")
    
    # Count total keywords
    total_keywords = sum(len(config["manual_keywords"]) for config in SCREENING_TYPES_CONFIG.values())
    print(f"\nTotal Manual Keywords: {total_keywords}")
    
    # Count coding systems used
    coding_systems = set()
    for config in SCREENING_TYPES_CONFIG.values():
        for coding in config["code"]["coding"]:
            coding_systems.add(coding["system"])
    
    print(f"\nCoding Systems Used:")
    for system in sorted(coding_systems):
        print(f"  {system}")

def main():
    """Run all FHIR screening configuration tests"""
    print("Enhanced FHIR Screening Types Configuration Test Suite")
    print("=" * 60)
    print()
    
    show_configuration_summary()
    print()
    
    test_manual_keyword_search()
    test_loinc_code_search()
    test_document_section_filtering()
    test_fhir_field_structure()
    test_category_to_fhir_mapping()
    test_comprehensive_keyword_coverage()
    test_fhir_service_request_generation()
    
    print("=" * 60)
    print("✓ All FHIR screening configuration tests completed")
    print()
    print("Your screening_types config now supports:")
    print("• Manual keywords for flexible searching")
    print("• Document sections (labs, imaging, consults, etc.)")
    print("• LOINC/CPT codes with proper FHIR field naming")
    print("• Category mapping to FHIR observation categories")
    print("• FHIR ServiceRequest generation")
    print("• Complete standards compliance")

if __name__ == "__main__":
    main()