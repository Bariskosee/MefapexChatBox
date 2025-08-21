// JavaScript for MEFAPEX Chatbot
// 🎯 Exact Session & History Implementation
const API_BASE_URL = window.location.origin;

// Safe debug logging
safeLog('API_BASE_URL initialized');
safeLog('JavaScript loaded successfully!');

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
let currentUser = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Check for existing auth session (cookies)
    checkAuthStatus();
    
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
    
    // Set up scroll to top button
    if (scrollToTopBtn) {
        scrollToTopBtn.addEventListener('click', scrollToTop);
    }
    
    // Update history button visibility
    updateHistoryButtonVisibility();
    
    // Set up sidebar close button
    const sidebarCloseBtn = document.querySelector('.sidebar-close-btn');
    if (sidebarCloseBtn) {
        sidebarCloseBtn.addEventListener('click', closeChatHistorySidebar);
    }
    
    safeLog('Event listeners added successfully');
});

// Check authentication status with cookie-based auth
async function checkAuthStatus() {
    try {
        safeLog('Checking authentication status...');
        const response = await fetch(`${API_BASE_URL}/me`, {
            credentials: 'include' // Include cookies
        });
        
        if (response.ok) {
            const userData = await response.json();
            safeLog('User authenticated successfully');
            
            // Auto-login successful
            currentUser = userData;
            isLoggedIn = true;
            loginContainer.style.display = 'none';
            chatContainer.style.display = 'flex';
            logoutBtn.style.display = 'block';
            
            // 🎯 CORE: New session on login - always create fresh session
            await sessionManager.startNewSessionOnLogin(true, userData.user_id);
            
            // Focus message input
            messageInput.focus();
            
            // Update history button visibility
            updateHistoryButtonVisibility();
            
            // Refresh theme for user
            if (window.themeManager) {
                window.themeManager.refreshForUser();
            }
            
            // Announce login success to screen readers
            if (window.accessibilityManager) {
                window.accessibilityManager.announceMessage('Başarıyla giriş yapıldı', 'polite');
            }
        } else {
            safeLog('Not authenticated or session expired');
            // User not authenticated
            currentUser = null;
            isLoggedIn = false;
            sessionManager.cleanup();
        }
    } catch (error) {
        safeLog('Auth check failed', error.message);
        currentUser = null;
        isLoggedIn = false;
        sessionManager.cleanup();
    }
}

