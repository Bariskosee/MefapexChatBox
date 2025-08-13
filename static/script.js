// JavaScript for MEFAPEX Chatbot
// 🎯 Exact Session & History Implementation
const API_BASE_URL = window.location.origin;

// Debug: Log the API URL
console.log('API_BASE_URL:', API_BASE_URL);
console.log('JavaScript loaded successfully!');

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
let authToken = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Check for saved auth token
    const savedToken = localStorage.getItem('authToken');
    if (savedToken) {
        authToken = savedToken;
        console.log('🔑 Found saved auth token:', authToken.substring(0, 20) + '...');
        // Verify token is still valid
        verifyTokenAndAutoLogin();
    }
    
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
    
    // Update history button visibility
    updateHistoryButtonVisibility();
    
    console.log('✅ Event listeners added!');
});

// Verify saved token and auto-login with new session management
async function verifyTokenAndAutoLogin() {
    if (!authToken) return;
    
    try {
        console.log('🔍 Verifying saved auth token...');
        const response = await fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const userData = await response.json();
            console.log('✅ Token verified, auto-login successful:', userData.username);
            
            // Auto-login successful
            isLoggedIn = true;
            loginContainer.style.display = 'none';
            chatContainer.style.display = 'flex';
            logoutBtn.style.display = 'block';
            
            // 🎯 CORE: New session on login - always create fresh session
            await sessionManager.startNewSessionOnLogin(authToken, userData.user_id);
            
            // Focus message input
            messageInput.focus();
            
            // Update history button visibility
            updateHistoryButtonVisibility();
        } else {
            console.log('❌ Token expired or invalid, clearing...');
            // Token invalid, clear it
            authToken = null;
            localStorage.removeItem('authToken');
            sessionManager.cleanup();
        }
    } catch (error) {
        console.log('❌ Token verification failed:', error);
        authToken = null;
        localStorage.removeItem('authToken');
        sessionManager.cleanup();
    }
}

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

