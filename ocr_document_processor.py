"""
OCR Document Processor
Integrates Tesseract OCR with the healthcare screening system for image-based document processing
"""

import os
import io
import json
import logging
import tempfile
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from PIL import Image
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path, convert_from_bytes

from app import db
from models import MedicalDocument


logger = logging.getLogger(__name__)


class OCRQualityMetrics:
    """Track OCR processing quality and performance"""
    
    def __init__(self):
        self.confidence_threshold = 60  # Minimum confidence for reliable OCR
        self.min_text_length = 50  # Minimum text length to consider successful
        self.processing_stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'low_confidence_results': 0,
            'failed_extractions': 0,
            'average_confidence': 0.0,
            'processing_time_total': 0.0
        }


class TesseractOCRProcessor:
    """Enhanced OCR processor using Tesseract for medical document text extraction"""
    
    def __init__(self):
        self.quality_metrics = OCRQualityMetrics()
        
        # Configure Tesseract for medical documents
        self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:()[]{}/-+ '
        
        # Medical terminology optimization
        self.medical_preprocessing_enabled = True
        
        # File type detection
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
        self.pdf_extensions = {'.pdf'}
        self.supported_extensions = self.image_extensions | self.pdf_extensions
        
        logger.info("✅ Tesseract OCR Processor initialized with medical document optimization")
    
    def is_image_based_document(self, filename: str, content_bytes: bytes = None) -> bool:
        """Check if document requires OCR processing"""
        if not filename:
            return False
            
        file_extension = os.path.splitext(filename.lower())[1]
        
        # Direct image files always need OCR
        if file_extension in self.image_extensions:
            return True
            
        # PDFs might be image-based - check if they contain searchable text
        if file_extension in self.pdf_extensions:
            if content_bytes:
                return self._is_scanned_pdf(content_bytes)
            return True  # Assume PDF needs OCR if we can't check content
            
        return False
    
    def _is_scanned_pdf(self, pdf_bytes: bytes) -> bool:
        """Check if PDF is scanned (image-based) or contains searchable text"""
        try:
            # Simple heuristic: if PDF has very little text content, it's likely scanned
            pdf_text = self._extract_pdf_text_simple(pdf_bytes)
            return len(pdf_text.strip()) < 100  # Less than 100 characters suggests scanned PDF
        except Exception as e:
            logger.warning(f"Could not analyze PDF text content: {e}")
            return True  # Assume scanned if we can't determine
    
    def _extract_pdf_text_simple(self, pdf_bytes: bytes) -> str:
        """Quick text extraction from PDF to check if it's searchable"""
        try:
            # This is a placeholder - would use PyPDF2 or similar in real implementation
            # For now, assume all PDFs need OCR
            return ""
        except Exception:
            return ""
    
    def process_document_ocr(self, document_id: int) -> Dict[str, Any]:
        """Process a document with OCR if needed"""
        processing_start = datetime.now()
        result = {
            'success': False,
            'document_id': document_id,
            'ocr_applied': False,
            'original_text_length': 0,
            'extracted_text_length': 0,
            'confidence_score': 0,
            'processing_time_seconds': 0,
            'error': None,
            'quality_flags': []
        }
        
        try:
            # Get document from database
            document = MedicalDocument.query.get(document_id)
            if not document:
                result['error'] = f"Document {document_id} not found"
                return result
            
            # Check if document needs OCR
            needs_ocr = self.is_image_based_document(document.document_name, None)
            if not needs_ocr:
                result['success'] = True
                result['ocr_applied'] = False
                result['original_text_length'] = len(document.content or "")
                result['quality_flags'].append("text_based_document")
                return result
            
            # Store original content length
            result['original_text_length'] = len(document.content or "")
            
            # Process document with OCR
            # Check if binary content exists and has actual data
            if not document.binary_content or len(document.binary_content) == 0:
                result['error'] = f"Document {document_id} has no binary content to process"
                result['quality_flags'].append("no_binary_content")
                return result
            
            extracted_text, confidence, quality_flags = self._extract_text_with_ocr(
                document.document_name,
                document.binary_content  # Use the actual binary content field
            )
            
            if extracted_text:
                # Combine OCR text with any existing content
                combined_content = self._combine_content(document.content, extracted_text)
                
                # Update document with OCR results
                document.content = combined_content
                
                # Update OCR status fields directly on document
                document.ocr_processed = True
                document.ocr_confidence = confidence
                document.ocr_processing_date = processing_start
                document.ocr_text_length = len(extracted_text)
                document.ocr_quality_flags = json.dumps(quality_flags)
                
                # Also update metadata for backward compatibility
                metadata = json.loads(document.doc_metadata) if document.doc_metadata else {}
                metadata['ocr_processed'] = True
                metadata['ocr_confidence'] = confidence
                metadata['ocr_processing_date'] = processing_start.isoformat()
                metadata['ocr_text_length'] = len(extracted_text)
                metadata['ocr_quality_flags'] = quality_flags
                
                document.doc_metadata = json.dumps(metadata)
                db.session.commit()
                
                # Update result
                result['success'] = True
                result['ocr_applied'] = True
                result['extracted_text_length'] = len(extracted_text)
                result['confidence_score'] = confidence
                result['quality_flags'] = quality_flags
                
                # Update processing stats
                self.quality_metrics.processing_stats['successful_extractions'] += 1
                
                if confidence < self.quality_metrics.confidence_threshold:
                    self.quality_metrics.processing_stats['low_confidence_results'] += 1
                    result['quality_flags'].append("low_confidence_ocr")
                
                logger.info(f"✅ OCR processed document {document_id}: {len(extracted_text)} characters extracted with {confidence}% confidence")
                
            else:
                result['error'] = "OCR failed to extract any text"
                self.quality_metrics.processing_stats['failed_extractions'] += 1
                logger.warning(f"⚠️ OCR failed for document {document_id}")
            
        except Exception as e:
            result['error'] = f"OCR processing error: {str(e)}"
            self.quality_metrics.processing_stats['failed_extractions'] += 1
            logger.error(f"❌ OCR processing error for document {document_id}: {e}")
            
        finally:
            # Update processing time
            processing_time = (datetime.now() - processing_start).total_seconds()
            result['processing_time_seconds'] = processing_time
            
            self.quality_metrics.processing_stats['total_processed'] += 1
            self.quality_metrics.processing_stats['processing_time_total'] += processing_time
            
        return result
    
    def _extract_text_with_ocr(self, filename: str, file_data: bytes) -> Tuple[str, float, List[str]]:
        """Extract text using Tesseract OCR"""
        extracted_text = ""
        confidence = 0.0
        quality_flags = []
        
        try:
            file_extension = os.path.splitext(filename.lower())[1]
            
            if file_extension in self.image_extensions:
                extracted_text, confidence, quality_flags = self._process_image_ocr(file_data)
                
            elif file_extension in self.pdf_extensions:
                extracted_text, confidence, quality_flags = self._process_pdf_ocr(file_data)
                
            else:
                quality_flags.append("unsupported_file_type")
                
        except Exception as e:
            logger.error(f"OCR text extraction error: {e}")
            quality_flags.append("extraction_error")
            
        return extracted_text, confidence, quality_flags
    
    def _process_image_ocr(self, image_data: bytes) -> Tuple[str, float, List[str]]:
        """Process image file with OCR"""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Preprocess image for better OCR results
            if self.medical_preprocessing_enabled:
                image = self._preprocess_medical_image(image)
            
            # Extract text with Tesseract
            extracted_text = pytesseract.image_to_string(image, config=self.tesseract_config)
            
            # Get confidence data
            confidence_data = pytesseract.image_to_data(image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
            avg_confidence = self._calculate_average_confidence(confidence_data)
            
            # Quality assessment
            quality_flags = self._assess_ocr_quality(extracted_text, avg_confidence)
            
            return extracted_text.strip(), avg_confidence, quality_flags
            
        except Exception as e:
            logger.error(f"Image OCR processing error: {e}")
            return "", 0.0, ["image_processing_error"]
    
    def _process_pdf_ocr(self, pdf_data: bytes) -> Tuple[str, float, List[str]]:
        """Process PDF file with OCR"""
        try:
            # Convert PDF pages to images
            images = convert_from_bytes(pdf_data, dpi=300)  # High DPI for better OCR
            
            all_text = []
            all_confidences = []
            quality_flags = ["pdf_converted_to_images"]
            
            for page_num, image in enumerate(images):
                # Preprocess each page
                if self.medical_preprocessing_enabled:
                    image = self._preprocess_medical_image(image)
                
                # Extract text from page
                page_text = pytesseract.image_to_string(image, config=self.tesseract_config)
                
                # Get confidence for page
                confidence_data = pytesseract.image_to_data(image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
                page_confidence = self._calculate_average_confidence(confidence_data)
                
                all_text.append(page_text.strip())
                all_confidences.append(page_confidence)
                
                if page_confidence < 50:  # Low confidence page
                    quality_flags.append(f"low_confidence_page_{page_num + 1}")
            
            # Combine all pages
            full_text = "\n\n".join([text for text in all_text if text])
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            # Additional quality assessment
            quality_flags.extend(self._assess_ocr_quality(full_text, avg_confidence))
            
            return full_text, avg_confidence, quality_flags
            
        except Exception as e:
            logger.error(f"PDF OCR processing error: {e}")
            return "", 0.0, ["pdf_processing_error"]
    
    def _preprocess_medical_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy for medical documents"""
        try:
            # Convert PIL Image to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Improve contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Apply threshold to get clear black and white
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(thresh)
            
            return processed_image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image  # Return original if preprocessing fails
    
    def _calculate_average_confidence(self, confidence_data: Dict) -> float:
        """Calculate average confidence from Tesseract output"""
        try:
            confidences = [int(conf) for conf in confidence_data['conf'] if int(conf) > 0]
            return sum(confidences) / len(confidences) if confidences else 0.0
        except Exception:
            return 0.0
    
    def _assess_ocr_quality(self, text: str, confidence: float) -> List[str]:
        """Assess OCR quality and return quality flags"""
        flags = []
        
        if confidence < 60:
            flags.append("low_confidence")
        elif confidence < 80:
            flags.append("medium_confidence")
        else:
            flags.append("high_confidence")
        
        if len(text) < 50:
            flags.append("short_text")
        elif len(text) > 5000:
            flags.append("long_text")
        
        # Check for common OCR errors in medical context
        if text.count('|') > text.count('l') * 2:  # Too many pipes vs letters
            flags.append("possible_character_errors")
            
        if len([c for c in text if not c.isascii()]) > len(text) * 0.1:
            flags.append("non_ascii_characters")
        
        return flags
    
    def _combine_content(self, original_content: str, ocr_text: str) -> str:
        """Intelligently combine original content with OCR extracted text"""
        if not original_content or len(original_content.strip()) < 10:
            return ocr_text
            
        if not ocr_text or len(ocr_text.strip()) < 10:
            return original_content
            
        # Combine with clear separation
        combined = f"{original_content}\n\n--- OCR EXTRACTED TEXT ---\n{ocr_text}"
        return combined
    
    def bulk_process_documents(self, document_ids: List[int]) -> Dict[str, Any]:
        """Process multiple documents with OCR in batch"""
        results = {
            'total_processed': 0,
            'successful_ocr': 0,
            'failed_ocr': 0,
            'no_ocr_needed': 0,
            'total_text_extracted': 0,
            'processing_time_total': 0,
            'document_results': []
        }
        
        start_time = datetime.now()
        
        for doc_id in document_ids:
            doc_result = self.process_document_ocr(doc_id)
            results['document_results'].append(doc_result)
            results['total_processed'] += 1
            
            if doc_result['success']:
                if doc_result['ocr_applied']:
                    results['successful_ocr'] += 1
                    results['total_text_extracted'] += doc_result['extracted_text_length']
                else:
                    results['no_ocr_needed'] += 1
            else:
                results['failed_ocr'] += 1
        
        results['processing_time_total'] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"📊 Bulk OCR completed: {results['successful_ocr']} successful, {results['failed_ocr']} failed, {results['no_ocr_needed']} no OCR needed")
        
        return results
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get OCR processing statistics"""
        stats = self.quality_metrics.processing_stats.copy()
        
        if stats['total_processed'] > 0:
            stats['success_rate'] = (stats['successful_extractions'] / stats['total_processed']) * 100
            stats['average_processing_time'] = stats['processing_time_total'] / stats['total_processed']
        else:
            stats['success_rate'] = 0
            stats['average_processing_time'] = 0
        
        return stats


# Global OCR processor instance
ocr_processor = TesseractOCRProcessor()


def process_document_with_ocr(document_id: int) -> Dict[str, Any]:
    """Convenience function to process a single document with OCR"""
    return ocr_processor.process_document_ocr(document_id)


def bulk_ocr_processing(document_ids: List[int]) -> Dict[str, Any]:
    """Convenience function for bulk OCR processing"""
    return ocr_processor.bulk_process_documents(document_ids)