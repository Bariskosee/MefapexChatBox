# 🆕 NEW FEATURES: Chat History & Multi-User Support

## 📋 Overview

MEFAPEX Chatbot now includes advanced user authentication and session management features:

### ✨ New Features Added:

1. **🔐 Multi-User Authentication System**
   - User registration with email validation
   - JWT-based authentication 
   - Secure password hashing with bcrypt
   - Session-based access control

2. **💬 Chat History & Session Management**
   - Persistent chat sessions per user
   - Last 20 messages stored automatically
   - Session history retrieval and clearing
   - Message timestamps and source tracking

## 🚀 API Endpoints

### Authentication Endpoints

#### Register New User
```bash
POST /register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com", 
  "password": "secure_password123",
  "full_name": "John Doe"
}
```

#### Login (JWT Token)
```bash
POST /login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password123"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

#### Legacy Login (Backward Compatibility)
```bash
POST /login-legacy
Content-Type: application/json

{
  "username": "demo", 
  "password": "1234"
}
```

### Chat & Session Management

#### Authenticated Chat (with Session Saving)
```bash
POST /chat/authenticated
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "message": "Merhaba, fabrika hakkında bilgi verir misin?"
}
```

#### Get Chat History
```bash
GET /chat/history/{user_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Clear Chat History
```bash
DELETE /chat/history/{user_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Get Current User Info
```bash
GET /me
Authorization: Bearer YOUR_JWT_TOKEN
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Security (REQUIRED!)
SECRET_KEY=your-very-secure-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Settings
USE_OPENAI=false
USE_HUGGINGFACE=true
HUGGINGFACE_MODEL=microsoft/DialoGPT-small

# Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## 📝 Usage Examples

### 1. Register and Authenticate
```python
import requests

# Register user
user_data = {
    "username": "test_user",
    "email": "test@company.com",
    "password": "secure123",
    "full_name": "Test User"
}
response = requests.post("http://localhost:8000/register", json=user_data)

# Login
login_data = {"username": "test_user", "password": "secure123"}
response = requests.post("http://localhost:8000/login", json=login_data)
token = response.json()["access_token"]
```

### 2. Chat with Session Management
```python
headers = {"Authorization": f"Bearer {token}"}
chat_data = {"message": "MEFAPEX güvenlik kuralları nelerdir?"}
response = requests.post("http://localhost:8000/chat/authenticated", 
                        json=chat_data, headers=headers)
```

### 3. Retrieve Chat History
```python
# Get user info
user_info = requests.get("http://localhost:8000/me", headers=headers).json()
user_id = user_info["user_id"]

# Get chat history
history = requests.get(f"http://localhost:8000/chat/history/{user_id}", 
                      headers=headers).json()

print(f"Total messages: {history['total_messages']}")
for msg in history['messages']:
    print(f"User: {msg['user_message']}")
    print(f"Bot: {msg['bot_response']}")
```

## 🔒 Security Features

1. **Password Security**: bcrypt hashing with salt
2. **JWT Tokens**: Secure, stateless authentication
3. **Access Control**: Users can only access their own data
4. **Token Expiration**: Configurable token lifetime
5. **Input Validation**: Email format validation, password requirements

## 📊 Data Storage

- **In-Memory Storage**: Currently uses Python dictionaries (development)
- **Session Limits**: Max 100 messages per user session
- **Message Retention**: Last 20 messages returned by default
- **Future**: Can be extended to use Redis, PostgreSQL, or MongoDB

## 🧪 Testing

Run the included test script:
```bash
python test_new_features.py
```

This will test:
- User registration
- Authentication
- Authenticated chat
- Session management
- Chat history retrieval

## 🔄 Backward Compatibility

- Original `/chat` endpoint still works without authentication
- Legacy `/login-legacy` endpoint supports demo/1234 login
- All existing functionality preserved

## 🛠️ Development Notes

### Adding Database Persistence
To replace in-memory storage with a database:

1. Install database driver (e.g., `asyncpg` for PostgreSQL)
2. Replace `users_db` and `chat_sessions` dictionaries
3. Add database models and connection logic
4. Update authentication functions

### Extending User Roles
Add admin functionality:
```python
class UserInDB(BaseModel):
    # ... existing fields ...
    role: str = "user"  # user, admin, moderator
    permissions: List[str] = []
```

## 📋 Migration from Demo Version

If migrating from demo version:
1. Users can continue using demo/1234 via `/login-legacy`
2. Encourage users to register with `/register` 
3. Use `/chat/authenticated` for session management
4. Gradually deprecate legacy endpoints

## 🔮 Future Enhancements

- [ ] Database persistence (PostgreSQL/MongoDB)
- [ ] User roles and permissions
- [ ] Chat export functionality
- [ ] Multi-language session support
- [ ] Real-time chat with WebSockets
- [ ] Chat analytics and insights
