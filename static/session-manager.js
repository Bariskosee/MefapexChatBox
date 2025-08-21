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
        this.isAuthenticated = false;
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
        
        // Save debounce mechanism
        this.saveTimeout = null;
        this.isSaving = false;
        this.pendingSaveRequest = false;
        
        safeLog('SessionManager initialized');
    }

    /**
     * CORE: New session on login
     * Create fresh session - clean start, no history display
     */
    async startNewSessionOnLogin(isAuthenticated, userId) {
        safeLog('Starting new session on login');
        devLog('Is authenticated', !!isAuthenticated);
        devLog('User ID provided', !!userId);
        
        this.isAuthenticated = !!isAuthenticated;
        this.userId = userId;
        
        devLog('Auth status set in sessionManager', this.isAuthenticated);
        devLog('User ID set in sessionManager', !!this.userId);
        
        // Always create fresh session on login
        this.currentSession = generateSessionId();
        this.sessionStartedAt = new Date().toISOString();
        this.messages = [];
        
        // Clear any existing chat UI
        this.clearChatUI();
        
        // Show welcome message only - no history display
        this.showWelcomeMessage();
        
        // Focus composer
        this.focusComposer();
        
        safeLog('New session started successfully');
        return this.currentSession;
    }
    
    /**
     * Get authentication headers for API requests
     */
    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add JWT token if available (for fallback compatibility)
        if (window.jwtToken) {
            headers['Authorization'] = `Bearer ${window.jwtToken}`;
        }
        
        return headers;
    }
    
    /**
     * Get fetch options with credentials for cookie-based auth
     */
    getFetchOptions(method = 'GET', body = null) {
        const options = {
            method: method,
            headers: this.getAuthHeaders(),
            credentials: 'include' // Include cookies
        };
        
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        return options;
    }

    /**
     * CORE: Save on logout
     * Save current session to history if it has messages
     */
    async saveSessionOnLogout() {
        safeLog('Save session on logout triggered');
        
        if (!this.currentSession || !this.isAuthenticated || !this.userId) {
            safeLog('No session to save - missing session, auth, or user');
            return { success: true, reason: 'no_session' };
        }

        // Edge case: Don't save empty sessions
        if (this.messages.length === 0) {
            safeLog('Empty session - not saving');
            return { success: true, reason: 'empty_session' };
        }

        try {
            const sessionData = this.buildSessionData();
            
            // Save to backend with retry logic
            const saveResult = await this.saveToBackendWithRetry(sessionData);
            
            if (saveResult.success) {
                safeLog('Session saved successfully on logout');
                
                // Clear current session
                this.clearCurrentSession();
                
                // Invalidate history cache
                this.invalidateHistoryCache();
                
                return { success: true, reason: 'saved' };
            } else {
                throw new Error(saveResult.error || 'Backend save failed');
            }
            
        } catch (error) {
            safeError('Failed to save session on logout', error.message);
            
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
        safeLog('Loading history panel');
        devLog('Auth status', this.isAuthenticated);
        devLog('User ID exists', !!this.userId);
        
        // Check if user is logged in first
        if (!this.isAuthenticated || !this.userId) {
            safeWarn('Not authenticated or no user ID - user not logged in');
            this.showHistoryLoginRequired();
            return;
        }

        // Show loading state
        this.showHistoryLoading();
        safeLog('Loading state shown, fetching history...');

        try {
            const history = await this.fetchUserHistory();
            safeLog('History fetched successfully', { count: history.length });
            devLog('History data', history);
            
            if (history.length === 0) {
                safeLog('No history found, showing empty state');
                this.showHistoryEmpty();
            } else {
                safeLog('Rendering history list');
                this.renderHistoryList(history);
            }
            
        } catch (error) {
            safeError('Failed to load history', error.message);
            
            // Check if it's an authentication error
            if (error.message.includes('401') || error.message.includes('403')) {
                this.showHistoryLoginRequired();
            } else {
                this.showHistoryError('Geçmiş yüklenemedi: ' + error.message);
            }
        }
    }

    /**
     * Manual save action for retry scenarios
     */

    /**
     * Add message to current session and save to database with debounce
     */
    async addMessage(userMessage, botResponse) {
        if (!this.currentSession) {
            console.warn('⚠️ No active session for message');
            return;
        }

        // Create message hash for duplicate prevention
        const messageHash = this.createMessageHash(userMessage, botResponse);
        
        // Check if this exact message already exists in the session
        const messageExists = this.messages.some(msg => {
            const existingHash = this.createMessageHash(
                msg.user_message || '',
                msg.bot_response || ''
            );
            return existingHash === messageHash;
        });

        if (messageExists) {
            console.warn('⚠️ Duplicate message detected, skipping save:', {userMessage, botResponse});
            return;
        }

        const message = {
            id: Date.now(),
            user_message: userMessage,
            bot_response: botResponse,
            timestamp: new Date().toISOString(),
            hash: messageHash
        };

        this.messages.push(message);
        console.log(`📝 Message added to session ${this.currentSession} (total: ${this.messages.length})`);
        
        // Schedule debounced save
        this.scheduleDebouncedSave();
    }

    /**
     * Create a hash for message duplicate detection
     */
    createMessageHash(userMessage, botResponse) {
        const content = `${userMessage || ''}:${botResponse || ''}`;
        // Simple hash function
        let hash = 0;
        for (let i = 0; i < content.length; i++) {
            const char = content.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return hash.toString(36);
    }

    /**
     * Schedule a debounced save to prevent multiple save requests
     */
    scheduleDebouncedSave() {
        // Clear existing timeout
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }

        // If already saving, mark that we need another save after completion
        if (this.isSaving) {
            this.pendingSaveRequest = true;
            return;
        }

        // Schedule save with debounce
        this.saveTimeout = setTimeout(async () => {
            await this.performDebouncedSave();
        }, 500); // 500ms debounce
    }

    /**
     * Perform the actual save with protection against duplicate requests
     */
    async performDebouncedSave() {
        if (this.isSaving) {
            this.pendingSaveRequest = true;
            return;
        }

        this.isSaving = true;
        this.pendingSaveRequest = false;

        try {
            await this.saveCurrentSessionToDatabase();
            console.log('✅ Session saved via debounced save');
        } catch (error) {
            console.error('❌ Failed to save session via debounced save:', error);
        } finally {
            this.isSaving = false;
            
            // If there's a pending request, schedule another save
            if (this.pendingSaveRequest) {
                setTimeout(() => this.scheduleDebouncedSave(), 100);
            }
        }
    }

    /**
     * Save current session to database
     */
    async saveCurrentSessionToDatabase() {
        if (!this.isAuthenticated || !this.currentSession || this.messages.length === 0) {
            console.log('⚠️ Cannot save: not authenticated, no session, or no messages');
            return;
        }

        const sessionData = this.buildSessionData();
        
        console.log('💾 Saving current session to database:', sessionData.sessionId);
        console.log('💾 Message count:', sessionData.messageCount);

        const response = await fetch(`${this.API_BASE_URL}/chat/sessions/save`, this.getFetchOptions('POST', sessionData));

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
            showToast('Kaydedilecek mesaj yok', 'info');
            return;
        }

        try {
            await this.saveCurrentSessionToDatabase();
            showToast('Oturum başarıyla kaydedildi', 'success');
            this.invalidateHistoryCache();
        } catch (error) {
            console.error('❌ Manual save failed:', error);
            showToast('Kaydetme başarısız: ' + error.message, 'error');
        }
    }

    /**
     * PRIVATE METHODS
     */

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
                console.log(`🔑 Auth status: ${this.isAuthenticated}`);
                console.log(`📝 Session data:`, sessionData);
                
                if (!this.isAuthenticated) {
                    throw new Error('User not authenticated');
                }
                
                const response = await fetch(`${this.API_BASE_URL}/chat/sessions/save`, this.getFetchOptions('POST', sessionData));

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
        console.log('📡 Auth status:', this.isAuthenticated);
        
        const response = await fetch(`${this.API_BASE_URL}/chat/sessions/${this.userId}`, this.getFetchOptions());

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

    showHistoryLoginRequired() {
        const historyList = document.getElementById('chatHistoryList');
        if (historyList) {
            historyList.innerHTML = `
                <li style="padding: 40px; text-align: center; color: #5dade2;">
                    🔒 Geçmiş sohbetleri görüntülemek için<br>
                    giriş yapmanız gerekiyor<br><br>
                    <button onclick="closeChatHistorySidebar()" 
                            style="margin-top: 10px; padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">
                        Tamam
                    </button>
                </li>
            `;
        }
    }

    renderHistoryList(sessions) {
        console.log('🎯 renderHistoryList called with sessions:', sessions);
        const historyList = document.getElementById('chatHistoryList');
        if (!historyList) {
            console.error('❌ chatHistoryList element not found');
            return;
        }

        let html = ``;

        // Show current session if it has messages
        if (this.currentSession && this.messages.length > 0) {
            console.log('📝 Adding current session to history list');
            html += `
                <li class="history-session-item active-session">
                    <div class="session-header">
                        <span class="session-title">🔥 Aktif Sohbet</span>
                        <span class="session-count">${this.messages.length} mesaj</span>
                    </div>
                    <div class="session-preview">
                        ${this.getSessionPreview(this.messages)}
                    </div>
                </li>
            `;
        }

        // Render history sessions
        sessions.forEach((session, index) => {
            console.log('📚 Processing session:', session);
            const timeAgo = this.getTimeAgo(new Date(session.startedAt || session.created_at));
            const preview = session.preview || this.getSessionPreview(session.messages || []);
            
            html += `
                <li class="history-session-item" data-session-id="${session.sessionId || session.session_id}">
                    <div class="session-header">
                        <span class="session-title">💬 Sohbet #${sessions.length - index}</span>
                        <span class="session-count">${session.messageCount || session.message_count || 0} mesaj</span>
                    </div>
                    <div class="session-preview" title="${preview}">
                        "${preview}"
                    </div>
                    <div class="session-time">🕒 ${timeAgo}</div>
                </li>
            `;
        });

        // Footer info
        html += `
            <li class="history-footer">
                💡 En son ${this.MAX_HISTORY_SESSIONS} sohbet saklanır
            </li>
        `;

        console.log('📝 Setting historyList innerHTML');
        historyList.innerHTML = html;
        
        // Add event listeners for session items
        const sessionItems = historyList.querySelectorAll('.history-session-item');
        console.log('🎯 Adding event listeners to', sessionItems.length, 'session items');
        sessionItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const sessionId = item.getAttribute('data-session-id');
                console.log('🎯 Session item clicked:', sessionId);
                if (sessionId) {
                    this.loadHistorySession(sessionId);
                }
            });
        });
        console.log('✅ Event listeners added successfully');
    }

    async loadHistorySession(sessionId) {
        console.log(`📖 Loading history session: ${sessionId}`);
        
        try {
            const response = await fetch(`${this.API_BASE_URL}/chat/sessions/${sessionId}/messages`, this.getFetchOptions());

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

                    // Determine role and safely extract content
                    const content = msg.content || msg.user_message || msg.message ||
                                   msg.bot_response || msg.response || '';

                    if (msg.type === 'user' || msg.role === 'user') {
                        addMessageToUI(content || 'Boş mesaj', 'user');
                    } else {
                        addMessageToUI(content || 'Boş yanıt', 'bot');
                    }
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
            if (window.closeChatHistorySidebar) {
                window.closeChatHistorySidebar();
            } else {
                this.closeHistorySidebar();
            }
            
        } catch (error) {
            console.error('❌ Failed to load history session:', error);
            showToast('Geçmiş sohbet yüklenemedi', 'error');
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
                
                addMessageToUI(userMsg, 'user');
                addMessageToUI(botMsg, 'bot');
            });
        } else {
            // Show welcome message
            this.showWelcomeMessage();
        }
        
        this.focusComposer();
        scrollToBottom();
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
        showToast(`Kaydetme başarısız: ${message}`, 'error');
    }

    /**
     * CLEANUP METHODS
     */
    
    cleanup() {
        console.log('🧹 Cleaning up SessionManager...');
        console.log('🧹 Before cleanup - isAuthenticated:', this.isAuthenticated, 'userId:', this.userId);
        
        // Clear any pending save timeout
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
            this.saveTimeout = null;
        }
        
        this.currentSession = null;
        this.isAuthenticated = false;
        this.userId = null;
        this.sessionStartedAt = null;
        this.messages = [];
        this.isSaving = false;
        this.pendingSaveRequest = false;
        this.invalidateHistoryCache();
        
        console.log('🧹 After cleanup - isAuthenticated:', this.isAuthenticated, 'userId:', this.userId);
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
