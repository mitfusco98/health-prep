#!/usr/bin/env python3
"""
Test Charlotte Taylor's documents with the enhanced keyword matcher
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Patient, MedicalDocument, ScreeningType
from enhanced_keyword_matcher import EnhancedKeywordMatcher
import json

def test_charlotte_with_new_system():
    """Test Charlotte's documents with enhanced phrase matching"""
    
    with app.app_context():
        print("🔍 TESTING CHARLOTTE TAYLOR WITH ENHANCED PHRASE MATCHING")
        print("=" * 60)
        
        # Get Charlotte
        charlotte = Patient.query.filter(
            Patient.first_name.ilike('Charlotte'),
            Patient.last_name.ilike('Taylor')
        ).first()
        
        if not charlotte:
            print("❌ Charlotte Taylor not found")
            return
        
        # Get mammogram screening type with new keywords
        mammogram_type = ScreeningType.query.filter(
            ScreeningType.name.ilike('%mammogram%')
        ).first()
        
        if not mammogram_type:
            print("❌ Mammogram screening type not found")
            return
        
        # Get the updated keywords
        keywords = json.loads(mammogram_type.content_keywords)
        doc_type_keywords = json.loads(mammogram_type.document_keywords) if mammogram_type.document_keywords else []
        
        print(f"👤 Patient: {charlotte.first_name} {charlotte.last_name}")
        print(f"📋 Mammogram Keywords: {keywords}")
        print(f"📄 Document Type Filter: {doc_type_keywords}")
        print()
        
        # Get Charlotte's documents
        docs = MedicalDocument.query.filter_by(patient_id=charlotte.id).all()
        
        matcher = EnhancedKeywordMatcher()
        
        matches_found = 0
        legitimate_matches = []
        
        for i, doc in enumerate(docs, 1):
            print(f"📄 Document {i}: {doc.filename}")
            print(f"    Type: {doc.document_type}")
            print(f"    Content Length: {len(doc.content) if doc.content else 0}")
            
            # Test content matching
            content_result = matcher.match_keywords_in_content(doc.content or "", keywords)
            
            # Test document type matching
            doc_type_match = False
            if doc_type_keywords and doc.document_type:
                doc_type_match = any(dt.lower() in doc.document_type.lower() for dt in doc_type_keywords)
            
            # Overall match logic (content match AND doc type match if filter exists)
            has_doc_type_filter = len(doc_type_keywords) > 0
            
            if has_doc_type_filter:
                overall_match = content_result['is_match'] and doc_type_match
            else:
                overall_match = content_result['is_match']
            
            if overall_match:
                matches_found += 1
                legitimate_matches.append(doc)
                print(f"    ✅ MATCHES MAMMOGRAM SCREENING")
                print(f"    🎯 Content Match: {content_result['is_match']}")
                print(f"    📁 Doc Type Match: {doc_type_match}")
                
                if content_result['matched_keywords']:
                    print(f"    🔍 Matched Keywords: {content_result['matched_keywords']}")
                    for context in content_result['match_contexts']:
                        print(f"    📝 Context: {context['context'][:100]}...")
            else:
                print(f"    ❌ No match")
                if content_result['is_match']:
                    print(f"    ⚠️  Content matched but wrong document type")
                
            print()
        
        print(f"📊 FINAL RESULTS:")
        print(f"    Documents analyzed: {len(docs)}")
        print(f"    Legitimate matches: {matches_found}")
        
        if matches_found == 0:
            print(f"    ✅ SUCCESS: No false positives! Enhanced matching works correctly.")
        else:
            print(f"    ⚠️  Found {matches_found} matches - reviewing for legitimacy:")
            for doc in legitimate_matches:
                print(f"       • {doc.filename} ({doc.document_type})")
        
        return matches_found == 0

if __name__ == "__main__":
    test_charlotte_with_new_system()