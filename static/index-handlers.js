// Event handlers and functions for index.html

function openChatHistorySidebar() {
    const sidebar = document.getElementById('chatHistorySidebar');
    if (sidebar) {
        sidebar.style.transform = 'translateX(0)';
    }
}

function closeChatHistorySidebar() {
    const sidebar = document.getElementById('chatHistorySidebar');
    if (sidebar) {
        sidebar.style.transform = 'translateX(-100%)';
    }
}

function logout() {
    console.log('🚪 Logout');
    
    // Clear any authentication data
    sessionStorage.clear();
    localStorage.removeItem('authToken');
    
    // Reset the interface
    const loginContainer = document.getElementById('loginContainer');
    const chatContainer = document.getElementById('chatContainer');
    const logoutBtn = document.getElementById('logoutBtn');
    const openHistoryBtn = document.getElementById('openHistoryBtn');
    
    if (loginContainer) loginContainer.style.display = 'flex';
    if (chatContainer) chatContainer.style.display = 'none';
    if (logoutBtn) logoutBtn.style.display = 'none';
    if (openHistoryBtn) openHistoryBtn.style.display = 'none';
    
    // Clear form fields
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');
    const messageInput = document.getElementById('messageInput');
    
    if (usernameField) usernameField.value = '';
    if (passwordField) passwordField.value = '';
    if (messageInput) messageInput.value = '';
    
    // Reset chat messages
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = `
            <div class="welcome-message">
                👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>
                Size nasıl yardımcı olabilirim?
            </div>
        `;
    }
    
    // Clear any error messages
    const loginError = document.getElementById('loginError');
    if (loginError) loginError.style.display = 'none';
    
    // Focus on username field
    if (usernameField) usernameField.focus();
}

function login() {
    const username = document.getElementById('username')?.value?.trim();
    const password = document.getElementById('password')?.value?.trim();
    const loginError = document.getElementById('loginError');
    
    // Clear previous errors
    if (loginError) {
        loginError.style.display = 'none';
    }
    
    if (!username || !password) {
        showLoginError('Kullanıcı adı ve şifre gereklidir.');
        return;
    }
    
    // Use existing login logic from script.js
    if (window.performLogin) {
        window.performLogin();
    } else {
        showLoginError('Giriş sistemi yüklenemedi. Sayfayı yenileyin.');
    }
}

function showLoginError(message) {
    const loginError = document.getElementById('loginError');
    if (loginError) {
        loginError.textContent = message;
        loginError.style.display = 'block';
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    if (!messageInput) return;
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Use existing send message logic from script.js
    if (window.performSendMessage) {
        window.performSendMessage(message);
    } else {
        console.error('Send message function not available');
    }
}

function scrollToTop() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
}

// Setup event listeners when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Setup Enter key handlers for login form
    const passwordField = document.getElementById('password');
    if (passwordField) {
        passwordField.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                login();
            }
        });
    }
    
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                login();
            }
        });
    }
    
    // Setup login button click handler
    const loginButton = document.getElementById('loginButton');
    if (loginButton) {
        loginButton.addEventListener('click', login);
    }
    
    // Setup logout button click handler
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    
    // Setup history button click handler
    const openHistoryBtn = document.getElementById('openHistoryBtn');
    if (openHistoryBtn) {
        openHistoryBtn.addEventListener('click', openChatHistorySidebar);
    }
    
    // Setup send button click handler
    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    // Setup scroll to top button click handler
    const scrollToTopBtn = document.getElementById('scrollToTop');
    if (scrollToTopBtn) {
        scrollToTopBtn.addEventListener('click', scrollToTop);
    }
    
    // Setup message input key handler
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keypress', handleKeyPress);
    }
    
    // Setup sidebar close button
    const sidebarCloseBtn = document.querySelector('.sidebar-close-btn');
    if (sidebarCloseBtn) {
        sidebarCloseBtn.addEventListener('click', closeChatHistorySidebar);
        
        // Add hover effects
        sidebarCloseBtn.addEventListener('mouseover', function() {
            this.style.background = 'rgba(255,255,255,0.2)';
        });
        sidebarCloseBtn.addEventListener('mouseout', function() {
            this.style.background = 'none';
        });
    }
    
    // Setup scroll to top button visibility
    const chatMessages = document.getElementById('chatMessages');
    
    if (chatMessages && scrollToTopBtn) {
        chatMessages.addEventListener('scroll', function() {
            if (chatMessages.scrollTop > 300) {
                scrollToTopBtn.classList.add('show');
            } else {
                scrollToTopBtn.classList.remove('show');
            }
        });
    }
    
    // Setup sidebar close on click outside
    document.addEventListener('click', function(event) {
        const sidebar = document.getElementById('chatHistorySidebar');
        const openHistoryBtn = document.getElementById('openHistoryBtn');
        
        if (sidebar && !sidebar.contains(event.target) && event.target !== openHistoryBtn) {
            const sidebarTransform = window.getComputedStyle(sidebar).transform;
            if (sidebarTransform !== 'matrix(1, 0, 0, 1, -300, 0)' && sidebarTransform !== 'none') {
                closeChatHistorySidebar();
            }
        }
    });
});
