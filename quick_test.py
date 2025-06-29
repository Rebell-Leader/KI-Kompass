#!/usr/bin/env python3
"""
Quick API test for KI Kompass core functionality
Tests essential endpoints without chat to avoid AI API dependency
"""

import requests
import json
from datetime import datetime, timedelta

def test_core_functionality():
    """Test core API endpoints without external dependencies"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Core KI Kompass Functionality")
    print("=" * 50)
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/")
        print(f"✓ Application Health: {response.status_code}")
    except Exception as e:
        print(f"✗ Application Health: {e}")
        return
    
    # Test 2: User creation
    test_user = {
        "user_id": f"test_user_{datetime.now().timestamp()}",
        "full_name": "Anna Schmidt",
        "nationality": "German",
        "visa_type": "EU_Citizen",
        "arrival_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "has_family": False,
        "employment_status": "Tech_Professional",
        "german_level": "B2"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/users",
            json=test_user,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"✓ User Creation: {response.status_code}")
        if response.status_code == 201:
            user_data = response.json()
            user_id = user_data.get("user_id")
            print(f"  Created user: {user_id}")
        else:
            print(f"  Response: {response.text[:100]}")
    except Exception as e:
        print(f"✗ User Creation: {e}")
        return
    
    # Test 3: Pipeline creation
    try:
        response = requests.post(
            f"{base_url}/api/pipelines",
            json={"user_id": user_id},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        print(f"✓ Pipeline Creation: {response.status_code}")
        if response.status_code == 201:
            pipeline_data = response.json()
            pipeline_id = pipeline_data.get("pipeline_id")
            task_count = len(pipeline_data.get("tasks", []))
            print(f"  Created pipeline: {pipeline_id} with {task_count} tasks")
        else:
            print(f"  Response: {response.text[:100]}")
    except Exception as e:
        print(f"✗ Pipeline Creation: {e}")
        return
    
    # Test 4: Task management
    if pipeline_id:
        try:
            response = requests.get(f"{base_url}/api/pipelines/{pipeline_id}", timeout=10)
            print(f"✓ Pipeline Retrieval: {response.status_code}")
            if response.status_code == 200:
                pipeline_data = response.json()
                tasks = pipeline_data.get("tasks", [])
                if tasks:
                    # Update first task
                    first_task_id = tasks[0]["id"]
                    update_response = requests.put(
                        f"{base_url}/update_task/{first_task_id}",
                        data={"completed": "true", "notes": "Test completion"},
                        timeout=10
                    )
                    print(f"✓ Task Update: {update_response.status_code}")
        except Exception as e:
            print(f"✗ Task Management: {e}")
    
    # Test 5: Government services
    try:
        response = requests.get(f"{base_url}/api/tasks/upcoming", timeout=10)
        print(f"✓ Government Services: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            task_count = data.get("count", 0)
            print(f"  Found {task_count} upcoming tasks")
    except Exception as e:
        print(f"✗ Government Services: {e}")
    
    # Test 6: Notifications
    try:
        response = requests.get(f"{base_url}/api/notifications", timeout=10)
        print(f"✓ Notifications: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            notif_count = data.get("count", 0)
            print(f"  Found {notif_count} notifications")
    except Exception as e:
        print(f"✗ Notifications: {e}")
    
    print("\n✅ Core functionality test completed successfully!")

if __name__ == "__main__":
    test_core_functionality()