"""
Test Script for Enhanced FHIR Document Parser

This demonstrates how your document parser now extracts tags in FHIR format:
{ 'code': { 'coding': [{ 'system': 'http://loinc.org', 'code': '4548-4', 'display': 'Hemoglobin A1C' }] } }
"""

import json
from fhir_document_parser import (
    parse_document_with_fhir_codes,
    get_primary_document_code,
    extract_lab_test_codes_from_text,
    extract_imaging_codes_from_text,
    classify_document_with_fhir_codes
)


def test_lab_result_parsing():
    """Test parsing lab results with FHIR codes"""
    print("=== Lab Result Document Parsing ===")
    
    content = """
    LABORATORY REPORT
    
    Patient: John Smith
    MRN: 12345
    Date: 2024-06-15
    
    Complete Blood Count (CBC):
    - Hemoglobin: 14.2 g/dL (Normal: 12.0-16.0)
    - Hematocrit: 42.1% (Normal: 36-46%)
    - White Blood Cell Count: 7.2 K/uL (Normal: 4.5-11.0)
    
    Hemoglobin A1C: 6.8% (Normal: <5.7%)
    
    Basic Metabolic Panel (BMP):
    - Glucose: 145 mg/dL (Normal: 70-100)
    - Creatinine: 1.1 mg/dL (Normal: 0.7-1.3)
    
    Thyroid Stimulating Hormone (TSH): 2.4 mIU/L (Normal: 0.4-4.0)
    """
    
    filename = "cbc_hba1c_results_2024.pdf"
    
    # Parse document with FHIR codes
    result = parse_document_with_fhir_codes(content, filename)
    
    print(f"Success: {result['success']}")
    print(f"Number of extracted codes: {len(result['extracted_codes'])}")
    print()
    
    print("Extracted FHIR Codes:")
    for i, code_info in enumerate(result['extracted_codes'][:5], 1):  # Show first 5
        code = code_info['code']['coding'][0]
        print(f"{i}. {code['display']}")
        print(f"   System: {code['system']}")
        print(f"   Code: {code['code']}")
        print(f"   Source: {code_info['source']}")
        print(f"   Matched: {code_info['matched_text']}")
        print()
    
    # Get primary document code
    primary = get_primary_document_code(content, filename)
    print("Primary Document Code:")
    primary_coding = primary['code']['coding'][0]
    print(f"Display: {primary_coding['display']}")
    print(f"System: {primary_coding['system']}")
    print(f"Code: {primary_coding['code']}")
    print()
    
    return result


def test_imaging_report_parsing():
    """Test parsing imaging reports with FHIR codes"""
    print("=== Imaging Report Document Parsing ===")
    
    content = """
    RADIOLOGY REPORT
    
    Study: Chest X-Ray
    Patient: Jane Doe
    Date: 2024-06-20
    
    CLINICAL HISTORY:
    Shortness of breath, rule out pneumonia
    
    TECHNIQUE:
    PA and lateral chest radiographs
    
    FINDINGS:
    The lungs are clear bilaterally. No evidence of pneumonia, pleural effusion, or pneumothorax.
    The heart size is normal. No acute cardiopulmonary process.
    
    IMPRESSION:
    Normal chest X-ray
    """
    
    filename = "chest_xray_report_20240620.pdf"
    
    # Parse document with FHIR codes
    result = parse_document_with_fhir_codes(content, filename)
    
    print(f"Success: {result['success']}")
    print(f"Number of extracted codes: {len(result['extracted_codes'])}")
    print()
    
    print("Extracted FHIR Codes:")
    for i, code_info in enumerate(result['extracted_codes'], 1):
        code = code_info['code']['coding'][0]
        print(f"{i}. {code['display']}")
        print(f"   System: {code['system']}")
        print(f"   Code: {code['code']}")
        print(f"   Source: {code_info['source']}")
        print()
    
    return result


