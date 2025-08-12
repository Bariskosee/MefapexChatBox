#!/usr/bin/env python3
"""
Test script for chat history functionality
Verifies that messages are properly persisted and retrieved
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_chat_history():
    """Test complete chat history flow"""
    print("🧪 Testing Chat History Functionality")
    
    # 1. Login
    print("1. Logging in...")
    login_response = requests.post(f"{BASE_URL}/login", json={
        "username": "demo",
        "password": "1234"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_info"]["user_id"]
    print(f"✅ Login successful for user: {user_id}")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 2. Send messages
    test_messages = [
        "Hello, this is test message 1",
        "Second test message for history",
        "Third message to verify persistence"
    ]
    
    print("2. Sending test messages...")
    for i, message in enumerate(test_messages, 1):
        response = requests.post(f"{BASE_URL}/chat/authenticated", 
                               json={"message": message}, headers=headers)
        if response.status_code == 200:
            print(f"✅ Message {i} sent successfully")
        else:
            print(f"❌ Message {i} failed: {response.status_code}")
            return False
    
    # 3. Check history
    print("3. Checking chat history...")
    history_response = requests.get(f"{BASE_URL}/chat/sessions/{user_id}", headers=headers)
    
    if history_response.status_code != 200:
        print(f"❌ History retrieval failed: {history_response.status_code}")
        return False
    
    sessions = history_response.json()["sessions"]
    print(f"✅ Found {len(sessions)} session(s)")
    
    if not sessions:
        print("❌ No sessions found in history")
        return False
    
    session = sessions[0]
    message_count = session["messageCount"]
    print(f"✅ Session has {message_count} messages")
    
    if message_count < len(test_messages):
        print(f"❌ Expected at least {len(test_messages)} messages, got {message_count}")
        return False
    
    # 4. Check session messages
    print("4. Checking session messages...")
    session_id = session["sessionId"]
    messages_response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/messages", 
                                   headers=headers)
    
    if messages_response.status_code != 200:
        print(f"❌ Session messages retrieval failed: {messages_response.status_code}")
        return False
    
    messages = messages_response.json()["messages"]
    user_messages = [msg for msg in messages if msg["type"] == "user"]
    print(f"✅ Retrieved {len(user_messages)} user messages from session")
    
    # 5. Verify message content
    print("5. Verifying message content...")
    latest_user_messages = [msg["content"] for msg in user_messages[-len(test_messages):]]
    latest_user_messages.reverse()  # Reverse to match chronological order
    
    for i, (sent, retrieved) in enumerate(zip(test_messages, latest_user_messages)):
        if sent == retrieved:
            print(f"✅ Message {i+1} content matches")
        else:
            print(f"❌ Message {i+1} mismatch: sent '{sent}', got '{retrieved}'")
            return False
    
    # 6. Test permission scoping
    print("6. Testing permission scoping...")
    other_user_response = requests.get(f"{BASE_URL}/chat/sessions/other_user", headers=headers)
    
    if other_user_response.status_code == 403:
        print("✅ Permission scoping works - access denied to other user's data")
    else:
        print(f"❌ Permission scoping failed: {other_user_response.status_code}")
        return False
    
    print("\n🎉 All tests passed! Chat history functionality is working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = test_chat_history()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        exit(1)
