// JavaScript for MEFAPEX Chatbot
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const loginContainer = document.getElementById('loginContainer');
const chatContainer = document.getElementById('chatContainer');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');
const logoutBtn = document.getElementById('logoutBtn');
const loginError = document.getElementById('loginError');

// State
let isLoggedIn = false;
let isTyping = false;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Focus on username input
    document.getElementById('username').focus();
});

// Login function
async function login() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    
    if (!username || !password) {
        showLoginError('Kullanıcı adı ve şifre gereklidir.');
        return;
    }
    
    try {
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
        
        const data = await response.json();
        
        if (data.success) {
            isLoggedIn = true;
            loginContainer.style.display = 'none';
            chatContainer.style.display = 'flex';
            logoutBtn.style.display = 'block';
            messageInput.focus();
            hideLoginError();
        } else {
            showLoginError(data.message);
        }
    } catch (error) {
        console.error('Login error:', error);
        showLoginError('Bağlantı hatası. Lütfen tekrar deneyin.');
    }
}

// Logout function
function logout() {
    isLoggedIn = false;
    loginContainer.style.display = 'flex';
    chatContainer.style.display = 'none';
    logoutBtn.style.display = 'none';
    
    // Clear chat messages
    chatMessages.innerHTML = '<div class="welcome-message">👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>Size nasıl yardımcı olabilirim?</div>';
    
    // Clear input fields
    document.getElementById('username').value = 'demo';
    document.getElementById('password').value = '1234';
    messageInput.value = '';
    
    hideLoginError();
}

// Show login error
function showLoginError(message) {
    loginError.textContent = message;
    loginError.style.display = 'block';
}

// Hide login error
function hideLoginError() {
    loginError.style.display = 'none';
}

// Handle Enter key press in message input
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Handle Enter key press in login form
document.getElementById('username').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        document.getElementById('password').focus();
    }
});

document.getElementById('password').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        login();
    }
});

// Send message function
async function sendMessage() {
    if (isTyping || !isLoggedIn) return;
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Clear input
    messageInput.value = '';
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Show typing indicator
    showTyping();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTyping();
        
        // Add bot response to chat
        addMessage(data.response, 'bot');
        
    } catch (error) {
        console.error('Chat error:', error);
        hideTyping();
        addMessage('Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', 'bot');
    }
}

// Add message to chat
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.textContent = text;
    
    messageDiv.appendChild(bubbleDiv);
    
    // Remove welcome message if it exists
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Show typing indicator
function showTyping() {
    isTyping = true;
    sendButton.disabled = true;
    typingIndicator.style.display = 'block';
    
    // Scroll to bottom
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

// Hide typing indicator
function hideTyping() {
    isTyping = false;
    sendButton.disabled = false;
    typingIndicator.style.display = 'none';
}

// Sample questions for easy testing
const sampleQuestions = [
    "Çalışma saatleri nelerdir?",
    "İzin nasıl alınır?",
    "Güvenlik kuralları nelerdir?",
    "Vardiya değişiklikleri nasıl yapılır?",
    "Güncel üretim çıktısı nedir?"
];

// Add sample questions as buttons (optional feature)
function addSampleQuestions() {
    const sampleDiv = document.createElement('div');
    sampleDiv.className = 'sample-questions';
    sampleDiv.innerHTML = '<p>Örnek sorular:</p>';
    
    sampleQuestions.forEach(question => {
        const button = document.createElement('button');
        button.textContent = question;
        button.className = 'sample-question-btn';
        button.onclick = () => {
            messageInput.value = question;
            sendMessage();
        };
        sampleDiv.appendChild(button);
    });
    
    chatMessages.appendChild(sampleDiv);
}

// Error handling for fetch requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});

// Connection test function
async function testConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('Health check:', data);
        return data.status === 'healthy';
    } catch (error) {
        console.error('Connection test failed:', error);
        return false;
    }
}

// Initialize connection test
testConnection().then(isHealthy => {
    if (!isHealthy) {
        console.warn('Backend connection may be unavailable');
    }
});
