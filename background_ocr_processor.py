#!/usr/bin/env python3
"""
Background OCR Processor
Non-blocking OCR processing for document uploads using threading and multiprocessing
"""

import threading
import multiprocessing
import queue
import time
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
import uuid

from app import app, db
from models import MedicalDocument
from background_screening_processor import BackgroundTask, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)


class OCRTaskType(Enum):
    """Types of OCR tasks"""
    SINGLE_DOCUMENT = "single_document"
    BULK_DOCUMENTS = "bulk_documents"
    RETRY_FAILED = "retry_failed"


@dataclass
class OCRTask(BackgroundTask):
    """OCR-specific background task"""
    document_ids: List[int] = None
    ocr_method: str = "tesseract"  # tesseract, cloud_vision, etc.
    quality_threshold: float = 0.7
    
    def __init__(self, document_ids: List[int] = None, patient_ids: List[int] = None, 
                 priority: TaskPriority = TaskPriority.NORMAL, **kwargs):
        document_ids = document_ids or []
        patient_ids = patient_ids or []
        
        super().__init__(
            task_id=str(uuid.uuid4()),
            task_type=OCRTaskType.SINGLE_DOCUMENT.value if len(document_ids) == 1 else OCRTaskType.BULK_DOCUMENTS.value,
            priority=priority,
            patient_ids=patient_ids,
            screening_type_ids=None,
            context=kwargs.get('context', {}),
            status=TaskStatus.PENDING,
            progress=0.0,
            result=None,
            error_message=None,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None
        )
        self.document_ids = document_ids
        self.ocr_method = kwargs.get('ocr_method', 'tesseract')
        self.quality_threshold = kwargs.get('quality_threshold', 0.7)


