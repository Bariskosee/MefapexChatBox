#!/usr/bin/env python3
"""
Test script for secure cookie-based authentication
This script tests the new secure authentication implementation
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "demo",
    "password": "1234"
}

def test_cookie_based_auth():
    """Test the new cookie-based authentication flow"""
    print("🔐 Testing Secure Cookie-Based Authentication")
    print("=" * 50)
    
    # Create session to maintain cookies
    session = requests.Session()
    
    # Test 1: Login with cookie-based auth
    print("\n1. Testing login with cookies...")
    login_response = session.post(
        f"{BASE_URL}/api/auth/login",
        json=TEST_USER,
        timeout=10
    )
    
    print(f"   Status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        data = login_response.json()
        print(f"   Success: {data.get('success')}")
        print(f"   User: {data.get('user_info', {}).get('username')}")
        
        # Check if cookies were set
        cookies = session.cookies
        print(f"   Cookies set: {len(cookies)} cookies")
        for cookie in cookies:
            print(f"     - {cookie.name}: {cookie.value[:20]}... (HttpOnly: {cookie.has_nonstandard_attr('httponly')})")
    else:
        print(f"   Error: {login_response.text}")
        return False
    
    # Test 2: Access protected endpoint with cookies
    print("\n2. Testing protected endpoint access...")
    me_response = session.get(f"{BASE_URL}/api/auth/me")
    print(f"   Status: {me_response.status_code}")
    
    if me_response.status_code == 200:
        user_data = me_response.json()
        print(f"   User ID: {user_data.get('user_id')}")
        print(f"   Username: {user_data.get('username')}")
    else:
        print(f"   Error: {me_response.text}")
    
    # Test 3: Send authenticated chat message
    print("\n3. Testing authenticated chat...")
    chat_response = session.post(
        f"{BASE_URL}/chat/authenticated",
        json={"message": "Hello, this is a test message!"},
        timeout=10
    )
    print(f"   Status: {chat_response.status_code}")
    
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        print(f"   Response received: {len(chat_data.get('response', ''))} characters")
    else:
        print(f"   Error: {chat_response.text}")
    
    # Test 4: Token refresh
    print("\n4. Testing token refresh...")
    refresh_response = session.post(f"{BASE_URL}/api/auth/refresh")
    print(f"   Status: {refresh_response.status_code}")
    
    if refresh_response.status_code == 200:
        refresh_data = refresh_response.json()
        print(f"   Refresh success: {refresh_data.get('success')}")
        print(f"   Message: {refresh_data.get('message')}")
    else:
        print(f"   Error: {refresh_response.text}")
    
    # Test 5: Logout with cookie cleanup
    print("\n5. Testing logout...")
    logout_response = session.post(f"{BASE_URL}/api/auth/logout")
    print(f"   Status: {logout_response.status_code}")
    
    if logout_response.status_code == 200:
        logout_data = logout_response.json()
        print(f"   Logout success: {logout_data.get('success')}")
        
        # Check if cookies were cleared
        cookies_after = session.cookies
        print(f"   Cookies remaining: {len(cookies_after)}")
    else:
        print(f"   Error: {logout_response.text}")
    
    # Test 6: Verify access is denied after logout
    print("\n6. Testing access after logout...")
    me_after_logout = session.get(f"{BASE_URL}/api/auth/me")
    print(f"   Status: {me_after_logout.status_code}")
    
    if me_after_logout.status_code == 401:
        print("   ✅ Access correctly denied after logout")
    else:
        print(f"   ⚠️ Unexpected response: {me_after_logout.status_code}")
    
    print("\n" + "=" * 50)
    print("🎯 Secure Authentication Test Completed!")
    return True

def test_legacy_fallback():
    """Test backward compatibility with JWT tokens"""
    print("\n\n🔄 Testing Legacy JWT Fallback")
    print("=" * 50)
    
    # Test legacy login endpoint
    print("\n1. Testing legacy JWT login...")
    response = requests.post(
        f"{BASE_URL}/login",
        json=TEST_USER,
        timeout=10
    )
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        access_token = data.get('access_token')
        if access_token:
            print(f"   JWT Token received: {access_token[:20]}...")
            
            # Test using JWT token
            print("\n2. Testing JWT token usage...")
            headers = {"Authorization": f"Bearer {access_token}"}
            me_response = requests.get(f"{BASE_URL}/me", headers=headers)
            print(f"   Status: {me_response.status_code}")
            
            if me_response.status_code == 200:
                user_data = me_response.json()
                print(f"   Username: {user_data.get('username')}")
            else:
                print(f"   Error: {me_response.text}")
        else:
            print("   No access token in response")
    else:
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    try:
        print("🚀 Starting Authentication Security Tests")
        print("Make sure the MEFAPEX server is running on localhost:8000")
        
        # Wait a moment for any server startup
        time.sleep(1)
        
        # Test new secure cookie-based auth
        test_cookie_based_auth()
        
        # Test legacy compatibility
        test_legacy_fallback()
        
        print("\n✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ Test error: {e}")
