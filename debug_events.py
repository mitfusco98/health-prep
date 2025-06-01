#!/usr/bin/env python3
"""
Debug script to test template logic for event types
"""

from app import app, db
from models import AdminLog

def test_template_logic():
    """Test the template logic for event type detection"""
    with app.app_context():
        # Get recent data_access logs
        logs = AdminLog.query.filter_by(event_type='data_access').order_by(AdminLog.timestamp.desc()).limit(5).all()
        
        print("Testing template logic for event types:")
        print("=" * 60)
        
        for log in logs:
            print(f"ID: {log.id}")
            print(f"Event Type: {log.event_type}")
            
            if log.event_details_dict and log.event_details_dict.get('route'):
                route = log.event_details_dict['route']
                print(f"Route: {route}")
                
                # Test the same logic as in the template
                if route == '/' or '/date/' in route:
                    result = "Home Page"
                elif '/patient/' in route or '/patient_detail/' in route:
                    result = "View Patient"
                elif '/edit_patient/' in route:
                    result = "Edit Demographics"
                elif '/delete_patient/' in route:
                    result = "Delete Patient"
                elif '/add_appointment' in route:
                    result = "Save Appointment"
                elif '/edit_appointment/' in route:
                    result = "Edit Appointment"
                elif '/delete_appointment/' in route:
                    result = "Delete Appointment"
                elif '/all_visits' in route:
                    result = "View Visits"
                elif '/delete_appointments_bulk' in route:
                    result = "Delete Visits"
                elif '/admin' in route:
                    result = "Admin Access"
                elif route.startswith('/api/'):
                    result = "API Call"
                else:
                    result = "Data Access (fallback)"
                    
                print(f"Template would show: {result}")
                
            else:
                print("No route found")
                
            print("-" * 30)

if __name__ == "__main__":
    test_template_logic()