
#!/usr/bin/env python3
"""
Script to find specific request ID error details
"""

from app import app, db
from models import AdminLog
import json

def find_request_error(request_id):
    """Find error details for specific request ID"""
    with app.app_context():
        # Search for the specific request ID
        logs = AdminLog.query.filter(
            AdminLog.request_id.like(f"%{request_id}%")
        ).order_by(AdminLog.timestamp.desc()).all()
        
        if not logs:
            print(f"No logs found for request ID: {request_id}")
            return
        
        print(f"Found {len(logs)} log entries for request ID: {request_id}")
        print("=" * 80)
        
        for log in logs:
            print(f"Timestamp: {log.timestamp}")
            print(f"Event Type: {log.event_type}")
            print(f"User: {log.user.username if log.user else 'Anonymous'}")
            print(f"IP Address: {log.ip_address}")
            print(f"Request ID: {log.request_id}")
            print(f"Details: {log.event_details}")
            if log.user_agent:
                print(f"User Agent: {log.user_agent}")
            print("-" * 40)

if __name__ == "__main__":
    find_request_error("d554c18a")
