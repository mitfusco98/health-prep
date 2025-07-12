#!/usr/bin/env python3
"""
Test phrase matching specifically for medical contexts
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_keyword_matcher import EnhancedKeywordMatcher

def test_medical_phrases():
    """Test phrase matching with medical examples"""
    
    matcher = EnhancedKeywordMatcher()
    
    # Test cases that should match "breast US"
    positive_cases = [
        "Patient underwent breast US examination today",
        "Breast-US shows normal findings", 
        "Follow-up breast_US recommended",
        "BREAST US RESULTS: Normal",
        "breast US imaging completed"
    ]
    
    # Test cases that should NOT match "breast US" 
    negative_cases = [
        "Patient has suspicious lesions identified",  # Contains "US" in "suspicious" 
        "Average risk patient, age appropriate",      # Contains "US" in words
        "OUTPATIENT PROCEDURE SUMMARY",               # Contains "US" in words
        "All routine procedures performed",           # Contains "US" in words
        "Status update provided to family"           # Contains "US" in "Status"
    ]
    
    keywords = ["breast US"]
    
    print("🧪 TESTING PHRASE MATCHING FOR 'breast US'")
    print("=" * 50)
    
    print("\n✅ SHOULD MATCH (breast US contexts):")
    for i, text in enumerate(positive_cases, 1):
        result = matcher.match_keywords_in_content(text, keywords)
        status = "✅ PASS" if result['is_match'] else "❌ FAIL"
        print(f"{i}. {status} - '{text}'")
        if result['is_match']:
            for context in result['match_contexts']:
                print(f"   Match: '{context['keyword']}' ({context['match_type']})")
    
    print("\n❌ SHOULD NOT MATCH (false positive cases):")
    for i, text in enumerate(negative_cases, 1):
        result = matcher.match_keywords_in_content(text, keywords)
        status = "✅ PASS" if not result['is_match'] else "❌ FAIL"
        print(f"{i}. {status} - '{text}'")
        if result['is_match']:
            print(f"   ⚠️  Unexpected match detected!")
            for context in result['match_contexts']:
                print(f"   Match: '{context['keyword']}' ({context['match_type']})")

def test_charlotte_specific_content():
    """Test with Charlotte Taylor's actual document content"""
    
    matcher = EnhancedKeywordMatcher()
    
    # Sample content from Charlotte's documents that previously matched "US"
    charlotte_samples = [
        ("gastroenterology", "Reason: Colorectal cancer screening discussion History: Average risk patient, age appropriate"),
        ("dermatology", "Full body skin examination performed Findings: No suspicious lesions identified"),
        ("procedure", "OUTPATIENT PROCEDURE SUMMARY Date: August 28, 2024 Procedure: Routine screening"),
        ("vaccination", "Influenza vaccine: Administered COVID-19 status: Up to date All routine procedures"),
        ("gynecology", "GYNECOLOGY CONSULTATION Date: August 29, 2024 Reason: Annual gynecological examination")
    ]
    
    keywords = ["breast US", "mammogram", "breast imaging"]
    
    print("\n\n🔍 TESTING CHARLOTTE'S DOCUMENT CONTENT")
    print("=" * 50)
    
    for doc_type, content in charlotte_samples:
        result = matcher.match_keywords_in_content(content, keywords)
        status = "Match" if result['is_match'] else "No match"
        print(f"\n📄 {doc_type.title()} Document:")
        print(f"   Content: {content[:80]}...")
        print(f"   Result: {status}")
        
        if result['is_match']:
            print(f"   ⚠️  Unexpected match found!")
            for context in result['match_contexts']:
                print(f"   Trigger: '{context['keyword']}'")
        else:
            print(f"   ✅ Correctly filtered out")

if __name__ == "__main__":
    test_medical_phrases()
    test_charlotte_specific_content()