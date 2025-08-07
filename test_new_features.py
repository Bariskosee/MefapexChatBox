#!/usr/bin/env python3
"""
Test script for new Chat History & Session Management features
This script demonstrates the new authentication and session management functionality
"""

import requests
import json
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8000"

def test_user_registration():
    """Test user registration"""
    print("🔧 Testing User Registration...")
    
    user_data = {
        "username": "testuser",
        "email": "test@example.com", 
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    response = requests.post(f"{BASE_URL}/register", json=user_data)
    print(f"Registration Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Registration successful: {response.json()}")
        return True
    else:
        print(f"❌ Registration failed: {response.text}")
        return False

def test_user_login():
    """Test user authentication"""
    print("\n🔧 Testing User Login...")
    
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    print(f"Login Status: {response.status_code}")
    if response.status_code == 200:
        token_data = response.json()
        print(f"✅ Login successful: Token received")
        return token_data["access_token"]
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def test_authenticated_chat(token):
    """Test authenticated chat with session management"""
    print("\n🔧 Testing Authenticated Chat...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send a few messages
    messages = [
        "Merhaba, nasılsın?",
        "MEFAPEX fabrikası hakkında bilgi verir misin?",
        "Güvenlik kuralları nelerdir?"
    ]
    
    for msg in messages:
        chat_data = {"message": msg}
        response = requests.post(f"{BASE_URL}/chat/authenticated", json=chat_data, headers=headers)
        
        if response.status_code == 200:
            chat_response = response.json()
            print(f"✅ User: {msg}")
            print(f"✅ Bot ({chat_response['source']}): {chat_response['response'][:100]}...")
        else:
            print(f"❌ Chat failed: {response.text}")

def test_chat_history(token):
    """Test chat history retrieval"""
    print("\n🔧 Testing Chat History...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get user info first
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    if response.status_code == 200:
        user_info = response.json()
        user_id = user_info["user_id"]
        print(f"✅ User ID: {user_id}")
        
        # Get chat history
        response = requests.get(f"{BASE_URL}/chat/history/{user_id}", headers=headers)
        if response.status_code == 200:
            history = response.json()
            print(f"✅ Chat history retrieved: {history['total_messages']} messages")
            for i, msg in enumerate(history['messages'][-2:], 1):  # Show last 2 messages
                print(f"  {i}. User: {msg['user_message']}")
                print(f"     Bot: {msg['bot_response'][:50]}...")
        else:
            print(f"❌ History retrieval failed: {response.text}")
    else:
        print(f"❌ User info failed: {response.text}")

def test_system_status():
    """Test system status endpoint"""
    print("\n🔧 Testing System Status...")
    
    response = requests.get(f"{BASE_URL}/system/status")
    if response.status_code == 200:
        status = response.json()
        print("✅ System Status:")
        print(f"  - OpenAI: {'✅' if status['openai_enabled'] else '❌'}")
        print(f"  - Hugging Face: {'✅' if status['huggingface_enabled'] else '❌'}")
        print(f"  - Version: {status['version']}")
        print(f"  - Current Model: {status['current_model']}")
    else:
        print(f"❌ Status check failed: {response.text}")

def main():
    """Run all tests"""
    print("🚀 MEFAPEX Chatbot - New Features Test")
    print("=" * 50)
    
    # Test registration
    if test_user_registration():
        # Test login
        token = test_user_login()
        if token:
            # Test authenticated features
            test_authenticated_chat(token)
            test_chat_history(token)
    
    # Test system status (doesn't require auth)
    test_system_status()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\n💡 To run manually:")
    print("1. Start the server: python main.py")
    print("2. Run this test: python test_new_features.py")
    print("3. Or test via web interface at http://localhost:8000")

if __name__ == "__main__":
    main()
