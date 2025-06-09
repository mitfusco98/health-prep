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
from sqlalchemy import desc, and_, or_

logger = logging.getLogger(__name__)

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """
    Comprehensive admin log viewer with filtering and search
    """
    try:
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        event_type = request.args.get('event_type', '')
        user_filter = request.args.get('user', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        search_term = request.args.get('search', '')

        # Build query
        query = AdminLog.query

        # Apply filters
        if event_type:
            query = query.filter(AdminLog.event_type.like(f'%{event_type}%'))

        if user_filter:
            # Join with User table to filter by username
            query = query.join(User, AdminLog.user_id == User.id, isouter=True)
            query = query.filter(User.username.like(f'%{user_filter}%'))

        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(AdminLog.timestamp >= from_date)
            except ValueError:
                pass

        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(AdminLog.timestamp < to_date)
            except ValueError:
                pass

        if search_term:
            # Search in event_details JSON
            query = query.filter(AdminLog.event_details.like(f'%{search_term}%'))

        # Order by timestamp (newest first)
        query = query.order_by(desc(AdminLog.timestamp))

        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )

        logs = pagination.items

        # Get summary statistics
        total_logs = AdminLog.query.count()
        today_logs = AdminLog.query.filter(
            AdminLog.timestamp >= datetime.now().date()
        ).count()

        failed_logins_today = AdminLog.query.filter(
            and_(
                AdminLog.event_type == 'login_fail',
                AdminLog.timestamp >= datetime.now().date()
            )
        ).count()

        # Get unique event types for filter dropdown
        event_types = db.session.query(AdminLog.event_type).distinct().all()
        event_types = [et[0] for et in event_types]

        # Process logs for display
        processed_logs = []
        for log in logs:
            log_data = {
                'id': log.id,
                'timestamp': log.timestamp,
                'event_type': log.event_type,
                'user': log.user.username if log.user else 'Anonymous',
                'ip_address': log.ip_address,
                'details': format_log_details(log.event_details_dict),
                'request_id': log.request_id
            }
            processed_logs.append(log_data)

        return render_template('admin_logs.html',
                             logs=processed_logs,
                             pagination=pagination,
                             total_logs=total_logs,
                             today_logs=today_logs,
                             failed_logins_today=failed_logins_today,
                             event_types=event_types,
                             current_filters={
                                 'event_type': event_type,
                                 'user': user_filter,
                                 'date_from': date_from,
                                 'date_to': date_to,
                                 'search': search_term,
                                 'per_page': per_page
                             })

    except Exception as e:
        logger.error(f"Error in admin logs viewer: {str(e)}")
        return render_template('admin_logs.html', 
                             logs=[], 
                             error=f"Error loading logs: {str(e)}")

@app.route('/admin/logs/export')
@admin_required
def export_admin_logs():
    """
    Export admin logs as JSON or CSV
    """
    try:
        format_type = request.args.get('format', 'json')
        days = request.args.get('days', 30, type=int)

        # Get logs from the last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        logs = AdminLog.query.filter(
            AdminLog.timestamp >= cutoff_date
        ).order_by(desc(AdminLog.timestamp)).all()

        export_data = []
        for log in logs:
            log_data = {
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'event_type': log.event_type,
                'user_id': log.user_id,
                'username': log.user.username if log.user else 'Anonymous',
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'request_id': log.request_id,
                'event_details': log.event_details_dict
            }
            export_data.append(log_data)

        if format_type == 'csv':
            # Convert to CSV format
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(['Timestamp', 'Event Type', 'Username', 'IP Address', 'Details'])

            # Write data
            for log in export_data:
                writer.writerow([
                    log['timestamp'],
                    log['event_type'],
                    log['username'],
                    log['ip_address'],
                    json.dumps(log['event_details'])
                ])

            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=admin_logs_{days}days.csv'
            return response

        else:  # JSON format
            from flask import make_response
            response = make_response(json.dumps(export_data, indent=2))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename=admin_logs_{days}days.json'
            return response

    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/admin/logs/stats')
