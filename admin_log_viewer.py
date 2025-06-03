"""
Analysis: The provided code updates the admin log viewer to display more detailed information about patients, appointments, and form data changes. It enhances the formatting of log details to highlight key information such as Patient ID, Patient Name, Appointment ID, and specific changes made to appointment or form data.
"""
"""
Admin Log Viewer - Comprehensive view of all system activities
"""

from flask import render_template, request, jsonify, session
from app import app, db
from models import AdminLog, User, Patient
from admin_middleware import admin_required
from datetime import datetime, timedelta
import json
from sqlalchemy import desc, and_, or_

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
                'details': format_log_details(log),
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

def format_log_details(log):
    """
    Format event details for display in admin logs
    Show Patient ID, Patient Name, Appointment ID, and form changes
    """
    # Parse event details if it's JSON
    if log.event_details:
        try:
            # Try parsing as JSON first
            if log.event_details.startswith('{'):
                event_data = json.loads(log.event_details)
            else:
                # If not JSON, try to evaluate as Python dict
                event_data = eval(log.event_details)

            if isinstance(event_data, dict):
                # Get standardized action from event_data or event_type
                action = event_data.get('action', log.event_type)
                
                # Ensure action is one of the four standard types
                if action not in ['view', 'edit', 'delete', 'add']:
                    # Map legacy event types
                    if 'edit' in action.lower() or 'update' in action.lower():
                        action = "edit"
                    elif 'delete' in action.lower() or 'remove' in action.lower():
                        action = "delete"
                    elif 'add' in action.lower() or 'create' in action.lower():
                        action = "add"
                    else:
                        action = "view"

                formatted_details = []
                
                # Start with standardized action
                action_badge_color = {
                    'view': 'bg-secondary', 
                    'edit': 'bg-warning', 
                    'delete': 'bg-danger', 
                    'add': 'bg-success'
                }.get(action, 'bg-dark')
                formatted_details.append(f"<span class='badge {action_badge_color}'>Action: {action.title()}</span>")

                # Show Patient information prominently
                patient_name = event_data.get('patient_name')
                patient_id = event_data.get('patient_id')
                
                if patient_name and patient_name != 'Unknown':
                    formatted_details.append(f"<span class='badge bg-info'>Patient: {patient_name}</span>")
                if patient_id:
                    formatted_details.append(f"<span class='badge bg-primary'>Patient ID: {patient_id}</span>")

                # Show Appointment ID if present
                appointment_id = event_data.get('appointment_id')
                if appointment_id:
                    formatted_details.append(f"<span class='badge bg-success'>Appointment ID: {appointment_id}</span>")

                # Show page address/endpoint
                page_address = None
                if 'endpoint' in event_data:
                    page_address = event_data['endpoint']
                elif 'route' in event_data:
                    page_address = event_data['route']
                
                if page_address:
                    formatted_details.append(f"<span class='badge bg-dark'>Page: {page_address}</span>")

                # Show form changes with detailed information
                if action in ["edit", "add"] and event_data.get('form_changes'):
                    changes = event_data['form_changes']
                    if changes:
                        formatted_details.append("<div class='mt-2'><strong>Form Changes:</strong></div>")
                        for change_key, change_value in changes.items():
                            change_label = change_key.replace('_', ' ').title()
                            formatted_details.append(f"&nbsp;&nbsp;• {change_label}: <span class='text-primary'>{change_value}</span>")

                # Also show appointment changes if present
                if action == "edit" and event_data.get('appointment_changes'):
                    changes = event_data['appointment_changes']
                    if changes:
                        formatted_details.append("<div class='mt-2'><strong>Appointment Changes:</strong></div>")
                        for change_key, change_value in changes.items():
                            change_label = change_key.replace('_', ' ').title()
                            formatted_details.append(f"&nbsp;&nbsp;• {change_label}: <span class='text-primary'>{change_value}</span>")

                # Show form data fields (what was submitted)
                if event_data.get('form_data') and isinstance(event_data['form_data'], dict):
                    form_data = event_data['form_data']
                    field_names = [field for field in form_data.keys() if field != 'csrf_token']
                    if field_names:
                        formatted_details.append(f"<div class='mt-1'><small class='text-muted'>Form Fields: {', '.join(field_names)}</small></div>")

                # Show relevant technical details
                relevant_details = []
                for key, value in event_data.items():
                    if key in ['action', 'endpoint', 'route', 'patient_name', 'patient_id', 'appointment_id', 'form_changes', 'appointment_changes', 'form_data']:
                        continue  # Already shown above
                    
                    # Include specific technical details
                    if key in ['method', 'ip_address', 'function_name']:
                        if key == 'method':
                            relevant_details.append(f"Method: {value}")
                        elif key == 'ip_address':
                            relevant_details.append(f"IP: {value}")
                        elif key == 'function_name':
                            relevant_details.append(f"Function: {value}")

                if relevant_details:
                    formatted_details.append("<div class='mt-1'><small class='text-muted'>")
                    formatted_details.extend(relevant_details)
                    formatted_details.append("</small></div>")

                return "<br>".join(formatted_details)
        except Exception as e:
            # Log the parsing error but don't show it to users
            pass

    # If parsing fails, show simplified format
    action_type = log.event_type.replace('_', ' ').title()
    return f"<span class='badge bg-secondary'>{action_type}</span>"