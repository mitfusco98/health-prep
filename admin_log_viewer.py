"""
Analysis: The provided code updates the admin log viewer to display more detailed information about patients, appointments, and form data changes. It enhances the formatting of log details to highlight key information such as Patient ID, Patient Name, Appointment ID, and specific changes made to appointment or form data.
"""

"""
Admin Log Viewer - Comprehensive view of all system activities
"""

from flask import render_template, request, jsonify, session, make_response
from app import app, db
from models import AdminLog, User, Patient
from admin_middleware import admin_required
from datetime import datetime, timedelta
import json
import logging
from sqlalchemy import desc, and_, or_, func

logger = logging.getLogger(__name__)


@app.route("/admin/logs")
@admin_required
def admin_logs():
    """
    Comprehensive admin log viewer with filtering and search
    """
    try:
        # Get filter parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)
        event_type = request.args.get("event_type", "")
        user_filter = request.args.get("user", "")
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")
        search_term = request.args.get("search", "")
        ip_filter = request.args.get("ip_address", "")
        sort_order = request.args.get("sort", "desc")  # desc or asc

        # Date range shortcuts
        date_range = request.args.get("date_range", "")
        if date_range:
            today = datetime.now().date()
            if date_range == "today":
                date_from = today.strftime("%Y-%m-%d")
                date_to = today.strftime("%Y-%m-%d")
            elif date_range == "yesterday":
                yesterday = today - timedelta(days=1)
                date_from = yesterday.strftime("%Y-%m-%d")
                date_to = yesterday.strftime("%Y-%m-%d")
            elif date_range == "week":
                week_ago = today - timedelta(days=7)
                date_from = week_ago.strftime("%Y-%m-%d")
                date_to = today.strftime("%Y-%m-%d")
            elif date_range == "month":
                month_ago = today - timedelta(days=30)
                date_from = month_ago.strftime("%Y-%m-%d")
                date_to = today.strftime("%Y-%m-%d")

        # Ensure fresh database session
        try:
            db.session.commit()
        except:
            db.session.rollback()
        
        # Build query with left join to User table
        query = AdminLog.query.outerjoin(User, AdminLog.user_id == User.id)

        # Apply filters
        if event_type:
            if event_type == "authentication":
                query = query.filter(
                    AdminLog.event_type.in_(["login_success", "login_fail", "logout"])
                )
            elif event_type == "patient_operations":
                query = query.filter(
                    AdminLog.event_type.in_(["view", "edit", "delete", "add"])
                )
            elif event_type == "alert_operations":
                query = query.filter(
                    AdminLog.event_type.in_(["alert_add", "alert_edit", "alert_delete"])
                )
            elif event_type == "appointment_operations":
                query = query.filter(
                    AdminLog.event_type.in_(
                        [
                            "appointment_addition",
                            "appointment_deletion",
                            "appointment_edit",
                        ]
                    )
                )
            elif event_type == "data_modifications":
                query = query.filter(AdminLog.event_type == "data_modification")
            elif event_type == "admin_actions":
                query = query.filter(AdminLog.event_type.like("admin_%"))
            elif event_type == "errors":
                error_conditions = [
                    AdminLog.event_type.in_(["error", "validation_error", "error_response"]),
                    AdminLog.event_type.like("%error%"),
                    AdminLog.event_details.like("%error%"),
                    AdminLog.event_details.like("%exception%"),
                    AdminLog.event_details.like("%traceback%")
                ]
                query = query.filter(or_(*error_conditions))
            else:
                query = query.filter(AdminLog.event_type.like(f"%{event_type}%"))

        if user_filter:
            query = query.filter(User.username.like(f"%{user_filter}%"))

        if ip_filter:
            query = query.filter(AdminLog.ip_address.like(f"%{ip_filter}%"))

        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(AdminLog.timestamp >= from_date)
            except ValueError:
                pass

        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(AdminLog.timestamp < to_date)
            except ValueError:
                pass

        if search_term:
            # Search in event_details JSON and other fields
            search_pattern = f"%{search_term}%"
            search_conditions = [
                AdminLog.event_details.ilike(search_pattern),
                AdminLog.event_type.ilike(search_pattern),
                AdminLog.ip_address.ilike(search_pattern),
                User.username.ilike(search_pattern)
            ]
            query = query.filter(or_(*search_conditions))

        # Apply sorting
        if sort_order == "asc":
            query = query.order_by(AdminLog.timestamp.asc())
        else:
            query = query.order_by(AdminLog.timestamp.desc())

        # Paginate with error handling
        try:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        except Exception as paginate_error:
            logger.warning(f"Pagination error, retrying with simple query: {str(paginate_error)}")
            # Fallback to simple query without filters
            simple_query = AdminLog.query.order_by(AdminLog.timestamp.desc())
            pagination = simple_query.paginate(page=1, per_page=per_page, error_out=False)

        logs = pagination.items

        # Get summary statistics with error handling
        try:
            total_logs = AdminLog.query.count()
        except:
            total_logs = 0
            
        try:
            today = datetime.now().date()
            today_logs = AdminLog.query.filter(AdminLog.timestamp >= today).count()
        except:
            today_logs = 0

        try:
            failed_logins_today = AdminLog.query.filter(
                and_(AdminLog.event_type == "login_fail", AdminLog.timestamp >= today)
            ).count()
        except:
            failed_logins_today = 0

        try:
            # Get recent activity (last 24 hours)
            recent_activity = AdminLog.query.filter(
                AdminLog.timestamp >= datetime.now() - timedelta(hours=24)
            ).count()
        except:
            recent_activity = 0

        try:
            # Get unique event types for filter dropdown
            event_types_raw = db.session.query(AdminLog.event_type).distinct().limit(100).all()
            event_types = sorted([et[0] for et in event_types_raw])
        except:
            event_types = []

        try:
            # Get unique users for filter dropdown
            users_raw = db.session.query(User.username).distinct().limit(100).all()
            users = sorted([u[0] for u in users_raw if u[0]])
        except:
            users = []

        # Process logs for display
        processed_logs = []
        for log in logs:
            log_data = {
                "id": log.id,
                "timestamp": log.timestamp,
                "event_type": log.event_type,
                "user": log.user.username if log.user else "Anonymous",
                "ip_address": log.ip_address,
                "details": format_log_details(log),
                "request_id": log.request_id,
                "user_agent": (
                    log.user_agent[:100] + "..."
                    if log.user_agent and len(log.user_agent) > 100
                    else log.user_agent
                ),
            }
            processed_logs.append(log_data)

        return render_template(
            "admin_logs.html",
            logs=processed_logs,
            pagination=pagination,
            total_logs=total_logs,
            today_logs=today_logs,
            failed_logins_today=failed_logins_today,
            recent_activity=recent_activity,
            event_types=event_types,
            users=users,
            current_filters={
                "event_type": event_type,
                "user": user_filter,
                "date_from": date_from,
                "date_to": date_to,
                "search": search_term,
                "ip_address": ip_filter,
                "per_page": per_page,
                "sort": sort_order,
                "date_range": date_range,
            },
        )

    except Exception as e:
        logger.error(f"Error in admin logs viewer: {str(e)}")
        
        # Try to reconnect to database and retry once
        try:
            db.session.rollback()
            db.session.close()
            
            # Retry the basic query without complex filters
            simple_query = AdminLog.query.order_by(AdminLog.timestamp.desc())
            pagination = simple_query.paginate(page=1, per_page=per_page, error_out=False)
            logs = pagination.items
            
            # Get basic stats
            total_logs = AdminLog.query.count()
            today_logs = 0
            failed_logins_today = 0
            recent_activity = 0
            
            # Get simple event types and users lists
            event_types = []
            users = []
            
            # Process logs for display
            processed_logs = []
            for log in logs:
                log_data = {
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "event_type": log.event_type,
                    "user": log.user.username if log.user else "Anonymous",
                    "ip_address": log.ip_address,
                    "details": format_log_details(log),
                    "request_id": log.request_id,
                    "user_agent": (
                        log.user_agent[:100] + "..."
                        if log.user_agent and len(log.user_agent) > 100
                        else log.user_agent
                    ),
                }
                processed_logs.append(log_data)
            
            # Ensure current_filters is defined
            current_filters = {
                "event_type": event_type,
                "user": user_filter,
                "date_from": date_from,
                "date_to": date_to,
                "search": search_term,
                "ip_address": ip_filter,
                "per_page": per_page,
                "sort": sort_order,
                "date_range": date_range,
            }
            
            return render_template(
                "admin_logs.html",
                logs=processed_logs,
                pagination=pagination,
                total_logs=total_logs,
                today_logs=today_logs,
                failed_logins_today=failed_logins_today,
                recent_activity=recent_activity,
                event_types=event_types,
                users=users,
                current_filters=current_filters,
                error="Database connection issue occurred. Showing recent logs without filters."
            )
            
        except Exception as retry_error:
            logger.error(f"Retry failed in admin logs viewer: {str(retry_error)}")
            
            # Ensure current_filters is defined even on error
            current_filters = {
                "event_type": event_type,
                "user": user_filter,
                "date_from": date_from,
                "date_to": date_to,
                "search": search_term,
                "ip_address": ip_filter,
                "per_page": per_page,
                "sort": sort_order,
                "date_range": date_range,
            }
            return render_template(
                "admin_logs.html", 
                logs=[], 
                error=f"Database connection error: {str(e)}. Please try again.",
                current_filters=current_filters,
                pagination=None,
                total_logs=0,
                today_logs=0,
                failed_logins_today=0,
                recent_activity=0,
                event_types=[],
                users=[]
            )