// Auto-refresh tokens when access token expires
async function refreshTokens() {
    try {
        safeLog('Refreshing access token...');
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            safeLog('Tokens refreshed successfully');
            currentUser = data.user_info;
            return true;
        } else {
            safeLog('Token refresh failed, redirecting to login');
            await logout();
            return false;
        }
    } catch (error) {
        safeError('Token refresh error', error.message);
        await logout();
        return false;
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

// Login function - Cookie-based authentication
async function login() {
    safeLog('Login function called');
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    
    // SECURITY: Never log actual credentials or their lengths
    devLog('Login attempt with provided credentials');
    
    if (!username || !password) {
        safeLog('Missing credentials');
        showLoginError('Kullanıcı adı ve şifre gereklidir.');
        return;
    }
    
    safeLog('Attempting login with cookie-based authentication');
    
    try {
        // Try new cookie-based auth first
        safeLog('Calling cookie-based auth endpoint...');
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include', // Include cookies
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        safeLog('Response received from auth endpoint');
        
        if (response.ok) {
            const data = await response.json();
            safeLog('Cookie auth response received');
            
            if (data.success) {
                currentUser = data.user_info;
                
                safeLog('Cookie-based login successful');
                isLoggedIn = true;
                loginContainer.style.display = 'none';
                chatContainer.style.display = 'flex';
                logoutBtn.style.display = 'block';
                hideLoginError();
                
                // 🎯 CORE: New session on every login
                await sessionManager.startNewSessionOnLogin(true, currentUser.user_id);
                
                // Focus composer
                messageInput.focus();
                
                updateHistoryButtonVisibility();
            } else {
                throw new Error(data.message || 'Login failed');
            }
        } else {
            // Fallback to legacy JWT login
            await loginJWTFallback(username, password);
        }
    } catch (error) {
        safeError('Cookie auth error', error.message);
        // Try JWT fallback
        await loginJWTFallback(username, password);
    }
}

// JWT fallback login for backwards compatibility
async function loginJWTFallback(username, password) {
    try {
        safeLog('Calling JWT login endpoint...');
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
        
        safeLog('JWT Response received');
        
        if (response.ok) {
            const data = await response.json();
            safeLog('JWT Response processed');
            
            if (data.access_token) {
                // For JWT fallback, we still avoid localStorage
                // The token will be sent in Authorization header for this session only
                currentUser = data.user_info;
                window.jwtToken = data.access_token; // Store in memory only
                
                safeLog('JWT Login successful');
                isLoggedIn = true;
                loginContainer.style.display = 'none';
                chatContainer.style.display = 'flex';
                logoutBtn.style.display = 'block';
                hideLoginError();
                
                // 🎯 CORE: New session on every login
                await sessionManager.startNewSessionOnLogin(window.jwtToken, currentUser.user_id);
                
                // Focus composer
                messageInput.focus();
                
                updateHistoryButtonVisibility();
            } else {
                throw new Error('No access token received');
            }
        } else {
            // Final fallback to legacy login
            await loginLegacyFallback(username, password);
        }
    } catch (error) {
        safeError('JWT fallback error', error.message);
        // Try legacy login as final fallback
        await loginLegacyFallback(username, password);
    }
}

// Legacy login fallback for older systems
async function loginLegacyFallback(username, password) {
    try {
        safeLog('Calling legacy login endpoint...');
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
        
        safeLog('Legacy Response received');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        safeLog('Legacy Response processed');
        
        if (data.success) {
            safeLog('Legacy login successful');
            
            currentUser = { username: username, user_id: username };
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
            // Note: Limited functionality without authentication
            await sessionManager.startNewSessionOnLogin(null, username);
            
            updateHistoryButtonVisibility();
            
            safeLog('Legacy login completed');
        } else {
            throw new Error(data.message || 'Giriş başarısız');
        }
        
    } catch (legacyError) {
        safeError('Legacy login error', legacyError.message);
        showLoginError('Giriş başarısız. Kullanıcı adı ve şifreyi kontrol edin.');
    }
}

// Add message to UI function - Enhanced with accessibility and markdown formatting
function addMessageToUI(message, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.setAttribute('role', 'listitem');
    
    const messageBubble = document.createElement('div');
    messageBubble.className = 'message-bubble';
    
    // Format message content based on sender
    if (sender === 'bot') {
        // Parse and format bot messages with markdown-like syntax
        const formattedMessage = formatBotMessage(message);
        messageBubble.innerHTML = formattedMessage;
    } else {
        // User messages remain as plain text
        messageBubble.textContent = message;
    }
    
    // Add timestamp for screen readers
    const timestamp = new Date().toLocaleTimeString('tr-TR');
    const srTimestamp = document.createElement('span');
    srTimestamp.className = 'sr-only';
    srTimestamp.textContent = ` ${timestamp}`;
    messageBubble.appendChild(srTimestamp);
    
    // Add sender information for screen readers
    if (sender === 'user') {
        messageBubble.setAttribute('aria-label', `Siz: ${message} ${timestamp}`);
    } else {
        messageBubble.setAttribute('aria-label', `AI: ${message} ${timestamp}`);
    }
    
    messageDiv.appendChild(messageBubble);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Update message count for accessibility
    if (window.accessibilityManager) {
        window.accessibilityManager.updateMessageCount();
    }
}

// Add this function if it doesn't exist
if (typeof addMessageToUI === 'undefined') {
    window.addMessageToUI = addMessageToUI;
}

// Format bot messages with markdown-like syntax to HTML
function formatBotMessage(message) {
    if (!message) return '';
    
    let formatted = message;
    
    // Convert **bold** to <strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Split into lines for processing
    const lines = formatted.split('\n');
    let inList = false;
    let result = [];
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        // Skip completely empty lines but add spacing
        if (line === '') {
            // If we were in a list, close it
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            result.push('<div class="bot-spacer"></div>');
            continue;
        }
        
        // Check if line starts with bullet point
        if (line.startsWith('• ') || line.startsWith('- ')) {
            if (!inList) {
                result.push('<ul class="bot-list">');
                inList = true;
            }
            // Remove the bullet/dash and wrap in li
            const content = line.substring(2).trim();
            result.push(`<li>${content}</li>`);
        } else {
            // If we were in a list and this line is not a list item, close the list
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            
            // Handle different types of lines
            if (line.match(/^\*\*.*\*\*:?\s*$/)) {
                // Lines that are entirely bold (main section headers)
                result.push(`<div class="bot-section-header">${line}</div>`);
            } else if (line.includes('<strong>') && line.includes('</strong>') && line.includes(':')) {
                // Lines with bold parts and colons (subsection headers)
                result.push(`<div class="bot-subsection">${line}</div>`);
            } else if (line.match(/^[🎯🏭💻🛠️⏰🔧📞💬📧🎫🚀🤖🌐📱🛡️🔒✅🆕]/)) {
                // Lines starting with emojis (special highlights)
                result.push(`<div class="bot-highlight-line">${line}</div>`);
            } else {
                // Regular text lines
                result.push(`<div class="bot-text-line">${line}</div>`);
            }
        }
    }
    
    // Close any open list
    if (inList) {
        result.push('</ul>');
    }
    
    return result.join('');
}

