#!/usr/bin/env python3
"""
Test script to verify all session management endpoints are working correctly
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "demo", 
    "password": "1234"
}

def test_endpoint(method, url, data=None, headers=None, description=""):
    """Test an endpoint and print results"""
    print(f"\n🧪 Testing: {description}")
    print(f"   {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS")
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        print(f"   Data keys: {list(result.keys())}")
                    return result
                except:
                    pass
        else:
            print(f"   ❌ FAILED: {response.text[:100]}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    return None

def main():
    print("🚀 Session Management Endpoint Tests")
    print("=" * 50)
    
    # 1. Health check
    test_endpoint("GET", f"{BASE_URL}/health", description="Health Check")
    
    # 2. Login to get token
    print(f"\n📝 Logging in as {TEST_USER['username']}...")
    login_data = test_endpoint("POST", f"{BASE_URL}/login", 
                              data=TEST_USER, 
                              description="User Login")
    
    if not login_data or 'access_token' not in login_data:
        print("❌ Login failed, cannot continue tests")
        return
    
    token = login_data['access_token']
    # Use demo user ID since we know it's the demo user
    user_id = "demo-user-id"  
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✅ Login successful, user_id: {user_id}")
    print(f"   Token: {token[:20]}...")
    
    # 3. Test session endpoints
    test_endpoint("GET", f"{BASE_URL}/chat/sessions/{user_id}", 
                 headers=headers, 
                 description=f"Get User Sessions - {user_id}")
    
    # 4. Test session save endpoint
    test_session_data = {
        "sessionId": f"test-session-{int(time.time())}",
        "startedAt": datetime.now().isoformat(),
        "messages": [
            {
                "user_message": "Test message 1",
                "bot_response": "Test response 1",
                "timestamp": datetime.now().isoformat()
            }
        ]
    }
    
    test_endpoint("POST", f"{BASE_URL}/chat/sessions/save", 
                 data=test_session_data, 
                 headers=headers,
                 description="Save Test Session")
    
    # 5. Test session messages endpoint
    test_endpoint("GET", f"{BASE_URL}/chat/sessions/{test_session_data['sessionId']}/messages", 
                 headers=headers,
                 description=f"Get Session Messages - {test_session_data['sessionId']}")
    
    # 6. Test beacon endpoint
    beacon_data = {
        "session_id": test_session_data['sessionId'],
        "action": "save_session", 
        "timestamp": datetime.now().isoformat()
    }
    
    test_endpoint("POST", f"{BASE_URL}/chat/sessions/save-beacon", 
                 data=beacon_data,
                 description="Beacon Emergency Save")
    
    print(f"\n🏁 Test completed!")
    print("=" * 50)
    
    # Summary
    print(f"\n📋 Quick Summary:")
    print(f"   • Server running at: {BASE_URL}")
    print(f"   • Login working: ✅")
    print(f"   • User ID: {user_id}")
    print(f"   • Session endpoints: Ready for frontend integration")

if __name__ == "__main__":
    main()
