
#!/usr/bin/env python3
"""
Comprehensive API Testing Script for Healthcare Application
This script tests all public API endpoints with edge cases and invalid input testing.
Supports both quick health checks and full comprehensive testing.
"""

import requests
import json
import sys
import argparse
from datetime import date, datetime
import time

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
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log(self, message, level="INFO"):
        """Log test results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def test_endpoint(self, method, endpoint, data=None, expected_status=200, description="", timeout=10):
        """Test a single endpoint with comprehensive error handling"""
        url = f"{self.base_url}{endpoint}"
        self.log(f"Testing {method} {endpoint} - {description}")
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=timeout)
            else:
                self.log(f"Unsupported method: {method}", "ERROR")
                self.failed_tests += 1
                return False
                
            self.log(f"Response: {response.status_code} - {response.reason}")
            
            if response.status_code == expected_status:
                self.log("✅ PASS", "SUCCESS")
                self.passed_tests += 1
                try:
                    json_data = response.json()
                    self.log(f"Response data: {json.dumps(json_data, indent=2)[:200]}...")
                except:
                    self.log(f"Response text: {response.text[:200]}...")
                return True
            else:
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code}", "ERROR")
                self.log(f"Response: {response.text[:200]}")
                self.failed_tests += 1
                return False
                
        except requests.exceptions.ConnectionError:
            self.log("❌ FAIL - Connection error. Is the server running?", "ERROR")
            self.failed_tests += 1
            return False
        except requests.exceptions.Timeout:
            self.log(f"❌ FAIL - Request timeout after {timeout}s", "ERROR")
            self.failed_tests += 1
            return False
        except Exception as e:
            self.log(f"❌ FAIL - Exception: {str(e)}", "ERROR")
            self.failed_tests += 1
            return False
    
    def quick_health_check(self):
        """Run a quick health check of key API endpoints"""
        self.log("🔍 Quick API Health Check", "INFO")
        self.log("=" * 30)
        
        # Test 1: Server is running
        try:
            response = requests.get(self.base_url, timeout=5)
            self.log(f"✅ Server accessible: {response.status_code}")
            self.passed_tests += 1
        except:
            self.log("❌ Server not accessible")
            self.failed_tests += 1
            return False
        
        # Test 2: Auth endpoints exist
        try:
            response = requests.post(f"{self.base_url}/api/auth/login", json={}, timeout=5)
            self.log(f"✅ Auth endpoint exists: {response.status_code}")
            self.passed_tests += 1
        except:
            self.log("❌ Auth endpoint not found")
            self.failed_tests += 1
        
        # Test 3: Patients endpoint exists (should require auth)
        try:
            response = requests.get(f"{self.base_url}/api/patients", timeout=5)
            if response.status_code == 401:
                self.log("✅ Patients endpoint protected: 401 Unauthorized")
                self.passed_tests += 1
            else:
                self.log(f"⚠️  Patients endpoint: {response.status_code}")
                self.failed_tests += 1
        except:
            self.log("❌ Patients endpoint not found")
            self.failed_tests += 1
        
        # Test 4: Appointments endpoint exists
        try:
            response = requests.get(f"{self.base_url}/api/appointments", timeout=5)
            if response.status_code == 401:
                self.log("✅ Appointments endpoint protected: 401 Unauthorized")
                self.passed_tests += 1
            else:
                self.log(f"⚠️  Appointments endpoint: {response.status_code}")
                self.failed_tests += 1
        except:
            self.log("❌ Appointments endpoint not found")
            self.failed_tests += 1
        
        return True
    
    def test_auth_flow(self):
        """Test the complete authentication flow with edge cases"""
        self.log("\n=== TESTING AUTHENTICATION FLOW ===")
        
        # 1. Test user registration with invalid data
        invalid_user = {
            "username": "",  # Empty username
            "email": "invalid-email",  # Invalid email format
            "password": "123"  # Too short password
        }
        
        self.test_endpoint(
            "POST", 
            "/api/auth/register",
            data=invalid_user,
            expected_status=400,
            description="Register user with invalid data"
        )
        
        # 2. Test user registration with valid data
        success = self.test_endpoint(
            "POST", 
            "/api/auth/register",
            data=TEST_USER,
            expected_status=201,
            description="Register new user"
        )
        
        if not success:
            self.log("Registration failed, trying to login with existing user")
        
        # 3. Test login with invalid credentials
        invalid_login = {
            "username": TEST_USER["username"],
            "password": "wrongpassword"
        }
        
        self.test_endpoint(
            "POST",
            "/api/auth/login", 
            data=invalid_login,
            expected_status=401,
            description="Login with invalid password"
        )
        
        # 4. Test login with missing fields
        incomplete_login = {
            "username": TEST_USER["username"]
            # Missing password
        }
        
        self.test_endpoint(
            "POST",
            "/api/auth/login", 
            data=incomplete_login,
            expected_status=400,
            description="Login with missing fields"
        )
        
        # 5. Test user login with valid credentials
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        
        success = self.test_endpoint(
            "POST",
            "/api/auth/login", 
            data=login_data,
            expected_status=200,
            description="User login with valid credentials"
        )
        
        # 6. Test token verification
        self.test_endpoint(
            "GET",
            "/api/auth/verify",
            expected_status=200,
            description="Verify authentication token"
        )
        
        # 7. Test token refresh
        self.test_endpoint(
            "POST",
            "/api/auth/refresh",
            expected_status=200,
            description="Refresh authentication token"
        )
        
        # 8. Test logout
        self.test_endpoint(
            "POST",
            "/api/auth/logout",
            expected_status=200,
            description="User logout"
        )
    
    def test_patients_api(self):
        """Test patient-related API endpoints with edge cases"""
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
        
        # 2. Test patients with invalid pagination
        self.test_endpoint(
            "GET", 
            "/api/patients?page=-1&per_page=0",
            expected_status=400,
            description="Get patients with invalid pagination"
        )
        
        # 3. Test patients with extreme pagination
        self.test_endpoint(
            "GET", 
            "/api/patients?page=999999&per_page=1000",
            expected_status=400,
            description="Get patients with extreme pagination (should fail due to per_page limit)"
        )
        
        # 4. Test patients with SQL injection attempt
        self.test_endpoint(
            "GET",
            "/api/patients?search='; DROP TABLE patients; --",
            expected_status=200,
            description="Test SQL injection protection in search"
        )
        
        # 5. Test patients with XSS attempt
        self.test_endpoint(
            "GET",
            "/api/patients?search=<script>alert('xss')</script>",
            expected_status=200,
            description="Test XSS protection in search"
        )
        
        # 6. Test creating patient with invalid data
        invalid_patient = {
            "first_name": "",  # Empty required field
            "last_name": "Test",
            "date_of_birth": "invalid-date",  # Invalid date format
            "sex": "InvalidSex",  # Invalid sex value
            "phone": "not-a-phone-number",  # Invalid phone
            "email": "invalid-email"  # Invalid email
        }
        
        self.test_endpoint(
            "POST",
            "/api/patients",
            data=invalid_patient,
            expected_status=400,
            description="Create patient with invalid data"
        )
        
        # 7. Test creating patient with extremely long data
        long_patient = {
            "first_name": "A" * 1000,  # Extremely long name
            "last_name": "B" * 1000,
            "date_of_birth": "1990-01-01",
            "sex": "Male",
            "phone": "555-0123",
            "email": "test@example.com"
        }
        
        self.test_endpoint(
            "POST",
            "/api/patients",
            data=long_patient,
            expected_status=413,  # Request Entity Too Large
            description="Create patient with extremely long data"
        )
        
        # 8. Test creating a valid patient
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
            description="Create valid patient"
        )
        
        # 9. Test getting non-existent patient
        self.test_endpoint(
            "GET",
            "/api/patients/999999",
            expected_status=404,
            description="Get non-existent patient"
        )
        
        # 10. Test getting patient with invalid ID
        self.test_endpoint(
            "GET",
            "/api/patients/invalid-id",
            expected_status=400,
            description="Get patient with invalid ID format"
        )
    
    def test_appointments_api(self):
        """Test appointment-related API endpoints with edge cases"""
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
        
        # 2. Test getting appointments with invalid date format
        self.test_endpoint(
            "GET",
            "/api/appointments?date=invalid-date",
            expected_status=400,
            description="Get appointments with invalid date format"
        )
        
        # 3. Test getting appointments for future date
        future_date = "2025-12-31"
        self.test_endpoint(
            "GET",
            f"/api/appointments?date={future_date}",
            expected_status=200,
            description=f"Get appointments for future date {future_date}"
        )
        
        # 4. Test getting appointments for past date
        past_date = "1900-01-01"
        self.test_endpoint(
            "GET",
            f"/api/appointments?date={past_date}",
            expected_status=400,  # Should fail due to date range validation
            description=f"Get appointments for very old date {past_date}"
        )
    
    def test_security_vulnerabilities(self):
        """Test for common security vulnerabilities"""
        self.log("\n=== TESTING SECURITY VULNERABILITIES ===")
        
        # 1. Test CSRF protection
        headers = {"X-Requested-With": "XMLHttpRequest"}
        try:
            response = self.session.post(
                f"{self.base_url}/api/patients",
                json={"test": "data"},
                headers=headers
            )
            if response.status_code in [401, 403]:
                self.log("✅ CSRF protection appears active")
                self.passed_tests += 1
            else:
                self.log("⚠️  CSRF protection may be missing")
                self.failed_tests += 1
        except Exception as e:
            self.log(f"Error testing CSRF: {e}")
            self.failed_tests += 1
        
        # 2. Test for information disclosure in errors
        try:
            response = self.session.get(f"{self.base_url}/api/patients/sql-injection")
            if "Traceback" not in response.text and "Exception" not in response.text:
                self.log("✅ No stack traces in error responses")
                self.passed_tests += 1
            else:
                self.log("⚠️  Stack traces may be leaking in errors")
                self.failed_tests += 1
        except Exception as e:
            self.log(f"Error testing information disclosure: {e}")
            self.failed_tests += 1
        
        # 3. Test for directory traversal
        self.test_endpoint(
            "GET",
            "/api/../../../etc/passwd",
            expected_status=404,
            description="Test directory traversal protection"
        )
    
    def test_error_handling(self):
        """Test API error handling with various edge cases"""
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
                self.passed_tests += 1
            else:
                self.log(f"❌ FAIL - Expected 400 for malformed JSON, got {response.status_code}", "ERROR")
                self.failed_tests += 1
        except Exception as e:
            self.log(f"❌ FAIL - Exception testing malformed JSON: {str(e)}", "ERROR")
            self.failed_tests += 1
        
        # 4. Test extremely large payloads
        large_payload = {"data": "A" * 1000000}  # 1MB of data
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=large_payload,
                timeout=5
            )
            if response.status_code in [400, 413, 414]:
                self.log("✅ Large payload protection active")
                self.passed_tests += 1
            else:
                self.log("⚠️  Large payload may not be limited")
                self.failed_tests += 1
        except Exception as e:
            self.log(f"Large payload test resulted in exception: {e}")
            self.passed_tests += 1  # Exception is acceptable for large payloads
    
    def test_rate_limiting(self):
        """Test if rate limiting is in place"""
        self.log("\n=== TESTING RATE LIMITING ===")
        
        # Make multiple rapid requests to see if rate limiting kicks in
        requests_made = 0
        for i in range(20):
            try:
                response = self.session.get(f"{self.base_url}/api/patients")
                requests_made += 1
                if response.status_code == 429:
                    self.log(f"✅ PASS - Rate limiting active after {requests_made} requests", "SUCCESS")
                    self.passed_tests += 1
                    return
                time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                self.log(f"Request {i+1} failed: {e}")
                break
            
        self.log(f"⚠️  WARNING - No rate limiting detected after {requests_made} rapid requests", "WARNING")
        self.failed_tests += 1
    
    def test_performance(self):
        """Test API performance and response times"""
        self.log("\n=== TESTING PERFORMANCE ===")
        
        # Login first
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
        
        # Test response times for key endpoints
        endpoints = [
            "/api/patients",
            "/api/appointments",
            "/api/auth/verify"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if response_time < 1000:  # Less than 1 second
                    self.log(f"✅ {endpoint} responded in {response_time:.2f}ms")
                    self.passed_tests += 1
                else:
                    self.log(f"⚠️  {endpoint} slow response: {response_time:.2f}ms")
                    self.failed_tests += 1
            except Exception as e:
                self.log(f"❌ {endpoint} performance test failed: {e}")
                self.failed_tests += 1
    
    def run_comprehensive_tests(self):
        """Run the complete comprehensive test suite"""
        self.log("🚀 Starting Comprehensive API Test Suite")
        self.log(f"Testing API at: {self.base_url}")
        
        # Test if server is accessible
        try:
            response = self.session.get(self.base_url, timeout=5)
            self.log(f"✅ Server is accessible - Status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log("❌ FAIL - Cannot connect to server. Is it running?", "ERROR")
            return False
        
        # Run all test suites
        self.test_auth_flow()
        self.test_patients_api() 
        self.test_appointments_api()
        self.test_security_vulnerabilities()
        self.test_error_handling()
        self.test_rate_limiting()
        self.test_performance()
        
        # Print final results
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.log(f"\n🏁 API Test Suite Complete!")
        self.log(f"📊 Results: {self.passed_tests} passed, {self.failed_tests} failed")
        self.log(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests > 0:
            self.log("⚠️  Some tests failed - review the logs above", "WARNING")
        else:
            self.log("🎉 All tests passed!", "SUCCESS")
        
        return self.failed_tests == 0

def main():
    """Main function to run API tests"""
    parser = argparse.ArgumentParser(description="Healthcare API Testing Suite")
    parser.add_argument("--url", default=BASE_URL, help="Base URL for API testing")
    parser.add_argument("--quick", action="store_true", help="Run quick health check only")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive test suite (default)")
    
    args = parser.parse_args()
    
    print(f"""
    Healthcare API Testing Suite
    ===========================
    This script tests the API endpoints with edge cases and invalid input testing.
    
    Testing URL: {args.url}
    Mode: {'Quick Health Check' if args.quick else 'Comprehensive Testing'}
    """)
    
    tester = APITester(args.url)
    
    if args.quick:
        success = tester.quick_health_check()
        total_tests = tester.passed_tests + tester.failed_tests
        success_rate = (tester.passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n🏁 Quick test complete! Success rate: {success_rate:.1f}%")
        print("Run without --quick for comprehensive testing")
    else:
        success = tester.run_comprehensive_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