// Logout function - Cookie-based with token cleanup
async function logout() {
    safeLog('Logout initiated');
    
    // 🎯 CORE: Save on logout (only if session has messages)
    const saveResult = await sessionManager.saveSessionOnLogout();
    
    if (saveResult.success) {
        safeLog(`Logout save completed: ${saveResult.reason}`);
    } else {
        safeWarn(`Logout save failed: ${saveResult.error}`);
        // Non-blocking error - user can still logout
    }
    
    try {
        // Call logout endpoint to clear cookies and revoke tokens
        const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            safeLog('Server logout successful');
        } else {
            safeWarn('Server logout failed, continuing with client cleanup');
        }
    } catch (error) {
        safeWarn('Server logout error', error.message);
        // Continue with client cleanup even if server logout fails
    }
    
    // Close history sidebar if it's open
    closeChatHistorySidebar();
    
    // Clear UI state
    isLoggedIn = false;
    currentUser = null;
    window.jwtToken = null; // Clear any JWT token from memory
    
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
    
    updateHistoryButtonVisibility();
    
    safeLog('Logout completed');
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

// Send message function - Updated for cookie-based authentication
async function sendMessage() {
    devLog('sendMessage called', { isTyping, isLoggedIn });
    
    if (isTyping || !isLoggedIn) {
        safeLog('Message blocked: typing in progress or user not logged in');
        return;
    }
    
    const message = messageInput.value.trim();
    if (!message) {
        safeLog('Empty message, returning');
        return;
    }
    
    safeLog('Sending message to chat API');
    
    // Clear input but keep it enabled
    messageInput.value = '';
    messageInput.disabled = false;
    
    // Add user message to chat UI
    addMessageToUI(message, 'user');
    safeLog('User message added to chat');
    
    // Show typing indicator
    showTyping();
    
    try {
        // Use authenticated endpoint for logged-in users
        const endpoint = '/chat/authenticated';
        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include', // Include cookies
            body: JSON.stringify({
                message: message
            })
        };
        
        // Add JWT token if available (for fallback compatibility)
        if (window.jwtToken) {
            requestOptions.headers['Authorization'] = `Bearer ${window.jwtToken}`;
        }
        
        safeLog('Making API request to authenticated chat endpoint');
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, requestOptions);
        
        // Handle token expiration
        if (response.status === 401) {
            safeLog('Access token expired, attempting refresh...');
            const refreshed = await refreshTokens();
            if (refreshed) {
                // Retry the request
                const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, requestOptions);
                if (retryResponse.ok) {
                    const data = await retryResponse.json();
                    handleChatResponse(data, message);
                    return;
                }
            }
            throw new Error('Authentication failed');
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        safeLog('Received response from chat API');
        
        handleChatResponse(data, message);
        
    } catch (error) {
        safeError('Chat error', error.message);
        hideTyping();
        addMessageToUI('Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', 'bot');
        
        // If authentication error, prompt re-login
        if (error.message.includes('Authentication') || error.message.includes('401')) {
            setTimeout(() => {
                showLoginError('Oturumunuz sona erdi. Lütfen tekrar giriş yapın.');
                logout();
            }, 2000);
        }
        
        // Ensure input stays enabled even on error
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// Handle chat response processing
function handleChatResponse(data, originalMessage) {
    // Hide typing indicator
    hideTyping();
    
    // Add bot response to chat UI
    addMessageToUI(data.response, 'bot');
    safeLog('Bot response added to chat');
    
    // 🎯 CORE: Add message to session manager with auto-save
    devLog('About to call sessionManager.addMessage()');
    try {
        sessionManager.addMessage(originalMessage, data.response).then(() => {
            safeLog('Message saved to session and database');
        }).catch(error => {
            safeError('Failed to save message to session/database', error.message);
            safeWarn('Message saved to session but failed to save to database', error.message);
        });
    } catch (error) {
        safeError('Failed to save message to session/database', error.message);
    }
    
    // Ensure input stays enabled and focused
    messageInput.disabled = false;
    messageInput.focus();
}

// Error handling for fetch requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});

// Sidebar open/close logic - Updated for session manager with accessibility
function openChatHistorySidebar() {
    devLog('openChatHistorySidebar called');
    devLog('sessionManager exists', !!window.sessionManager);
    devLog('currentUser exists', !!currentUser);
    devLog('isLoggedIn', isLoggedIn);
    
    const sidebar = document.getElementById('chatHistorySidebar');
    const historyList = document.getElementById('chatHistoryList');
    
    devLog('sidebar element found', !!sidebar);
    devLog('historyList element found', !!historyList);
    
    if (sidebar) {
        sidebar.style.transform = 'translateX(0)';
        
        // Enable focus trap for accessibility
        if (window.accessibilityManager) {
            window.accessibilityManager.onSidebarOpen();
        }
        
        // Announce to screen readers
        if (window.accessibilityManager) {
            window.accessibilityManager.announceMessage('Geçmiş paneli açıldı', 'polite');
        }
    }
    
    // Check login state first
    if (!isLoggedIn || !currentUser) {
        safeLog('User not logged in, showing login required message');
        if (historyList) {
            historyList.innerHTML = `
                <li role="listitem" style="padding: 40px; text-align: center; color: #ffd700;">
                    🔒 Geçmiş sohbetleri görüntülemek için<br>
                    giriş yapmanız gerekiyor<br><br>
                    <button onclick="closeChatHistorySidebar()" 
                            style="margin-top: 10px; padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;"
                            aria-label="Geçmiş panelini kapat">
                        Tamam
                    </button>
                </li>
            `;
        }
        return;
    }
    
    if (window.sessionManager && typeof sessionManager.loadHistoryPanel === 'function') {
        devLog('Calling sessionManager.loadHistoryPanel()');
        sessionManager.loadHistoryPanel();
    } else {
        safeError('SessionManager or loadHistoryPanel not available');
        if (historyList) {
            historyList.innerHTML = `
                <li role="listitem" style="padding: 40px; text-align: center; color: #e74c3c;">
                    ❌ SessionManager yüklenemedi<br>
                    <button onclick="location.reload()" 
                            style="margin-top: 10px; padding: 5px 10px; background: #e74c3c; color: white; border: none; border-radius: 4px; cursor: pointer;"
                            aria-label="Sayfayı yenile">
                        Sayfayı Yenile
                    </button>
                </li>
            `;
        }
    }
}

function closeChatHistorySidebar() {
    const sidebar = document.getElementById('chatHistorySidebar');
    if (sidebar) {
        sidebar.style.transform = 'translateX(-100%)';
        
        // Disable focus trap for accessibility
        if (window.accessibilityManager) {
            window.accessibilityManager.onSidebarClose();
        }
        
        // Announce to screen readers
        if (window.accessibilityManager) {
            window.accessibilityManager.announceMessage('Geçmiş paneli kapatıldı', 'polite');
        }
    }
}

// Expose for HTML
window.openChatHistorySidebar = openChatHistorySidebar;
window.closeChatHistorySidebar = closeChatHistorySidebar;

// Show/hide history button based on login state
function updateHistoryButtonVisibility() {
    const historyBtn = document.getElementById('openHistoryBtn');
    
    devLog('updateHistoryButtonVisibility called');
    devLog('historyBtn element found', !!historyBtn);
    devLog('isLoggedIn', isLoggedIn);
    devLog('currentUser exists', !!currentUser);
    
    if (historyBtn) {
        // Only show history button when user is logged in
        if (isLoggedIn && currentUser) {
            historyBtn.style.display = 'block';
            devLog('History button made visible (user logged in)');
        } else {
            historyBtn.style.display = 'none';
            devLog('History button hidden (user not logged in)');
        }
    } else {
        safeError('History button element not found');
    }
}

// 🚪 AUTO-SAVE ON PAGE CLOSE/REFRESH
window.addEventListener('beforeunload', function(event) {
    // Save session when user closes tab or refreshes page
    if (isLoggedIn && sessionManager && sessionManager.currentSession && (currentUser || window.jwtToken)) {
        safeLog('Page closing, saving session...');
        
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
                    devLog('Session save beacon sent successfully');
                }
            }
        } catch (error) {
            safeWarn('Error saving session on page close', error.message);
        }
    }
});

safeLog('Main script loaded - session management ready');