@app.route("/admin/logs/export")
@admin_required
def export_admin_logs():
    """
    Export admin logs as JSON or CSV
    """
    try:
        format_type = request.args.get("format", "json")
        days = request.args.get("days", 30, type=int)

        # Get logs from the last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        logs = (
            AdminLog.query.filter(AdminLog.timestamp >= cutoff_date)
            .order_by(desc(AdminLog.timestamp))
            .all()
        )

        export_data = []
        for log in logs:
            log_data = {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "username": log.user.username if log.user else "Anonymous",
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "request_id": log.request_id,
                "event_details": log.event_details_dict,
            }
            export_data.append(log_data)

        if format_type == "csv":
            # Convert to CSV format
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                ["Timestamp", "Event Type", "Username", "IP Address", "Details"]
            )

            # Write data
            for log in export_data:
                writer.writerow(
                    [
                        log["timestamp"],
                        log["event_type"],
                        log["username"],
                        log["ip_address"],
                        json.dumps(log["event_details"]),
                    ]
                )

            response = make_response(output.getvalue())
            response.headers["Content-Type"] = "text/csv"
            response.headers["Content-Disposition"] = (
                f"attachment; filename=admin_logs_{days}days.csv"
            )
            return response

        else:  # JSON format
            from flask import make_response

            response = make_response(json.dumps(export_data, indent=2))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Disposition"] = (
                f"attachment; filename=admin_logs_{days}days.json"
            )
            return response

    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