@admin_required
def admin_log_stats():
    """
    Get admin log statistics for dashboard
    """
    try:
        # Get various statistics
        stats = {}

        # Total logs
        stats['total_logs'] = AdminLog.query.count()

        # Today's activity
        today = datetime.now().date()
        stats['today_logs'] = AdminLog.query.filter(
            AdminLog.timestamp >= today
        ).count()

        # Failed login attempts (last 24 hours)
        yesterday = datetime.now() - timedelta(hours=24)
        stats['failed_logins_24h'] = AdminLog.query.filter(
            and_(
                AdminLog.event_type == 'login_fail',
                AdminLog.timestamp >= yesterday
            )
        ).count()

        # Patient access events (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        stats['patient_access_7d'] = AdminLog.query.filter(
            and_(
                AdminLog.event_type.like('patient_%'),
                AdminLog.timestamp >= week_ago
            )
        ).count()

        # Admin actions (last 7 days)
        stats['admin_actions_7d'] = AdminLog.query.filter(
            and_(
                AdminLog.event_type.like('admin_%'),
                AdminLog.timestamp >= week_ago
            )
        ).count()

        # Top event types (last 30 days)
        month_ago = datetime.now() - timedelta(days=30)
        top_events = db.session.query(
            AdminLog.event_type,
            db.func.count(AdminLog.id).label('count')
        ).filter(
            AdminLog.timestamp >= month_ago
        ).group_by(AdminLog.event_type).order_by(
            desc('count')
        ).limit(10).all()

        stats['top_event_types'] = [
            {'event_type': event[0], 'count': event[1]} 
            for event in top_events
        ]

        return jsonify(stats)

    except Exception as e:
        return jsonify({'error': f'Stats generation failed: {str(e)}'}), 500

