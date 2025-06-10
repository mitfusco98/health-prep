"""
Admin dashboard routes - handles administrative functions and monitoring
Extracted from demo_routes.py for better organization
"""
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from models import User, Patient, Appointment, AdminLog, ScreeningType, db
from organized.middleware.admin_logging import AdminLogger, admin_required
from organized.services.patient_service import PatientService
from datetime import datetime, timedelta
from sqlalchemy import func, desc

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Main admin dashboard with system overview"""
    try:
        # Get system statistics
        total_patients = Patient.query.count()
        total_appointments = Appointment.query.count()
        total_users = User.query.count()
        
        # Get recent activity
        recent_logs = AdminLog.query.order_by(desc(AdminLog.timestamp)).limit(10).all()
        
        # Get today's appointments
        today = datetime.now().date()
        today_appointments = Appointment.query.filter_by(date=today).count()
        
        # Get patient statistics
        patient_stats = PatientService.get_patient_statistics()
        
        # Get system health metrics
        db_status = "Connected"
        try:
            db.session.execute('SELECT 1')
        except:
            db_status = "Error"
        
        dashboard_data = {
            'total_patients': total_patients,
            'total_appointments': total_appointments,
            'total_users': total_users,
            'today_appointments': today_appointments,
            'db_status': db_status,
            'recent_logs': recent_logs,
            'patient_stats': patient_stats
        }
        
        # Log dashboard access
        AdminLogger.log_event(
            event_type='dashboard_access',
            event_details=f"Admin dashboard accessed at {datetime.now().isoformat()}"
        )
        
        return render_template('admin/dashboard.html', **dashboard_data)
        
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', error=True)

@admin_bp.route('/users')
@admin_required
def manage_users():
    """User management interface"""
    users = User.query.all()
    
    # Log user management access
    AdminLogger.log_event(
        event_type='user_management_access',
        event_details=f"User management accessed at {datetime.now().isoformat()}"
    )
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/logs')
@admin_required
def view_logs():
    """Admin log viewer with filtering"""
    page = request.args.get('page', 1, type=int)
    event_type = request.args.get('event_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    user_id = request.args.get('user_id', '', type=str)
    
    # Build query
    query = AdminLog.query
    
    if event_type:
        query = query.filter(AdminLog.event_type == event_type)
    
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
    
    if user_id:
        query = query.filter(AdminLog.user_id == user_id)
    
    # Paginate results
    logs = query.order_by(desc(AdminLog.timestamp)).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get available event types for filter
    event_types = db.session.query(AdminLog.event_type).distinct().all()
    event_types = [et[0] for et in event_types]
    
    # Get available users for filter
    users = User.query.all()
    
    return render_template('admin/logs.html', 
                         logs=logs, 
                         event_types=event_types,
                         users=users,
                         filters={
                             'event_type': event_type,
                             'date_from': date_from,
                             'date_to': date_to,
                             'user_id': user_id
                         })

@admin_bp.route('/screening-types')
@admin_required
def manage_screening_types():
    """Manage screening types"""
    screening_types = ScreeningType.query.all()
    
    return render_template('admin/screening_types.html', screening_types=screening_types)

@admin_bp.route('/screening-types/add', methods=['GET', 'POST'])
@admin_required
def add_screening_type():
    """Add new screening type"""
    if request.method == 'POST':
        try:
            screening_type = ScreeningType(
                name=request.form.get('name'),
                description=request.form.get('description'),
                frequency_months=int(request.form.get('frequency_months', 12)),
                age_start=int(request.form.get('age_start', 0)),
                age_end=int(request.form.get('age_end', 120)),
                gender_specific=request.form.get('gender_specific'),
                is_active=request.form.get('is_active') == 'on'
            )
            
            db.session.add(screening_type)
            db.session.commit()
            
            # Log the action
            AdminLogger.log_data_modification(
                action='add',
                data_type='screening_type',
                record_id=screening_type.id,
                form_changes=request.form.to_dict()
            )
            
            flash('Screening type added successfully', 'success')
            return redirect(url_for('admin.manage_screening_types'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding screening type: {str(e)}', 'error')
    
    return render_template('admin/add_screening_type.html')

@admin_bp.route('/screening-types/<int:type_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_screening_type(type_id):
    """Edit screening type"""
    screening_type = ScreeningType.query.get_or_404(type_id)
    
    if request.method == 'POST':
        try:
            old_data = {
                'name': screening_type.name,
                'description': screening_type.description,
                'frequency_months': screening_type.frequency_months,
                'age_start': screening_type.age_start,
                'age_end': screening_type.age_end,
                'gender_specific': screening_type.gender_specific,
                'is_active': screening_type.is_active
            }
            
            screening_type.name = request.form.get('name')
            screening_type.description = request.form.get('description')
            screening_type.frequency_months = int(request.form.get('frequency_months', 12))
            screening_type.age_start = int(request.form.get('age_start', 0))
            screening_type.age_end = int(request.form.get('age_end', 120))
            screening_type.gender_specific = request.form.get('gender_specific')
            screening_type.is_active = request.form.get('is_active') == 'on'
            
            db.session.commit()
            
            # Log changes
            new_data = request.form.to_dict()
            changes = {}
            for key in old_data:
                if str(old_data[key]) != str(new_data.get(key, '')):
                    changes[key] = {'old': str(old_data[key]), 'new': str(new_data.get(key, ''))}
            
            if changes:
                AdminLogger.log_data_modification(
                    action='edit',
                    data_type='screening_type',
                    record_id=type_id,
                    form_changes=changes
                )
            
            flash('Screening type updated successfully', 'success')
            return redirect(url_for('admin.manage_screening_types'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating screening type: {str(e)}', 'error')
    
    return render_template('admin/edit_screening_type.html', screening_type=screening_type)

@admin_bp.route('/system-health')
@admin_required
def system_health():
    """System health monitoring"""
    health_data = {
        'timestamp': datetime.now(),
        'database': 'Connected',
        'disk_usage': 'Normal',
        'memory_usage': 'Normal',
        'recent_errors': []
    }
    
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        # Get recent error logs
        error_logs = AdminLog.query.filter(
            AdminLog.event_type.like('%error%')
        ).order_by(desc(AdminLog.timestamp)).limit(10).all()
        
        health_data['recent_errors'] = error_logs
        
    except Exception as e:
        health_data['database'] = f'Error: {str(e)}'
    
    return render_template('admin/system_health.html', health_data=health_data)

@admin_bp.route('/api/dashboard-stats')
@admin_required
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = {
            'patients': Patient.query.count(),
            'appointments_today': Appointment.query.filter_by(date=datetime.now().date()).count(),
            'total_appointments': Appointment.query.count(),
            'active_users': User.query.filter_by(is_active=True).count() if hasattr(User, 'is_active') else User.query.count(),
            'recent_activity': AdminLog.query.order_by(desc(AdminLog.timestamp)).limit(5).count()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/logs/export')
@admin_required
def export_logs():
    """Export admin logs as JSON"""
    logs = AdminLog.query.order_by(desc(AdminLog.timestamp)).limit(1000).all()
    
    logs_data = []
    for log in logs:
        logs_data.append({
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'event_type': log.event_type,
            'user_id': log.user_id,
            'event_details': log.event_details,
            'request_id': log.request_id,
            'ip_address': log.ip_address
        })
    
    return jsonify(logs_data)

@admin_bp.route('/settings')
@admin_required
def admin_settings():
    """Admin settings page"""
    return render_template('admin/settings.html')

@admin_bp.route('/maintenance')
@admin_required
def maintenance_mode():
    """Maintenance mode controls"""
    return render_template('admin/maintenance.html')