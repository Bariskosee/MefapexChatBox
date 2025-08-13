/**
 * 🛠️ MEFAPEX Chatbot - Shared Utilities
 * Common JavaScript functions used across multiple files
 * Version: 2.2.0
 */

/**
 * Format message text with markdown-like support
 * @param {string|null|undefined} text - Text to format
 * @returns {string} Formatted HTML string
 */
function formatMessage(text) {
    // Safety check for text parameter
    if (text === null || text === undefined) {
        return '';
    }
    
    // Convert to string if not already
    text = String(text);
    
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold: **text**
        .replace(/\*(.*?)\*/g, '<em>$1</em>')              // Italic: *text*
        .replace(/\n/g, '<br>')                            // Line breaks
        .replace(/•/g, '&bull;')                           // Bullet points
        .replace(/✅/g, '&#x2705;')                        // Check mark
        .replace(/❌/g, '&#x274C;')                        // Cross mark
        .replace(/🚀/g, '&#x1F680;')                       // Rocket
        .replace(/💡/g, '&#x1F4A1;')                       // Light bulb
        .replace(/📋/g, '&#x1F4CB;')                       // Clipboard
        .replace(/🛡️/g, '&#x1F6E1;&#xFE0F;');             // Shield
}

/**
 * Smooth scroll to bottom of chat container
 * @param {string} [containerId='chatMessages'] - ID of the chat container
 */
function scrollToBottom(containerId = 'chatMessages') {
    const chatMessages = document.getElementById(containerId);
    if (chatMessages) {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }
}

/**
 * Add message to chat UI
 * @param {string} text - Message text
 * @param {string} sender - Message sender ('user' or 'bot')
 * @param {string} [containerId='chatMessages'] - ID of the chat container
 */
function addMessageToUI(text, sender, containerId = 'chatMessages') {
    const chatMessages = document.getElementById(containerId);
    if (!chatMessages) {
        console.warn(`⚠️ Chat container '${containerId}' not found`);
        return;
    }

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
    bubbleDiv.innerHTML = formatMessage(text);
    
    messageDiv.appendChild(bubbleDiv);
    chatMessages.appendChild(messageDiv);
    
    // Auto-scroll to bottom
    scrollToBottom(containerId);
}

/**
 * Show typing indicator
 * @param {string} [indicatorId='typingIndicator'] - ID of typing indicator element
 */
function showTyping(indicatorId = 'typingIndicator') {
    const typingIndicator = document.getElementById(indicatorId);
    const sendButton = document.getElementById('sendButton');
    const messageInput = document.getElementById('messageInput');
    
    if (typingIndicator) {
        typingIndicator.style.display = 'block';
    }
    
    if (sendButton) sendButton.disabled = true;
    if (messageInput) messageInput.disabled = true;
    
    // Scroll to show typing indicator
    scrollToBottom();
}

/**
 * Hide typing indicator
 * @param {string} [indicatorId='typingIndicator'] - ID of typing indicator element
 */
function hideTyping(indicatorId = 'typingIndicator') {
    const typingIndicator = document.getElementById(indicatorId);
    const sendButton = document.getElementById('sendButton');
    const messageInput = document.getElementById('messageInput');
    
    if (typingIndicator) {
        typingIndicator.style.display = 'none';
    }
    
    if (sendButton) sendButton.disabled = false;
    if (messageInput) {
        messageInput.disabled = false;
        // Focus for next message
        setTimeout(() => messageInput.focus(), 100);
    }
}

/**
 * Generate a unique session ID
 * @returns {string} Unique session ID
 */
function generateSessionId() {
    const timestamp = Date.now();
    const randomString = Math.random().toString(36).substring(2, 11);
    return `session_${timestamp}_${randomString}`;
}

/**
 * Get time ago string
 * @param {Date|string} date - Date to compare
 * @returns {string} Time ago string (e.g., "2 dakika önce")
 */
function getTimeAgo(date) {
    const now = new Date();
    const past = new Date(date);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Şimdi';
    if (diffMins < 60) return `${diffMins} dakika önce`;
    if (diffHours < 24) return `${diffHours} saat önce`;
    if (diffDays < 7) return `${diffDays} gün önce`;
    
    return past.toLocaleDateString('tr-TR');
}

/**
 * Show toast notification
 * @param {string} message - Message to show
 * @param {string} [type='info'] - Toast type: 'info', 'success', 'error', 'warning'
 * @param {number} [duration=5000] - Duration in milliseconds
 */
function showToast(message, type = 'info', duration = 5000) {
    // Create toast element
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        max-width: 300px;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    `;

    // Style based on type
    switch (type) {
        case 'success':
            toast.style.background = '#28a745';
            break;
        case 'error':
            toast.style.background = '#dc3545';
            break;
        case 'warning':
            toast.style.background = '#ffc107';
            toast.style.color = '#000';
            break;
        default:
            toast.style.background = '#6c757d';
    }

    toast.textContent = message;
    document.body.appendChild(toast);

    // Auto remove after duration
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, duration);
}

// Add CSS animations for toast if not already present
if (!document.querySelector('#toast-animations')) {
    const style = document.createElement('style');
    style.id = 'toast-animations';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

console.log('🛠️ MEFAPEX Utils loaded - v2.2.0');