def format_log_details(log_or_details):
    """Format log details for display with enhanced medical data formatting"""
    if not log_or_details:
        return "No details available"

    try:
        # Handle AdminLog object vs raw details
        if hasattr(log_or_details, 'event_details_dict'):
            # This is an AdminLog object
            data = log_or_details.event_details_dict
        elif isinstance(log_or_details, str):
            # This is a JSON string
            data = json.loads(log_or_details)
        else:
            # This is already a dictionary
            data = log_or_details

        formatted = []

        # Format common fields first
        if 'action' in data:
            formatted.append(f"Action: {data['action'].title()}")
        if 'patient_name' in data:
            formatted.append(f"Patient: {data['patient_name']}")
        if 'patient_id' in data:
            formatted.append(f"Patient ID: {data['patient_id']}")

        # Format data type specific information
        data_type = data.get('data_type', '')
        if data_type:
            formatted.append(f"Data Type: {data_type.title()}")

            # Add specific details based on data type
            if data_type == 'vital':
                if 'vital_date' in data:
                    formatted.append(f"Vital Date: {data['vital_date']}")
                if 'vital_time' in data:
                    formatted.append(f"Vital Time: {data['vital_time']}")
                if 'weight' in data:
                    formatted.append(f"Weight: {data['weight']}")
                if 'height' in data:
                    formatted.append(f"Height: {data['height']}")
                if 'temperature' in data:
                    formatted.append(f"Temperature: {data['temperature']}")
                if 'pulse' in data:
                    formatted.append(f"Pulse: {data['pulse']}")

            elif data_type == 'condition':
                if 'condition_name' in data:
                    formatted.append(f"Condition: {data['condition_name']}")
                if 'diagnosis_date' in data:
                    formatted.append(f"Diagnosis Date: {data['diagnosis_date']}")
                if 'diagnosis_time' in data:
                    formatted.append(f"Diagnosis Time: {data['diagnosis_time']}")
                if 'condition_code' in data:
                    formatted.append(f"ICD Code: {data['condition_code']}")
                if 'condition_status' in data:
                    formatted.append(f"Status: {data['condition_status']}")

            elif data_type == 'lab':
                if 'test_name' in data:
                    formatted.append(f"Test: {data['test_name']}")
                if 'test_date' in data:
                    formatted.append(f"Test Date: {data['test_date']}")
                if 'test_time' in data:
                    formatted.append(f"Test Time: {data['test_time']}")
                if 'result' in data:
                    formatted.append(f"Result: {data['result']}")
                if 'unit' in data:
                    formatted.append(f"Unit: {data['unit']}")
                if 'reference_range' in data:
                    formatted.append(f"Reference: {data['reference_range']}")
                if 'abnormal_flag' in data:
                    formatted.append(f"Abnormal: {data['abnormal_flag']}")

            elif data_type == 'immunization':
                if 'vaccine_name' in data:
                    formatted.append(f"Vaccine: {data['vaccine_name']}")
                if 'immunization_date' in data:
                    formatted.append(f"Date: {data['immunization_date']}")
                if 'immunization_time' in data:
                    formatted.append(f"Time: {data['immunization_time']}")
                if 'manufacturer' in data:
                    formatted.append(f"Manufacturer: {data['manufacturer']}")
                if 'lot_number' in data:
                    formatted.append(f"Lot Number: {data['lot_number']}")
                if 'dose_number' in data:
                    formatted.append(f"Dose: {data['dose_number']}")

            elif data_type == 'imaging':
                if 'study_type' in data:
                    formatted.append(f"Study: {data['study_type']}")
                if 'study_date' in data:
                    formatted.append(f"Study Date: {data['study_date']}")
                if 'study_time' in data:
                    formatted.append(f"Study Time: {data['study_time']}")
                if 'body_site' in data:
                    formatted.append(f"Body Site: {data['body_site']}")
                if 'findings' in data:
                    formatted.append(f"Findings: {data['findings'][:100]}...")

            elif data_type == 'consult':
                if 'specialist' in data:
                    formatted.append(f"Specialist: {data['specialist']}")
                if 'specialty' in data:
                    formatted.append(f"Specialty: {data['specialty']}")
                if 'consult_date' in data:
                    formatted.append(f"Consult Date: {data['consult_date']}")
                if 'consult_time' in data:
                    formatted.append(f"Consult Time: {data['consult_time']}")
                if 'referral_reason' in data:
                    formatted.append(f"Reason: {data['referral_reason']}")

            elif data_type == 'hospital':
                if 'hospital_name' in data:
                    formatted.append(f"Hospital: {data['hospital_name']}")
                if 'admission_date' in data:
                    formatted.append(f"Admission: {data['admission_date']}")
                if 'admission_time' in data:
                    formatted.append(f"Admission Time: {data['admission_time']}")
                if 'discharge_date' in data:
                    formatted.append(f"Discharge: {data['discharge_date']}")
                if 'admitting_diagnosis' in data:
                    formatted.append(f"Diagnosis: {data['admitting_diagnosis']}")

            elif data_type == 'document':
                if 'file_name' in data:
                    formatted.append(f"File: {data['file_name']}")
                if 'document_type' in data:
                    formatted.append(f"Type: {data['document_type']}")
                if 'document_date' in data:
                    formatted.append(f"Document Date: {data['document_date']}")
                if 'document_time' in data:
                    formatted.append(f"Document Time: {data['document_time']}")
                if 'provider' in data:
                    formatted.append(f"Provider: {data['provider']}")
                if 'file_type' in data:
                    formatted.append(f"File Type: {data['file_type']}")
                if 'file_size' in data:
                    formatted.append(f"File Size: {data['file_size']} bytes")

            elif data_type == 'visit':
                if 'visit_date' in data:
                    formatted.append(f"Visit Date: {data['visit_date']}")
                if 'visit_time' in data:
                    formatted.append(f"Visit Time: {data['visit_time']}")
                if 'visit_type' in data:
                    formatted.append(f"Visit Type: {data['visit_type']}")
                if 'provider' in data:
                    formatted.append(f"Provider: {data['provider']}")
                if 'visit_reason' in data:
                    formatted.append(f"Reason: {data['visit_reason']}")

            elif data_type == 'alert':
                if 'description' in data:
                    formatted.append(f"Alert: {data['description']}")
                if 'alert_type' in data:
                    formatted.append(f"Type: {data['alert_type']}")
                if 'alert_date' in data:
                    formatted.append(f"Alert Date: {data['alert_date']}")
                if 'alert_time' in data:
                    formatted.append(f"Alert Time: {data['alert_time']}")
                if 'severity' in data:
                    formatted.append(f"Severity: {data['severity']}")
                if 'alert_status' in data:
                    formatted.append(f"Status: {data['alert_status']}")

        # Format route and method
        if 'endpoint' in data:
            formatted.append(f"Page: {data['endpoint']}")
        if 'function' in data:
            formatted.append(f"Function: {data['function']}")
        if 'method' in data:
            formatted.append(f"Method: {data['method']}")
        if 'ip_address' in data:
            formatted.append(f"IP: {data['ip_address']}")

        # Add status if available
        if 'status' in data:
            formatted.append(f"Status: {data['status'].title()}")
        if 'error' in data:
            formatted.append(f"Error: {data['error']}")

        return "\n".join(formatted)

    except Exception as e:
        return f"Error formatting details: {str(e)}"