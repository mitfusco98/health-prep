#!/usr/bin/env python3

import re
import json

# Enhanced document parser that returns tags in FHIR code.coding format
def extract_tags_in_fhir_format(content, filename=None):
    """
    Extract tags from document content/filename and return in FHIR format:
    { 'code': { 'coding': [{ 'system': 'http://loinc.org', 'code': '4548-4', 'display': 'Hemoglobin A1C' }] } }
    """
    
    # LOINC codes for common lab tests
    lab_patterns = {
        r'hemoglobin\s+a1?c|hba1c': {
            'system': 'http://loinc.org',
            'code': '4548-4', 
            'display': 'Hemoglobin A1c/Hemoglobin.total in Blood'
        },
        r'complete\s+blood\s+count|cbc': {
            'system': 'http://loinc.org',
            'code': '58410-2',
            'display': 'Complete blood count (hemogram) panel - Blood by Automated count'
        },
        r'basic\s+metabolic\s+panel|bmp': {
            'system': 'http://loinc.org', 
            'code': '51990-0',
            'display': 'Basic metabolic panel - Blood'
        },
        r'lipid\s+panel': {
            'system': 'http://loinc.org',
            'code': '57698-3',
            'display': 'Lipid panel with direct LDL - Serum or Plasma'
        }
    }
    
    # Check content and filename
    text_to_check = content.lower()
    if filename:
        text_to_check += " " + filename.lower()
    
    # Find matching patterns
    for pattern, coding in lab_patterns.items():
        if re.search(pattern, text_to_check):
            return {
                'code': {
                    'coding': [coding]
                }
            }
    
    # Default if no match
    return {
        'code': {
            'coding': [{
                'system': 'http://loinc.org',
                'code': '34133-9',
                'display': 'Summarization of episode note'
            }]
        }
    }

# Test cases
print("Enhanced Document Parser - FHIR Code.Coding Format")
print("=" * 55)

# Test 1: HbA1c extraction
content1 = "Patient lab results show elevated Hemoglobin A1C at 7.2%"
result1 = extract_tags_in_fhir_format(content1)
print("\nTest 1 - HbA1c Content:")
print(f"Input: {content1}")
print("Output:")
print(json.dumps(result1, indent=2))

# Test 2: Filename extraction  
filename2 = "hba1c_lab_results_2024.pdf"
result2 = extract_tags_in_fhir_format("", filename2)
print(f"\nTest 2 - HbA1c Filename:")
print(f"Input: {filename2}")
print("Output:")
print(json.dumps(result2, indent=2))

# Test 3: CBC extraction
content3 = "Complete Blood Count shows normal values"
result3 = extract_tags_in_fhir_format(content3)
print(f"\nTest 3 - CBC Content:")
print(f"Input: {content3}")
print("Output:")
print(json.dumps(result3, indent=2))

# Test 4: BMP extraction
content4 = "Basic Metabolic Panel results available"
result4 = extract_tags_in_fhir_format(content4)
print(f"\nTest 4 - BMP Content:")
print(f"Input: {content4}")
print("Output:")
print(json.dumps(result4, indent=2))

# Test 5: Default case
content5 = "General medical document"
result5 = extract_tags_in_fhir_format(content5)
print(f"\nTest 5 - Default Case:")
print(f"Input: {content5}")
print("Output:")
print(json.dumps(result5, indent=2))

print("\n" + "=" * 55)
print("✓ Parser returns tags in exact FHIR format:")
print("{ 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }")