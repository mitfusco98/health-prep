"""
OCR Management Routes
Provides admin interface for managing OCR processing, viewing status, and reprocessing documents
"""

from datetime import datetime, timedelta
from flask import render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
import json
import logging

from app import app, db
from models import MedicalDocument, Patient, ScreeningType
# Import moved to avoid circular imports - will import when needed
from selective_screening_refresh_manager import selective_refresh_manager, ChangeType

logger = logging.getLogger(__name__)

# Initialize OCR processor at module level
try:
    from ocr_document_processor import TesseractOCRProcessor
    ocr_processor = TesseractOCRProcessor()
except ImportError as e:
    logger.warning(f"OCR processor not available: {e}")
    ocr_processor = None


@app.route('/admin/ocr/reprocess-document/<int:doc_id>', methods=['POST'])
def reprocess_document(doc_id):
    """Reprocess OCR for a specific document and trigger selective screening refresh"""
    try:
        # Import here to avoid circular imports
        from ocr_document_processor import ocr_processor
        
        # Get the document
        document = MedicalDocument.query.get_or_404(doc_id)
        
        if not document.binary_content:
            return jsonify({
                'success': False,
                'error': 'Document has no binary content to process'
            })
        
        # Reset OCR status to force reprocessing
        document.ocr_processed = False
        document.content = None
        document.ocr_confidence = None
        document.ocr_processing_date = None
        document.ocr_text_length = None
        db.session.commit()
        
        # Reprocess OCR
        result = ocr_processor.process_document_ocr(doc_id)
        
        if result['success']:
            # Trigger selective screening refresh for this document's patient
            if document.patient_id:
                try:
                    # Trigger screening refresh for this patient after document reprocessing
                    from timeout_safe_refresh import timeout_safe_refresh
                    refresh_success = timeout_safe_refresh._refresh_single_patient(document.patient_id)
                    refresh_triggered = refresh_success
                except Exception as refresh_error:
                    logger.warning(f"Failed to trigger screening refresh after reprocessing doc {doc_id}: {refresh_error}")
                    refresh_triggered = False
            else:
                refresh_triggered = False
            
            return jsonify({
                'success': True,
                'confidence': result.get('confidence_score', 0),
                'text_length': result.get('text_length', 0),
                'screening_refresh_triggered': refresh_triggered,
                'message': 'Document reprocessed successfully and screening matches updated'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'OCR processing failed')
            })
            
    except Exception as e:
        logger.error(f"Error reprocessing document {doc_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/admin/ocr-dashboard')
def ocr_dashboard():
    """OCR management dashboard"""
    try:
        # Import here to avoid circular imports
        from ocr_document_processor import ocr_processor
        
        # Get OCR statistics
        ocr_stats = ocr_processor.get_processing_statistics()
        
        # Get document counts by OCR status
        total_documents = MedicalDocument.query.count()
        ocr_processed = MedicalDocument.query.filter_by(ocr_processed=True).count()
        needs_ocr = 0
        
        # Count documents that might need OCR
        all_documents = MedicalDocument.query.all()
        for doc in all_documents:
            if doc.document_name and ocr_processor.is_image_based_document(doc.document_name):
                needs_ocr += 1
        
        # Get recent OCR processing activity
        recent_ocr_docs = (
            MedicalDocument.query
            .filter(MedicalDocument.ocr_processed == True)
            .filter(MedicalDocument.ocr_processing_date >= datetime.now() - timedelta(days=7))
            .order_by(MedicalDocument.ocr_processing_date.desc())
            .limit(10)
            .all()
        )
        
        # Get documents with low OCR confidence
        low_confidence_docs = (
            MedicalDocument.query
            .filter(MedicalDocument.ocr_processed == True)
            .filter(MedicalDocument.ocr_confidence < 60)
            .order_by(MedicalDocument.ocr_confidence.asc())
            .limit(5)
            .all()
        )
        
        # Get documents that need OCR processing
        pending_ocr_docs = []
        for doc in MedicalDocument.query.filter_by(ocr_processed=False).limit(20).all():
            if doc.document_name and ocr_processor.is_image_based_document(doc.document_name):
                pending_ocr_docs.append(doc)
        
        # Get PHI filter status
        from phi_filter import phi_filter
        phi_filter_stats = phi_filter.get_filter_statistics()
        phi_filter_enabled = phi_filter_stats['config']['phi_filtering_enabled']
        
        dashboard_data = {
            'total_documents': total_documents,
            'ocr_processed': ocr_processed,
            'needs_ocr': needs_ocr,
            'processing_stats': ocr_stats,
            'recent_activity': recent_ocr_docs,
            'low_confidence': low_confidence_docs,
            'pending_processing': pending_ocr_docs,
            'phi_filter_enabled': phi_filter_enabled,
            'phi_filter_stats': phi_filter_stats
        }
        
        return render_template('admin/ocr_dashboard.html', data=dashboard_data)
        
    except Exception as e:
        logger.error(f"OCR dashboard error: {e}")
        flash(f"Error loading OCR dashboard: {str(e)}", "error")
        return redirect(url_for('index'))


@app.route('/admin/ocr-process-document/<int:document_id>', methods=['POST'])
def ocr_process_single_document(document_id):
    """Process a single document with OCR"""
    try:
        document = MedicalDocument.query.get_or_404(document_id)
        
        # Import here to avoid circular imports
        from ocr_document_processor import process_document_with_ocr
        
        # Process document with OCR
        result = process_document_with_ocr(document_id)
        
        if result['success']:
            if result['ocr_applied']:
                # Trigger selective refresh for the affected patient
                from selective_screening_refresh_manager import selective_refresh_manager, ChangeType
                
                # Mark all active screening types as potentially affected
                active_screening_types = ScreeningType.query.filter_by(is_active=True).all()
                
                for screening_type in active_screening_types:
                    selective_refresh_manager.mark_screening_type_dirty(
                        screening_type.id, 
                        ChangeType.KEYWORDS,
                        "no_ocr_content", 
                        f"ocr_reprocessed_{document_id}",
                        affected_criteria={"patient_id": document.patient_id}
                    )
                
                # Process selective refresh
                refresh_stats = selective_refresh_manager.process_selective_refresh()
                
                flash(f"Document OCR processing completed successfully! Extracted {result['extracted_text_length']} characters with {result['confidence_score']:.1f}% confidence. Updated {refresh_stats.screenings_updated} screenings.", "success")
            else:
                flash(f"Document processed - no OCR needed (text-based document)", "info")
        else:
            flash(f"OCR processing failed: {result['error']}", "error")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Single document OCR processing error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/ocr-bulk-process', methods=['POST'])
def ocr_bulk_process():
    """Process multiple documents with OCR"""
    try:
        data = request.get_json()
        document_ids = data.get('document_ids', [])
        
        if not document_ids:
            return jsonify({"success": False, "error": "No documents selected"}), 400
        
        # Validate document IDs
        valid_doc_ids = []
        for doc_id in document_ids:
            if MedicalDocument.query.get(doc_id):
                valid_doc_ids.append(doc_id)
        
        if not valid_doc_ids:
            return jsonify({"success": False, "error": "No valid documents found"}), 400
        
        # Import here to avoid circular imports
        from ocr_document_processor import ocr_processor
        
        # Process documents individually (simplified bulk processing)
        successful_ocr = 0
        failed_ocr = 0
        no_ocr_needed = 0
        
        for doc_id in valid_doc_ids:
            try:
                result = ocr_processor.process_document_ocr(doc_id)
                if result['success']:
                    successful_ocr += 1
                else:
                    failed_ocr += 1
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {e}")
                failed_ocr += 1
        
        result = {
            'successful_ocr': successful_ocr,
            'failed_ocr': failed_ocr,
            'no_ocr_needed': no_ocr_needed,
            'total_processed': len(valid_doc_ids)
        }
        
        # Trigger selective refresh for all affected patients
        if result['successful_ocr'] > 0:
            affected_patients = set()
            processed_docs = MedicalDocument.query.filter(MedicalDocument.id.in_(valid_doc_ids)).all()
            
            for doc in processed_docs:
                affected_patients.add(doc.patient_id)
            
            # Mark screening types as dirty for selective refresh
            active_screening_types = ScreeningType.query.filter_by(is_active=True).all()
            
            for screening_type in active_screening_types:
                selective_refresh_manager.mark_screening_type_dirty(
                    screening_type.id, 
                    ChangeType.KEYWORDS,
                    "bulk_no_ocr", 
                    "bulk_ocr_processed",
                    affected_criteria={"patient_ids": list(affected_patients)}
                )
            
            # Process selective refresh
            refresh_stats = selective_refresh_manager.process_selective_refresh()
            
            result['selective_refresh'] = {
                'screenings_updated': refresh_stats.screenings_updated,
                'patients_affected': refresh_stats.affected_patients
            }
            
            flash(f"Bulk OCR processing completed! Successfully processed {result['successful_ocr']} documents, updated {refresh_stats.screenings_updated} screenings across {refresh_stats.affected_patients} patients.", "success")
        else:
            flash(f"Bulk OCR processing completed with {result['failed_ocr']} failures and {result['no_ocr_needed']} documents that didn't need OCR.", "warning")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Bulk OCR processing error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/ocr-reprocess-low-confidence', methods=['POST'])
def ocr_reprocess_low_confidence():
    """Reprocess documents with low OCR confidence scores"""
    try:
        confidence_threshold = float(request.form.get('confidence_threshold', 60))
        
        # Find documents with low confidence scores
        low_confidence_docs = (
            MedicalDocument.query
            .filter(MedicalDocument.ocr_processed == True)
            .filter(MedicalDocument.ocr_confidence < confidence_threshold)
            .all()
        )
        
        if not low_confidence_docs:
            flash(f"No documents found with OCR confidence below {confidence_threshold}%", "info")
            return redirect(url_for('ocr_dashboard'))
        
        document_ids = [doc.id for doc in low_confidence_docs]
        
        # Import here to avoid circular imports  
        from ocr_document_processor import ocr_processor
        
        # Reprocess documents individually
        successful_ocr = 0
        failed_ocr = 0
        
        for doc_id in document_ids:
            try:
                # Reset OCR status to force reprocessing
                doc = MedicalDocument.query.get(doc_id)
                if doc:
                    doc.ocr_processed = False
                    doc.content = None
                    db.session.commit()
                    
                result_single = ocr_processor.process_document_ocr(doc_id)
                if result_single['success']:
                    successful_ocr += 1
                else:
                    failed_ocr += 1
            except Exception as e:
                logger.error(f"Error reprocessing document {doc_id}: {e}")
                failed_ocr += 1
        
        result = {
            'successful_ocr': successful_ocr,
            'failed_ocr': failed_ocr,
            'total_processed': len(document_ids)
        }
        
        flash(f"Reprocessed {len(document_ids)} low-confidence documents. Success: {result['successful_ocr']}, Failed: {result['failed_ocr']}", "info")
        
        return redirect(url_for('ocr_dashboard'))
        
    except Exception as e:
        logger.error(f"Low confidence reprocessing error: {e}")
        flash(f"Error reprocessing low-confidence documents: {str(e)}", "error")
        return redirect(url_for('ocr_dashboard'))


@app.route('/admin/ocr-process-pending', methods=['POST'])
def ocr_process_pending():
    """Process all pending OCR documents"""
    try:
        # Find all documents that need OCR processing
        all_documents = MedicalDocument.query.filter_by(ocr_processed=False).all()
        pending_doc_ids = []
        
        for doc in all_documents:
            if doc.document_name and ocr_processor.is_image_based_document(doc.document_name):
                pending_doc_ids.append(doc.id)
        
        if not pending_doc_ids:
            flash("No documents pending OCR processing", "info")
            return redirect(url_for('ocr_dashboard'))
        
        # Limit to prevent overwhelming the system
        max_batch_size = 50
        if len(pending_doc_ids) > max_batch_size:
            flash(f"Processing first {max_batch_size} of {len(pending_doc_ids)} pending documents", "info")
            pending_doc_ids = pending_doc_ids[:max_batch_size]
        
        # Import here to avoid circular imports
        from ocr_document_processor import ocr_processor
        
        # Process pending documents individually
        successful_ocr = 0
        failed_ocr = 0
        no_ocr_needed = 0
        
        for doc_id in pending_doc_ids:
            try:
                result_single = ocr_processor.process_document_ocr(doc_id)
                if result_single['success']:
                    successful_ocr += 1
                else:
                    failed_ocr += 1
            except Exception as e:
                logger.error(f"Error processing pending document {doc_id}: {e}")
                failed_ocr += 1
        
        result = {
            'successful_ocr': successful_ocr,
            'failed_ocr': failed_ocr,
            'no_ocr_needed': no_ocr_needed,
            'total_processed': len(pending_doc_ids)
        }
        
        flash(f"Processed {result['total_processed']} pending documents. Success: {result['successful_ocr']}, No OCR needed: {result['no_ocr_needed']}, Failed: {result['failed_ocr']}", "success")
        
        return redirect(url_for('ocr_dashboard'))
        
    except Exception as e:
        logger.error(f"Pending OCR processing error: {e}")
        flash(f"Error processing pending OCR documents: {str(e)}", "error")
        return redirect(url_for('ocr_dashboard'))


@app.route('/api/document/<int:document_id>/ocr-status')
def get_document_ocr_status(document_id):
    """Get OCR processing status for a specific document"""
    try:
        document = MedicalDocument.query.get_or_404(document_id)
        
        ocr_status = {
            'document_id': document_id,
            'document_name': document.document_name,
            'ocr_processed': document.ocr_processed,
            'ocr_confidence': document.ocr_confidence,
            'ocr_processing_date': document.ocr_processing_date.isoformat() if document.ocr_processing_date else None,
            'ocr_text_length': document.ocr_text_length,
            'needs_ocr': ocr_processor.is_image_based_document(document.document_name or ''),
            'quality_assessment': 'high' if document.ocr_confidence and document.ocr_confidence >= 80 else 'medium' if document.ocr_confidence and document.ocr_confidence >= 60 else 'low' if document.ocr_confidence else 'unknown'
        }
        
        if document.ocr_quality_flags:
            try:
                ocr_status['quality_flags'] = json.loads(document.ocr_quality_flags)
            except json.JSONDecodeError:
                ocr_status['quality_flags'] = []
        
        return jsonify(ocr_status)
        
    except Exception as e:
        logger.error(f"OCR status retrieval error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ocr-statistics')
def get_ocr_statistics():
    """Get overall OCR processing statistics"""
    try:
        stats = ocr_processor.get_processing_statistics()
        
        # Add database statistics
        total_documents = MedicalDocument.query.count()
        ocr_processed = MedicalDocument.query.filter_by(ocr_processed=True).count()
        
        # Count documents that need OCR
        all_documents = MedicalDocument.query.limit(1000).all()  # Limit for performance
        needs_ocr_count = sum(1 for doc in all_documents 
                             if doc.document_name and ocr_processor.is_image_based_document(doc.document_name))
        
        combined_stats = {
            **stats,
            'database_stats': {
                'total_documents': total_documents,
                'ocr_processed': ocr_processed,
                'needs_ocr_estimated': needs_ocr_count,
                'processing_coverage': (ocr_processed / total_documents * 100) if total_documents > 0 else 0
            }
        }
        
        return jsonify(combined_stats)
        
    except Exception as e:
        logger.error(f"OCR statistics error: {e}")
        return jsonify({"error": str(e)}), 500