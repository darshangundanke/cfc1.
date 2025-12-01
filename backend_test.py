import requests
import sys
import json
from datetime import datetime

class KamchAPITester:
    def __init__(self, base_url="https://dosha-quiz.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except:
                    # For non-JSON responses like Excel export
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response.content
            else:
                try:
                    error_data = response.json()
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Error: {error_data}")
                except:
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Response: {response.text}")
                return False, {}

        except requests.exceptions.RequestException as e:
            self.log_test(name, False, f"Network error: {str(e)}")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Unexpected error: {str(e)}")
            return False, {}

    def test_assessment_submission(self):
        """Test assessment form submission"""
        test_data = {
            "name": "Test User",
            "age": "18 yrs above",
            "gender": "Male",
            "date": "2025-01-15",
            "mobile": "9876543210",
            "answers": [
                {"question_id": 1, "value": 3},
                {"question_id": 2, "value": 2},
                {"question_id": 3, "value": 1},
                {"question_id": 4, "value": 4},
                {"question_id": 5, "value": 2},
                {"question_id": 6, "value": 3},
                {"question_id": 7, "value": 1},
                {"question_id": 8, "value": 2},
                {"question_id": 9, "value": 3},
                {"question_id": 10, "value": 1},
                {"question_id": 11, "value": 2},
                {"question_id": 12, "value": 3},
                {"question_id": 13, "value": 2},
                {"question_id": 14, "value": 1}
            ]
        }
        
        success, response = self.run_test(
            "Assessment Submission",
            "POST",
            "assessments",
            200,
            data=test_data
        )
        
        if success:
            # Verify response structure
            required_fields = ['id', 'name', 'score', 'result', 'timestamp']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                self.log_test("Assessment Response Structure", False, f"Missing fields: {missing_fields}")
                return None
            else:
                self.log_test("Assessment Response Structure", True, "All required fields present")
                
            # Verify score calculation (sum should be 31)
            expected_score = sum([answer["value"] for answer in test_data["answers"]])
            actual_score = response.get("score", 0)
            
            if actual_score == expected_score:
                self.log_test("Score Calculation", True, f"Score: {actual_score}")
            else:
                self.log_test("Score Calculation", False, f"Expected {expected_score}, got {actual_score}")
            
            # Verify result determination (31 should be "Ama slightly present")
            expected_result = "Ama slightly present"  # 31 is between 29-42
            actual_result = response.get("result", "")
            
            if actual_result == expected_result:
                self.log_test("Result Determination", True, f"Result: {actual_result}")
            else:
                self.log_test("Result Determination", False, f"Expected '{expected_result}', got '{actual_result}'")
                
            return response.get("id")
        
        return None

    def test_contact_request(self):
        """Test contact request submission"""
        test_data = {
            "name": "Test Contact",
            "mobile": "9876543210",
            "email": "test@example.com",
            "message": "This is a test contact request"
        }
        
        success, response = self.run_test(
            "Contact Request Submission",
            "POST",
            "contact-requests",
            200,
            data=test_data
        )
        
        if success:
            # Verify response structure
            required_fields = ['id', 'name', 'mobile', 'message', 'timestamp']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                self.log_test("Contact Response Structure", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Contact Response Structure", True, "All required fields present")
                
            return response.get("id")
        
        return None

    def test_admin_login_valid(self):
        """Test admin login with valid credentials"""
        test_data = {
            "username": "admin_kamch",
            "password": "admin_kamch123"
        }
        
        success, response = self.run_test(
            "Admin Login (Valid)",
            "POST",
            "admin/login",
            200,
            data=test_data
        )
        
        if success:
            if response.get("success") == True:
                self.log_test("Admin Login Response", True, "Login successful")
            else:
                self.log_test("Admin Login Response", False, "Success field not true")
        
        return success

    def test_admin_login_invalid(self):
        """Test admin login with invalid credentials"""
        test_data = {
            "username": "wrong_user",
            "password": "wrong_pass"
        }
        
        success, response = self.run_test(
            "Admin Login (Invalid)",
            "POST",
            "admin/login",
            401,
            data=test_data
        )
        
        return success

    def test_admin_assessments(self):
        """Test fetching all assessments (admin endpoint)"""
        success, response = self.run_test(
            "Admin Get Assessments",
            "GET",
            "admin/assessments",
            200
        )
        
        if success:
            if isinstance(response, list):
                self.log_test("Assessments Response Type", True, f"Got {len(response)} assessments")
            else:
                self.log_test("Assessments Response Type", False, "Response is not a list")
        
        return success

    def test_admin_export(self):
        """Test Excel export functionality"""
        success, response = self.run_test(
            "Admin Export Excel",
            "GET",
            "admin/assessments/export",
            200
        )
        
        if success:
            # Check if response is binary (Excel file)
            if isinstance(response, bytes) and len(response) > 0:
                self.log_test("Excel Export Content", True, f"Got {len(response)} bytes")
            else:
                self.log_test("Excel Export Content", False, "No binary content received")
        
        return success

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n🔍 Testing Edge Cases...")
        
        # Test assessment with missing fields
        incomplete_data = {
            "name": "Test User"
            # Missing required fields
        }
        
        success, response = self.run_test(
            "Assessment Missing Fields",
            "POST",
            "assessments",
            422,  # Validation error
            data=incomplete_data
        )
        
        # Test contact with missing fields
        incomplete_contact = {
            "name": "Test"
            # Missing required fields
        }
        
        success, response = self.run_test(
            "Contact Missing Fields",
            "POST",
            "contact-requests",
            422,  # Validation error
            data=incomplete_contact
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Kamch API Tests...")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test basic endpoints
        self.test_assessment_submission()
        self.test_contact_request()
        
        # Test admin endpoints
        self.test_admin_login_valid()
        self.test_admin_login_invalid()
        self.test_admin_assessments()
        self.test_admin_export()
        
        # Test edge cases
        self.test_edge_cases()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Print failed tests
        failed_tests = [test for test in self.test_results if not test["success"]]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = KamchAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())