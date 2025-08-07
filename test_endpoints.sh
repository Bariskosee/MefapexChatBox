#!/bin/bash
# Test script to check which login endpoint works

echo "🧪 Testing MEFAPEX Login Endpoints..."

# Test 1: Legacy Login (should work with demo/1234)
echo "1. Testing /login-legacy endpoint:"
curl -X POST "http://localhost:8000/login-legacy" \
     -H "Content-Type: application/json" \
     -d '{"username": "demo", "password": "1234"}'

echo -e "\n"

# Test 2: JWT Login (should work with demo/1234) 
echo "2. Testing /login endpoint (JWT):"
JWT_RESPONSE=$(curl -s -X POST "http://localhost:8000/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "demo", "password": "1234"}')

echo $JWT_RESPONSE

# Extract token for authenticated endpoints
TOKEN=$(echo $JWT_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo -e "\n"

# Test 3: Health check
echo "3. Testing health endpoint:"
curl "http://localhost:8000/health"

echo -e "\n"

# Test 4: System status
echo "4. Testing system status:"
curl "http://localhost:8000/system/status"

echo -e "\n"

# Test 5: Authenticated chat (if we have a token)
if [ ! -z "$TOKEN" ]; then
    echo "5. Testing authenticated chat:"
    curl -X POST "http://localhost:8000/chat/authenticated" \
         -H "Content-Type: application/json" \
         -H "Authorization: Bearer $TOKEN" \
         -d '{"message": "Merhaba"}'
    echo -e "\n"
fi

# Test 6: Regular chat (no auth)
echo "6. Testing regular chat:"
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Merhaba"}'

echo -e "\n\n✅ Test completed!"
echo "💡 Frontend should use /login-legacy endpoint for demo user"
echo "🌐 Web interface: http://localhost:8000"
echo "🔑 Login: demo / 1234"
