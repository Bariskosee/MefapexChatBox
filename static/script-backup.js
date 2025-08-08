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
            👋 MEFAPEX AI asistanına hoş geldiniz.<br>
            ${saveResult.reason === 'saved' ? 'Oturumunuz geçmişe kaydedildi.' : 'Yeni oturuma hazırsınız.'}<br>
            Size nasıl yardımcı olabilirim?
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
        
        // 🎯 CORE: Add message to session manager
        sessionManager.addMessage(message, data.response);
        
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

// Save current chat to localStorage as backup
function saveChatToLocalStorage() {
    try {
        if (!currentSessionId) {
            console.log('No current session ID, skipping localStorage save');
            return false;
        }
        
        const messages = [];
        const messageElements = chatMessages.querySelectorAll('.message');
        
        for (let i = 0; i < messageElements.length; i += 2) {
            const userMsg = messageElements[i];
            const botMsg = messageElements[i + 1];
            
            if (userMsg && botMsg) {
                const userBubble = userMsg.querySelector('.message-bubble');
                const botBubble = botMsg.querySelector('.message-bubble');
                
                if (userBubble && botBubble) {
                    messages.push({
                        user_message: userBubble.textContent || '',
                        bot_response: botBubble.innerHTML || '',
                        timestamp: new Date().toISOString(),
                        session_id: currentSessionId
                    });
                }
            }
        }
        
        const sessionData = {
            sessionId: currentSessionId,
            startTime: sessionStartTime || new Date().toISOString(),
            messages: messages,
            lastUpdate: new Date().toISOString(),
            messageCount: messages.length,
            savedOnLogout: true
        };
        
        localStorage.setItem('currentSession', JSON.stringify(sessionData));
        console.log(`💾 Session saved to localStorage: ${currentSessionId} (${messages.length} messages)`);
        return true;
        
    } catch (error) {
        console.warn('Failed to save chat backup:', error);
        return false;
    }
}

// Load chat from localStorage backup
function loadChatFromLocalStorage() {
    try {
        const sessionData = localStorage.getItem('currentSession');
        if (sessionData) {
            const session = JSON.parse(sessionData);
            
            // Only load if no current messages or we're loading the same session
            const currentMessages = chatMessages.querySelectorAll('.message');
            const hasWelcomeMessage = chatMessages.querySelector('.welcome-message');
            
            if (currentMessages.length === 0 || hasWelcomeMessage) {
                chatMessages.innerHTML = '';
                
                // Restore session info
                currentSessionId = session.sessionId;
                sessionStartTime = session.startTime;
                
                session.messages.forEach(msg => {
                    addMessageWithoutSaving(msg.user_message, 'user');
                    addMessageWithoutSaving(msg.bot_response, 'bot');
                });
                
                scrollToBottom();
                console.log('📱 Loaded current session from localStorage:', currentSessionId);
            }
        }
    } catch (error) {
        console.warn('Failed to load chat backup:', error);
    }
}

