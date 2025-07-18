#!/usr/bin/env python3
"""
Comprehensive Keyword Diagnostic Tool
Analyzes keyword triggers for document matching in screening system
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Screening, MedicalDocument, Patient, ScreeningType
# Import classes properly  
try:
    from unified_screening_engine import unified_engine
except ImportError:
    ScreeningEngine = None

try:
    from document_screening_matcher import DocumentScreeningMatcher
except ImportError:
    DocumentScreeningMatcher = None
from datetime import datetime
import re

class KeywordDiagnosticTool:
    def __init__(self):
        self.engine = unified_engine if ScreeningEngine else None
        self.matcher = DocumentScreeningMatcher() if DocumentScreeningMatcher else None
    
    def analyze_patient_screening(self, patient_name, screening_type_name=None):
        """Analyze keyword matches for a specific patient"""
        print(f"\n🔍 KEYWORD ANALYSIS FOR: {patient_name}")
        print("=" * 60)
        
        # Find patient
        patient = Patient.query.filter(
            (Patient.first_name + ' ' + Patient.last_name).ilike(f'%{patient_name}%')
        ).first()
        
        if not patient:
            print(f"❌ Patient '{patient_name}' not found")
            return
        
        print(f"📋 Patient: {patient.first_name} {patient.last_name} (ID: {patient.id})")
        
        # Get all documents for this patient
        documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()
        print(f"📄 Total Documents: {len(documents)}")
        
        # Get screening types to analyze
        if screening_type_name:
            screening_types = ScreeningType.query.filter(
                ScreeningType.name.ilike(f'%{screening_type_name}%')
            ).all()
        else:
            screening_types = ScreeningType.query.all()
        
        for screening_type in screening_types:
            self._analyze_screening_type_for_patient(patient, screening_type, documents)
    
    def _analyze_screening_type_for_patient(self, patient, screening_type, documents):
        """Analyze a specific screening type for a patient"""
        print(f"\n🎯 SCREENING TYPE: {screening_type.name}")
        print("-" * 40)
        
        # Show parsing rules
        self._display_parsing_rules(screening_type)
        
        # Analyze each document
        matched_documents = []
        for doc in documents:
            match_details = self._analyze_document_match(doc, screening_type)
            if match_details['is_match']:
                matched_documents.append((doc, match_details))
        
        print(f"\n📊 MATCH RESULTS:")
        print(f"   Total Documents Checked: {len(documents)}")
        print(f"   Documents Matched: {len(matched_documents)}")
        
        if matched_documents:
            print(f"\n📁 MATCHED DOCUMENTS:")
            for i, (doc, details) in enumerate(matched_documents, 1):
                print(f"\n   {i}. {doc.filename or doc.document_name or 'Unnamed Document'}")
                print(f"      Document ID: {doc.id}")
                print(f"      Document Type: {doc.document_type or 'Not specified'}")
                print(f"      Created: {doc.created_at}")
                print(f"      Match Triggers:")
                for trigger in details['triggers']:
                    print(f"        • {trigger}")
                if details['matched_content']:
                    print(f"      Content Excerpt: {details['matched_content'][:100]}...")
        else:
            print("   ❌ No documents matched this screening type")
    
    def _display_parsing_rules(self, screening_type):
        """Display the parsing rules for a screening type"""
        print(f"📋 PARSING RULES:")
        
        # Content keywords
        if screening_type.content_keywords:
            try:
                content_kw = json.loads(screening_type.content_keywords)
                print(f"   Content Keywords: {content_kw}")
            except:
                print(f"   Content Keywords: {screening_type.content_keywords}")
        else:
            print(f"   Content Keywords: None")
        
        # Document type keywords  
        if screening_type.document_keywords:
            try:
                doc_kw = json.loads(screening_type.document_keywords)
                print(f"   Document Type Keywords: {doc_kw}")
            except:
                print(f"   Document Type Keywords: {screening_type.document_keywords}")
        else:
            print(f"   Document Type Keywords: None")
        
        # Filename keywords
        if screening_type.filename_keywords:
            try:
                filename_kw = json.loads(screening_type.filename_keywords)
                print(f"   Filename Keywords: {filename_kw}")
            except:
                print(f"   Filename Keywords: {screening_type.filename_keywords}")
        else:
            print(f"   Filename Keywords: None")
    
    def _analyze_document_match(self, document, screening_type):
        """Analyze if and why a document matches a screening type"""
        match_details = {
            'is_match': False,
            'triggers': [],
            'matched_content': None
        }
        
        # Check content keywords
        if screening_type.content_keywords:
            try:
                content_keywords = json.loads(screening_type.content_keywords)
                if document.content:
                    for keyword in content_keywords:
                        if keyword.lower() in document.content.lower():
                            match_details['is_match'] = True
                            match_details['triggers'].append(f"Content keyword: '{keyword}'")
                            # Find the context around the keyword
                            content_lower = document.content.lower()
                            keyword_lower = keyword.lower()
                            start_idx = content_lower.find(keyword_lower)
                            if start_idx != -1:
                                start = max(0, start_idx - 50)
                                end = min(len(document.content), start_idx + len(keyword) + 50)
                                match_details['matched_content'] = document.content[start:end]
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Check document type keywords
        if screening_type.document_keywords:
            try:
                doc_keywords = json.loads(screening_type.document_keywords)
                if document.document_type:
                    for keyword in doc_keywords:
                        if keyword.lower() in document.document_type.lower():
                            match_details['is_match'] = True
                            match_details['triggers'].append(f"Document type keyword: '{keyword}' (in '{document.document_type}')")
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Check filename keywords
        if screening_type.filename_keywords:
            try:
                filename_keywords = json.loads(screening_type.filename_keywords)
                if document.filename:
                    for keyword in filename_keywords:
                        if keyword.lower() in document.filename.lower():
                            match_details['is_match'] = True
                            match_details['triggers'].append(f"Filename keyword: '{keyword}' (in '{document.filename}')")
            except (json.JSONDecodeError, TypeError):
                pass
        
        return match_details
    
    def analyze_all_screening_types(self):
        """Analyze all screening types and their parsing rules"""
        print("\n🎯 ALL SCREENING TYPES ANALYSIS")
        print("=" * 50)
        
        screening_types = ScreeningType.query.all()
        
        for screening_type in screening_types:
            print(f"\n📋 {screening_type.name}")
            print("-" * 30)
            self._display_parsing_rules(screening_type)
            
            # Count documents that would match
            all_documents = MedicalDocument.query.all()
            match_count = 0
            for doc in all_documents:
                if self._analyze_document_match(doc, screening_type)['is_match']:
                    match_count += 1
            
            print(f"   📊 Documents matched across all patients: {match_count}")
    
    def analyze_document_coverage(self):
        """Analyze which documents are covered by screening types"""
        print("\n📄 DOCUMENT COVERAGE ANALYSIS")
        print("=" * 40)
        
        all_documents = MedicalDocument.query.all()
        screening_types = ScreeningType.query.all()
        
        covered_docs = set()
        uncovered_docs = []
        
        for doc in all_documents:
            is_covered = False
            for screening_type in screening_types:
                if self._analyze_document_match(doc, screening_type)['is_match']:
                    covered_docs.add(doc.id)
                    is_covered = True
                    break
            
            if not is_covered:
                uncovered_docs.append(doc)
        
        print(f"📊 COVERAGE STATISTICS:")
        print(f"   Total Documents: {len(all_documents)}")
        print(f"   Covered by Screening Types: {len(covered_docs)}")
        print(f"   Not Covered: {len(uncovered_docs)}")
        print(f"   Coverage Rate: {len(covered_docs)/len(all_documents)*100:.1f}%")
        
        if uncovered_docs:
            print(f"\n📂 UNCOVERED DOCUMENTS:")
            for doc in uncovered_docs[:10]:  # Show first 10
                print(f"   • {doc.filename or doc.document_name or 'Unnamed'} (Type: {doc.document_type or 'None'})")
                if doc.content:
                    print(f"     Content preview: {doc.content[:100]}...")
    
    def charlotte_taylor_deep_dive(self):
        """Specific analysis for Charlotte Taylor's mammogram screening"""
        print("\n🔍 CHARLOTTE TAYLOR MAMMOGRAM DEEP DIVE")
        print("=" * 50)
        
        # Find Charlotte Taylor
        charlotte = Patient.query.filter(
            Patient.first_name.ilike('Charlotte'),
            Patient.last_name.ilike('Taylor')
        ).first()
        
        if not charlotte:
            print("❌ Charlotte Taylor not found")
            return
        
        # Find mammogram screening type
        mammogram_type = ScreeningType.query.filter(
            ScreeningType.name.ilike('%mammogram%')
        ).first()
        
        if not mammogram_type:
            print("❌ Mammogram screening type not found")
            return
        
        print(f"👤 Patient: {charlotte.first_name} {charlotte.last_name}")
        print(f"📋 Screening: {mammogram_type.name}")
        
        # Get Charlotte's documents
        charlotte_docs = MedicalDocument.query.filter_by(patient_id=charlotte.id).all()
        print(f"📄 Charlotte's Total Documents: {len(charlotte_docs)}")
        
        # Analyze mammogram parsing rules in detail
        print(f"\n📋 MAMMOGRAM PARSING RULES:")
        self._display_parsing_rules(mammogram_type)
        
        # Analyze each of Charlotte's documents against mammogram rules
        print(f"\n📊 DOCUMENT-BY-DOCUMENT ANALYSIS:")
        matched_count = 0
        
        for i, doc in enumerate(charlotte_docs, 1):
            match_details = self._analyze_document_match(doc, mammogram_type)
            
            print(f"\n   📄 Document {i}: {doc.filename or doc.document_name or 'Unnamed'}")
            print(f"      ID: {doc.id}")
            print(f"      Type: {doc.document_type or 'Not specified'}")
            print(f"      Created: {doc.created_at}")
            
            if match_details['is_match']:
                matched_count += 1
                print(f"      ✅ MATCHES MAMMOGRAM SCREENING")
                print(f"      🎯 Triggers:")
                for trigger in match_details['triggers']:
                    print(f"         • {trigger}")
                if match_details['matched_content']:
                    print(f"      📝 Content Context: {match_details['matched_content']}")
            else:
                print(f"      ❌ Does not match mammogram screening")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Documents analyzed: {len(charlotte_docs)}")
        print(f"   Documents matching mammogram: {matched_count}")
        
        # Check current screening record
        current_screening = Screening.query.filter_by(
            patient_id=charlotte.id,
            screening_type=mammogram_type.name
        ).first()
        
        if current_screening:
            print(f"\n📋 CURRENT SCREENING RECORD:")
            print(f"   Status: {current_screening.status}")
            print(f"   Linked Documents: {current_screening.document_count}")
            print(f"   Last Updated: {current_screening.updated_at}")

def main():
    """Main function"""
    with app.app_context():
        tool = KeywordDiagnosticTool()
        
        # Run Charlotte Taylor deep dive
        tool.charlotte_taylor_deep_dive()
        
        # Run general analysis for Charlotte Taylor
        print("\n" + "="*80)
        tool.analyze_patient_screening("Charlotte Taylor")
        
        # Show all screening types
        print("\n" + "="*80)
        tool.analyze_all_screening_types()

if __name__ == "__main__":
    main()