/**
 * 🎯 MEFAPEX Session & History Manager
 * Implements exact session behavior as specified:
 * - New session on every login
 * - Save on logout (only if has messages)
 * - History cap = 15 sessions per user
 * - Per-user isolation
 * - Proper error handling and edge cases
 */

class SessionManager {
    constructor() {
        this.currentSession = null;
        this.authToken = null;
        this.userId = null;
        this.API_BASE_URL = window.location.origin;
        
        // Session state
        this.sessionStartedAt = null;
        this.messages = [];
        
        // History cache
        this.historyCache = null;
        this.historyCacheExpiry = null;
        
        // Constants
        this.MAX_HISTORY_SESSIONS = 15;
        this.CACHE_DURATION_MS = 30000; // 30 seconds
        
        console.log('🚀 SessionManager initialized');
    }

    /**
     * CORE: New session on login
     * Create fresh session - clean start, no history display
     */
    async startNewSessionOnLogin(authToken, userId) {
        console.log('🆕 Starting new session on login');
        
        this.authToken = authToken;
        this.userId = userId;
        
        // Always create fresh session on login
        this.currentSession = this.generateSessionId();
        this.sessionStartedAt = new Date().toISOString();
        this.messages = [];
        
        // Clear any existing chat UI
        this.clearChatUI();
        
        // Show welcome message only - no history display
        this.showWelcomeMessage();
        
        // Focus composer
        this.focusComposer();
        
        console.log(`✅ New session started: ${this.currentSession}`);
        return this.currentSession;
    }

    /**
     * CORE: Save on logout
     * Save current session to history if it has messages
     */
    async saveSessionOnLogout() {
        console.log('💾 Save session on logout triggered');
        
        if (!this.currentSession || !this.authToken || !this.userId) {
            console.log('❌ No session to save - missing session, auth, or user');
            return { success: true, reason: 'no_session' };
        }

        // Edge case: Don't save empty sessions
        if (this.messages.length === 0) {
            console.log('✅ Empty session - not saving');
            return { success: true, reason: 'empty_session' };
        }

        try {
            const sessionData = this.buildSessionData();
            
            // Save to backend with retry logic
            const saveResult = await this.saveToBackendWithRetry(sessionData);
            
            if (saveResult.success) {
                console.log('✅ Session saved successfully on logout');
                
                // Clear current session
                this.clearCurrentSession();
                
                // Invalidate history cache
                this.invalidateHistoryCache();
                
                return { success: true, reason: 'saved' };
            } else {
                throw new Error(saveResult.error || 'Backend save failed');
            }
            
        } catch (error) {
            console.error('❌ Failed to save session on logout:', error);
            
            // Show non-blocking toast
            this.showSaveErrorToast(error.message);
            
            // Keep session in memory for retry
            return { success: false, error: error.message };
        }
    }

    /**
     * CORE: Load history panel
     * Fetch and render the list with proper states
     */
    async loadHistoryPanel() {
        console.log('📚 Loading history panel');
        console.log('📚 Auth token exists:', !!this.authToken);
        console.log('📚 User ID:', this.userId);
        
        if (!this.authToken || !this.userId) {
            console.error('❌ Missing auth token or user ID');
            this.showHistoryError('Lütfen önce giriş yapın');
            return;
        }

        // Show loading state
        this.showHistoryLoading();
        console.log('📚 Loading state shown, fetching history...');

        try {
            const history = await this.fetchUserHistory();
            console.log('📚 History fetched:', history.length, 'sessions');
            console.log('📚 History data:', history);
            
            if (history.length === 0) {
                console.log('📚 No history found, showing empty state');
                this.showHistoryEmpty();
            } else {
                console.log('📚 Rendering history list');
                this.renderHistoryList(history);
            }
            
        } catch (error) {
            console.error('❌ Failed to load history:', error);
            this.showHistoryError('Geçmiş yüklenemedi: ' + error.message);
        }
    }

    /**
     * Manual save action for retry scenarios
     */

    /**
     * Add message to current session and save to database
     */
    async addMessage(userMessage, botResponse) {
        if (!this.currentSession) {
            console.warn('⚠️ No active session for message');
            return;
        }

        const message = {
            id: Date.now(),
            user_message: userMessage,
            bot_response: botResponse,
            timestamp: new Date().toISOString()
        };

        this.messages.push(message);
        console.log(`📝 Message added to session ${this.currentSession} (total: ${this.messages.length})`);
        
        // Auto-save to database immediately
        try {
            await this.saveMessageToDatabase(message);
            console.log('✅ Message auto-saved to database');
        } catch (error) {
            console.error('❌ Failed to auto-save message:', error);
            // Continue anyway - message is still in memory for manual save
        }
    }

