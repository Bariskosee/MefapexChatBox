// JavaScript for MEFAPEX Chatbot
// Dynamic API URL based on current page location
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
let currentSessionId = null;  // Track current chat session
let sessionStartTime = null;  // Track when current session started

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
    
    console.log('✅ Event listeners added!');
});

// Verify saved token and auto-login
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
            
            // Focus message input
            messageInput.focus();
            
            // Automatically create a new session for this app visit/reload
            await createNewSessionOnLogin();
            
            // Update history button visibility
            updateHistoryButtonVisibility();
        } else {
            console.log('❌ Token expired or invalid, clearing...');
            // Token invalid, clear it
            authToken = null;
            localStorage.removeItem('authToken');
        }
    } catch (error) {
        console.log('❌ Token verification failed:', error);
        authToken = null;
        localStorage.removeItem('authToken');
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

// Login function - Fixed for JWT and legacy endpoints
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
    
    console.log('🚀 Attempting login with:', username, '****'); // Debug log
    
    try {
        // Try legacy login first (this should work for demo/1234)
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
        
        console.log('📊 Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📄 Response data:', data);
        
        if (data.success) {
            console.log('✅ Login successful!');
            isLoggedIn = true;
            loginContainer.style.display = 'none';
            chatContainer.style.display = 'flex';
            logoutBtn.style.display = 'block';
            messageInput.focus();
            hideLoginError();
            try {
                await loginWithJWT(username, password);
                // Automatically create a new session for each app visit/reload
                await createNewSessionOnLogin();
            } catch (err) {
                console.warn('JWT login failed but legacy succeeded:', err);
                // Still start new session even if JWT fails
                startNewChatSession();
            }
            updateHistoryButtonVisibility();
        } else {
            console.log('❌ Login failed:', data.message);
            showLoginError(data.message || 'Giriş başarısız');
        }
    } catch (error) {
        console.error('💥 Login error:', error);
        showLoginError('Bağlantı hatası. Lütfen tekrar deneyin. Server çalışıyor mu?');
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
            
            // Legacy login doesn't provide JWT, but we can still proceed
            // Note: History features will be limited without JWT
            isLoggedIn = true;
            loginContainer.style.display = 'none';
            chatContainer.style.display = 'flex';
            logoutBtn.style.display = 'block';
            
            // Focus message input
            messageInput.focus();
            
            // Clear login error
            showLoginError('');
            
            // Clear password field for security
            document.getElementById('password').value = '';
            
            try {
                await loginWithJWT(username, password);
                // Don't automatically load chat history - let users start fresh
            } catch (err) {
                console.warn('JWT login failed but legacy succeeded:', err);
            }
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

// Logout function
function logout() {
    isLoggedIn = false;
    loginContainer.style.display = 'flex';
    chatContainer.style.display = 'none';
    logoutBtn.style.display = 'none';
    
    // Keep current session messages visible until next login
    // Only reset to welcome message if no messages exist
    const messages = chatMessages.querySelectorAll('.message');
    if (messages.length === 0) {
        chatMessages.innerHTML = '<div class="welcome-message">👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>Size nasıl yardımcı olabilirim?</div>';
    }
    
    // Clear input fields
    document.getElementById('username').value = 'demo';
    document.getElementById('password').value = '1234';
    messageInput.value = '';

    hideLoginError();
    
    // Clear session info (will start fresh on next login)
    currentSessionId = null;
    sessionStartTime = null;
    
    // Keep token temporarily to allow history loading on re-login
    // authToken = null;
    // localStorage.removeItem('authToken');
    updateHistoryButtonVisibility();
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
    
    // Save to localStorage as backup (only if logged in)
    if (isLoggedIn && authToken) {
        saveChatToLocalStorage();
    }
    
    // Auto-scroll to bottom with smooth animation
    scrollToBottom();
}

// Save current chat to localStorage as backup
function saveChatToLocalStorage() {
    try {
        const messages = [];
        const messageElements = chatMessages.querySelectorAll('.message');
        
        for (let i = 0; i < messageElements.length; i += 2) {
            const userMsg = messageElements[i];
            const botMsg = messageElements[i + 1];
            
            if (userMsg && botMsg) {
                messages.push({
                    user_message: userMsg.querySelector('.message-bubble').textContent,
                    bot_response: botMsg.querySelector('.message-bubble').innerHTML,
                    timestamp: new Date().toISOString(),
                    session_id: currentSessionId
                });
            }
        }
        
        const sessionData = {
            sessionId: currentSessionId,
            startTime: sessionStartTime,
            messages: messages,
            lastUpdate: new Date().toISOString()
        };
        
        localStorage.setItem('currentSession', JSON.stringify(sessionData));
        console.log('💾 Current session saved to localStorage:', currentSessionId);
    } catch (error) {
        console.warn('Failed to save chat backup:', error);
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

// Auto-create new session on login (instead of loading history)
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
            console.log('� Using local session as fallback');
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

// Sidebar open/close logic
function openChatHistorySidebar() {
    document.getElementById('chatHistorySidebar').style.transform = 'translateX(0)';
    fetchAndDisplayChatHistorySidebar();
}
function closeChatHistorySidebar() {
    document.getElementById('chatHistorySidebar').style.transform = 'translateX(-100%)';
}

async function fetchAndDisplayChatHistorySidebar() {
    if (!authToken) {
        document.getElementById('chatHistoryList').innerHTML = '<li style="padding:20px; color:#ccc;">Giriş yapmalısınız.</li>';
        return;
    }
    try {
        // Get user_id
        const meResp = await fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!meResp.ok) throw new Error('Kullanıcı bilgisi alınamadı');
        const meData = await meResp.json();
        const userId = meData.user_id;
        
        // Fetch session-based chat history (NEW API)
        const sessionsResp = await fetch(`${API_BASE_URL}/chat/sessions/${userId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!sessionsResp.ok) throw new Error('Oturum geçmişi alınamadı');
        const sessionsData = await sessionsResp.json();
        const sessions = sessionsData.sessions || [];
        
        // Display session previews
        const list = document.getElementById('chatHistoryList');
        list.innerHTML = '';
        
        if (sessions.length === 0) {
            list.innerHTML = '<li style="padding:20px; color:#ccc;">Hiç geçmiş yok.</li>';
        } else {
            // Show current session if it has messages
            if (hasCurrentSessionMessages()) {
                const currentSessionLi = document.createElement('li');
                currentSessionLi.style.cssText = 'padding:16px 20px; border-bottom:2px solid #667eea; cursor:pointer; background:rgba(102,126,234,0.1);';
                const sessionInfo = getCurrentSessionInfo();
                currentSessionLi.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="color:#667eea; font-weight:600;">📝 Mevcut Oturum</span>
                        <span style="color:#999; font-size:12px;">${sessionInfo.messageCount} mesaj</span>
                    </div>
                    <div style="color:#ccc; font-size:13px; margin-top:4px;">Devam eden sohbet...</div>
                `;
                currentSessionLi.onclick = () => {
                    closeChatHistorySidebar();
                    // Already showing current session, just close sidebar
                };
                list.appendChild(currentSessionLi);
            }
            
            // Show previous sessions (up to 15)
            sessions.forEach((session, idx) => {
                const li = document.createElement('li');
                li.style.cssText = 'padding:16px 20px; border-bottom:1px solid #444; cursor:pointer; transition:background 0.3s;';
                li.onmouseenter = () => li.style.background = 'rgba(255,255,255,0.05)';
                li.onmouseleave = () => li.style.background = 'transparent';
                
                const messageCount = session.message_count;
                const sessionDate = new Date(session.first_message_time || session.created_at);
                const timeAgo = getTimeAgo(sessionDate);
                
                li.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="color:#ffd700; font-weight:500;">💬 Oturum ${idx + 1}</span>
                        <span style="color:#999; font-size:12px;">${messageCount} mesaj</span>
                    </div>
                    <div style="color:#ccc; font-size:13px; margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${session.preview}">
                        "${session.preview}"
                    </div>
                    <div style="color:#888; font-size:11px; margin-top:2px;">${timeAgo}</div>
                `;
                
                li.onclick = () => loadHistorySession(session);
                list.appendChild(li);
            });
        }
    } catch (err) {
        console.error('Error fetching session history:', err);
        document.getElementById('chatHistoryList').innerHTML = '<li style="padding:20px; color:#fcc;">Geçmiş yüklenemedi.</li>';
    }
}

// Group messages into sessions based on time gaps
function groupMessagesBySessions(messages) {
    if (messages.length === 0) return [];
    
    const sessions = [];
    let currentSession = { messages: [], startTime: null };
    const SESSION_GAP_MINUTES = 30; // 30 minutes gap = new session
    
    messages.forEach((message, index) => {
        const messageTime = new Date(message.timestamp || Date.now());
        
        if (currentSession.messages.length === 0) {
            // First message of session
            currentSession.startTime = messageTime;
            currentSession.messages.push(message);
        } else {
            // Check time gap from last message
            const lastMessageTime = new Date(currentSession.messages[currentSession.messages.length - 1].timestamp || Date.now());
            const timeDiffMinutes = (messageTime - lastMessageTime) / (1000 * 60);
            
            if (timeDiffMinutes > SESSION_GAP_MINUTES) {
                // Start new session
                sessions.push({ ...currentSession });
                currentSession = { messages: [message], startTime: messageTime };
            } else {
                // Continue current session
                currentSession.messages.push(message);
            }
        }
    });
    
    // Add last session
    if (currentSession.messages.length > 0) {
        sessions.push(currentSession);
    }
    
    // Return sessions in reverse order (newest first)
    return sessions.reverse();
}

// Load a specific historical session
function loadHistorySession(session) {
    console.log('📖 Loading historical session with', session.messages.length, 'messages');
    
    // Clear current chat
    chatMessages.innerHTML = '';
    
    // Add session header
    const sessionHeader = document.createElement('div');
    sessionHeader.style.cssText = 'text-align:center; padding:15px; margin-bottom:10px; background:rgba(102,126,234,0.1); border-radius:10px; color:#667eea; font-weight:600;';
    sessionHeader.innerHTML = `📚 Geçmiş Oturum - ${new Date(session.startTime).toLocaleString('tr-TR')}`;
    chatMessages.appendChild(sessionHeader);
    
    // Load messages from this session
    session.messages.forEach(msg => {
        addMessageWithoutSaving(msg.user_message, 'user');
        addMessageWithoutSaving(msg.bot_response, 'bot');
    });
    
    // Add back to current session button
    const backButton = document.createElement('div');
    backButton.style.cssText = 'text-align:center; padding:15px; margin-top:20px;';
    backButton.innerHTML = '<button onclick="returnToCurrentSession()" style="background:#667eea; color:white; border:none; padding:10px 20px; border-radius:8px; cursor:pointer; font-weight:600;">📝 Mevcut Oturuma Dön</button>';
    chatMessages.appendChild(backButton);
    
    closeChatHistorySidebar();
    scrollToBottom();
}

// Return to current session
function returnToCurrentSession() {
    console.log('🔄 Returning to current session');
    
    // Close the history sidebar if it's open
    closeChatHistorySidebar();
    
    // Check if we have any current session data stored locally
    try {
        const currentSessionData = localStorage.getItem('currentSession');
        if (currentSessionData) {
            // We have current session data, restore it
            const sessionData = JSON.parse(currentSessionData);
            console.log('📱 Restoring current session:', sessionData.sessionId);
            
            // Clear chat area and restore current session messages
            chatMessages.innerHTML = '';
            
            // Restore session info
            currentSessionId = sessionData.sessionId;
            sessionStartTime = sessionData.startTime;
            
            // Restore messages if any
            if (sessionData.messages && sessionData.messages.length > 0) {
                sessionData.messages.forEach(msg => {
                    addMessageWithoutSaving(msg.user_message, 'user');
                    addMessageWithoutSaving(msg.bot_response, 'bot');
                });
                console.log(`📚 Restored ${sessionData.messages.length} current session messages`);
            } else {
                // No messages in current session, show welcome
                chatMessages.innerHTML = '<div class="welcome-message">👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>Size nasıl yardımcı olabilirim?</div>';
            }
        } else {
            // No current session data, show fresh session
            console.log('📝 No current session data, showing fresh session');
            chatMessages.innerHTML = '<div class="welcome-message">👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>Size nasıl yardımcı olabilirim?</div>';
        }
    } catch (error) {
        console.warn('Error restoring current session:', error);
        // Fallback to fresh session
        chatMessages.innerHTML = '<div class="welcome-message">👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>Size nasıl yardımcı olabilirim?</div>';
    }
    
    // Focus on the message input for user convenience
    if (messageInput) {
        messageInput.focus();
    }
    
    console.log('✅ Returned to current session successfully');
    scrollToBottom();
}

// Helper function to get time ago string
function getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffMins < 60) {
        return `${diffMins} dakika önce`;
    } else if (diffHours < 24) {
        return `${diffHours} saat önce`;
    } else if (diffDays < 7) {
        return `${diffDays} gün önce`;
    } else {
        return date.toLocaleDateString('tr-TR');
    }
}

// Make returnToCurrentSession globally available
window.returnToCurrentSession = returnToCurrentSession;

function loadHistoryConversation(idx, messages) {
    // Show only the selected Q&A in the chat window
    const msg = messages[idx];
    chatMessages.innerHTML = '';
    addMessage(msg.user_message, 'user');
    addMessage(msg.bot_response, 'bot');
    closeChatHistorySidebar();
    scrollToBottom();
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

// Call on page load
window.addEventListener('DOMContentLoaded', function() {
    updateHistoryButtonVisibility();
    // Note: Auto-session creation is handled by verifyTokenAndAutoLogin() and login() functions
});