def test_clinical_note_parsing():
    """Test parsing clinical notes with FHIR codes"""
    print("=== Clinical Note Document Parsing ===")
    
    content = """
    CARDIOLOGY CONSULTATION NOTE
    
    Patient: Robert Johnson
    Date: 2024-06-25
    
    CHIEF COMPLAINT:
    Chest pain and shortness of breath
    
    HISTORY OF PRESENT ILLNESS:
    Mr. Johnson is a 58-year-old male with a history of hypertension and diabetes who presents 
    with chest pain that started 2 days ago. The pain is substernal, radiating to the left arm.
    
    CARDIOVASCULAR EXAMINATION:
    Heart rate: 88 bpm
    Blood pressure: 145/92 mmHg
    Regular rhythm, no murmurs
    
    ASSESSMENT AND PLAN:
    1. Chest pain - likely angina
       - Order echocardiogram
       - Start cardiac monitoring
    
    2. Diabetes mellitus
       - Continue current medications
       - Check Hemoglobin A1C
    
    Dr. Sarah Wilson, MD
    Cardiology
    """
    
    filename = "cardiology_consult_note.docx"
    
    # Parse document with FHIR codes
    result = parse_document_with_fhir_codes(content, filename)
    
    print(f"Success: {result['success']}")
    print(f"Number of extracted codes: {len(result['extracted_codes'])}")
    print()
    
    print("Extracted FHIR Codes:")
    for i, code_info in enumerate(result['extracted_codes'], 1):
        code = code_info['code']['coding'][0]
        print(f"{i}. {code['display']}")
        print(f"   System: {code['system']}")
        print(f"   Code: {code['code']}")
        print(f"   Source: {code_info['source']}")
        print()
    
    # Show metadata
    metadata = result.get('metadata', {})
    if metadata.get('extracted_providers'):
        print(f"Extracted Providers: {metadata['extracted_providers']}")
    if metadata.get('extracted_dates'):
        print(f"Extracted Dates: {metadata['extracted_dates']}")
    print()
    
    return result


def test_filename_only_parsing():
    """Test parsing based on filename only"""
    print("=== Filename-Only Parsing ===")
    
    filenames = [
        "hba1c_results_lab_2024.pdf",
        "chest_ct_scan_report.pdf", 
        "mri_brain_with_contrast.pdf",
        "discharge_summary_hospital.docx",
        "cardiology_consultation_note.pdf",
        "mammography_screening_2024.pdf"
    ]
    
    for filename in filenames:
        primary = get_primary_document_code("", filename)
        coding = primary['code']['coding'][0]
        print(f"Filename: {filename}")
        print(f"  Code: {coding['code']} - {coding['display']}")
        print(f"  System: {coding['system'].split('/')[-1]}")
        print()


def test_specific_extraction_functions():
    """Test specific extraction functions"""
    print("=== Specific Extraction Function Tests ===")
    
    lab_content = "Patient had CBC, Lipid Panel, and Hemoglobin A1C tests performed."
    lab_codes = extract_lab_test_codes_from_text(lab_content)
    
    print("Lab Test Codes Extracted:")
    for code_info in lab_codes:
        code = code_info['code']['coding'][0]
        print(f"  {code['display']} ({code['code']})")
    print()
    
    imaging_content = "Chest X-ray shows clear lungs. MRI of brain recommended."
    imaging_codes = extract_imaging_codes_from_text(imaging_content)
    
    print("Imaging Codes Extracted:")
    for code_info in imaging_codes:
        code = code_info['code']['coding'][0]
        print(f"  {code['display']} ({code['code']})")
    print()


def test_backward_compatibility():
    """Test backward compatibility with existing classify_document function"""
    print("=== Backward Compatibility Test ===")
    
    content = "Laboratory results show elevated glucose and abnormal lipid panel."
    filename = "lab_results.pdf"
    
    # Use enhanced function that maintains compatibility
    doc_type, metadata = classify_document_with_fhir_codes(content, filename)
    
    print(f"Document Type: {doc_type}")
    print(f"FHIR Codes in Metadata: {len(metadata.get('fhir_codes', []))}")
    
    if metadata.get('primary_fhir_code'):
        primary_coding = metadata['primary_fhir_code']['coding'][0]
        print(f"Primary FHIR Code: {primary_coding['display']} ({primary_coding['code']})")
    print()


