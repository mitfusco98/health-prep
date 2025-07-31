#!/usr/bin/env python3
"""
Background Task Routes
API endpoints for managing and monitoring background tasks (OCR, bulk operations)
"""

from flask import jsonify, request, session, render_template, flash, redirect, url_for
from app import app
import logging

logger = logging.getLogger(__name__)


@app.route("/api/ocr/status/<task_id>", methods=["GET"])
def get_ocr_task_status(task_id):
    """Get the status of a specific OCR task"""
    try:
        from background_ocr_processor import get_background_ocr_processor
        
        processor = get_background_ocr_processor()
        task_status = processor.get_task_status(task_id)
        
        if task_status:
            return jsonify({
                "success": True,
                "task": task_status
            })
        else:
            return jsonify({
                "success": False,
                "error": "Task not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting OCR task status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/ocr/status", methods=["GET"])
def get_all_ocr_tasks():
    """Get status of all OCR tasks"""
    try:
        from background_ocr_processor import get_background_ocr_processor
        
        processor = get_background_ocr_processor()
        all_tasks = processor.get_all_tasks()
        
        return jsonify({
            "success": True,
            "tasks": all_tasks
        })
        
    except Exception as e:
        logger.error(f"Error getting all OCR tasks: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/ocr/user-tasks", methods=["GET"])
def get_user_ocr_tasks():
    """Get OCR tasks for the current user session"""
    try:
        user_tasks = session.get('ocr_tasks', [])
        
        # Get detailed status for each task
        from background_ocr_processor import get_background_ocr_processor
        processor = get_background_ocr_processor()
        
        detailed_tasks = []
        for task_info in user_tasks:
            task_status = processor.get_task_status(task_info['task_id'])
            if task_status:
                task_status.update(task_info)  # Add session info
                detailed_tasks.append(task_status)
        
        return jsonify({
            "success": True,
            "tasks": detailed_tasks
        })
        
    except Exception as e:
        logger.error(f"Error getting user OCR tasks: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/ocr/queue", methods=["POST"])
def queue_bulk_ocr():
    """Queue multiple documents for OCR processing"""
    try:
        data = request.get_json()
        document_ids = data.get('document_ids', [])
        patient_ids = data.get('patient_ids', [])
        priority = data.get('priority', 'normal')
        
        if not document_ids:
            return jsonify({
                "success": False,
                "error": "No document IDs provided"
            }), 400
        
        from background_ocr_processor import get_background_ocr_processor, TaskPriority
        
        # Map priority string to enum
        priority_map = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'urgent': TaskPriority.URGENT
        }
        task_priority = priority_map.get(priority.lower(), TaskPriority.NORMAL)
        
        processor = get_background_ocr_processor()
        task_id = processor.queue_bulk_document_ocr(
            document_ids=document_ids,
            patient_ids=patient_ids,
            priority=task_priority,
            context={
                'bulk_request': True,
                'user_id': session.get('user_id'),
                'requested_at': data.get('timestamp')
            }
        )
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"Queued {len(document_ids)} documents for OCR processing"
        })
        
    except Exception as e:
        logger.error(f"Error queueing bulk OCR: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/background-tasks/stats", methods=["GET"])
def get_background_task_stats():
    """Get overall background task statistics"""
    try:
        from background_ocr_processor import get_background_ocr_processor
        from background_screening_processor import BackgroundScreeningProcessor
        
        stats = {
            "ocr_processor": {
                "available": True,
                "tasks": {}
            },
            "screening_processor": {
                "available": False,
                "tasks": {}
            }
        }
        
        # OCR processor stats
        try:
            ocr_processor = get_background_ocr_processor()
            ocr_tasks = ocr_processor.get_all_tasks()
            stats["ocr_processor"]["tasks"] = {
                "active_count": len(ocr_tasks.get("active", [])),
                "completed_count": len(ocr_tasks.get("completed", [])),
                "queue_size": ocr_tasks.get("queue_size", 0)
            }
        except Exception as ocr_error:
            stats["ocr_processor"]["available"] = False
            stats["ocr_processor"]["error"] = str(ocr_error)
        
        # Future: Add screening processor stats when implemented
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting background task stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/background-tasks", methods=["GET"])
def background_tasks_dashboard():
    """Web dashboard for monitoring background tasks"""
    try:
        # Get task statistics
        from background_ocr_processor import get_background_ocr_processor
        
        processor = get_background_ocr_processor()
        all_tasks = processor.get_all_tasks()
        user_tasks = session.get('ocr_tasks', [])
        
        return render_template(
            "background_tasks.html",
            title="Background Tasks",
            all_tasks=all_tasks,
            user_tasks=user_tasks,
            active_count=len(all_tasks.get("active", [])),
            completed_count=len(all_tasks.get("completed", [])),
            queue_size=all_tasks.get("queue_size", 0)
        )
        
    except Exception as e:
        logger.error(f"Error loading background tasks dashboard: {e}")
        flash(f"Error loading background tasks: {str(e)}", "error")
        return redirect(url_for("index"))


# Background task JavaScript functions are embedded in the template