
#!/usr/bin/env python3
"""
Quick API Test Script
Run this to do a basic health check of your API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def quick_test():
    """Run a quick test of key API endpoints"""
    print("🔍 Quick API Health Check")
    print("=" * 30)
    
    # Test 1: Server is running
    try:
        response = requests.get(BASE_URL)
        print(f"✅ Server accessible: {response.status_code}")
    except:
        print("❌ Server not accessible")
        return
    
    # Test 2: Auth endpoints exist
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json={})
        print(f"✅ Auth endpoint exists: {response.status_code}")
    except:
        print("❌ Auth endpoint not found")
    
    # Test 3: Patients endpoint exists (should require auth)
    try:
        response = requests.get(f"{BASE_URL}/api/patients")
        if response.status_code == 401:
            print("✅ Patients endpoint protected: 401 Unauthorized")
        else:
            print(f"⚠️  Patients endpoint: {response.status_code}")
    except:
        print("❌ Patients endpoint not found")
    
    # Test 4: Appointments endpoint exists
    try:
        response = requests.get(f"{BASE_URL}/api/appointments")
        if response.status_code == 401:
            print("✅ Appointments endpoint protected: 401 Unauthorized")
        else:
            print(f"⚠️  Appointments endpoint: {response.status_code}")
    except:
        print("❌ Appointments endpoint not found")
    
    print("\n🏁 Quick test complete!")
    print("Run 'python test_api_external.py' for comprehensive testing")

if __name__ == "__main__":
    quick_test()
