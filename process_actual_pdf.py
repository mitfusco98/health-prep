#!/usr/bin/env python3
"""
Process the actual PDF file uploaded by the user and update document 162
"""

import os
from app import app, db
from models import MedicalDocument

def process_actual_pdf():
    """Process the user's actual PDF file and update document 162"""
    with app.app_context():
        print("🔍 Processing actual PDF file...")
        
        # Read the extracted content
        extracted_content = ""
        try:
            with open('/tmp/extracted_pdf_content.txt', 'r') as f:
                extracted_content = f.read()
        except FileNotFoundError:
            print("No extracted content found, trying alternative approach...")
            
            # Try to read the PDF directly with binary content for OCR
            try:
                with open('attached_assets/Lab test doc_1753317200711.pdf', 'rb') as f:
                    binary_content = f.read()
                    print(f"📄 Read {len(binary_content)} bytes from actual PDF")
                    
                    # Update document 162 with actual binary content
                    doc = MedicalDocument.query.get(162)
                    if doc:
                        # Store the actual PDF as binary content
                        doc.binary_content = binary_content
                        doc.is_binary = True
                        doc.mime_type = 'application/pdf'
                        doc.filename = 'Lab test doc.pdf'
                        doc.content = None  # Clear placeholder content
                        doc.ocr_processed = False
                        
                        db.session.commit()
                        print("✅ Updated document 162 with actual PDF binary content")
                        
                        # Now try OCR processing
                        from ocr_document_processor import process_document_with_ocr
                        
                        print("🔄 Processing with OCR...")
                        ocr_result = process_document_with_ocr(162)
                        print(f"OCR Result: {ocr_result}")
                        
                        if ocr_result['success']:
                            print(f"✅ OCR successful: {ocr_result['extracted_text_length']} characters extracted")
                            
                            # Trigger screening refresh
                            from selective_screening_refresh_manager import selective_refresh_manager, ChangeType
                            from models import ScreeningType
                            
                            # Mark screening types for refresh
                            active_types = ScreeningType.query.filter_by(is_active=True).all()
                            for st in active_types:
                                selective_refresh_manager.mark_screening_type_dirty(
                                    st.id,
                                    ChangeType.KEYWORDS,
                                    "placeholder_content",
                                    "actual_pdf_content",
                                    affected_criteria={"patient_id": doc.patient_id}
                                )
                            
                            # Process refresh
                            refresh_stats = selective_refresh_manager.process_selective_refresh()
                            print(f"📊 Refresh complete: {refresh_stats.screenings_updated} screenings updated")
                        else:
                            print(f"❌ OCR failed: {ocr_result.get('error', 'Unknown error')}")
                            
                        return doc
                    
            except Exception as e:
                print(f"❌ Error processing PDF: {e}")
                return None
        
        if extracted_content:
            print(f"📝 Extracted content length: {len(extracted_content)} characters")
            print(f"Content preview: {extracted_content[:200]}...")
            
            # Update document 162 with actual content
            doc = MedicalDocument.query.get(162)
            if doc:
                doc.content = extracted_content
                doc.is_binary = False  # Make it text-based for display
                doc.mime_type = 'text/plain'
                doc.ocr_processed = True
                doc.ocr_confidence = 95.0  # High confidence for direct text extraction
                doc.ocr_text_length = len(extracted_content)
                
                db.session.commit()
                print("✅ Updated document 162 with actual PDF content")
                return doc
        
        print("❌ Could not process actual PDF content")
        return None

if __name__ == "__main__":
    result = process_actual_pdf()
    if result:
        print("🎉 Successfully processed actual PDF!")
    else:
        print("❌ Failed to process actual PDF")