def test_complex_document():
    """Test parsing a complex document with multiple elements"""
    print("=== Complex Document Parsing ===")
    
    content = """
    COMPREHENSIVE MEDICAL REPORT
    
    Patient: Michael Davis
    MRN: MRN123456789
    Date: June 28, 2024
    Provider: Dr. Jennifer Martinez, MD
    
    CHIEF COMPLAINT:
    Annual physical examination
    
    LABORATORY RESULTS:
    Complete Blood Count (CBC):
    - WBC: 6.8 K/uL
    - Hemoglobin: 15.1 g/dL
    - Platelets: 245 K/uL
    
    Comprehensive Metabolic Panel (CMP):
    - Glucose: 98 mg/dL
    - Creatinine: 0.9 mg/dL
    
    Lipid Panel:
    - Total Cholesterol: 185 mg/dL
    - HDL: 55 mg/dL
    - LDL: 110 mg/dL
    
    Hemoglobin A1C: 5.4%
    
    Thyroid Function:
    - TSH: 1.8 mIU/L
    
    IMAGING STUDIES:
    Chest X-ray: Clear lungs, normal heart size
    
    VITAL SIGNS:
    BP: 128/78 mmHg
    HR: 72 bpm
    Temp: 98.6°F
    Weight: 175 lbs
    Height: 5'10"
    
    ASSESSMENT:
    1. Healthy adult male
    2. Optimal cardiovascular health
    3. Normal laboratory values
    
    PLAN:
    Continue current lifestyle
    Return in 1 year for routine follow-up
    """
    
    filename = "comprehensive_annual_physical_exam.pdf"
    
    # Parse document
    result = parse_document_with_fhir_codes(content, filename)
    
    print(f"Success: {result['success']}")
    print(f"Total extracted codes: {len(result['extracted_codes'])}")
    print()
    
    # Group codes by system
    loinc_codes = []
    snomed_codes = []
    
    for code_info in result['extracted_codes']:
        code = code_info['code']['coding'][0]
        if 'loinc' in code['system']:
            loinc_codes.append(code)
        elif 'snomed' in code['system']:
            snomed_codes.append(code)
    
    print(f"LOINC Codes Found: {len(loinc_codes)}")
    for code in loinc_codes[:5]:  # Show first 5
        print(f"  {code['code']}: {code['display']}")
    
    print(f"\nSNOMED CT Codes Found: {len(snomed_codes)}")
    for code in snomed_codes:
        print(f"  {code['code']}: {code['display']}")
    
    # Show metadata
    metadata = result.get('metadata', {})
    if metadata.get('document_stats'):
        stats = metadata['document_stats']
        print(f"\nDocument Statistics:")
        print(f"  Word Count: {stats['word_count']}")
        print(f"  Sentence Count: {stats['sentence_count']}")
        print(f"  Complexity: {stats['estimated_complexity']}")
    
    if metadata.get('extracted_providers'):
        print(f"  Providers: {metadata['extracted_providers']}")
    
    if metadata.get('extracted_mrn'):
        print(f"  MRN: {metadata['extracted_mrn']}")
    
    return result


def main():
    """Run all FHIR document parser tests"""
    print("🔬 Enhanced Document Parser with FHIR Code.Coding Format")
    print("=" * 65)
    print()
    
    # Run all tests
    test_lab_result_parsing()
    test_imaging_report_parsing()
    test_clinical_note_parsing()
    test_filename_only_parsing()
    test_specific_extraction_functions()
    test_backward_compatibility()
    complex_result = test_complex_document()
    
    # Summary
    print("=" * 65)
    print("✅ Enhanced Document Parser Tests Complete")
    print()
    print("Your document parser now extracts tags in FHIR format:")
    print("  • Lab tests → LOINC codes (HbA1c: 4548-4, CBC: 58410-2)")
    print("  • Imaging → LOINC codes (Chest X-ray: 36643-5, CT: 18748-4)")
    print("  • Specialties → SNOMED CT codes (Cardiology: 394579002)")
    print("  • Documents → LOINC codes (Progress Note: 11506-3)")
    print()
    print("Format: { 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }")
    print()
    print("Functions available:")
    print("  • parse_document_with_fhir_codes() - Full parsing with all codes")
    print("  • get_primary_document_code() - Single primary code only") 
    print("  • extract_lab_test_codes_from_text() - Lab codes only")
    print("  • extract_imaging_codes_from_text() - Imaging codes only")
    
    return True


if __name__ == "__main__":
    main()