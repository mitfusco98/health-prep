
#!/usr/bin/env python3
"""
Screening Diagnostic Helper
Helps identify why documents are matching to screenings when they shouldn't
"""

from models import ScreeningType, MedicalDocument, Patient
from automated_screening_engine import ScreeningStatusEngine
import json

def diagnose_pap_smear_matches(patient_id=None):
    """Diagnose Pap smear screening matches for a specific patient or all patients"""
    
    # Get Pap smear screening type
    pap_smear = ScreeningType.query.filter_by(name='Pap Smear').first()
    if not pap_smear:
        print("❌ Pap Smear screening type not found")
        return
    
    print(f"🔍 Analyzing Pap Smear screening configuration:")
    print(f"  All keywords: {pap_smear.get_all_keywords()}")
    print(f"  Content keywords: {pap_smear.get_content_keywords()}")
    print(f"  Document keywords: {pap_smear.get_document_keywords()}")
    
    # Get patient(s) to analyze
    if patient_id:
        patients = [Patient.query.get(patient_id)]
    else:
        patients = Patient.query.limit(5).all()  # Analyze first 5 patients
    
    engine = ScreeningStatusEngine()
    
    for patient in patients:
        if not patient:
            continue
            
        print(f"\n👤 Patient: {patient.full_name} (ID: {patient.id})")
        
        # Get all documents for this patient
        documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
        print(f"  Total documents: {len(documents)}")
        
        matching_docs = []
        non_matching_docs = []
        
        for doc in documents:
            matches = engine._document_matches_screening(doc, pap_smear)
            
            if matches:
                matching_docs.append(doc)
                print(f"  ✅ MATCH: {doc.filename or 'Unnamed'} (Type: {doc.document_type})")
                
                # Show why it matched
                content_has_keywords = False
                filename_has_keywords = False
                doc_type_has_keywords = False
                
                if pap_smear.get_all_keywords() and doc.content:
                    for keyword in pap_smear.get_all_keywords():
                        if keyword.lower() in doc.content.lower():
                            content_has_keywords = True
                            print(f"    📄 Content contains: '{keyword}'")
                
                if pap_smear.get_all_keywords() and doc.filename:
                    for keyword in pap_smear.get_all_keywords():
                        if keyword.lower() in doc.filename.lower():
                            filename_has_keywords = True
                            print(f"    📁 Filename contains: '{keyword}'")
                
                if pap_smear.get_all_keywords() and doc.document_type:
                    for keyword in pap_smear.get_all_keywords():
                        if keyword.lower() in doc.document_type.lower():
                            doc_type_has_keywords = True
                            print(f"    📋 Document type contains: '{keyword}'")
                
            else:
                non_matching_docs.append(doc)
        
        print(f"  📊 Summary: {len(matching_docs)} matches, {len(non_matching_docs)} non-matches")
        
        if matching_docs:
            print(f"  ⚠️  POTENTIAL FALSE POSITIVES:")
            for doc in matching_docs:
                print(f"    - {doc.filename or 'Unnamed'} ({doc.document_type})")

def fix_pap_smear_configuration():
    """Fix Pap smear configuration to be more specific"""
    
    pap_smear = ScreeningType.query.filter_by(name='Pap Smear').first()
    if not pap_smear:
        print("❌ Pap Smear screening type not found")
        return
    
    # More specific keywords that are less likely to produce false positives
    specific_content_keywords = [
        "pap smear",
        "papanicolaou",
        "cervical cytology",
        "cervical screening",
        "pap test",
        "cervical cancer screening",
        "cytologic examination",
        "cervical specimen"
    ]
    
    # Require specific document types
    specific_document_keywords = [
        "Lab Report",
        "Pathology Report",
        "Cytology Report"
    ]
    
    print("🔧 Updating Pap smear configuration...")
    print(f"  New content keywords: {specific_content_keywords}")
    print(f"  New document keywords: {specific_document_keywords}")
    
    pap_smear.set_content_keywords(specific_content_keywords)
    pap_smear.set_document_keywords(specific_document_keywords)
    
    from app import db
    db.session.commit()
    
    print("✅ Pap smear configuration updated")

if __name__ == "__main__":
    print("Pap Smear Diagnostic Tool")
    print("1. Analyze current matches")
    diagnose_pap_smear_matches()
    
    print("\n2. Fix configuration (uncomment to apply)")
    # fix_pap_smear_configuration()
