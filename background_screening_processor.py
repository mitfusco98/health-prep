"""
Background Screening Processor
Implements asynchronous background processing for screening refresh operations
"""

import json
import time
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from app import app, db
from models import Patient, ScreeningType


class TaskStatus(Enum):
    """Status of background tasks"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Priority levels for background tasks"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class BackgroundTask:
    """Represents a background processing task"""
    task_id: str
    task_type: str
    priority: TaskPriority
    patient_ids: List[int]
    screening_type_ids: Optional[List[int]]
    context: Dict[str, Any]
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "patient_count": len(self.patient_ids),
            "screening_type_count": len(self.screening_type_ids) if self.screening_type_ids else 0,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "estimated_duration": self._estimate_duration(),
        }
        
    def _estimate_duration(self) -> float:
        """Estimate task duration in seconds"""
        base_time_per_patient = 2.0  # seconds
        screening_factor = 1.0 + (len(self.screening_type_ids) * 0.2 if self.screening_type_ids else 0)
        return len(self.patient_ids) * base_time_per_patient * screening_factor


@dataclass
class ProcessingStats:
    """Statistics for background processing"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_patients_processed: int = 0
    total_screenings_updated: int = 0
    average_processing_time: float = 0.0
    last_processing_time: Optional[datetime] = None


