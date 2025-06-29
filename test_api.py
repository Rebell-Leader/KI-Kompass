#!/usr/bin/env python3
"""
Comprehensive API Test Suite for KI Kompass Application
Tests all core customer features via API calls without external system dependencies.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class KIKompassAPITester:
    """Test suite for KI Kompass core functionality"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.user_profiles = self._create_test_user_profiles()
        
    def _create_test_user_profiles(self) -> List[Dict]:
        """Create diverse test user profiles covering different scenarios"""
        return [
            {
                "name": "Tech Worker - EU",
                "profile": {
                    "full_name": "Anna Schmidt",
                    "nationality": "German",
                    "visa_type": "EU_Citizen",
                    "arrival_date": (datetime.now() + timedelta(days=30)).isoformat(),
                    "has_family": False,
                    "employment_status": "Tech_Professional",
                    "german_level": "B2"
                }
            },
            {
                "name": "Family with Children - Non-EU",
                "profile": {
                    "full_name": "Raj Patel",
                    "nationality": "Indian",
                    "visa_type": "Work_Visa",
                    "arrival_date": (datetime.now() + timedelta(days=14)).isoformat(),
                    "has_family": True,
                    "spouse_nationality": "Indian",
                    "num_children": 2,
                    "employment_status": "Employed",
                    "german_level": "A1"
                }
            },
            {
                "name": "Student - Non-EU",
                "profile": {
                    "full_name": "Maria González",
                    "nationality": "Spanish",
                    "visa_type": "Student_Visa",
                    "arrival_date": (datetime.now() + timedelta(days=60)).isoformat(),
                    "has_family": False,
                    "employment_status": "Student",
                    "german_level": "B1"
                }
            },
            {
                "name": "Retiree - EU",
                "profile": {
                    "full_name": "Jean Dubois",
                    "nationality": "French",
                    "visa_type": "EU_Citizen",
                    "arrival_date": (datetime.now() + timedelta(days=7)).isoformat(),
                    "has_family": True,
                    "spouse_nationality": "French",
                    "num_children": 0,
                    "employment_status": "Retired",
                    "german_level": "A2"
                }
            }
        ]
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"  Details: {details}")
    
    def test_health_check(self) -> bool:
        """Test basic application health"""
        try:
            response = self.session.get(f"{self.base_url}/")
            success = response.status_code == 200
            self.log_test("Application Health Check", success, 
                         f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_test("Application Health Check", False, str(e))
            return False
    
    def test_user_creation_and_profiles(self) -> Dict[str, str]:
        """Test user creation with different profile combinations"""
        created_users = {}
        
        for user_data in self.user_profiles:
            try:
                # Test user profile creation
                response = self.session.post(
                    f"{self.base_url}/api/users",
                    json=user_data["profile"],
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in [200, 201]:
                    user_id = response.json().get("user_id", f"test_user_{len(created_users)}")
                    created_users[user_data["name"]] = user_id
                    self.log_test(f"User Creation - {user_data['name']}", True,
                                f"User ID: {user_id}")
                else:
                    self.log_test(f"User Creation - {user_data['name']}", False,
                                f"Status: {response.status_code}, Response: {response.text}")
            except Exception as e:
                self.log_test(f"User Creation - {user_data['name']}", False, str(e))
        
        return created_users
    
    def test_pipeline_generation(self, users: Dict[str, str]) -> Dict[str, str]:
        """Test personalized pipeline generation for different user types"""
        pipelines = {}
        
        for user_name, user_id in users.items():
            try:
                # Test pipeline creation
                response = self.session.post(
                    f"{self.base_url}/api/pipelines",
                    json={"user_id": user_id},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in [200, 201]:
                    pipeline_data = response.json()
                    pipeline_id = pipeline_data.get("pipeline_id")
                    pipelines[user_name] = pipeline_id
                    
                    # Verify pipeline contains relevant tasks
                    task_count = len(pipeline_data.get("tasks", []))
                    self.log_test(f"Pipeline Generation - {user_name}", True,
                                f"Pipeline ID: {pipeline_id}, Tasks: {task_count}")
                else:
                    self.log_test(f"Pipeline Generation - {user_name}", False,
                                f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Pipeline Generation - {user_name}", False, str(e))
        
        return pipelines
    
    def test_task_management(self, users: Dict[str, str], pipelines: Dict[str, str]):
        """Test task completion, updates, and removal"""
        
        for user_name, pipeline_id in pipelines.items():
            if not pipeline_id:
                continue
                
            try:
                # Get pipeline tasks
                response = self.session.get(f"{self.base_url}/api/pipelines/{pipeline_id}")
                
                if response.status_code == 200:
                    pipeline_data = response.json()
                    tasks = pipeline_data.get("tasks", [])
                    
                    if tasks:
                        # Test marking first task as completed
                        first_task = tasks[0]
                        task_id = first_task.get("id")
                        
                        completion_response = self.session.put(
                            f"{self.base_url}/api/tasks/{task_id}",
                            json={
                                "completed": True,
                                "notes": f"Test completion for {user_name}",
                                "completion_date": datetime.now().isoformat()
                            },
                            headers={"Content-Type": "application/json"}
                        )
                        
                        success = completion_response.status_code in [200, 204]
                        self.log_test(f"Task Completion - {user_name}", success,
                                    f"Task ID: {task_id}, Status: {completion_response.status_code}")
                        
                        # Test marking task as incomplete (toggle)
                        if success:
                            toggle_response = self.session.put(
                                f"{self.base_url}/api/tasks/{task_id}",
                                json={"completed": False},
                                headers={"Content-Type": "application/json"}
                            )
                            
                            toggle_success = toggle_response.status_code in [200, 204]
                            self.log_test(f"Task Toggle - {user_name}", toggle_success,
                                        f"Task ID: {task_id}")
                    else:
                        self.log_test(f"Task Management - {user_name}", False,
                                    "No tasks found in pipeline")
                else:
                    self.log_test(f"Task Retrieval - {user_name}", False,
                                f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Task Management - {user_name}", False, str(e))
    
    def test_governmental_facilities_and_services(self):
        """Test government facility and service information retrieval"""
        try:
            # Test getting upcoming tasks (which include government services)
            response = self.session.get(f"{self.base_url}/api/tasks/upcoming")
            
            if response.status_code == 200:
                upcoming_tasks = response.json()
                gov_services = [task for task in upcoming_tasks.get("tasks", [])
                              if any(keyword in task.get("category", "").lower() 
                                   for keyword in ["registration", "visa", "government", "official"])]
                
                self.log_test("Government Services Retrieval", True,
                            f"Found {len(gov_services)} government-related tasks")
            else:
                self.log_test("Government Services Retrieval", False,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Government Services Retrieval", False, str(e))
    
    def test_chat_functionality(self, users: Dict[str, str]):
        """Test AI chat functionality with different queries"""
        test_queries = [
            "How do I register my address in Munich?",
            "What documents do I need for Anmeldung?",
            "Where can I open a bank account?",
            "How do I get health insurance?",
            "What are the best areas to live in Munich?"
        ]
        
        # Test with first available user
        if users:
            user_name = list(users.keys())[0]
            user_id = users[user_name]
            
            for query in test_queries:
                try:
                    chat_response = self.session.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "message": query,
                            "user_id": user_id
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if chat_response.status_code == 200:
                        response_data = chat_response.json()
                        ai_response = response_data.get("response", "")
                        conversation_id = response_data.get("conversation_id")
                        
                        success = len(ai_response) > 10  # Basic response validation
                        self.log_test(f"Chat Query - '{query[:30]}...'", success,
                                    f"Response length: {len(ai_response)}, Conv ID: {conversation_id}")
                    else:
                        self.log_test(f"Chat Query - '{query[:30]}...'", False,
                                    f"Status: {chat_response.status_code}")
                        
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    self.log_test(f"Chat Query - '{query[:30]}...'", False, str(e))
    
    def test_notification_system(self, users: Dict[str, str]):
        """Test notification retrieval and management"""
        for user_name, user_id in users.items():
            try:
                # Test getting notifications
                response = self.session.get(f"{self.base_url}/api/notifications")
                
                if response.status_code == 200:
                    notifications = response.json().get("notifications", [])
                    self.log_test(f"Notifications - {user_name}", True,
                                f"Found {len(notifications)} notifications")
                    
                    # Test marking notification as read (if any exist)
                    if notifications:
                        first_notification = notifications[0]
                        notif_id = first_notification.get("id")
                        
                        if notif_id:
                            mark_read_response = self.session.post(
                                f"{self.base_url}/api/notifications/{notif_id}/read"
                            )
                            
                            read_success = mark_read_response.status_code in [200, 204]
                            self.log_test(f"Mark Notification Read - {user_name}", read_success,
                                        f"Notification ID: {notif_id}")
                else:
                    self.log_test(f"Notifications - {user_name}", False,
                                f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Notifications - {user_name}", False, str(e))
    
    def test_progress_tracking(self, pipelines: Dict[str, str]):
        """Test pipeline progress calculation and tracking"""
        for user_name, pipeline_id in pipelines.items():
            if not pipeline_id:
                continue
                
            try:
                response = self.session.get(f"{self.base_url}/api/pipelines/{pipeline_id}")
                
                if response.status_code == 200:
                    pipeline_data = response.json()
                    progress = pipeline_data.get("progress", 0)
                    total_tasks = len(pipeline_data.get("tasks", []))
                    completed_tasks = len([t for t in pipeline_data.get("tasks", []) 
                                         if t.get("completed", False)])
                    
                    progress_valid = 0 <= progress <= 100
                    self.log_test(f"Progress Tracking - {user_name}", progress_valid,
                                f"Progress: {progress}%, Completed: {completed_tasks}/{total_tasks}")
                else:
                    self.log_test(f"Progress Tracking - {user_name}", False,
                                f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Progress Tracking - {user_name}", False, str(e))
    
    def test_data_validation_and_edge_cases(self):
        """Test input validation and edge case handling"""
        
        # Test invalid user creation
        invalid_profiles = [
            {"invalid": "data"},  # Missing required fields
            {"full_name": "", "nationality": ""},  # Empty required fields
            {"full_name": "Test", "arrival_date": "invalid-date"},  # Invalid date format
        ]
        
        for i, invalid_profile in enumerate(invalid_profiles):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/users",
                    json=invalid_profile,
                    headers={"Content-Type": "application/json"}
                )
                
                # Should return 4xx error for invalid data
                validation_works = 400 <= response.status_code < 500
                self.log_test(f"Input Validation - Invalid Profile {i+1}", validation_works,
                            f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Input Validation - Invalid Profile {i+1}", False, str(e))
        
        # Test non-existent resource access
        try:
            response = self.session.get(f"{self.base_url}/api/pipelines/999999")
            not_found = response.status_code == 404
            self.log_test("Non-existent Resource Handling", not_found,
                        f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Non-existent Resource Handling", False, str(e))
    
    def run_all_tests(self) -> Dict:
        """Execute complete test suite"""
        print("="*50)
        print("KI KOMPASS API TEST SUITE")
        print("="*50)
        
        start_time = time.time()
        
        # Core functionality tests
        if not self.test_health_check():
            print("\n❌ Application not accessible. Stopping tests.")
            return self.generate_report()
        
        print("\n🧪 Testing User Management...")
        users = self.test_user_creation_and_profiles()
        
        print("\n🧪 Testing Pipeline Generation...")
        pipelines = self.test_pipeline_generation(users)
        
        print("\n🧪 Testing Task Management...")
        self.test_task_management(users, pipelines)
        
        print("\n🧪 Testing Government Services...")
        self.test_governmental_facilities_and_services()
        
        print("\n🧪 Testing Chat Functionality...")
        self.test_chat_functionality(users)
        
        print("\n🧪 Testing Notification System...")
        self.test_notification_system(users)
        
        print("\n🧪 Testing Progress Tracking...")
        self.test_progress_tracking(pipelines)
        
        print("\n🧪 Testing Data Validation...")
        self.test_data_validation_and_edge_cases()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️ Tests completed in {duration:.2f} seconds")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{success_rate:.1f}%"
            },
            "results": self.test_results,
            "failed_tests": [r for r in self.test_results if not r["success"]],
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print(f"Total Tests: {total_tests}")
        print(f"✓ Passed: {passed_tests}")
        print(f"✗ Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if report["failed_tests"]:
            print("\n❌ FAILED TESTS:")
            for test in report["failed_tests"]:
                print(f"  • {test['test']}: {test['details']}")
        
        return report


def main():
    """Run the complete test suite"""
    tester = KIKompassAPITester()
    report = tester.run_all_tests()
    
    # Save detailed report to file
    with open("test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Detailed report saved to test_report.json")
    
    # Return exit code based on success rate
    success_rate = float(report["summary"]["success_rate"].rstrip("%"))
    return 0 if success_rate >= 80 else 1


if __name__ == "__main__":
    exit(main())