@app.route("/admin/logs/stats")
@admin_required
def admin_log_stats():
    """
    Get admin log statistics for dashboard
    """
    try:
        # Get various statistics
        stats = {}

        # Total logs
        stats["total_logs"] = AdminLog.query.count()

        # Today's activity
        today = datetime.now().date()
        stats["today_logs"] = AdminLog.query.filter(AdminLog.timestamp >= today).count()

        # Failed login attempts (last 24 hours)
        yesterday = datetime.now() - timedelta(hours=24)
        stats["failed_logins_24h"] = AdminLog.query.filter(
            and_(AdminLog.event_type == "login_fail", AdminLog.timestamp >= yesterday)
        ).count()

        # Patient access events (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        stats["patient_access_7d"] = AdminLog.query.filter(
            and_(AdminLog.event_type.like("patient_%"), AdminLog.timestamp >= week_ago)
        ).count()

        # Admin actions (last 7 days)
        stats["admin_actions_7d"] = AdminLog.query.filter(
            and_(AdminLog.event_type.like("admin_%"), AdminLog.timestamp >= week_ago)
        ).count()

        # Top event types (last 30 days)
        month_ago = datetime.now() - timedelta(days=30)
        top_events = (
            db.session.query(
                AdminLog.event_type, db.func.count(AdminLog.id).label("count")
            )
            .filter(AdminLog.timestamp >= month_ago)
            .group_by(AdminLog.event_type)
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        stats["top_event_types"] = [
            {"event_type": event[0], "count": event[1]} for event in top_events
        ]

        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": f"Stats generation failed: {str(e)}"}), 500


def format_log_details(log):
    """
    Format event details for display in admin logs
    Show Patient ID, Patient Name, Appointment ID, and form changes
    """
    # Parse event details if it's JSON
    if log.event_details:
        try:
            # Try parsing as JSON first
            if log.event_details.startswith("{"):
                event_data = json.loads(log.event_details)
            else:
                # If not JSON, try to evaluate as Python dict
                event_data = eval(log.event_details)

            if isinstance(event_data, dict):
                # Get standardized action from event_data or event_type
                action = event_data.get("action", log.event_type)

                # Map event types to standard actions
                if log.event_type == "appointment_addition":
                    action = "add"
                elif log.event_type == "appointment_deletion":
                    action = "delete"
                elif action not in ["view", "edit", "delete", "add"]:
                    # Map legacy event types
                    if "edit" in action.lower() or "update" in action.lower():
                        action = "edit"
                    elif "delete" in action.lower() or "remove" in action.lower():
                        action = "delete"
                    elif "add" in action.lower() or "create" in action.lower():
                        action = "add"
                    else:
                        action = "view"

                formatted_details = []

                # Start with standardized action
                action_badge_color = {
                    "view": "bg-secondary",
                    "edit": "bg-warning",
                    "delete": "bg-danger",
                    "add": "bg-success",
                }.get(action, "bg-dark")
                formatted_details.append(
                    f"<span class='badge {action_badge_color}'>Action: {action.title()}</span>"
                )

                # Show Patient information prominently
                patient_name = event_data.get("patient_name")
                patient_id = event_data.get("patient_id")

                if patient_name and patient_name != "Unknown":
                    formatted_details.append(
                        f"<span class='badge bg-info'>Patient: {patient_name}</span>"
                    )
                if patient_id:
                    formatted_details.append(
                        f"<span class='badge bg-primary'>Patient ID: {patient_id}</span>"
                    )

                # Show Appointment ID if present
                appointment_id = event_data.get("appointment_id")
                if appointment_id:
                    formatted_details.append(
                        f"<span class='badge bg-success'>Appointment ID: {appointment_id}</span>"
                    )

                # Show appointment details for add/delete operations
                if action in ["add", "delete"] and appointment_id:
                    appointment_date = event_data.get("appointment_date")
                    appointment_time = event_data.get("appointment_time")
                    appointment_note = event_data.get("note")

                    if appointment_date:
                        formatted_details.append(
                            f"<span class='badge bg-info'>Date: {appointment_date}</span>"
                        )
                    if appointment_time and appointment_time != "N/A":
                        formatted_details.append(
                            f"<span class='badge bg-info'>Time: {appointment_time}</span>"
                        )
                    if appointment_note:
                        formatted_details.append(
                            f"<span class='badge bg-secondary'>Note: {appointment_note}</span>"
                        )

                # Get data type from event_details for enhanced logging
                data_type = event_data.get("data_type", "")

                # Show alert details for add/edit/delete operations
                if (
                    "alert" in log.event_type.lower()
                    or "alert" in action.lower()
                    or data_type == "alert"
                ):
                    alert_text = event_data.get("alert_text") or event_data.get("text")
                    alert_date = event_data.get("alert_date") or event_data.get(
                        "date_created"
                    )
                    alert_time = event_data.get("alert_time") or event_data.get(
                        "time_created"
                    )
                    alert_priority = event_data.get("priority")
                    alert_type = event_data.get("alert_type")

                    if alert_text:
                        # Truncate long alert text for display
                        display_text = (
                            alert_text[:100] + "..."
                            if len(alert_text) > 100
                            else alert_text
                        )
                        formatted_details.append(
                            f"<span class='badge bg-warning'>Alert Text: {display_text}</span>"
                        )
                    if alert_date:
                        formatted_details.append(
                            f"<span class='badge bg-info'>Alert Date: {alert_date}</span>"
                        )
                    if alert_time:
                        formatted_details.append(
                            f"<span class='badge bg-info'>Alert Time: {alert_time}</span>"
                        )
                    if alert_priority:
                        formatted_details.append(
                            f"<span class='badge bg-danger'>Priority: {alert_priority}</span>"
                        )
                    if alert_type:
                        formatted_details.append(
                            f"<span class='badge bg-secondary'>Type: {alert_type}</span>"
                        )

                # Show medical data details (documents, conditions, vitals, etc.)
                medical_data_types = [
                    "document",
                    "condition",
                    "vital",
                    "lab",
                    "imaging",
                    "consult",
                    "hospital",
                    "immunization",
                ]
                is_medical_data = (
                    any(
                        data_type_check in log.event_type.lower()
                        for data_type_check in medical_data_types
                    )
                    or data_type in medical_data_types
                )

                if is_medical_data:
                    # Document-specific details (file-based submissions)
                    if "document" in log.event_type.lower() or data_type == "document":
                        file_name = (
                            event_data.get("file_name")
                            or event_data.get("filename")
                            or event_data.get("document_name")
                        )
                        file_type = event_data.get("file_type") or event_data.get(
                            "document_type"
                        )
                        upload_date = event_data.get("upload_date") or event_data.get(
                            "document_date"
                        )
                        upload_time = event_data.get("upload_time") or event_data.get(
                            "time_uploaded"
                        )
                        file_size = event_data.get("file_size")
                        provider = event_data.get("provider")

                        if file_name:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>File: {file_name}</span>"
                            )
                        if file_type:
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Type: {file_type}</span>"
                            )
                        if upload_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Date: {upload_date}</span>"
                            )
                        if upload_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Time: {upload_time}</span>"
                            )
                        if provider:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Provider: {provider}</span>"
                            )
                        if file_size:
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Size: {file_size}</span>"
                            )

                    # Lab/Test results details (test name + results)
                    elif (
                        "lab" in log.event_type.lower()
                        or "test" in log.event_type.lower()
                        or data_type == "lab"
                    ):
                        test_name = event_data.get("test_name") or event_data.get(
                            "lab_name"
                        )
                        test_date = event_data.get("test_date") or event_data.get(
                            "lab_date"
                        )
                        test_time = event_data.get("test_time") or event_data.get(
                            "lab_time"
                        )
                        result_value = (
                            event_data.get("result_value")
                            or event_data.get("result")
                            or event_data.get("value")
                        )
                        unit = event_data.get("unit")
                        reference_range = event_data.get("reference_range")
                        is_abnormal = event_data.get("is_abnormal")

                        if test_name:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Test: {test_name}</span>"
                            )
                        if test_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Date: {test_date}</span>"
                            )
                        if test_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Time: {test_time}</span>"
                            )
                        if result_value:
                            badge_class = "bg-danger" if is_abnormal else "bg-success"
                            formatted_details.append(
                                f"<span class='badge {badge_class}'>Result: {result_value}</span>"
                            )
                        if unit:
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Unit: {unit}</span>"
                            )
                        if reference_range:
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Range: {reference_range}</span>"
                            )

                    # Medical Condition details (condition name + diagnosis info)
                    elif (
                        "condition" in log.event_type.lower()
                        or data_type == "condition"
                    ):
                        condition_name = (
                            event_data.get("condition_name")
                            or event_data.get("name")
                            or event_data.get("diagnosis")
                        )
                        diagnosis_date = (
                            event_data.get("diagnosis_date")
                            or event_data.get("diagnosed_date")
                            or event_data.get("condition_date")
                        )
                        diagnosis_time = event_data.get(
                            "diagnosis_time"
                        ) or event_data.get("condition_time")
                        code = event_data.get("code") or event_data.get("icd_code")
                        is_active = event_data.get("is_active") or event_data.get(
                            "status"
                        )
                        severity = event_data.get("severity")
                        notes = event_data.get("notes")

                        if condition_name:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Condition: {condition_name}</span>"
                            )
                        if diagnosis_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Date: {diagnosis_date}</span>"
                            )
                        if diagnosis_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Time: {diagnosis_time}</span>"
                            )
                        if code:
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Code: {code}</span>"
                            )
                        if is_active is not None:
                            status_text = "Active" if is_active else "Inactive"
                            status_class = "bg-success" if is_active else "bg-warning"
                            formatted_details.append(
                                f"<span class='badge {status_class}'>Status: {status_text}</span>"
                            )
                        if severity:
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Severity: {severity}</span>"
                            )
                        if notes and len(notes.strip()) > 0:
                            truncated_notes = (
                                notes[:50] + "..." if len(notes) > 50 else notes
                            )
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Notes: {truncated_notes}</span>"
                            )

                    # Vital signs details (measurement values + date/time)
                    elif "vital" in log.event_type.lower() or data_type == "vital":
                        vital_date = (
                            event_data.get("vital_date")
                            or event_data.get("date")
                            or event_data.get("measurement_date")
                        )
                        vital_time = (
                            event_data.get("vital_time")
                            or event_data.get("time")
                            or event_data.get("measurement_time")
                        )
                        blood_pressure = event_data.get("blood_pressure")
                        systolic = event_data.get("blood_pressure_systolic")
                        diastolic = event_data.get("blood_pressure_diastolic")
                        heart_rate = event_data.get("heart_rate") or event_data.get(
                            "pulse"
                        )
                        temperature = event_data.get("temperature")
                        weight = event_data.get("weight")
                        height = event_data.get("height")
                        bmi = event_data.get("bmi")
                        oxygen_saturation = event_data.get("oxygen_saturation")

                        if vital_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Date: {vital_date}</span>"
                            )
                        if vital_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Time: {vital_time}</span>"
                            )
                        if blood_pressure:
                            formatted_details.append(
                                f"<span class='badge bg-success'>BP: {blood_pressure}</span>"
                            )
                        elif systolic and diastolic:
                            formatted_details.append(
                                f"<span class='badge bg-success'>BP: {systolic}/{diastolic}</span>"
                            )
                        if heart_rate:
                            formatted_details.append(
                                f"<span class='badge bg-success'>HR: {heart_rate} bpm</span>"
                            )
                        if temperature:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Temp: {temperature}°</span>"
                            )
                        if weight:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Weight: {weight}</span>"
                            )
                        if height:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Height: {height}</span>"
                            )
                        if bmi:
                            formatted_details.append(
                                f"<span class='badge bg-success'>BMI: {bmi}</span>"
                            )
                        if oxygen_saturation:
                            formatted_details.append(
                                f"<span class='badge bg-success'>O2 Sat: {oxygen_saturation}%</span>"
                            )

                    # Immunization details (vaccine name + administration info)
                    elif (
                        "immunization" in log.event_type.lower()
                        or data_type == "immunization"
                    ):
                        vaccine_name = event_data.get("vaccine_name") or event_data.get(
                            "immunization_name"
                        )
                        vaccination_date = (
                            event_data.get("vaccination_date")
                            or event_data.get("administration_date")
                            or event_data.get("immunization_date")
                        )
                        vaccination_time = (
                            event_data.get("vaccination_time")
                            or event_data.get("administration_time")
                            or event_data.get("immunization_time")
                        )
                        dose_number = event_data.get("dose_number") or event_data.get(
                            "dose"
                        )
                        manufacturer = event_data.get("manufacturer")
                        lot_number = event_data.get("lot_number")
                        notes = event_data.get("notes")

                        if vaccine_name:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Vaccine: {vaccine_name}</span>"
                            )
                        if vaccination_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Date: {vaccination_date}</span>"
                            )
                        if vaccination_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Time: {vaccination_time}</span>"
                            )
                        if dose_number:
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Dose: {dose_number}</span>"
                            )
                        if manufacturer:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Manufacturer: {manufacturer}</span>"
                            )
                        if lot_number:
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Lot: {lot_number}</span>"
                            )
                        if notes and len(notes.strip()) > 0:
                            truncated_notes = (
                                notes[:50] + "..." if len(notes) > 50 else notes
                            )
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Notes: {truncated_notes}</span>"
                            )

                    # Imaging Study details (study type + findings)
                    elif "imaging" in log.event_type.lower() or data_type == "imaging":
                        study_type = event_data.get("study_type") or event_data.get(
                            "imaging_type"
                        )
                        study_date = event_data.get("study_date") or event_data.get(
                            "imaging_date"
                        )
                        study_time = event_data.get("study_time") or event_data.get(
                            "imaging_time"
                        )
                        body_site = event_data.get("body_site") or event_data.get(
                            "location"
                        )
                        findings = event_data.get("findings")
                        impression = event_data.get("impression")

                        if study_type:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Study: {study_type}</span>"
                            )
                        if study_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Date: {study_date}</span>"
                            )
                        if study_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Time: {study_time}</span>"
                            )
                        if body_site:
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Site: {body_site}</span>"
                            )
                        if findings and len(findings.strip()) > 0:
                            truncated_findings = (
                                findings[:50] + "..."
                                if len(findings) > 50
                                else findings
                            )
                            formatted_details.append(
                                f"<span class='badge bg-success'>Findings: {truncated_findings}</span>"
                            )
                        if impression and len(impression.strip()) > 0:
                            truncated_impression = (
                                impression[:50] + "..."
                                if len(impression) > 50
                                else impression
                            )
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Impression: {truncated_impression}</span>"
                            )

                    # Consultation Report details (specialist + report info)
                    elif "consult" in log.event_type.lower() or data_type == "consult":
                        specialist = event_data.get("specialist") or event_data.get(
                            "consultant"
                        )
                        specialty = event_data.get("specialty") or event_data.get(
                            "speciality"
                        )
                        report_date = event_data.get("report_date") or event_data.get(
                            "consult_date"
                        )
                        report_time = event_data.get("report_time") or event_data.get(
                            "consult_time"
                        )
                        reason = event_data.get("reason") or event_data.get(
                            "referral_reason"
                        )
                        findings = event_data.get("findings")
                        recommendations = event_data.get("recommendations")

                        if specialist:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Specialist: {specialist}</span>"
                            )
                        if specialty:
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Specialty: {specialty}</span>"
                            )
                        if report_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Date: {report_date}</span>"
                            )
                        if report_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Time: {report_time}</span>"
                            )
                        if reason:
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Reason: {reason}</span>"
                            )
                        if findings and len(findings.strip()) > 0:
                            truncated_findings = (
                                findings[:50] + "..."
                                if len(findings) > 50
                                else findings
                            )
                            formatted_details.append(
                                f"<span class='badge bg-success'>Findings: {truncated_findings}</span>"
                            )
                        if recommendations and len(recommendations.strip()) > 0:
                            truncated_recommendations = (
                                recommendations[:50] + "..."
                                if len(recommendations) > 50
                                else recommendations
                            )
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Recommendations: {truncated_recommendations}</span>"
                            )

                    # Hospital Summary details (admission + discharge info)
                    elif (
                        "hospital" in log.event_type.lower() or data_type == "hospital"
                    ):
                        hospital_name = event_data.get(
                            "hospital_name"
                        ) or event_data.get("facility")
                        admission_date = event_data.get("admission_date")
                        admission_time = event_data.get("admission_time")
                        discharge_date = event_data.get("discharge_date")
                        discharge_time = event_data.get("discharge_time")
                        admitting_diagnosis = event_data.get("admitting_diagnosis")
                        discharge_diagnosis = event_data.get("discharge_diagnosis")
                        procedures = event_data.get("procedures")

                        if hospital_name:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Hospital: {hospital_name}</span>"
                            )
                        if admission_date:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Admission: {admission_date}</span>"
                            )
                        if admission_time:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Admission Time: {admission_time}</span>"
                            )
                        if discharge_date:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Discharge: {discharge_date}</span>"
                            )
                        if discharge_time:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Discharge Time: {discharge_time}</span>"
                            )
                        if admitting_diagnosis:
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Admit Dx: {admitting_diagnosis}</span>"
                            )
                        if discharge_diagnosis:
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Discharge Dx: {discharge_diagnosis}</span>"
                            )
                        if procedures and len(procedures.strip()) > 0:
                            truncated_procedures = (
                                procedures[:50] + "..."
                                if len(procedures) > 50
                                else procedures
                            )
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Procedures: {truncated_procedures}</span>"
                            )

                # Show screening-related details (screening types and individual screenings)
                screening_data_types = ["screening_type", "screening"]
                is_screening_data = (
                    any(
                        screening_type_check in log.event_type.lower()
                        for screening_type_check in ["screening"]
                    )
                    or data_type in screening_data_types
                )

                if is_screening_data:
                    # Screening Type details (name, frequency, age criteria, etc.)
                    if (
                        data_type == "screening_type"
                        or "screening_type" in log.event_type.lower()
                    ):
                        screening_type_name = event_data.get("screening_type_name")
                        description = event_data.get("description")
                        default_frequency = event_data.get("default_frequency")
                        gender_specific = event_data.get("gender_specific")
                        min_age = event_data.get("min_age")
                        max_age = event_data.get("max_age")
                        is_active = event_data.get("is_active")
                        patient_usage_count = event_data.get("patient_usage_count")
                        deactivation_reason = event_data.get("deactivation_reason")

                        if screening_type_name:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Screening Type: {screening_type_name}</span>"
                            )
                        if description and len(description.strip()) > 0:
                            truncated_desc = (
                                description[:60] + "..."
                                if len(description) > 60
                                else description
                            )
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Description: {truncated_desc}</span>"
                            )
                        if default_frequency and default_frequency != "None":
                            formatted_details.append(
                                f"<span class='badge bg-info'>Frequency: {default_frequency}</span>"
                            )
                        if gender_specific and gender_specific != "All Genders":
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Gender: {gender_specific}</span>"
                            )
                        if min_age and min_age != "None":
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Min Age: {min_age}</span>"
                            )
                        if max_age and max_age != "None":
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Max Age: {max_age}</span>"
                            )
                        if is_active is not None:
                            status_text = "Active" if is_active else "Inactive"
                            status_class = "bg-success" if is_active else "bg-danger"
                            formatted_details.append(
                                f"<span class='badge {status_class}'>Status: {status_text}</span>"
                            )
                        if patient_usage_count is not None:
                            formatted_details.append(
                                f"<span class='badge bg-info'>Patient Usage: {patient_usage_count}</span>"
                            )
                        if deactivation_reason:
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Reason: {deactivation_reason}</span>"
                            )

                    # Individual Screening details (patient screening recommendations)
                    elif data_type == "screening" or (
                        "screening" in log.event_type.lower()
                        and "screening_type" not in log.event_type.lower()
                    ):
                        screening_id = event_data.get("screening_id")
                        screening_type = event_data.get("screening_type")
                        due_date = event_data.get("due_date")
                        last_completed = event_data.get("last_completed")
                        priority = event_data.get("priority")
                        frequency = event_data.get("frequency")
                        notes = event_data.get("notes")

                        if screening_id:
                            formatted_details.append(
                                f"<span class='badge bg-primary'>Screening ID: {screening_id}</span>"
                            )
                        if screening_type:
                            formatted_details.append(
                                f"<span class='badge bg-success'>Type: {screening_type}</span>"
                            )
                        if due_date and due_date != "None":
                            formatted_details.append(
                                f"<span class='badge bg-warning'>Due Date: {due_date}</span>"
                            )
                        if last_completed and last_completed != "None":
                            formatted_details.append(
                                f"<span class='badge bg-info'>Last Completed: {last_completed}</span>"
                            )
                        if priority and priority != "None":
                            priority_class = {
                                "High": "bg-danger",
                                "Medium": "bg-warning",
                                "Low": "bg-secondary",
                            }.get(priority, "bg-secondary")
                            formatted_details.append(
                                f"<span class='badge {priority_class}'>Priority: {priority}</span>"
                            )
                        if frequency and frequency != "None":
                            formatted_details.append(
                                f"<span class='badge bg-light text-dark'>Frequency: {frequency}</span>"
                            )
                        if notes and len(notes.strip()) > 0 and notes != "None":
                            truncated_notes = (
                                notes[:60] + "..." if len(notes) > 60 else notes
                            )
                            formatted_details.append(
                                f"<span class='badge bg-secondary'>Notes: {truncated_notes}</span>"
                            )

                # Show page address/endpoint
                page_address = None
                if "endpoint" in event_data:
                    page_address = event_data["endpoint"]
                elif "route" in event_data:
                    page_address = event_data["route"]

                if page_address:
                    formatted_details.append(
                        f"<span class='badge bg-dark'>Page: {page_address}</span>"
                    )

                # Show form changes for any edit action
                if action == "edit" and "form_changes" in event_data:
                    changes = event_data["form_changes"]
                    if changes:
                        formatted_details.append(
                            "<div class='mt-1'><strong>Changes Made:</strong></div>"
                        )
                        for change_key, change_value in changes.items():
                            # Clean up the key for display (remove prefixes like 'appointment_', 'demographics_', etc.)
                            display_key = (
                                change_key.replace("appointment_", "")
                                .replace("demographics_", "")
                                .replace("alert_", "")
                                .replace("screening_", "")
                            )
                            change_label = display_key.replace("_", " ").title()
                            formatted_details.append(
                                f"&nbsp;&nbsp;• {change_label}: <span class='text-primary'>{change_value}</span>"
                            )

                # Show relevant technical details
                relevant_details = []
                for key, value in event_data.items():
                    if key in [
                        "endpoint",
                        "route",
                        "path",
                        "appointment_id",
                        "patient_name",
                        "patient_id",
                        "form_changes",
                    ]:
                        continue  # Already shown above

                    # Include specific technical details
                    if key in ["method", "ip_address", "function_name"]:
                        if key == "method":
                            relevant_details.append(f"Method: {value}")
                        elif key == "ip_address":
                            relevant_details.append(f"IP: {value}")
                        elif key == "function_name":
                            relevant_details.append(f"Function: {value}")

                if relevant_details:
                    formatted_details.append(
                        "<div class='mt-1'><small class='text-muted'>"
                    )
                    formatted_details.extend(relevant_details)
                    formatted_details.append("</small></div>")

                return "<br>".join(formatted_details)
        except Exception as e:
            # Log the parsing error but don't show it to users
            pass

    # If parsing fails, show simplified format
    action_type = log.event_type.replace("_", " ").title()
    return f"<span class='badge bg-secondary'>{action_type}</span>"
