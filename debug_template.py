#!/usr/bin/env python3
"""
Debug script to test the event_details_dict property
"""

from app import app, db
from models import AdminLog
import json

def test_event_details_parsing():
    """Test how event_details are being parsed"""
    with app.app_context():
        # Get a few recent admin logs
        logs = AdminLog.query.order_by(AdminLog.timestamp.desc()).limit(5).all()
        
        print("Testing event_details_dict parsing:")
        print("=" * 50)
        
        for log in logs:
            print(f"ID: {log.id}")
            print(f"Event Type: {log.event_type}")
            print(f"Raw event_details: {log.event_details}")
            print(f"event_details_dict: {log.event_details_dict}")
            
            if log.event_details_dict and 'route' in log.event_details_dict:
                print(f"Route found: {log.event_details_dict['route']}")
            else:
                print("No route found in event_details_dict")
            
            print("-" * 30)

if __name__ == "__main__":
    test_event_details_parsing()