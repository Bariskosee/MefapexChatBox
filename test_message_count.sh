#!/bin/bash

echo "🔧 Testing message count update feature..."

# Login first and get token
echo "📝 Logging in..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "demo", "password": "demo123"}')

echo "Login response: $TOKEN_RESPONSE"

# Extract token from response
TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token"
    exit 1
fi

echo "✅ Got token: ${TOKEN:0:20}..."

# Send a test message
echo "💬 Sending test message..."
CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"message": "Test message to check count update"}')

echo "Chat response: $CHAT_RESPONSE"

echo "✅ Test completed! Check server logs for message count update."
