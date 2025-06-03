
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
                'details': log.event_details_dict,
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