// Login function - Exact session behavior implementation
async function login() {
    console.log('🔐 Login function called!');
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    
    console.log('Username:', username, 'Password length:', password.length);
    
    if (!username || !password) {
        console.log('❌ Missing credentials');
        showLoginError('Kullanıcı adı ve şifre gereklidir.');
        return;
    }
    
    console.log('🚀 Attempting login with:', username, '****');
    
    try {
        // Try JWT login first
        console.log('📡 Calling JWT login endpoint...');
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
        
        console.log('📊 Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('📄 JWT Response data:', data);
            
            if (data.access_token) {
                authToken = data.access_token;
                localStorage.setItem('authToken', authToken);
                
                // Get user data
                const meResponse = await fetch(`${API_BASE_URL}/me`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                
                if (meResponse.ok) {
                    const userData = await meResponse.json();
                    
                    console.log('✅ JWT Login successful!');
                    isLoggedIn = true;
                    loginContainer.style.display = 'none';
                    chatContainer.style.display = 'flex';
                    logoutBtn.style.display = 'block';
                    hideLoginError();
                    
                    // 🎯 CORE: New session on every login
                    await sessionManager.startNewSessionOnLogin(authToken, userData.user_id);
                    
                    // Focus composer
                    messageInput.focus();
                    
                    updateHistoryButtonVisibility();
                } else {
                    throw new Error('Failed to get user data');
                }
            } else {
                throw new Error('No access token received');
            }
        } else {
            // Fallback to legacy login
            await loginLegacyFallback(username, password);
        }
    } catch (error) {
        console.error('💥 Login error:', error);
        // Try legacy login as final fallback
        await loginLegacyFallback(username, password);
    }
}

// Fallback to legacy login if JWT fails
async function loginLegacyFallback(username, password) {
    try {
        console.log('📡 Calling legacy login endpoint...');
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
        
        console.log('📊 Legacy Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📄 Legacy Response data:', data);
        
        if (data.success) {
            console.log('✅ Legacy login successful!');
            
            isLoggedIn = true;
            loginContainer.style.display = 'none';
            chatContainer.style.display = 'flex';
            logoutBtn.style.display = 'block';
            
            // Focus message input
            messageInput.focus();
            
            // Clear login error
            hideLoginError();
            
            // Clear password field for security
            document.getElementById('password').value = '';
            
            // 🎯 CORE: New session on login (even for legacy)
            // Note: Limited functionality without JWT token
            await sessionManager.startNewSessionOnLogin(null, username);
            
            updateHistoryButtonVisibility();
            
            console.log('🎯 Legacy login completed!');
        } else {
            throw new Error(data.message || 'Giriş başarısız');
        }
        
    } catch (legacyError) {
        console.error('❌ Legacy login error:', legacyError);
        showLoginError('Giriş başarısız. Kullanıcı adı ve şifreyi kontrol edin.');
    }
}

// Make login function available globally
window.login = login;

// Logout function - Exact session behavior implementation
async function logout() {
    console.log('🚪 Logout initiated...');
    
    // 🎯 CORE: Save on logout (only if session has messages)
    const saveResult = await sessionManager.saveSessionOnLogout();
    
    if (saveResult.success) {
        console.log(`✅ Logout save completed: ${saveResult.reason}`);
    } else {
        console.warn(`⚠️ Logout save failed: ${saveResult.error}`);
        // Non-blocking error - user can still logout
    }
    
    // Clear UI state
    isLoggedIn = false;
    loginContainer.style.display = 'flex';
    chatContainer.style.display = 'none';
    logoutBtn.style.display = 'none';
    
    // Clear chat window and show updated welcome message
    chatMessages.innerHTML = `
        <div class="welcome-message">
            👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>
            ${saveResult.reason === 'saved' ? 
                '<span style="color: #28a745;">✅ Oturumunuz geçmişe kaydedildi.</span>' : 
                '<span style="color: #667eea;">🆕 Yeni oturuma hazırsınız.</span>'}<br><br>
            Giriş yapın ve sohbetinizi başlatın!
        </div>
    `;
    
    // Clear input fields
    document.getElementById('username').value = 'demo';
    document.getElementById('password').value = '1234';
    messageInput.value = '';

    hideLoginError();
    
    // Clear authentication
    authToken = null;
    localStorage.removeItem('authToken');
    
    updateHistoryButtonVisibility();
    
    console.log('✅ Logout completed');
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

// Send message function - Updated for new session management
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
    
    // Add user message to chat UI
    addMessage(message, 'user');
    console.log('User message added to chat');
    
    // Show typing indicator
    showTyping();
    
    try {
        // Use authenticated endpoint if user is logged in and has token
        const endpoint = authToken ? '/chat/authenticated' : '/chat';
        const headers = {
            'Content-Type': 'application/json',
        };
        
        // Add authentication header if token exists
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }
        
        console.log('Making API request to:', `${API_BASE_URL}${endpoint}`);
        
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
        console.log('Received response:', data);
        
        // Hide typing indicator
        hideTyping();
        
        // Add bot response to chat UI
        addMessage(data.response, 'bot');
        console.log('Bot response added to chat');
        
        // 🎯 CORE: Add message to session manager with auto-save
        console.log('🔄 About to call sessionManager.addMessage()');
        try {
            await sessionManager.addMessage(message, data.response);
            console.log('✅ Message saved to session and database');
        } catch (error) {
            console.error('❌ Failed to save message to session/database:', error);
            console.warn('⚠️ Message saved to session but failed to save to database:', error);
        }
        
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

// Add message to chat UI (updated for session manager)
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

// Smooth scroll to bottom
function scrollToBottom() {
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
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

// Error handling for fetch requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});

// Sidebar open/close logic - Updated for session manager
function openChatHistorySidebar() {
    console.log('🔍 openChatHistorySidebar called');
    console.log('🔍 sessionManager exists:', !!window.sessionManager);
    console.log('🔍 sessionManager.authToken:', !!sessionManager?.authToken);
    console.log('🔍 sessionManager.userId:', sessionManager?.userId);
    console.log('🔍 isLoggedIn:', isLoggedIn);
    
    const sidebar = document.getElementById('chatHistorySidebar');
    const historyList = document.getElementById('chatHistoryList');
    
    console.log('🔍 sidebar element found:', !!sidebar);
    console.log('🔍 historyList element found:', !!historyList);
    
    if (sidebar) {
        sidebar.style.transform = 'translateX(0)';
    }
    
    if (!isLoggedIn) {
        console.log('🔍 User not logged in, showing login message');
        if (historyList) {
            historyList.innerHTML = `
                <li style="padding: 40px; text-align: center; color: #ffd700;">
                    🔒 Geçmiş sohbetleri görmek için giriş yapın
                </li>
            `;
        }
        return;
    }
    
    if (window.sessionManager && typeof sessionManager.loadHistoryPanel === 'function') {
        console.log('🔍 Calling sessionManager.loadHistoryPanel()');
        sessionManager.loadHistoryPanel();
    } else {
        console.error('❌ SessionManager or loadHistoryPanel not available');
        if (historyList) {
            historyList.innerHTML = `
                <li style="padding: 40px; text-align: center; color: #e74c3c;">
                    ❌ SessionManager yüklenemedi<br>
                    <button onclick="location.reload()" style="margin-top: 10px; padding: 5px 10px; background: #e74c3c; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Sayfayı Yenile
                    </button>
                </li>
            `;
        }
    }
}

function closeChatHistorySidebar() {
    document.getElementById('chatHistorySidebar').style.transform = 'translateX(-100%)';
}

// Expose for HTML
window.openChatHistorySidebar = openChatHistorySidebar;
window.closeChatHistorySidebar = closeChatHistorySidebar;

// Show/hide history button based on login state
function updateHistoryButtonVisibility() {
    const historyBtn = document.getElementById('openHistoryBtn');
    
    console.log('🔍 updateHistoryButtonVisibility called');
    console.log('🔍 historyBtn element found:', !!historyBtn);
    console.log('🔍 isLoggedIn:', isLoggedIn);
    
    if (historyBtn) {
        // Only show history button when user is logged in (like logout button)
        if (isLoggedIn) {
            historyBtn.style.display = 'block';
            console.log('🔍 History button made visible (user logged in)');
        } else {
            historyBtn.style.display = 'none';
            console.log('🔍 History button hidden (user not logged in)');
        }
    } else {
        console.error('❌ History button element not found');
    }
}

// 🚪 AUTO-SAVE ON PAGE CLOSE/REFRESH
window.addEventListener('beforeunload', function(event) {
    // Save session when user closes tab or refreshes page
    if (isLoggedIn && sessionManager && sessionManager.currentSession && sessionManager.authToken) {
        console.log('🚪 Page closing, saving session...');
        
        try {
            // Use sendBeacon for better reliability during page unload
            if (navigator.sendBeacon && sessionManager.currentSession) {
                const sessionData = {
                    session_id: sessionManager.currentSession,
                    action: 'save_session',
                    timestamp: new Date().toISOString()
                };
                
                const success = navigator.sendBeacon(
                    `${API_BASE_URL}/chat/sessions/save-beacon`, 
                    JSON.stringify(sessionData)
                );
                
                if (success) {
                    console.log('📡 Session save beacon sent successfully');
                }
            }
        } catch (error) {
            console.warn('Error saving session on page close:', error);
        }
    }
});

console.log('✅ Main script loaded - session management ready');