    /**
     * Save individual message to database
     */
    async saveMessageToDatabase(message) {
        if (!this.authToken || !this.currentSession) {
            throw new Error('No authentication token or session');
        }

        const sessionData = {
            sessionId: this.currentSession,
            startedAt: this.sessionStartedAt,
            messages: [message], // Single message
            messageCount: 1,
            userId: this.userId
        };

        const response = await fetch(`${this.API_BASE_URL}/chat/sessions/save`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.authToken}`
            },
            body: JSON.stringify(sessionData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        return await response.json();
    }

    /**
     * Manual save action for retry scenarios
     */
    async saveNow() {
        console.log('💾 Manual save triggered');
        
        if (!this.currentSession || this.messages.length === 0) {
            this.showToast('Kaydedilecek mesaj yok', 'info');
            return;
        }

        try {
            const sessionData = this.buildSessionData();
            const result = await this.saveToBackendWithRetry(sessionData);
            
            if (result.success) {
                this.showToast('Oturum başarıyla kaydedildi', 'success');
                this.invalidateHistoryCache();
            } else {
                throw new Error(result.error);
            }
            
        } catch (error) {
            console.error('❌ Manual save failed:', error);
            this.showToast('Kaydetme başarısız: ' + error.message, 'error');
        }
    }

    /**
     * PRIVATE METHODS
     */

    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    buildSessionData() {
        return {
            sessionId: this.currentSession,
            startedAt: this.sessionStartedAt,
            messages: this.messages,
            messageCount: this.messages.length,
            userId: this.userId
        };
    }

    async saveToBackendWithRetry(sessionData, maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`💾 Save attempt ${attempt}/${maxRetries}`);
                console.log(`🔑 Auth token available: ${!!this.authToken}`);
                console.log(`📝 Session data:`, sessionData);
                
                if (!this.authToken) {
                    throw new Error('No authentication token available');
                }
                
                const response = await fetch(`${this.API_BASE_URL}/chat/sessions/save`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${this.authToken}`
                    },
                    body: JSON.stringify(sessionData)
                });

                console.log(`📊 Response status: ${response.status}`);
                console.log(`📊 Response headers:`, [...response.headers.entries()]);

                if (response.ok) {
                    const result = await response.json();
                    console.log(`✅ Save successful:`, result);
                    return { success: true, data: result };
                } else {
                    const errorText = await response.text();
                    console.error(`❌ Response error: ${response.status} - ${errorText}`);
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
            } catch (error) {
                console.warn(`💥 Save attempt ${attempt} failed:`, error);
                
                if (attempt === maxRetries) {
                    return { success: false, error: error.message };
                }
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }

    async fetchUserHistory() {
        // Check cache first
        if (this.historyCache && this.historyCacheExpiry > Date.now()) {
            console.log('📚 Using cached history');
            return this.historyCache;
        }

        console.log('📡 Fetching fresh history from backend');
        console.log('📡 API URL:', `${this.API_BASE_URL}/chat/sessions/${this.userId}`);
        console.log('📡 Auth token available:', !!this.authToken);
        
        const response = await fetch(`${this.API_BASE_URL}/chat/sessions/${this.userId}`, {
            headers: {
                'Authorization': `Bearer ${this.authToken}`
            }
        });

        console.log('📡 Response status:', response.status);
        console.log('📡 Response headers:', [...response.headers.entries()]);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('📡 Response error:', errorText);
            throw new Error(`Failed to fetch history: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log('📡 Response data:', data);
        
        const sessions = data.sessions || [];
        console.log('📡 Extracted sessions:', sessions.length);
        
        // Cache the result
        this.historyCache = sessions;
        this.historyCacheExpiry = Date.now() + this.CACHE_DURATION_MS;
        console.log('📡 History cached for', this.CACHE_DURATION_MS / 1000, 'seconds');
        
        return sessions;
    }

    invalidateHistoryCache() {
        this.historyCache = null;
        this.historyCacheExpiry = null;
        console.log('🗑️ History cache invalidated');
    }

    clearCurrentSession() {
        this.currentSession = null;
        this.sessionStartedAt = null;
        this.messages = [];
        console.log('🧹 Current session cleared');
    }

    /**
     * UI METHODS
     */

    clearChatUI() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
    }

    showWelcomeMessage() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz.<br>
                    Size nasıl yardımcı olabilirim?
                </div>
            `;
        }
    }

    focusComposer() {
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            setTimeout(() => messageInput.focus(), 100);
        }
    }

    showHistoryLoading() {
        const historyList = document.getElementById('chatHistoryList');
        if (historyList) {
            historyList.innerHTML = `
                <li style="padding: 20px; text-align: center; color: #ccc;">
                    <div class="spinner" style="display: inline-block; width: 20px; height: 20px; border: 2px solid #666; border-top: 2px solid #fff; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <div style="margin-top: 10px;">Yükleniyor...</div>
                </li>
            `;
        }
    }

    showHistoryEmpty() {
        const historyList = document.getElementById('chatHistoryList');
        if (historyList) {
            historyList.innerHTML = `
                <li style="padding: 40px; text-align: center; color: #999;">
                    📭 Henüz hiç sohbet yok.<br>
                    <small style="color: #666;">İlk mesajınızı gönderin!</small>
                </li>
            `;
        }
    }

    showHistoryError(message = 'Geçmiş yüklenemedi') {
        const historyList = document.getElementById('chatHistoryList');
        if (historyList) {
            historyList.innerHTML = `
                <li style="padding: 40px; text-align: center; color: #e74c3c;">
                    ❌ ${message}<br>
                    <button onclick="sessionManager.loadHistoryPanel()" 
                            style="margin-top: 10px; padding: 5px 10px; background: #e74c3c; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Tekrar Dene
                    </button>
                </li>
            `;
        }
    }

    renderHistoryList(sessions) {
        const historyList = document.getElementById('chatHistoryList');
        if (!historyList) return;

        let html = `
            <li style="padding: 12px 20px; background: rgba(102,126,234,0.15); border-bottom: 2px solid #667eea; color: #667eea; font-weight: 600; text-align: center;">
                📚 Geçmiş Sohbetler (${sessions.length}/${this.MAX_HISTORY_SESSIONS})
            </li>
        `;

        // Show current session if it has messages
        if (this.currentSession && this.messages.length > 0) {
            html += `
                <li style="padding: 16px 20px; border-bottom: 2px solid #28a745; background: rgba(40,167,69,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #28a745; font-weight: 600;">🔥 Aktif Sohbet</span>
                        <span style="color: #999; font-size: 12px;">${this.messages.length} mesaj</span>
                    </div>
                    <div style="color: #ccc; font-size: 13px; margin-top: 4px;">
                        ${this.getSessionPreview(this.messages)}
                    </div>
                </li>
            `;
        }

        // Render history sessions
        sessions.forEach((session, index) => {
            const timeAgo = this.getTimeAgo(new Date(session.startedAt || session.created_at));
            const preview = session.preview || this.getSessionPreview(session.messages || []);
            
            html += `
                <li style="padding: 16px 20px; border-bottom: 1px solid #444; cursor: pointer; transition: background 0.3s;"
                    onmouseover="this.style.background='rgba(255,255,255,0.05)'"
                    onmouseout="this.style.background='transparent'"
                    onclick="sessionManager.loadHistorySession('${session.sessionId || session.session_id}')">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #ffd700; font-weight: 500;">💬 Sohbet #${sessions.length - index}</span>
                        <span style="color: #999; font-size: 12px;">${session.messageCount || session.message_count || 0} mesaj</span>
                    </div>
                    <div style="color: #ccc; font-size: 13px; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" 
                         title="${preview}">
                        "${preview}"
                    </div>
                    <div style="color: #888; font-size: 11px; margin-top: 2px;">🕒 ${timeAgo}</div>
                </li>
            `;
        });

        // Footer info
        html += `
            <li style="padding: 12px 20px; background: rgba(255,255,255,0.05); border-top: 1px solid #666; color: #888; text-align: center; font-size: 12px;">
                💡 En son ${this.MAX_HISTORY_SESSIONS} sohbet saklanır
            </li>
        `;

        historyList.innerHTML = html;
    }

    async loadHistorySession(sessionId) {
        console.log(`📖 Loading history session: ${sessionId}`);
        
        try {
            const response = await fetch(`${this.API_BASE_URL}/chat/sessions/${sessionId}/messages`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to load session: ${response.status}`);
            }

            const data = await response.json();
            const messages = data.messages || [];

            // Clear chat and show history header
            this.clearChatUI();
            
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                // Session header
                const sessionDate = new Date(data.startedAt || data.created_at).toLocaleString('tr-TR');
                chatMessages.innerHTML = `
                    <div style="text-align: center; padding: 15px; margin-bottom: 10px; background: rgba(102,126,234,0.1); border-radius: 10px; color: #667eea; font-weight: 600;">
                        📚 Geçmiş Sohbet - ${sessionDate}
                    </div>
                `;

                // Load messages
                messages.forEach(msg => {
                    console.log('📖 Loading history message:', msg);
                    
                    // Safety checks for message content
                    const userMsg = msg.user_message || msg.message || 'Boş mesaj';
                    const botMsg = msg.bot_response || msg.response || 'Boş yanıt';
                    
                    this.addMessageToUI(userMsg, 'user');
                    this.addMessageToUI(botMsg, 'bot');
                });

                // Back button
                const backButton = document.createElement('div');
                backButton.style.cssText = 'text-align: center; padding: 15px; margin-top: 20px;';
                backButton.innerHTML = `
                    <button onclick="sessionManager.returnToCurrentSession()" 
                            style="background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600;">
                        📝 Mevcut Sohbete Dön
                    </button>
                `;
                chatMessages.appendChild(backButton);
            }

            // Close sidebar
            this.closeHistorySidebar();
            
        } catch (error) {
            console.error('❌ Failed to load history session:', error);
            this.showToast('Geçmiş sohbet yüklenemedi', 'error');
        }
    }

    returnToCurrentSession() {
        console.log('🔄 Returning to current session');
        
        this.clearChatUI();
        
        if (this.currentSession && this.messages.length > 0) {
            // Restore current session messages
            this.messages.forEach(msg => {
                console.log('🔄 Restoring current message:', msg);
                
                // Safety checks for message content
                const userMsg = msg.user_message || msg.message || 'Boş mesaj';
                const botMsg = msg.bot_response || msg.response || 'Boş yanıt';
                
                this.addMessageToUI(userMsg, 'user');
                this.addMessageToUI(botMsg, 'bot');
            });
        } else {
            // Show welcome message
            this.showWelcomeMessage();
        }
        
        this.focusComposer();
        this.scrollToBottom();
    }

    addMessageToUI(text, sender) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;

        // Safety check for text parameter
        if (text === null || text === undefined) {
            console.warn('⚠️ addMessageToUI called with null/undefined text');
            text = '';
        }
        
        // Convert to string if not already
        text = String(text);

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.innerHTML = this.formatMessage(text);
        
        messageDiv.appendChild(bubbleDiv);
        
        // Remove welcome message if exists
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        chatMessages.appendChild(messageDiv);
    }

    formatMessage(text) {
        // Safety check for text parameter
        if (text === null || text === undefined) {
            return '';
        }
        
        // Convert to string if not already
        text = String(text);
        
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 100);
        }
    }

    closeHistorySidebar() {
        const sidebar = document.getElementById('chatHistorySidebar');
        if (sidebar) {
            sidebar.style.transform = 'translateX(-100%)';
        }
    }

    getSessionPreview(messages) {
        if (!messages || messages.length === 0) return 'Boş sohbet';
        
        const firstMessage = messages[0];
        const text = firstMessage.user_message || firstMessage.message || '';
        return text.length > 50 ? text.substring(0, 50) + '...' : text;
    }

    getTimeAgo(date) {
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

    showSaveErrorToast(message) {
        this.showToast(`Kaydetme başarısız: ${message}`, 'error');
    }

    showToast(message, type = 'info') {
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

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 5000);
    }

    /**
     * CLEANUP METHODS
     */
    
    cleanup() {
        this.currentSession = null;
        this.authToken = null;
        this.userId = null;
        this.sessionStartedAt = null;
        this.messages = [];
        this.invalidateHistoryCache();
        console.log('🧹 SessionManager cleaned up');
    }
}

// Global instance
window.sessionManager = new SessionManager();

// Debug: Check if SessionManager is properly loaded
console.log('✅ SessionManager instance created:', !!window.sessionManager);
console.log('✅ SessionManager methods available:');
console.log('  - loadHistoryPanel:', typeof window.sessionManager.loadHistoryPanel);
console.log('  - fetchUserHistory:', typeof window.sessionManager.fetchUserHistory);
console.log('  - startNewSessionOnLogin:', typeof window.sessionManager.startNewSessionOnLogin);

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

console.log('✅ SessionManager module loaded');