class BackgroundOCRProcessor:
    """
    Non-blocking OCR processor that handles document processing in background threads/processes
    """
    
    def __init__(self, max_workers: int = 2, max_processes: int = None):
        """
        Initialize background OCR processor
        
        Args:
            max_workers: Max threads for I/O-bound tasks (file handling, DB operations)
            max_processes: Max processes for CPU-bound OCR tasks (None = auto-detect)
        """
        # Thread pool for I/O-bound operations (database, file operations)
        self.max_workers = max_workers
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Process pool for CPU-bound OCR operations
        if max_processes is None:
            max_processes = min(multiprocessing.cpu_count(), 4)  # Cap at 4 for Replit
        self.max_processes = max_processes
        self.process_executor = ProcessPoolExecutor(max_workers=max_processes)
        
        # Task queue and tracking
        self.task_queue = queue.PriorityQueue()
        self.active_tasks: Dict[str, OCRTask] = {}
        self.completed_tasks: Dict[str, OCRTask] = {}
        
        # Background worker thread
        self.worker_thread = None
        self.is_running = False
        
        # Progress callbacks
        self.progress_callbacks: List[Callable[[OCRTask], None]] = []
        
        logger.info(f"🔧 BackgroundOCRProcessor initialized: {max_workers} threads, {max_processes} processes")
    
    def start(self):
        """Start the background worker thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("🚀 Background OCR processor started")
    
    def stop(self):
        """Stop the background worker"""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        # Shutdown executors
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        logger.info("🛑 Background OCR processor stopped")
    
    def queue_document_ocr(self, document_id: int, patient_id: int, 
                          priority: TaskPriority = TaskPriority.NORMAL,
                          **kwargs) -> str:
        """
        Queue a single document for OCR processing
        
        Returns:
            task_id: Unique identifier for tracking the task
        """
        task = OCRTask(
            document_ids=[document_id],
            patient_ids=[patient_id],
            priority=priority,
            **kwargs
        )
        
        # Add to queue with priority (lower number = higher priority)
        priority_value = (4 - priority.value, time.time())  # Reverse priority for queue
        self.task_queue.put((priority_value, task))
        self.active_tasks[task.task_id] = task
        
        logger.info(f"📋 Queued OCR task {task.task_id} for document {document_id} (priority: {priority.name})")
        return task.task_id
    
    def queue_bulk_document_ocr(self, document_ids: List[int], patient_ids: List[int],
                               priority: TaskPriority = TaskPriority.LOW,
                               **kwargs) -> str:
        """
        Queue multiple documents for batch OCR processing
        
        Returns:
            task_id: Unique identifier for tracking the bulk task
        """
        task = OCRTask(
            document_ids=document_ids,
            patient_ids=patient_ids,
            priority=priority,
            **kwargs
        )
        task.task_type = OCRTaskType.BULK_DOCUMENTS.value
        
        priority_value = (4 - priority.value, time.time())
        self.task_queue.put((priority_value, task))
        self.active_tasks[task.task_id] = task
        
        logger.info(f"📋 Queued bulk OCR task {task.task_id} for {len(document_ids)} documents")
        return task.task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].to_dict()
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id].to_dict()
        return None
    
    def get_all_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get status of all tasks"""
        return {
            'active': [task.to_dict() for task in self.active_tasks.values()],
            'completed': [task.to_dict() for task in self.completed_tasks.values()],
            'queue_size': self.task_queue.qsize()
        }
    
    def _worker_loop(self):
        """Main worker loop that processes tasks from the queue"""
        logger.info("🔄 OCR worker loop started")
        
        while self.is_running:
            try:
                # Get next task from queue (blocks for 1 second)
                try:
                    priority_value, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the task
                self._process_task(task)
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
                time.sleep(1)  # Prevent rapid error loops
    
    def _process_task(self, task: OCRTask):
        """Process a single OCR task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._notify_progress(task)
        
        try:
            with app.app_context():  # Ensure Flask app context for database operations
                if len(task.document_ids) == 1:
                    # Single document processing
                    result = self._process_single_document(task)
                else:
                    # Bulk document processing
                    result = self._process_bulk_documents(task)
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.progress = 1.0
                
                # Cache invalidation for processed documents
                try:
                    from cached_operations import invalidate_patient_cache
                    for patient_id in task.patient_ids:
                        invalidate_patient_cache(patient_id)
                    logger.debug(f"🔄 Invalidated caches for patients: {task.patient_ids}")
                except Exception as cache_error:
                    logger.warning(f"Cache invalidation warning: {cache_error}")
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            logger.error(f"❌ OCR task {task.task_id} failed: {e}")
        
        finally:
            task.completed_at = datetime.now()
            
            # Move to completed tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            self.completed_tasks[task.task_id] = task
            
            # Cleanup old completed tasks (keep last 100)
            if len(self.completed_tasks) > 100:
                oldest_tasks = sorted(self.completed_tasks.keys(), 
                                    key=lambda k: self.completed_tasks[k].completed_at)
                for old_task_id in oldest_tasks[:-100]:
                    del self.completed_tasks[old_task_id]
            
            self._notify_progress(task)
    
    def _process_single_document(self, task: OCRTask) -> Dict[str, Any]:
        """Process OCR for a single document using multiprocessing"""
        document_id = task.document_ids[0]
        
        # Get document (I/O-bound operation in main thread)
        document = MedicalDocument.query.get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Check if OCR is needed
        if not self._needs_ocr(document):
            return {
                'success': True,
                'ocr_applied': False,
                'message': 'Document is text-based, no OCR needed',
                'processing_time_seconds': 0
            }
        
        # Prepare data for CPU-bound OCR processing
        ocr_data = {
            'document_id': document_id,
            'binary_content': document.binary_content,
            'filename': document.filename,
            'mime_type': getattr(document, 'mime_type', None),
            'ocr_method': task.ocr_method,
            'quality_threshold': task.quality_threshold
        }
        
        # Submit OCR job to process pool (CPU-bound)
        future = self.process_executor.submit(self._cpu_bound_ocr, ocr_data)
        
        # Update progress
        task.progress = 0.5
        self._notify_progress(task)
        
        # Wait for OCR result
        ocr_result = future.result()  # This blocks until OCR is complete
        
        if ocr_result['success']:
            # Update document with OCR results (I/O-bound, back in main thread)
            self._update_document_with_ocr(document, ocr_result)
            
            # Trigger screening refresh if needed
            try:
                self._trigger_screening_refresh(document.patient_id, document_id)
            except Exception as refresh_error:
                logger.warning(f"Screening refresh warning: {refresh_error}")
        
        return ocr_result
    
    def _process_bulk_documents(self, task: OCRTask) -> Dict[str, Any]:
        """Process OCR for multiple documents in parallel"""
        total_docs = len(task.document_ids)
        completed_docs = 0
        results = []
        
        # Process documents in batches to avoid overwhelming the system
        batch_size = min(self.max_processes, 10)  # Process max 10 at once
        
        for i in range(0, total_docs, batch_size):
            batch_ids = task.document_ids[i:i + batch_size]
            futures = []
            
            # Submit batch to process pool
            for doc_id in batch_ids:
                document = MedicalDocument.query.get(doc_id)
                if document and self._needs_ocr(document):
                    ocr_data = {
                        'document_id': doc_id,
                        'binary_content': document.binary_content,
                        'filename': document.filename,
                        'mime_type': getattr(document, 'mime_type', None),
                        'ocr_method': task.ocr_method,
                        'quality_threshold': task.quality_threshold
                    }
                    future = self.process_executor.submit(self._cpu_bound_ocr, ocr_data)
                    futures.append((doc_id, future))
            
            # Wait for batch completion
            for doc_id, future in futures:
                try:
                    ocr_result = future.result(timeout=300)  # 5 minute timeout per document
                    results.append(ocr_result)
                    
                    if ocr_result['success']:
                        document = MedicalDocument.query.get(doc_id)
                        if document:
                            self._update_document_with_ocr(document, ocr_result)
                    
                except Exception as e:
                    logger.error(f"OCR failed for document {doc_id}: {e}")
                    results.append({
                        'success': False,
                        'document_id': doc_id,
                        'error': str(e)
                    })
                
                completed_docs += 1
                task.progress = completed_docs / total_docs
                self._notify_progress(task)
        
        return {
            'total_processed': completed_docs,
            'successful': len([r for r in results if r.get('success')]),
            'failed': len([r for r in results if not r.get('success')]),
            'results': results
        }
    
    @staticmethod
    def _cpu_bound_ocr(ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        CPU-bound OCR processing function that runs in a separate process
        This function must be static to be pickle-able for multiprocessing
        """
        start_time = time.time()
        
        try:
            # Import OCR processor (must be done in each process)
            from ocr_document_processor import OCRDocumentProcessor
            
            processor = OCRDocumentProcessor()
            
            # Extract text using OCR
            extracted_text, confidence, quality_flags = processor._extract_text_with_ocr(
                ocr_data['filename'],
                ocr_data['binary_content']
            )
            
            processing_time = time.time() - start_time
            
            if extracted_text:
                return {
                    'success': True,
                    'document_id': ocr_data['document_id'],
                    'extracted_text': extracted_text,
                    'confidence_score': confidence,
                    'quality_flags': quality_flags,
                    'processing_time_seconds': processing_time,
                    'text_length': len(extracted_text)
                }
            else:
                return {
                    'success': False,
                    'document_id': ocr_data['document_id'],
                    'error': 'No text extracted from document',
                    'processing_time_seconds': processing_time
                }
                
        except Exception as e:
            return {
                'success': False,
                'document_id': ocr_data['document_id'],
                'error': str(e),
                'processing_time_seconds': time.time() - start_time
            }
    
    def _needs_ocr(self, document: MedicalDocument) -> bool:
        """Check if document needs OCR processing"""
        # Skip if already processed
        if getattr(document, 'ocr_processed', False):
            return False
        
        # Check if it's an image-based document
        from ocr_document_processor import OCRDocumentProcessor
        processor = OCRDocumentProcessor()
        
        filename = document.filename or document.document_name or ""
        return processor.is_image_based_document(filename, document.binary_content)
    
    def _update_document_with_ocr(self, document: MedicalDocument, ocr_result: Dict[str, Any]):
        """Update document with OCR results"""
        try:
            # Combine OCR text with existing content
            existing_content = document.content or ""
            extracted_text = ocr_result.get('extracted_text', '')
            
            if existing_content and extracted_text:
                combined_content = f"{existing_content}\n\n[OCR Extracted Text]\n{extracted_text}"
            else:
                combined_content = extracted_text or existing_content
            
            # Update document fields
            document.content = combined_content
            document.ocr_processed = True
            document.ocr_confidence = ocr_result.get('confidence_score', 0)
            document.ocr_processing_date = datetime.now()
            document.ocr_text_length = len(extracted_text)
            document.ocr_quality_flags = json.dumps(ocr_result.get('quality_flags', []))
            
            # Update metadata
            metadata = json.loads(document.doc_metadata) if document.doc_metadata else {}
            metadata.update({
                'ocr_processed': True,
                'ocr_confidence': ocr_result.get('confidence_score', 0),
                'ocr_processing_date': datetime.now().isoformat(),
                'ocr_text_length': len(extracted_text),
                'ocr_quality_flags': ocr_result.get('quality_flags', []),
                'background_processed': True
            })
            document.doc_metadata = json.dumps(metadata)
            
            # Commit to database
            db.session.commit()
            
            logger.info(f"✅ Updated document {document.id} with OCR results: {len(extracted_text)} characters")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Failed to update document {document.id} with OCR results: {e}")
            raise
    
    def _trigger_screening_refresh(self, patient_id: int, document_id: int):
        """Trigger screening refresh after OCR processing"""
        try:
            from selective_screening_refresh_manager import selective_refresh_manager, ChangeType
            from models import ScreeningType
            
            # Mark all active screening types as potentially affected
            active_screening_types = ScreeningType.query.filter_by(is_active=True).all()
            
            for screening_type in active_screening_types:
                selective_refresh_manager.mark_screening_type_dirty(
                    screening_type.id,
                    ChangeType.KEYWORDS,
                    f"no_ocr_document_{document_id}",
                    f"ocr_document_{document_id}_processed",
                    affected_criteria={"patient_id": patient_id}
                )
            
            # Process selective refresh
            refresh_stats = selective_refresh_manager.process_selective_refresh()
            logger.info(f"📊 Background OCR triggered screening refresh: {refresh_stats.screenings_updated} screenings updated")
            
        except Exception as e:
            logger.warning(f"Background screening refresh warning: {e}")
    
    def _notify_progress(self, task: OCRTask):
        """Notify progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def add_progress_callback(self, callback: Callable[[OCRTask], None]):
        """Add a progress callback function"""
        self.progress_callbacks.append(callback)


# Global background OCR processor instance
_background_ocr_processor = None

def get_background_ocr_processor() -> BackgroundOCRProcessor:
    """Get or create the global background OCR processor"""
    global _background_ocr_processor
    
    if _background_ocr_processor is None:
        _background_ocr_processor = BackgroundOCRProcessor()
        _background_ocr_processor.start()
    
    return _background_ocr_processor

def cleanup_background_ocr_processor():
    """Cleanup the background OCR processor"""
    global _background_ocr_processor
    
    if _background_ocr_processor is not None:
        _background_ocr_processor.stop()
        _background_ocr_processor = None