// Add message without saving to localStorage (for loading from backup)
function addMessageWithoutSaving(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    const formattedText = sender === 'bot' ? text : formatMessage(text);
    bubbleDiv.innerHTML = formattedText;
    
    messageDiv.appendChild(bubbleDiv);
    
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    chatMessages.appendChild(messageDiv);
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

// JWT management for MEFAPEX Chatbot
async function loginWithJWT(username, password) {
    const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    
    if (response.ok) {
        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        
        // 🚀 OPTIMIZED: Immediately check session status after login
        try {
            const meResponse = await fetch(`${API_BASE_URL}/me`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (meResponse.ok) {
                const userData = await meResponse.json();
                if (userData.session_ready && userData.session_id) {
                    currentSessionId = userData.session_id;
                    console.log(`🎯 Session ready immediately after login: ${currentSessionId}`);
                }
            }
        } catch (err) {
            console.warn('Could not get session info after login:', err);
        }
    }
}

async function fetchAndDisplayChatHistory() {
    if (!authToken) {
        alert('Önce giriş yapmalısınız.');
        return;
    }
    try {
        // Get current user info to obtain user_id
        const meResp = await fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!meResp.ok) throw new Error('Kullanıcı bilgisi alınamadı');
        const meData = await meResp.json();
        const userId = meData.user_id;

        // Fetch chat history
        const histResp = await fetch(`${API_BASE_URL}/chat/history/${userId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!histResp.ok) throw new Error('Geçmiş alınamadı');
        const histData = await histResp.json();
        const messages = histData.messages || [];

        // Clear chat window
        chatMessages.innerHTML = '';
        if (messages.length === 0) {
            chatMessages.innerHTML = '<div class="welcome-message">Hiç mesaj geçmişiniz yok.</div>';
        } else {
            messages.forEach(msg => {
                addMessage(msg.user_message, 'user');
                addMessage(msg.bot_response, 'bot');
            });
        }
        scrollToBottom();
    } catch (err) {
        alert('Geçmiş yüklenemedi: ' + err.message);
    }
}

// Make available globally for button
window.fetchAndDisplayChatHistory = fetchAndDisplayChatHistory;

// 🚀 OPTIMIZED: Ensure user has an active session (fast check)
async function ensureActiveSession() {
    if (!authToken) {
        console.log('No auth token for session check');
        return false;
    }
    
    try {
        console.log('🔍 Checking current session status...');
        
        // Fast check: Get current session info
        const response = await fetch(`${API_BASE_URL}/chat/session/current`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const sessionData = await response.json();
            if (sessionData.session_ready && sessionData.session_id) {
                currentSessionId = sessionData.session_id;
                sessionStartTime = new Date();
                console.log(`✅ Active session confirmed: ${currentSessionId}`);
                return true;
            }
        }
        
        // If no active session, create one
        console.log('📝 No active session found, creating new one...');
        return await createNewSessionAutomatically();
        
    } catch (err) {
        console.warn('Session check failed, creating fallback session:', err);
        return startNewChatSession();
    }
}

// Auto-create new session on login (optimized)
async function createNewSessionOnLogin() {
    if (!authToken) {
        console.log('No auth token for session creation');
        return;
    }
    
    try {
        console.log('🆕 Creating new session on login...');
        
        // Automatically create a new session for this app visit/login
        const newSessionId = await createNewSessionAutomatically();
        
        if (newSessionId) {
            console.log('✅ New session created successfully on login:', newSessionId);
        } else {
            console.log('🔄 Using local session as fallback');
        }
        
    } catch (err) {
        console.warn('Failed to create new session on login:', err);
        // Fallback to local session
        startNewChatSession();
    }
}

// 🆕 NEW SESSION MANAGEMENT FUNCTIONS

// Start a new chat session (clean slate)
function startNewChatSession() {
    console.log('🆕 Starting new chat session...');
    
    // Generate a new session ID
    currentSessionId = generateSessionId();
    sessionStartTime = new Date().toISOString();
    
    // Clear chat messages and show welcome message
    chatMessages.innerHTML = '<div class="welcome-message">👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>Size nasıl yardımcı olabilirim?</div>';
    
    // Clear localStorage backup for new session
    localStorage.removeItem('chatBackup');
    
    console.log('✅ New chat session started:', currentSessionId);
}

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Get current session info
function getCurrentSessionInfo() {
    return {
        sessionId: currentSessionId,
        startTime: sessionStartTime,
        messageCount: chatMessages.querySelectorAll('.message').length
    };
}

// Check if current session has messages
function hasCurrentSessionMessages() {
    const messages = chatMessages.querySelectorAll('.message');
    return messages.length > 0;
}

// Sidebar open/close logic - Updated for session manager
function openChatHistorySidebar() {
    document.getElementById('chatHistorySidebar').style.transform = 'translateX(0)';
    sessionManager.loadHistoryPanel();
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
    
    if (historyBtn) {
        if (isLoggedIn) {
            historyBtn.style.display = 'block';
        } else {
            historyBtn.style.display = 'none';
            closeChatHistorySidebar();
        }
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

// 🆕 AUTOMATIC SESSION MANAGEMENT

async function createNewSessionAutomatically() {
    if (!authToken) {
        console.log('No auth token for automatic session creation');
        return null;
    }
    
    try {
        // Get user info
        const meResp = await fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!meResp.ok) throw new Error('Kullanıcı bilgisi alınamadı');
        const meData = await meResp.json();
        const userId = meData.user_id;
        
        // Start new session on backend automatically
        const newSessionResp = await fetch(`${API_BASE_URL}/chat/sessions/${userId}/new`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!newSessionResp.ok) throw new Error('Otomatik oturum başlatılamadı');
        const newSessionData = await newSessionResp.json();
        
        // Clear current chat and start fresh silently
        chatMessages.innerHTML = '<div class="welcome-message">👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>Size nasıl yardımcı olabilirim?</div>';
        
        // Generate new session info
        currentSessionId = newSessionData.session_id;
        sessionStartTime = new Date().toISOString();
        
        console.log('✅ Automatic new session started:', newSessionData.session_id);
        return newSessionData.session_id;
        
    } catch (error) {
        console.error('Error creating automatic session:', error);
        // Fallback to local session if API fails
        startNewChatSession();
        return currentSessionId;
    }
}

// 💾 AUTO-SAVE SESSION TO BACKEND
async function saveSessionToBackend() {
    if (!authToken || !currentSessionId) {
        console.log('Cannot save to backend: missing auth token or session ID');
        return false;
    }
    
    try {
        console.log('💾 Saving session to backend...', currentSessionId);
        
        // Get user info
        const meResp = await fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!meResp.ok) {
            throw new Error('User info unavailable');
        }
        
        const meData = await meResp.json();
        const userId = meData.user_id;
        
        // Check if current session exists and has messages
        const messages = chatMessages.querySelectorAll('.message');
        if (messages.length === 0) {
            console.log('No messages to save, skipping backend save');
            return true;
        }
        
        // Get session info to verify it exists
        const sessionResp = await fetch(`${API_BASE_URL}/chat/sessions/info/${currentSessionId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (sessionResp.ok) {
            console.log('✅ Session already exists on backend, messages are auto-saved');
            return true;
        } else {
            console.log('⚠️ Session not found on backend, messages saved locally only');
            return false;
        }
        
    } catch (error) {
        console.warn('Failed to save session to backend:', error);
        return false;
    }
}

// Call on page load
window.addEventListener('DOMContentLoaded', function() {
    updateHistoryButtonVisibility();
    // Note: Auto-session creation is handled by verifyTokenAndAutoLogin() and login() functions
});

// 🚪 AUTO-SAVE ON PAGE CLOSE/REFRESH
window.addEventListener('beforeunload', function(event) {
    // Save session when user closes tab or refreshes page
    if (isLoggedIn && currentSessionId && authToken) {
        console.log('🚪 Page closing, saving session...');
        
        try {
            // Save to localStorage (synchronous, always works)
            saveChatToLocalStorage();
            
            // Try to save to backend (may not complete due to page closing)
            // Use sendBeacon for better reliability during page unload
            if (navigator.sendBeacon) {
                saveSessionWithBeacon();
            }
            
        } catch (error) {
            console.warn('Error saving session on page close:', error);
        }
    }
});

// 📡 SAVE SESSION WITH BEACON (for page unload)
function saveSessionWithBeacon() {
    if (!authToken || !currentSessionId) return;
    
    try {
        const sessionData = {
            session_id: currentSessionId,
            action: 'save_session',
            timestamp: new Date().toISOString()
        };
        
        // Use sendBeacon for reliable data sending during page unload
        const success = navigator.sendBeacon(
            `${API_BASE_URL}/chat/sessions/save-beacon`, 
            JSON.stringify(sessionData)
        );
        
        if (success) {
            console.log('📡 Session save beacon sent successfully');
        }
        
    } catch (error) {
        console.warn('Failed to send session save beacon:', error);
    }
}
