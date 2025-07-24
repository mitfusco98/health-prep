#!/usr/bin/env python3
"""
Universal Document Viewing Protocol
Handles PDF, image, and text document display with automatic OCR processing
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from flask import Response, render_template_string

from app import app, db
from models import MedicalDocument

logger = logging.getLogger(__name__)


class UniversalDocumentViewer:
    """Universal document viewing system with OCR support"""
    
    def __init__(self):
        self.supported_pdf_types = {'application/pdf'}
        self.supported_image_types = {
            'image/jpeg', 'image/jpg', 'image/png', 
            'image/tiff', 'image/bmp', 'image/gif'
        }
        self.supported_text_types = {'text/plain', 'text/html'}
        
    def get_document_display_info(self, document_id: int) -> Dict[str, Any]:
        """Get comprehensive document display information"""
        try:
            document = MedicalDocument.query.get(document_id)
            if not document:
                return {'error': f'Document {document_id} not found'}
            
            display_info = {
                'document_id': document_id,
                'document_name': document.document_name,
                'filename': document.filename,
                'mime_type': document.mime_type,
                'is_binary': document.is_binary,
                'has_content': bool(document.content),
                'has_binary': bool(document.binary_content),
                'content_length': len(document.content) if document.content else 0,
                'binary_length': len(document.binary_content) if document.binary_content else 0,
                'ocr_processed': document.ocr_processed,
                'ocr_confidence': document.ocr_confidence,
                'ocr_text_length': document.ocr_text_length,
                'display_strategy': self._determine_display_strategy(document),
                'needs_ocr': self._needs_ocr_processing(document),
                'can_display': self._can_display_document(document)
            }
            
            return display_info
            
        except Exception as e:
            logger.error(f"Error getting document display info: {e}")
            return {'error': str(e)}
    
    def _determine_display_strategy(self, document: MedicalDocument) -> str:
        """Determine the best way to display this document"""
        
        # If document has text content, display as text
        if document.content and len(document.content.strip()) > 0:
            return 'text_display'
        
        # If document has binary content but no text, needs OCR
        if document.binary_content and len(document.binary_content) > 0:
            if document.mime_type in self.supported_pdf_types:
                return 'pdf_with_ocr'
            elif document.mime_type in self.supported_image_types:
                return 'image_with_ocr'
            else:
                return 'binary_download_only'
        
        # No usable content
        return 'no_content'
    
    def _needs_ocr_processing(self, document: MedicalDocument) -> bool:
        """Check if document needs OCR processing"""
        if document.ocr_processed:
            return False
            
        if not document.binary_content or len(document.binary_content) == 0:
            return False
            
        return (document.mime_type in self.supported_pdf_types or 
                document.mime_type in self.supported_image_types)
    
    def _can_display_document(self, document: MedicalDocument) -> bool:
        """Check if document can be displayed in browser"""
        
        # Text content can always be displayed
        if document.content and len(document.content.strip()) > 0:
            return True
            
        # Binary content with supported types can be displayed
        if document.binary_content and len(document.binary_content) > 0:
            return (document.mime_type in self.supported_pdf_types or 
                   document.mime_type in self.supported_image_types)
        
        return False
    
    def process_document_for_display(self, document_id: int) -> Dict[str, Any]:
        """Process document and prepare it for display"""
        try:
            document = MedicalDocument.query.get(document_id)
            if not document:
                return {'success': False, 'error': f'Document {document_id} not found'}
            
            display_info = self.get_document_display_info(document_id)
            
            # If document needs OCR, process it
            if display_info['needs_ocr']:
                logger.info(f"Processing document {document_id} with OCR")
                ocr_result = self._process_with_ocr(document)
                display_info.update(ocr_result)
                
                # Refresh display info after OCR
                display_info = self.get_document_display_info(document_id)
            
            return {
                'success': True,
                'display_info': display_info,
                'document': document
            }
            
        except Exception as e:
            logger.error(f"Error processing document for display: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_with_ocr(self, document: MedicalDocument) -> Dict[str, Any]:
        """Process document with OCR"""
        try:
            import pytesseract
            from pdf2image import convert_from_bytes
            from PIL import Image
            import io
            
            extracted_text = ''
            total_confidence = 0
            page_count = 0
            
            # Handle PDF files
            if document.mime_type == 'application/pdf':
                images = convert_from_bytes(document.binary_content, dpi=300)
                logger.info(f"Converted PDF to {len(images)} images")
                
                for i, image in enumerate(images):
                    # Get OCR data with confidence
                    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    page_text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
                    
                    if page_text.strip():
                        extracted_text += page_text + '\n'
                        
                        # Calculate confidence
                        confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                        if confidences:
                            page_confidence = sum(confidences) / len(confidences)
                            total_confidence += page_confidence
                            page_count += 1
            
            # Handle image files  
            elif document.mime_type in self.supported_image_types:
                image = Image.open(io.BytesIO(document.binary_content))
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                extracted_text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
                
                confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                if confidences:
                    total_confidence = sum(confidences) / len(confidences)
                    page_count = 1
            
            if extracted_text.strip():
                avg_confidence = total_confidence / page_count if page_count > 0 else 0
                
                # Update document with OCR results
                document.content = extracted_text
                document.is_binary = False  # Make it displayable as text
                document.ocr_processed = True
                document.ocr_confidence = avg_confidence
                document.ocr_processing_date = datetime.now()
                document.ocr_text_length = len(extracted_text)
                document.ocr_quality_flags = json.dumps(['universal_viewer_ocr'])
                
                db.session.commit()
                
                logger.info(f"OCR completed: {len(extracted_text)} characters, {avg_confidence:.1f}% confidence")
                
                return {
                    'ocr_success': True,
                    'extracted_length': len(extracted_text),
                    'confidence': avg_confidence
                }
            else:
                return {'ocr_success': False, 'error': 'No text extracted'}
                
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return {'ocr_success': False, 'error': str(e)}


# Global instance
universal_viewer = UniversalDocumentViewer()


def process_document_for_universal_display(document_id: int) -> Dict[str, Any]:
    """Process any document for universal display"""
    return universal_viewer.process_document_for_display(document_id)


def get_document_display_strategy(document_id: int) -> str:
    """Get the display strategy for a document"""
    display_info = universal_viewer.get_document_display_info(document_id)
    return display_info.get('display_strategy', 'no_content')


if __name__ == "__main__":
    # Test the universal viewer
    with app.app_context():
        print("🔍 Testing Universal Document Viewer...")
        
        # Test with document 163
        result = process_document_for_universal_display(163)
        print(f"Document 163 processing result: {result}")