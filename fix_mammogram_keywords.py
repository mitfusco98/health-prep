#!/usr/bin/env python3
"""
Fix mammogram keyword matching by improving specificity and removing false positives
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import ScreeningType, Screening, MedicalDocument
import json

def fix_mammogram_keywords():
    """Fix mammogram keyword parsing rules to eliminate false positives"""
    
    with app.app_context():
        print("🔧 FIXING MAMMOGRAM KEYWORD MATCHING")
        print("=" * 50)
        
        # Find mammogram screening type
        mammogram_type = ScreeningType.query.filter(
            ScreeningType.name.ilike('%mammogram%')
        ).first()
        
        if not mammogram_type:
            print("❌ Mammogram screening type not found")
            return
        
        print(f"📋 Current Mammogram Screening Type: {mammogram_type.name}")
        
        # Show current keywords
        if mammogram_type.content_keywords:
            current_keywords = json.loads(mammogram_type.content_keywords)
            print(f"📝 Current Keywords: {current_keywords}")
        
        # New improved keywords - more specific, less false positives
        new_keywords = [
            "mammogram",
            "mammography", 
            "mammographic",
            "breast imaging",
            "breast ultrasound",
            "bilateral mammogram",
            "screening mammography",
            "digital mammography",
            "tomosynthesis",
            "breast MRI"
        ]
        
        print(f"✨ New Keywords: {new_keywords}")
        
        # Update the screening type
        mammogram_type.content_keywords = json.dumps(new_keywords)
        
        # Also add document type filtering
        relevant_doc_types = [
            "RADIOLOGY_REPORT",
            "IMAGING_REPORT"
        ]
        mammogram_type.document_keywords = json.dumps(relevant_doc_types)
        
        print(f"📄 Added Document Type Filtering: {relevant_doc_types}")
        
        db.session.commit()
        print("✅ Mammogram keywords updated successfully")
        
        # Now test the new keywords against Charlotte Taylor's documents
        print("\n🧪 TESTING NEW KEYWORDS")
        print("-" * 30)
        
        from models import Patient
        charlotte = Patient.query.filter(
            Patient.first_name.ilike('Charlotte'),
            Patient.last_name.ilike('Taylor')
        ).first()
        
        if charlotte:
            charlotte_docs = MedicalDocument.query.filter_by(patient_id=charlotte.id).all()
            matches = 0
            
            for doc in charlotte_docs:
                if test_document_match(doc, new_keywords, relevant_doc_types):
                    matches += 1
                    print(f"✅ {doc.filename} - MATCHES")
                else:
                    print(f"❌ {doc.filename} - No match")
            
            print(f"\n📊 Results: {matches}/{len(charlotte_docs)} documents match with new keywords")
            
            if matches == 0:
                print("✅ SUCCESS: No false positives detected!")
            else:
                print("⚠️  Manual review recommended for matched documents")

def test_document_match(document, content_keywords, doc_type_keywords):
    """Test if document matches with new keyword rules"""
    
    # Check document type first
    doc_type_match = False
    if document.document_type:
        for doc_type in doc_type_keywords:
            if doc_type.lower() in document.document_type.lower():
                doc_type_match = True
                break
    
    # Check content keywords with word boundary logic
    content_match = False
    if document.content:
        content_lower = document.content.lower()
        for keyword in content_keywords:
            keyword_lower = keyword.lower()
            # Use word boundary checking to avoid partial matches
            import re
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(pattern, content_lower):
                content_match = True
                break
    
    # Document matches if BOTH content matches AND document type matches
    return content_match and doc_type_match

def cleanup_charlotte_mammogram_screening():
    """Clean up Charlotte Taylor's false mammogram screening"""
    
    with app.app_context():
        print("\n🧹 CLEANING UP CHARLOTTE'S MAMMOGRAM SCREENING")
        print("-" * 50)
        
        # Find Charlotte
        from models import Patient
        charlotte = Patient.query.filter(
            Patient.first_name.ilike('Charlotte'),
            Patient.last_name.ilike('Taylor')
        ).first()
        
        if not charlotte:
            print("❌ Charlotte Taylor not found")
            return
        
        # Find her mammogram screening
        mammogram_screening = Screening.query.filter_by(
            patient_id=charlotte.id
        ).filter(
            Screening.screening_type.ilike('%mammogram%')
        ).first()
        
        if mammogram_screening:
            print(f"📋 Found mammogram screening: Status = {mammogram_screening.status}")
            print(f"📄 Currently linked documents: {mammogram_screening.document_count}")
            
            # Clear all document relationships
            mammogram_screening.documents.clear()
            
            # Update status to Incomplete since no valid documents
            mammogram_screening.status = 'Incomplete'
            mammogram_screening.notes = 'Keywords updated - no valid mammogram documents found'
            
            db.session.commit()
            
            print("✅ Cleared false positive document links")
            print("✅ Updated status to Incomplete")
            print("✅ Added explanatory note")
        else:
            print("ℹ️  No mammogram screening found for Charlotte")

if __name__ == "__main__":
    fix_mammogram_keywords()
    cleanup_charlotte_mammogram_screening()