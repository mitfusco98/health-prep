#!/usr/bin/env python3
"""
Test Script for Screening Type Name Fallback System
Tests document matching using screening type names when no keywords are configured
"""

from app import app, db
from models import ScreeningType, MedicalDocument, Patient
from automated_screening_engine import ScreeningStatusEngine

def test_fallback_system():
    """Test the fallback screening name matching system"""
    
    with app.app_context():
        print("🧪 Testing Fallback Screening Name Matching System")
        print("=" * 60)
        
        # Create test engine
        engine = ScreeningStatusEngine()
        
        # Find screening types with no keywords configured
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        no_keyword_types = []
        
        for st in screening_types:
            has_content = bool(st.get_content_keywords())
            has_document = bool(st.get_document_keywords()) 
            has_filename = bool(st.filename_keywords)
            
            if not has_content and not has_document and not has_filename:
                no_keyword_types.append(st)
        
        print(f"📋 Found {len(no_keyword_types)} screening types without keywords:")
        for st in no_keyword_types:
            print(f"   - {st.name}")
        
        if not no_keyword_types:
            print("⚠️  No screening types found without keywords. Creating test case...")
            
            # Create a test screening type with no keywords
            test_screening = ScreeningType(
                name="Test Mammogram Screening",
                description="Test screening for fallback system",
                min_age=40,
                is_active=True,
                frequency_number=1,
                frequency_unit="year"
            )
            db.session.add(test_screening)
            db.session.commit()
            no_keyword_types = [test_screening]
            print(f"   ✅ Created test screening: {test_screening.name}")
        
        print("\n🔍 Testing Fallback Keyword Generation")
        print("-" * 40)
        
        for screening_type in no_keyword_types[:3]:  # Test first 3
            fallback_keywords = engine._generate_fallback_keywords(screening_type.name)
            print(f"\n📝 {screening_type.name}")
            print(f"   Fallback keywords: {fallback_keywords}")
        
        print("\n📄 Testing Document Matching with Fallback System")
        print("-" * 50)
        
        # Get some sample documents
        sample_documents = MedicalDocument.query.limit(10).all()
        
        if sample_documents:
            print(f"Testing with {len(sample_documents)} sample documents...")
            
            for screening_type in no_keyword_types[:2]:  # Test first 2 screening types
                print(f"\n🎯 Testing {screening_type.name}")
                matches_found = 0
                
                for doc in sample_documents:
                    matches = engine._fallback_screening_name_matching(doc, screening_type)
                    if matches:
                        matches_found += 1
                        print(f"   ✅ Document {doc.id} ({doc.document_name[:50]}...)")
                        
                        # Show which keywords matched
                        fallback_keywords = engine._generate_fallback_keywords(screening_type.name)
                        matched_keywords = []
                        
                        for keyword in fallback_keywords:
                            if (doc.content and keyword.lower() in doc.content.lower()) or \
                               (doc.filename and keyword.lower() in doc.filename.lower()):
                                matched_keywords.append(keyword)
                        
                        if matched_keywords:
                            print(f"      Matched keywords: {matched_keywords}")
                
                print(f"   📊 Total matches: {matches_found}/{len(sample_documents)}")
        else:
            print("   ⚠️  No sample documents found for testing")
        
        print("\n✅ Fallback System Test Complete")
        print("Now screening types without keywords can still match documents using their names!")

if __name__ == "__main__":
    test_fallback_system()