class BackgroundScreeningProcessor:
    """Manages background processing of screening refresh operations"""
    
    def __init__(self, max_workers: int = 2, batch_size: int = 50):
        self.task_queue = queue.PriorityQueue()
        self.active_tasks: Dict[str, BackgroundTask] = {}
        self.completed_tasks: Dict[str, BackgroundTask] = {}
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.workers: List[threading.Thread] = []
        self.is_running = False
        self.stats = ProcessingStats()
        self.task_completion_callbacks: List[Callable] = []
        
        # Start worker threads
        self.start_workers()
        
    def start_workers(self):
        """Start background worker threads"""
        if self.is_running:
            return
            
        self.is_running = True
        
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"ScreeningWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            
        print(f"🚀 Started {self.max_workers} background screening workers")
        
    def stop_workers(self):
        """Stop background worker threads"""
        self.is_running = False
        
        # Add sentinel values to wake up workers
        for _ in range(self.max_workers):
            self.task_queue.put((TaskPriority.LOW.value, time.time(), None))
            
        # Wait for workers to finish
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=30)
                
        self.workers.clear()
        print("⏹️ Stopped background screening workers")
        
    def submit_screening_refresh_task(
        self,
        patient_ids: List[int],
        screening_type_ids: Optional[List[int]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        context: Dict[str, Any] = None
    ) -> str:
        """Submit a screening refresh task for background processing"""
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask(
            task_id=task_id,
            task_type="screening_refresh",
            priority=priority,
            patient_ids=patient_ids,
            screening_type_ids=screening_type_ids,
            context=context or {},
            status=TaskStatus.PENDING,
            progress=0.0,
            result=None,
            error_message=None,
            created_at=datetime.utcnow(),
            started_at=None,
            completed_at=None
        )
        
        # Add to queue with priority
        queue_item = (
            -priority.value,  # Negative for high priority first
            time.time(),      # Timestamp for FIFO within same priority
            task
        )
        
        self.task_queue.put(queue_item)
        self.active_tasks[task_id] = task
        
        print(f"📋 Submitted screening refresh task {task_id[:8]} for {len(patient_ids)} patients")
        
        return task_id
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task"""
        # Check active tasks
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].to_dict()
            
        # Check completed tasks
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id].to_dict()
            
        return None
        
    def get_all_task_statuses(self, include_completed: bool = True) -> List[Dict[str, Any]]:
        """Get status of all tasks"""
        statuses = []
        
        # Add active tasks
        for task in self.active_tasks.values():
            statuses.append(task.to_dict())
            
        # Add completed tasks if requested
        if include_completed:
            for task in self.completed_tasks.values():
                statuses.append(task.to_dict())
                
        # Sort by creation time (newest first)
        statuses.sort(key=lambda x: x['created_at'], reverse=True)
        
        return statuses
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()
                print(f"❌ Cancelled task {task_id[:8]}")
                return True
                
        return False
        
    def add_completion_callback(self, callback: Callable):
        """Add a callback to be called when tasks complete"""
        self.task_completion_callbacks.append(callback)
        
    def _worker_loop(self):
        """Main loop for worker threads"""
        while self.is_running:
            try:
                # Get next task from queue (blocking with timeout)
                try:
                    priority, timestamp, task = self.task_queue.get(timeout=5.0)
                except queue.Empty:
                    continue
                    
                # Check for sentinel value (shutdown signal)
                if task is None:
                    break
                    
                # Check if task was cancelled
                if task.status == TaskStatus.CANCELLED:
                    continue
                    
                # Process the task
                self._process_task(task)
                
            except Exception as e:
                print(f"❌ Error in worker loop: {e}")
                time.sleep(1)
                
    def _process_task(self, task: BackgroundTask):
        """Process a single screening refresh task"""
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            task.progress = 0.0
            
            print(f"🔄 Processing task {task.task_id[:8]} - {len(task.patient_ids)} patients")
            
            # Import here to avoid circular imports
            from selective_screening_refresh_manager import selective_refresh_manager
            from screening_cache_manager import screening_cache_manager
            
            processed_count = 0
            total_screenings_updated = 0
            errors = []
            
            # Process patients in batches
            for i in range(0, len(task.patient_ids), self.batch_size):
                # Check if task was cancelled
                if task.status == TaskStatus.CANCELLED:
                    break
                    
                batch = task.patient_ids[i:i + self.batch_size]
                
                try:
                    # Process batch with Flask app context
                    with app.app_context():
                        batch_results = self._process_patient_batch(
                            batch, 
                            task.screening_type_ids,
                            task.context
                        )
                        
                        processed_count += len(batch)
                        total_screenings_updated += batch_results.get('screenings_updated', 0)
                        
                        # Update progress
                        task.progress = processed_count / len(task.patient_ids)
                        
                except Exception as e:
                    error_msg = f"Batch {i//self.batch_size + 1} failed: {str(e)}"
                    errors.append(error_msg)
                    print(f"⚠️ {error_msg}")
                    
            # Finalize task
            if task.status != TaskStatus.CANCELLED:
                if errors:
                    task.status = TaskStatus.FAILED if len(errors) > len(task.patient_ids) / 2 else TaskStatus.COMPLETED
                    task.error_message = "; ".join(errors[:3])  # Keep first 3 errors
                else:
                    task.status = TaskStatus.COMPLETED
                    
                task.result = {
                    "patients_processed": processed_count,
                    "screenings_updated": total_screenings_updated,
                    "errors": len(errors),
                    "processing_time": (datetime.utcnow() - task.started_at).total_seconds()
                }
                
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            
            # Move to completed tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            self.completed_tasks[task.task_id] = task
            
            # Update stats
            if task.status == TaskStatus.COMPLETED:
                self.stats.tasks_completed += 1
                self.stats.total_patients_processed += processed_count
                self.stats.total_screenings_updated += total_screenings_updated
            else:
                self.stats.tasks_failed += 1
                
            self.stats.last_processing_time = datetime.utcnow()
            
            # Call completion callbacks
            for callback in self.task_completion_callbacks:
                try:
                    callback(task)
                except Exception as e:
                    print(f"⚠️ Callback error: {e}")
                    
            print(f"✅ Completed task {task.task_id[:8]} - {task.status.value}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            print(f"❌ Task {task.task_id[:8]} failed: {e}")
            
    def _process_patient_batch(
        self, 
        patient_ids: List[int], 
        screening_type_ids: Optional[List[int]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a batch of patients"""
        try:
            from automated_screening_engine import ScreeningStatusEngine
            engine = ScreeningStatusEngine()
            
            screenings_updated = 0
            
            for patient_id in patient_ids:
                try:
                    # Generate screenings for patient
                    screenings = engine.generate_patient_screenings(patient_id)
                    
                    # Filter to specific screening types if specified
                    if screening_type_ids:
                        relevant_screenings = []
                        for screening in screenings:
                            for st_id in screening_type_ids:
                                screening_type = ScreeningType.query.get(st_id)
                                if screening_type and screening_type.name == screening['screening_type']:
                                    relevant_screenings.append(screening)
                                    break
                        screenings = relevant_screenings
                        
                    screenings_updated += len(screenings)
                    
                except Exception as e:
                    print(f"⚠️ Error processing patient {patient_id}: {e}")
                    continue
                    
            # Commit batch
            db.session.commit()
            
            return {
                "patients_processed": len(patient_ids),
                "screenings_updated": screenings_updated
            }
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        active_count = len(self.active_tasks)
        pending_count = sum(1 for task in self.active_tasks.values() if task.status == TaskStatus.PENDING)
        running_count = sum(1 for task in self.active_tasks.values() if task.status == TaskStatus.RUNNING)
        
        return {
            "active_tasks": active_count,
            "pending_tasks": pending_count,
            "running_tasks": running_count,
            "completed_tasks": len(self.completed_tasks),
            "total_tasks_completed": self.stats.tasks_completed,
            "total_tasks_failed": self.stats.tasks_failed,
            "total_patients_processed": self.stats.total_patients_processed,
            "total_screenings_updated": self.stats.total_screenings_updated,
            "last_processing_time": self.stats.last_processing_time.isoformat() if self.stats.last_processing_time else None,
            "workers_running": len([w for w in self.workers if w.is_alive()]),
            "is_running": self.is_running
        }
        
    def cleanup_old_tasks(self, hours: int = 24):
        """Remove old completed tasks to prevent memory buildup"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        tasks_to_remove = [
            task_id for task_id, task in self.completed_tasks.items()
            if task.completed_at and task.completed_at < cutoff_time
        ]
        
        for task_id in tasks_to_remove:
            del self.completed_tasks[task_id]
            
        if tasks_to_remove:
            print(f"🧹 Cleaned up {len(tasks_to_remove)} old completed tasks")


# Global instance
background_processor = BackgroundScreeningProcessor()