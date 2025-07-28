#!/usr/bin/env python3
"""
Prep Sheet Hyperlink Demo
Demonstrates the enhanced prep sheet with medical document hyperlinks
controlled by data cutoff configuration from /screenings?tab=checklist
"""

from app import app, db
from models import Patient, MedicalDocument, ChecklistSettings
from checklist_routes import get_or_create_settings
from medical_data_parser import MedicalDataParser

def demo_prep_sheet_hyperlinks():
    """Demo the enhanced prep sheet hyperlink functionality"""
    
    with app.app_context():
        print("🔗 Prep Sheet Medical Document Hyperlinks Demo")
        print("=" * 60)
        
        # Get or create checklist settings
        settings = get_or_create_settings()
        
        print("\n1. Current Data Cutoff Configuration:")
        print("-" * 50)
        print(f"Laboratories cutoff: {settings.labs_cutoff_months} months")
        print(f"Imaging cutoff: {settings.imaging_cutoff_months} months")
        print(f"Consults cutoff: {settings.consults_cutoff_months} months")
        print(f"Hospital visits cutoff: {settings.hospital_cutoff_months} months")
        
        # Get sample patient with documents
        patient = Patient.query.first()
        if not patient:
            print("\n❌ No patients found in database")
            return
            
        print(f"\n2. Testing with Patient: {patient.first_name} {patient.last_name}")
        print("-" * 50)
        
        # Initialize medical data parser with cutoff settings
        data_parser = MedicalDataParser(patient.id, settings)
        filtered_medical_data = data_parser.get_all_filtered_data()
        
        # Show filtered documents by subsection
        subsections = ['labs', 'imaging', 'consults', 'hospital_visits']
        
        for subsection in subsections:
            subsection_data = filtered_medical_data.get(subsection, {})
            documents = subsection_data.get('documents', [])
            cutoff_months = subsection_data.get('cutoff_months', 'N/A')
            
            print(f"\n{subsection.title().replace('_', ' ')} Section:")
            print(f"  Cutoff: {cutoff_months} months")
            print(f"  Documents found: {len(documents)}")
            
            if documents:
                for i, doc in enumerate(documents[:3], 1):
                    doc_name = doc.document_name or doc.filename or f'Document {doc.id}'
                    upload_date = doc.upload_date.strftime('%Y-%m-%d') if doc.upload_date else 'Unknown'
                    hyperlink_url = f"/documents/{doc.id}"
                    print(f"    {i}. {doc_name} ({upload_date}) → {hyperlink_url}")
                    
                if len(documents) > 3:
                    print(f"    ... and {len(documents) - 3} more documents")
            else:
                print("    No documents within cutoff period")
        
        print("\n3. Hyperlink Features:")
        print("-" * 50)
        print("✅ Documents display as clickable badges in prep sheet")
        print("✅ Badge format: [Document Name (MM/DD/YYYY)]")
        print("✅ Tooltips show full document name and upload date")
        print("✅ Links open in new tab with return_to parameter")
        print("✅ Eligibility controlled by data cutoff configuration")
        print("✅ Maximum 3 documents shown per subsection with '...more' indicator")
        
        print("\n4. Data Cutoff Configuration Access:")
        print("-" * 50)
        print("📊 Configure cutoffs at: /screenings?tab=checklist")
        print("📊 Data Cutoff Settings modal controls document eligibility")
        print("📊 Different cutoffs for each medical data subsection")
        print("📊 Real-time filtering based on document upload dates")
        
        print("\n5. Technical Implementation:")
        print("-" * 50)
        print("🔧 Template: templates/prep_sheet.html")
        print("🔧 Data Parser: medical_data_parser.py")
        print("🔧 Settings Model: ChecklistSettings in models.py")
        print("🔧 Route Handler: /patients/<id>/prep_sheet in demo_routes.py")
        
        # Show some real document examples if available
        all_documents = MedicalDocument.query.filter_by(patient_id=patient.id).limit(5).all()
        if all_documents:
            print(f"\n6. Sample Documents Available for {patient.first_name}:")
            print("-" * 50)
            for doc in all_documents:
                doc_type = doc.document_type or 'Unknown'
                doc_name = doc.document_name or doc.filename or f'Document {doc.id}'
                upload_date = doc.upload_date.strftime('%Y-%m-%d') if doc.upload_date else 'Unknown'
                print(f"  • {doc_name} ({doc_type}) - {upload_date}")
        
        print("\n🎉 Prep Sheet Hyperlink System Ready!")
        print("\nUsage Instructions:")
        print("1. Visit any patient's prep sheet: /patients/<id>/prep_sheet")
        print("2. Navigate to Quality Checklist → Enhanced Medical Data Sections")
        print("3. Click any document badge to view the full document")
        print("4. Adjust data cutoffs via /screenings?tab=checklist → Data Cutoff Settings")
        print("5. Cutoff changes immediately affect which documents appear in prep sheets")

if __name__ == "__main__":
    demo_prep_sheet_hyperlinks()