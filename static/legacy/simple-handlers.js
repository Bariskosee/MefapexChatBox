// Simple page functionality
const API_BASE_URL = window.location.origin;
let isLoggedIn = false;
let authToken = null;
let isTyping = false;

function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.textContent = message;
    statusDiv.className = `status-message status-${type}`;
    statusDiv.style.display = 'block';
    
    // Auto-hide success and info messages
    if (type !== 'error') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 3000);
    }
}

function hideStatus() {
    document.getElementById('statusMessage').style.display = 'none';
}

async function performLogin() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    
    safeLog('Simple login attempt initiated');
    
    if (!username || !password) {
        showStatus('Kullanıcı adı ve şifre gereklidir.', 'error');
        return;
    }
    
    showStatus('Giriş yapılıyor...', 'info');
    
    try {
        // Try JWT login
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        safeLog('Login response received');
        
        if (response.ok) {
            const data = await response.json();
            safeLog('Login successful');
            
            if (data.access_token) {
                authToken = data.access_token;
                localStorage.setItem('authToken', authToken);
                
                // Get user data
                const meResponse = await fetch(`${API_BASE_URL}/me`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                
                if (meResponse.ok) {
                    const userData = await meResponse.json();
                    safeLog('User data retrieved successfully');
                    
                    // Successfully logged in
                    isLoggedIn = true;
                    showStatus('Giriş başarılı!', 'success');
                    
                    // Switch to chat interface
                    setTimeout(() => {
                        document.getElementById('loginContainer').style.display = 'none';
                        document.getElementById('chatContainer').style.display = 'flex';
                        document.getElementById('logoutBtn').style.display = 'block';
                        document.getElementById('messageInput').focus();
                        hideStatus();
                    }, 1500);
                } else {
                    throw new Error('Kullanıcı bilgileri alınamadı');
                }
            } else {
                throw new Error('Geçerli token alınamadı');
            }
        } else {
            // Try legacy login
            await tryLegacyLogin(username, password);
        }
    } catch (error) {
        safeError('Login error', error.message);
        showStatus('Giriş hatası: ' + error.message, 'error');
    }
}

async function tryLegacyLogin(username, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/login-legacy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        const data = await response.json();
        safeLog('Legacy login response received');
        
        if (data.success) {
            isLoggedIn = true;
            showStatus('Giriş başarılı! (Legacy Mode)', 'success');
            
            // Switch to chat interface
            setTimeout(() => {
                document.getElementById('loginContainer').style.display = 'none';
                document.getElementById('chatContainer').style.display = 'flex';
                document.getElementById('logoutBtn').style.display = 'block';
                document.getElementById('messageInput').focus();
                hideStatus();
            }, 1500);
        } else {
            throw new Error(data.message || 'Giriş başarısız');
        }
    } catch (error) {
        safeError('Legacy login error', error.message);
        showStatus('Kullanıcı adı veya şifre hatalı', 'error');
    }
}

function logout() {
    console.log('🚪 Logout');
    
    isLoggedIn = false;
    authToken = null;
    localStorage.removeItem('authToken');
    
    // Clear chat and show login
    document.getElementById('loginContainer').style.display = 'flex';
    document.getElementById('chatContainer').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
    
    // Clear and reset inputs
    document.getElementById('username').value = 'demo';
    document.getElementById('password').value = '1234';
    document.getElementById('messageInput').value = '';
    
    // Reset chat messages
    document.getElementById('chatMessages').innerHTML = `
        <div class="welcome-message">
            👋 MEFAPEX AI asistanına hoş geldiniz.<br>
            Size nasıl yardımcı olabilirim?
        </div>
    `;
    
    hideStatus();
    document.getElementById('username').focus();
}

function handleChatKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

async function sendChatMessage() {
    if (isTyping || !isLoggedIn) return;
    
    const message = document.getElementById('messageInput').value.trim();
    if (!message) return;
    
    // Clear input
    document.getElementById('messageInput').value = '';
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Show typing
    isTyping = true;
    document.getElementById('sendButton').disabled = true;
    
    try {
        const endpoint = authToken ? '/chat/authenticated' : '/chat';
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        safeLog('Chat response received');
        
        // Add bot response
        addMessage(data.response, 'bot');
        
    } catch (error) {
        safeError('Chat error', error.message);
        addMessage('Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', 'bot');
    } finally {
        isTyping = false;
        document.getElementById('sendButton').disabled = false;
        document.getElementById('messageInput').focus();
    }
}

function addMessage(text, sender) {
    const chatMessages = document.getElementById('chatMessages');
    
    // Remove welcome message if it exists
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.innerHTML = formatMessage ? formatMessage(text) : text;
    
    messageDiv.appendChild(bubbleDiv);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Simple MEFAPEX loaded');
    
    // Focus username field
    document.getElementById('username').focus();
    
    // Setup event listeners
    const loginButton = document.querySelector('button[data-action="performLogin"]');
    if (loginButton) {
        loginButton.addEventListener('click', performLogin);
    }
    
    const logoutButton = document.querySelector('button[data-action="logout"]');
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }
    
    const sendButton = document.querySelector('button[data-action="sendChatMessage"]');
    if (sendButton) {
        sendButton.addEventListener('click', sendChatMessage);
    }
    
    const messageInput = document.querySelector('input[data-handler="handleChatKeyPress"]');
    if (messageInput) {
        messageInput.addEventListener('keypress', handleChatKeyPress);
    }
    
    // Handle Enter key in login
    document.getElementById('password').addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            performLogin();
        }
    });
    
    // Check for saved token
    const savedToken = localStorage.getItem('authToken');
    if (savedToken) {
        console.log('🔑 Found saved token, auto-login...');
        authToken = savedToken;
        
        // Verify token
        fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Token expired');
        })
        .then(userData => {
            console.log('✅ Auto-login successful:', userData.username);
            isLoggedIn = true;
            document.getElementById('loginContainer').style.display = 'none';
            document.getElementById('chatContainer').style.display = 'flex';
            document.getElementById('logoutBtn').style.display = 'block';
            document.getElementById('messageInput').focus();
        })
        .catch(error => {
            console.log('❌ Auto-login failed:', error);
            authToken = null;
            localStorage.removeItem('authToken');
        });
    }
});

console.log('✅ Simple MEFAPEX script loaded');
