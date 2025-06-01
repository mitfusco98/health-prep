
#!/usr/bin/env python3
"""
External API Testing Script for Healthcare Application
This script tests all public API endpoints as if you're a new external developer.
"""

import requests
import json
import sys
from datetime import date, datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Change this to your deployed URL
TEST_USER = {
    "username": "api_test_user",
    "email": "apitest@example.com", 
    "password": "testpass123"
}

class APITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        
    def log(self, message, level="INFO"):
        """Log test results"""
        print(f"[{level}] {message}")
        
    def test_endpoint(self, method, endpoint, data=None, expected_status=200, description=""):
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        self.log(f"Testing {method} {endpoint} - {description}")
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                self.log(f"Unsupported method: {method}", "ERROR")
                return False
                
            self.log(f"Response: {response.status_code} - {response.reason}")
            
            if response.status_code == expected_status:
                self.log("✅ PASS", "SUCCESS")
                try:
                    json_data = response.json()
                    self.log(f"Response data: {json.dumps(json_data, indent=2)[:200]}...")
                except:
                    self.log(f"Response text: {response.text[:200]}...")
                return True
            else:
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code}", "ERROR")
                self.log(f"Response: {response.text[:200]}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log("❌ FAIL - Connection error. Is the server running?", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ FAIL - Exception: {str(e)}", "ERROR")
            return False
    
    def test_auth_flow(self):
        """Test the complete authentication flow"""
        self.log("\n=== TESTING AUTHENTICATION FLOW ===")
        
        # 1. Test user registration
        success = self.test_endpoint(
            "POST", 
            "/api/auth/register",
            data=TEST_USER,
            expected_status=201,
            description="Register new user"
        )
        
        if not success:
            self.log("Registration failed, trying to login with existing user")
        
        # 2. Test user login
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        
        success = self.test_endpoint(
            "POST",
            "/api/auth/login", 
            data=login_data,
            expected_status=200,
            description="User login"
        )
        
        # 3. Test token verification
        self.test_endpoint(
            "GET",
            "/api/auth/verify",
            expected_status=200,
            description="Verify authentication token"
        )
        
        # 4. Test token refresh
        self.test_endpoint(
            "POST",
            "/api/auth/refresh",
            expected_status=200,
            description="Refresh authentication token"
        )
        
        # 5. Test logout
        self.test_endpoint(
            "POST",
            "/api/auth/logout",
            expected_status=200,
            description="User logout"
        )
    
    def test_patients_api(self):
        """Test patient-related API endpoints"""
        self.log("\n=== TESTING PATIENTS API ===")
        
        # First login to get authentication
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
        
        # 1. Test getting patients list
        self.test_endpoint(
            "GET",
            "/api/patients",
            expected_status=200,
            description="Get patients list"
        )
        
        # 2. Test patients with pagination
        self.test_endpoint(
            "GET", 
            "/api/patients?page=1&per_page=5",
            expected_status=200,
            description="Get patients with pagination"
        )
        
        # 3. Test patients with search
        self.test_endpoint(
            "GET",
            "/api/patients?search=John",
            expected_status=200,
            description="Search patients by name"
        )
        
        # 4. Test patients with sorting
        self.test_endpoint(
            "GET",
            "/api/patients?sort=name&order=asc",
            expected_status=200,
            description="Get patients sorted by name"
        )
        
        # 5. Test creating a new patient
        new_patient = {
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": "1990-01-01",
            "sex": "Male",
            "phone": "555-0123",
            "email": "test.patient@example.com"
        }
        
        self.test_endpoint(
            "POST",
            "/api/patients",
            data=new_patient,
            expected_status=201,
            description="Create new patient"
        )
        
        # 6. Test getting a specific patient (assuming patient ID 1 exists)
        self.test_endpoint(
            "GET",
            "/api/patients/1",
            expected_status=200,
            description="Get specific patient details"
        )
    
    def test_appointments_api(self):
        """Test appointment-related API endpoints"""
        self.log("\n=== TESTING APPOINTMENTS API ===")
        
        # Login first
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
        
        # 1. Test getting today's appointments
        self.test_endpoint(
            "GET",
            "/api/appointments",
            expected_status=200,
            description="Get today's appointments"
        )
        
        # 2. Test getting appointments for a specific date
        test_date = date.today().strftime('%Y-%m-%d')
        self.test_endpoint(
            "GET",
            f"/api/appointments?date={test_date}",
            expected_status=200,
            description=f"Get appointments for {test_date}"
        )
    
    def test_error_handling(self):
        """Test API error handling"""
        self.log("\n=== TESTING ERROR HANDLING ===")
        
        # 1. Test authentication required endpoints without auth
        self.session.cookies.clear()  # Clear authentication
        
        self.test_endpoint(
            "GET",
            "/api/patients",
            expected_status=401,
            description="Access protected endpoint without auth"
        )
        
        # 2. Test invalid endpoints
        self.test_endpoint(
            "GET",
            "/api/nonexistent",
            expected_status=404,
            description="Access non-existent endpoint"
        )
        
        # 3. Test malformed JSON
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 400:
                self.log("✅ PASS - Malformed JSON handled correctly", "SUCCESS")
            else:
                self.log(f"❌ FAIL - Expected 400 for malformed JSON, got {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ FAIL - Exception testing malformed JSON: {str(e)}", "ERROR")
        
        # 4. Test invalid patient creation
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
        
        invalid_patient = {
            "first_name": "",  # Empty required field
            "last_name": "Test",
            "date_of_birth": "invalid-date",
            "sex": "InvalidSex"
        }
        
        self.test_endpoint(
            "POST",
            "/api/patients",
            data=invalid_patient,
            expected_status=400,
            description="Create patient with invalid data"
        )
    
    def test_rate_limiting(self):
        """Test if rate limiting is in place"""
        self.log("\n=== TESTING RATE LIMITING ===")
        
        # Make multiple rapid requests to see if rate limiting kicks in
        for i in range(10):
            response = self.session.get(f"{self.base_url}/api/patients")
            if response.status_code == 429:
                self.log("✅ PASS - Rate limiting is active", "SUCCESS")
                return
            
        self.log("⚠️  WARNING - No rate limiting detected after 10 rapid requests", "WARNING")
    
    def run_all_tests(self):
        """Run the complete test suite"""
        self.log("🚀 Starting API Test Suite")
        self.log(f"Testing API at: {self.base_url}")
        
        # Test if server is accessible
        try:
            response = self.session.get(self.base_url)
            self.log(f"✅ Server is accessible - Status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log("❌ FAIL - Cannot connect to server. Is it running?", "ERROR")
            return
        
        # Run test suites
        self.test_auth_flow()
        self.test_patients_api() 
        self.test_appointments_api()
        self.test_error_handling()
        self.test_rate_limiting()
        
        self.log("\n🏁 API Test Suite Complete!")

def main():
    """Main function to run API tests"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"""
    Healthcare API Testing Suite
    ===========================
    This script tests the API as an external developer would.
    
    Usage: python test_api_external.py [BASE_URL]
    Default URL: {BASE_URL}
    
    Testing URL: {base_url}
    """)
    
    tester = APITester(base_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
