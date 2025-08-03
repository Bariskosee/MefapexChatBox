// JavaScript for MEFAPEX Chatbot
// Dynamic API URL based on current page location
const API_BASE_URL = window.location.origin;

// DOM Elements
const loginContainer = document.getElementById('loginContainer');
const chatContainer = document.getElementById('chatContainer');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');
const logoutBtn = document.getElementById('logoutBtn');
const loginError = document.getElementById('loginError');
const scrollToTopBtn = document.getElementById('scrollToTop');

// State
let isLoggedIn = false;
let isTyping = false;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Focus on username input
    document.getElementById('username').focus();
    
    // Add event listeners for chat functionality
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });
        
        // Re-enable input after each message
        messageInput.addEventListener('input', function() {
            if (this.disabled) {
                this.disabled = false;
            }
        });
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    
    // Add scroll event listener for scroll-to-top button
    if (chatMessages) {
        chatMessages.addEventListener('scroll', handleScroll);
    }
});

// Handle scroll events
function handleScroll() {
    if (scrollToTopBtn) {
        // Show scroll-to-top button when user scrolls up from bottom
        if (chatMessages.scrollTop < chatMessages.scrollHeight - chatMessages.clientHeight - 200) {
            scrollToTopBtn.classList.add('show');
        } else {
            scrollToTopBtn.classList.remove('show');
        }
    }
}

// Scroll to top function
function scrollToTop() {
    chatMessages.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

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
    console.log('sendMessage called, isTyping:', isTyping, 'isLoggedIn:', isLoggedIn);
    
    if (isTyping || !isLoggedIn) {
        console.log('Blocked: isTyping or not logged in');
        return;
    }
    
    const message = messageInput.value.trim();
    if (!message) {
        console.log('Empty message, returning');
        return;
    }
    
    console.log('Sending message:', message);
    
    // Clear input but keep it enabled
    messageInput.value = '';
    messageInput.disabled = false;
    
    // Add user message to chat
    addMessage(message, 'user');
    console.log('User message added to chat');
    
    // Show typing indicator
    showTyping();
    
    try {
        console.log('Making API request to:', `${API_BASE_URL}/chat`);
        
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
        console.log('Received response:', data);
        
        // Hide typing indicator
        hideTyping();
        
        // Add bot response to chat
        addMessage(data.response, 'bot');
        console.log('Bot response added to chat');
        
        // Ensure input stays enabled and focused
        messageInput.disabled = false;
        messageInput.focus();
        
    } catch (error) {
        console.error('Chat error:', error);
        hideTyping();
        addMessage('Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', 'bot');
        
        // Ensure input stays enabled even on error
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// Add message to chat
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    // Support for markdown-like formatting
    const formattedText = formatMessage(text);
    bubbleDiv.innerHTML = formattedText;
    
    messageDiv.appendChild(bubbleDiv);
    
    // Remove welcome message if it exists
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    chatMessages.appendChild(messageDiv);
    
    // Auto-scroll to bottom with smooth animation
    scrollToBottom();
}

// Format message text (basic markdown support)
function formatMessage(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
        .replace(/\*(.*?)\*/g, '<em>$1</em>')              // Italic
        .replace(/\n/g, '<br>')                            // Line breaks
        .replace(/•/g, '&bull;')                           // Bullet points
        .replace(/✅/g, '&#x2705;')                        // Check mark
        .replace(/❌/g, '&#x274C;')                        // Cross mark
        .replace(/🚀/g, '&#x1F680;')                       // Rocket
        .replace(/💡/g, '&#x1F4A1;')                       // Light bulb
        .replace(/📋/g, '&#x1F4CB;')                       // Clipboard
        .replace(/🛡️/g, '&#x1F6E1;&#xFE0F;')             // Shield
        .replace(/🍽️/g, '&#x1F37D;&#xFE0F;')             // Fork and knife
        .replace(/🔄/g, '&#x1F504;')                       // Arrows
        .replace(/📦/g, '&#x1F4E6;')                       // Package
        .replace(/🔧/g, '&#x1F527;')                       // Wrench
        .replace(/🎯/g, '&#x1F3AF;');                      // Target
}

// Smooth scroll to bottom
function scrollToBottom() {
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

// Check if user is near bottom of chat
function isNearBottom() {
    const threshold = 100;
    return chatMessages.scrollHeight - chatMessages.clientHeight <= chatMessages.scrollTop + threshold;
}

// Show typing indicator
function showTyping() {
    isTyping = true;
    sendButton.disabled = true;
    messageInput.disabled = true;
    typingIndicator.style.display = 'block';
    
    // Scroll to bottom to show typing indicator
    scrollToBottom();
}

// Hide typing indicator
function hideTyping() {
    isTyping = false;
    sendButton.disabled = false;
    messageInput.disabled = false;
    typingIndicator.style.display = 'none';
    
    // Ensure input is ready for next message
    messageInput.focus();
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
