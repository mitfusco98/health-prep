"""
API Routes for Selective Refresh System
Provides REST endpoints for monitoring and controlling selective refresh operations
"""

from flask import jsonify, request
from app import app
from selective_screening_refresh_manager import selective_refresh_manager
from screening_cache_manager import screening_cache_manager
from background_screening_processor import background_processor


@app.route("/api/selective-refresh/status")
def get_selective_refresh_status():
    """Get current status of selective refresh system"""
    try:
        refresh_status = selective_refresh_manager.get_refresh_status()
        cache_stats = screening_cache_manager.get_cache_statistics()
        processing_stats = background_processor.get_processing_stats()
        
        return jsonify({
            "success": True,
            "refresh_manager": refresh_status,
            "cache_manager": cache_stats.to_dict() if hasattr(cache_stats, 'to_dict') else cache_stats.__dict__,
            "background_processor": processing_stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/selective-refresh/tasks")
def get_background_tasks():
    """Get list of background processing tasks"""
    try:
        include_completed = request.args.get('include_completed', 'true').lower() == 'true'
        tasks = background_processor.get_all_task_statuses(include_completed=include_completed)
        
        return jsonify({
            "success": True,
            "tasks": tasks,
            "total_tasks": len(tasks)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/selective-refresh/tasks/<task_id>")
def get_task_status(task_id):
    """Get status of a specific background task"""
    try:
        task_status = background_processor.get_task_status(task_id)
        
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
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/selective-refresh/tasks/<task_id>/cancel", methods=["POST"])
def cancel_background_task(task_id):
    """Cancel a background processing task"""
    try:
        success = background_processor.cancel_task(task_id)
        
        return jsonify({
            "success": success,
            "message": "Task cancelled successfully" if success else "Task not found or cannot be cancelled"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/selective-refresh/cache/invalidate", methods=["POST"])
def invalidate_cache():
    """Manually invalidate cache entries"""
    try:
        data = request.get_json() or {}
        
        if 'patient_id' in data:
            count = screening_cache_manager.invalidate_patient_cache(data['patient_id'])
            return jsonify({
                "success": True,
                "message": f"Invalidated {count} cache entries for patient {data['patient_id']}"
            })
            
        elif 'screening_type_id' in data:
            count = screening_cache_manager.invalidate_screening_type(data['screening_type_id'])
            return jsonify({
                "success": True,
                "message": f"Invalidated {count} cache entries for screening type {data['screening_type_id']}"
            })
            
        elif 'dependency' in data:
            count = screening_cache_manager.invalidate_by_dependency(data['dependency'])
            return jsonify({
                "success": True,
                "message": f"Invalidated {count} cache entries for dependency {data['dependency']}"
            })
            
        elif data.get('clear_all'):
            count = screening_cache_manager.clear_cache()
            return jsonify({
                "success": True,
                "message": f"Cleared all {count} cache entries"
            })
            
        else:
            return jsonify({
                "success": False,
                "error": "Must specify patient_id, screening_type_id, dependency, or clear_all"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/selective-refresh/force-refresh", methods=["POST"])
def force_selective_refresh():
    """Force a selective refresh operation"""
    try:
        data = request.get_json() or {}
        force_all = data.get('force_all', False)
        
        stats = selective_refresh_manager.process_selective_refresh(force_all=force_all)
        
        return jsonify({
            "success": True,
            "stats": {
                "total_patients_checked": stats.total_patients_checked,
                "affected_patients": stats.affected_patients,
                "screenings_updated": stats.screenings_updated,
                "screenings_cached": stats.screenings_cached,
                "processing_time": stats.processing_time,
                "change_summary": stats.change_summary
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/selective-refresh/patient/<int:patient_id>/cache-info")
def get_patient_cache_info(patient_id):
    """Get cache information for a specific patient"""
    try:
        cache_info = screening_cache_manager.get_cache_info_for_patient(patient_id)
        
        return jsonify({
            "success": True,
            "patient_id": patient_id,
            "cache_info": cache_info
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500