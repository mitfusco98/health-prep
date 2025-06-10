
from flask import Flask, jsonify, request
import asyncio
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def async_route(f):
    """Decorator to run async functions in Flask routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

def register_async_routes(app):
    """Register async route handlers"""
    
    @app.route('/api/async/patients')
    @async_route
    async def async_get_patients():
        """Non-blocking patient list endpoint"""
        try:
            search_term = request.args.get('search', '')
            limit = min(int(request.args.get('limit', 20)), 100)
            
            if search_term:
                patients = await async_db.search_patients_async(search_term, limit)
            else:
                # Get recent patients
                query = """
                SELECT id, first_name, last_name, mrn, date_of_birth, phone, email
                FROM patient 
                ORDER BY created_at DESC 
                LIMIT %s
                """
                result = await async_db.execute_query(query, [limit])
                patients = [dict(row) for row in result]
            
            return jsonify({
                'success': True,
                'patients': patients,
                'total': len(patients)
            })
            
        except Exception as e:
            logger.error(f"Error in async_get_patients: {e}")
            return jsonify({'error': 'Failed to fetch patients'}), 500
    
    @app.route('/api/async/dashboard')
    @async_route
    async def async_dashboard_data():
        """Non-blocking dashboard data endpoint"""
        try:
            from performance_optimizations import get_home_page_data_async
            
            # Get dashboard data asynchronously
            dashboard_data = await get_home_page_data_async()
            
            # Also get recent activity concurrently
            recent_appointments_query = """
            SELECT a.id, a.appointment_date, a.appointment_time, 
                   p.first_name, p.last_name, p.mrn
            FROM appointment a
            JOIN patient p ON a.patient_id = p.id
            WHERE a.appointment_date >= CURRENT_DATE
            ORDER BY a.appointment_date, a.appointment_time
            LIMIT 10
            """
            
            recent_appointments = await async_db.execute_query(recent_appointments_query)
            
            dashboard_data['recent_appointments'] = [
                {
                    'id': row[0],
                    'date': row[1].isoformat() if row[1] else None,
                    'time': row[2].strftime('%H:%M') if row[2] else None,
                    'patient_name': f"{row[3]} {row[4]}",
                    'patient_mrn': row[5]
                }
                for row in recent_appointments
            ]
            
            return jsonify({
                'success': True,
                'data': dashboard_data
            })
            
        except Exception as e:
            logger.error(f"Error in async_dashboard_data: {e}")
            return jsonify({'error': 'Failed to fetch dashboard data'}), 500
    
    @app.route('/api/async/appointments/<date>')
    @async_route
    async def async_get_appointments_by_date(date):
        """Non-blocking appointments by date endpoint"""
        try:
            query = """
            SELECT a.id, a.appointment_time, a.note, a.status,
                   p.first_name, p.last_name, p.mrn, p.id as patient_id
            FROM appointment a
            JOIN patient p ON a.patient_id = p.id
            WHERE a.appointment_date = %s
            ORDER BY a.appointment_time
            """
            
            appointments = await async_db.execute_query(query, [date])
            
            result = [
                {
                    'id': row[0],
                    'time': row[1].strftime('%H:%M') if row[1] else None,
                    'note': row[2],
                    'status': row[3],
                    'patient': {
                        'id': row[7],
                        'name': f"{row[4]} {row[5]}",
                        'mrn': row[6]
                    }
                }
                for row in appointments
            ]
            
            return jsonify({
                'success': True,
                'appointments': result,
                'date': date,
                'total': len(result)
            })
            
        except Exception as e:
            logger.error(f"Error in async_get_appointments_by_date: {e}")
            return jsonify({'error': 'Failed to fetch appointments'}), 500

    logger.info("Async routes registered successfully")
