/**
 * 🧪 Unit Tests for SessionManager
 * Tests all core functionality including edge cases
 */

// Mock fetch globally
global.fetch = jest.fn();

// Mock DOM elements
const mockDOM = {
    chatMessages: { innerHTML: '', appendChild: jest.fn(), querySelector: jest.fn(), querySelectorAll: jest.fn(() => []) },
    messageInput: { focus: jest.fn() },
    chatHistoryList: { innerHTML: '' },
    chatHistorySidebar: { style: { transform: '' } }
};

global.document = {
    getElementById: jest.fn((id) => mockDOM[id] || null),
    createElement: jest.fn(() => ({
        style: { cssText: '' },
        innerHTML: '',
        textContent: '',
        appendChild: jest.fn(),
        parentNode: { removeChild: jest.fn() }
    })),
    head: { appendChild: jest.fn() },
    body: { appendChild: jest.fn() }
};

global.window = { location: { origin: 'http://localhost:8000' } };
global.setTimeout = jest.fn((cb) => cb());

// Import the SessionManager class
require('./session-manager.js');
const SessionManager = global.sessionManager.constructor;

describe('SessionManager', () => {
    let sessionManager;

    beforeEach(() => {
        sessionManager = new SessionManager();
        jest.clearAllMocks();
        fetch.mockClear();
    });

    describe('Core Behavior Tests', () => {
        
        test('startNewSessionOnLogin creates fresh session every time', async () => {
            const authToken = 'test-token';
            const userId = 'user123';
            
            // First login
            const sessionId1 = await sessionManager.startNewSessionOnLogin(authToken, userId);
            
            expect(sessionManager.currentSession).toBe(sessionId1);
            expect(sessionManager.authToken).toBe(authToken);
            expect(sessionManager.userId).toBe(userId);
            expect(sessionManager.messages).toHaveLength(0);
            expect(sessionManager.sessionStartedAt).toBeTruthy();
            
            // Second login should create NEW session
            const sessionId2 = await sessionManager.startNewSessionOnLogin(authToken, userId);
            
            expect(sessionId2).not.toBe(sessionId1);
            expect(sessionManager.currentSession).toBe(sessionId2);
            expect(sessionManager.messages).toHaveLength(0); // Fresh messages
        });

        test('saveSessionOnLogout saves only sessions with messages', async () => {
            // Setup session
            await sessionManager.startNewSessionOnLogin('token', 'user123');
            
            // Mock successful save
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ success: true })
            });
            
            // Test empty session - should not save
            let result = await sessionManager.saveSessionOnLogout();
            expect(result.reason).toBe('empty_session');
            expect(fetch).not.toHaveBeenCalled();
            
            // Add messages
            sessionManager.addMessage('Hello', 'Hi there');
            sessionManager.addMessage('How are you?', 'I am fine');
            
            // Test session with messages - should save
            result = await sessionManager.saveSessionOnLogout();
            expect(result.success).toBe(true);
            expect(result.reason).toBe('saved');
            expect(fetch).toHaveBeenCalledWith(
                'http://localhost:8000/chat/sessions/save',
                expect.objectContaining({
                    method: 'POST',
                    headers: expect.objectContaining({
                        'Authorization': 'Bearer token'
                    }),
                    body: expect.stringContaining('user123')
                })
            );
        });

        test('saveSessionOnLogout handles save failures gracefully', async () => {
            // Setup session with messages
            await sessionManager.startNewSessionOnLogin('token', 'user123');
            sessionManager.addMessage('Test', 'Response');
            
            // Mock save failure
            fetch.mockRejectedValueOnce(new Error('Network error'));
            
            const result = await sessionManager.saveSessionOnLogout();
            
            expect(result.success).toBe(false);
            expect(result.error).toBe('Network error');
            
            // Session should remain in memory for retry
            expect(sessionManager.currentSession).toBeTruthy();
            expect(sessionManager.messages).toHaveLength(1);
        });

        test('history cap - enforces 15 session limit', async () => {
            // Mock API response with exactly 15 sessions
            const mockSessions = Array.from({ length: 15 }, (_, i) => ({
                sessionId: `session_${i}`,
                startedAt: new Date().toISOString(),
                messageCount: 5,
                preview: `Test session ${i}`
            }));
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ sessions: mockSessions })
            });
            
            sessionManager.authToken = 'token';
            sessionManager.userId = 'user123';
            
            const history = await sessionManager.fetchUserHistory();
            
            expect(history).toHaveLength(15);
            expect(history.length).toBeLessThanOrEqual(sessionManager.MAX_HISTORY_SESSIONS);
        });

        test('per-user isolation - uses correct user ID in requests', async () => {
            const userId1 = 'user123';
            const userId2 = 'user456';
            
            // Test with first user
            await sessionManager.startNewSessionOnLogin('token1', userId1);
            sessionManager.addMessage('User1 message', 'Response1');
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ success: true })
            });
            
            await sessionManager.saveSessionOnLogout();
            
            expect(fetch).toHaveBeenCalledWith(
                expect.any(String),
                expect.objectContaining({
                    body: expect.stringContaining(userId1)
                })
            );
            
            // Test with second user
            await sessionManager.startNewSessionOnLogin('token2', userId2);
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ sessions: [] })
            });
            
            await sessionManager.fetchUserHistory();
            
            expect(fetch).toHaveBeenCalledWith(
                `http://localhost:8000/chat/sessions/${userId2}`,
                expect.any(Object)
            );
        });

    });

    describe('Edge Cases', () => {

        test('empty chat skip - does not save sessions without messages', async () => {
            await sessionManager.startNewSessionOnLogin('token', 'user123');
            
            const result = await sessionManager.saveSessionOnLogout();
            
            expect(result.success).toBe(true);
            expect(result.reason).toBe('empty_session');
            expect(fetch).not.toHaveBeenCalled();
        });

        test('save failure keeps session in memory for retry', async () => {
            await sessionManager.startNewSessionOnLogin('token', 'user123');
            sessionManager.addMessage('Test', 'Response');
            
            const originalSessionId = sessionManager.currentSession;
            const originalMessages = [...sessionManager.messages];
            
            // Mock save failure
            fetch.mockRejectedValueOnce(new Error('Server error'));
            
            const result = await sessionManager.saveSessionOnLogout();
            
            expect(result.success).toBe(false);
            expect(sessionManager.currentSession).toBe(originalSessionId);
            expect(sessionManager.messages).toEqual(originalMessages);
        });

        test('no auth token handling', async () => {
            sessionManager.authToken = null;
            
            const saveResult = await sessionManager.saveSessionOnLogout();
            expect(saveResult.reason).toBe('no_session');
            
            // History should show login error
            await sessionManager.loadHistoryPanel();
            expect(mockDOM.chatHistoryList.innerHTML).toContain('giriş yapın');
        });

        test('network failure during history load', async () => {
            sessionManager.authToken = 'token';
            sessionManager.userId = 'user123';
            
            fetch.mockRejectedValueOnce(new Error('Network error'));
            
            await sessionManager.loadHistoryPanel();
            
            expect(mockDOM.chatHistoryList.innerHTML).toContain('yüklenemedi');
            expect(mockDOM.chatHistoryList.innerHTML).toContain('Tekrar Dene');
        });

    });

    describe('Message Management', () => {

        test('addMessage increments message count', () => {
            sessionManager.currentSession = 'test-session';
            
            expect(sessionManager.messages).toHaveLength(0);
            
            sessionManager.addMessage('Hello', 'Hi');
            expect(sessionManager.messages).toHaveLength(1);
            
            sessionManager.addMessage('How are you?', 'Fine');
            expect(sessionManager.messages).toHaveLength(2);
            
            const lastMessage = sessionManager.messages[1];
            expect(lastMessage.user_message).toBe('How are you?');
            expect(lastMessage.bot_response).toBe('Fine');
            expect(lastMessage.timestamp).toBeTruthy();
        });

        test('addMessage without active session logs warning', () => {
            const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
            
            sessionManager.currentSession = null;
            sessionManager.addMessage('Hello', 'Hi');
            
            expect(consoleSpy).toHaveBeenCalledWith('⚠️ No active session for message');
            expect(sessionManager.messages).toHaveLength(0);
            
            consoleSpy.mockRestore();
        });

    });

    describe('History Management', () => {

        test('loadHistoryPanel shows different states correctly', async () => {
            sessionManager.authToken = 'token';
            sessionManager.userId = 'user123';
            
            // Test loading state
            const loadingPromise = sessionManager.loadHistoryPanel();
            expect(mockDOM.chatHistoryList.innerHTML).toContain('Yükleniyor');
            
            // Mock empty history
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ sessions: [] })
            });
            
            await loadingPromise;
            expect(mockDOM.chatHistoryList.innerHTML).toContain('Henüz hiç sohbet yok');
        });

        test('history cache reduces API calls', async () => {
            sessionManager.authToken = 'token';
            sessionManager.userId = 'user123';
            
            const mockSessions = [{ sessionId: 'test', messageCount: 5 }];
            
            fetch.mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({ sessions: mockSessions })
            });
            
            // First call - should hit API
            await sessionManager.fetchUserHistory();
            expect(fetch).toHaveBeenCalledTimes(1);
            
            // Second call within cache period - should use cache
            await sessionManager.fetchUserHistory();
            expect(fetch).toHaveBeenCalledTimes(1); // Still 1
            
            // Invalidate cache
            sessionManager.invalidateHistoryCache();
            
            // Third call - should hit API again
            await sessionManager.fetchUserHistory();
            expect(fetch).toHaveBeenCalledTimes(2);
        });

    });

    describe('Retry Logic', () => {

        test('saveToBackendWithRetry retries on failure', async () => {
            const sessionData = { sessionId: 'test', messages: [] };
            
            // First two calls fail, third succeeds
            fetch
                .mockRejectedValueOnce(new Error('Network error'))
                .mockRejectedValueOnce(new Error('Server error'))
                .mockResolvedValueOnce({
                    ok: true,
                    json: () => Promise.resolve({ success: true })
                });
            
            const result = await sessionManager.saveToBackendWithRetry(sessionData, 3);
            
            expect(fetch).toHaveBeenCalledTimes(3);
            expect(result.success).toBe(true);
        });

        test('saveToBackendWithRetry gives up after max retries', async () => {
            const sessionData = { sessionId: 'test', messages: [] };
            
            fetch.mockRejectedValue(new Error('Persistent error'));
            
            const result = await sessionManager.saveToBackendWithRetry(sessionData, 2);
            
            expect(fetch).toHaveBeenCalledTimes(2);
            expect(result.success).toBe(false);
            expect(result.error).toBe('Persistent error');
        });

    });

    describe('Pure Functions', () => {

        test('generateSessionId creates unique IDs', () => {
            const id1 = sessionManager.generateSessionId();
            const id2 = sessionManager.generateSessionId();
            
            expect(id1).not.toBe(id2);
            expect(id1).toMatch(/^session_\d+_[a-z0-9]{9}$/);
            expect(id2).toMatch(/^session_\d+_[a-z0-9]{9}$/);
        });

        test('buildSessionData creates correct structure', () => {
            sessionManager.currentSession = 'test-session';
            sessionManager.sessionStartedAt = '2025-01-01T00:00:00.000Z';
            sessionManager.userId = 'user123';
            sessionManager.messages = [
                { user_message: 'Hello', bot_response: 'Hi' },
                { user_message: 'Bye', bot_response: 'Goodbye' }
            ];
            
            const data = sessionManager.buildSessionData();
            
            expect(data).toEqual({
                sessionId: 'test-session',
                startedAt: '2025-01-01T00:00:00.000Z',
                messages: sessionManager.messages,
                messageCount: 2,
                userId: 'user123'
            });
        });

        test('getSessionPreview handles edge cases', () => {
            // Empty messages
            expect(sessionManager.getSessionPreview([])).toBe('Boş sohbet');
            expect(sessionManager.getSessionPreview(null)).toBe('Boş sohbet');
            
            // Short message
            const shortMessages = [{ user_message: 'Hi' }];
            expect(sessionManager.getSessionPreview(shortMessages)).toBe('Hi');
            
            // Long message
            const longMessages = [{ user_message: 'A'.repeat(60) }];
            const preview = sessionManager.getSessionPreview(longMessages);
            expect(preview).toHaveLength(53); // 50 + '...'
            expect(preview).toEndWith('...');
        });

        test('getTimeAgo formats time correctly', () => {
            const now = new Date();
            
            // Minutes ago
            const fiveMinutesAgo = new Date(now - 5 * 60 * 1000);
            expect(sessionManager.getTimeAgo(fiveMinutesAgo)).toBe('5 dakika önce');
            
            // Hours ago
            const twoHoursAgo = new Date(now - 2 * 60 * 60 * 1000);
            expect(sessionManager.getTimeAgo(twoHoursAgo)).toBe('2 saat önce');
            
            // Days ago
            const threeDaysAgo = new Date(now - 3 * 24 * 60 * 60 * 1000);
            expect(sessionManager.getTimeAgo(threeDaysAgo)).toBe('3 gün önce');
        });

    });

    describe('Cleanup', () => {

        test('cleanup clears all session data', () => {
            sessionManager.currentSession = 'test-session';
            sessionManager.authToken = 'token';
            sessionManager.userId = 'user123';
            sessionManager.messages = [{ user_message: 'Test', bot_response: 'Response' }];
            sessionManager.historyCache = [{ sessionId: 'cache' }];
            
            sessionManager.cleanup();
            
            expect(sessionManager.currentSession).toBeNull();
            expect(sessionManager.authToken).toBeNull();
            expect(sessionManager.userId).toBeNull();
            expect(sessionManager.messages).toHaveLength(0);
            expect(sessionManager.historyCache).toBeNull();
        });

    });

});

// Integration test
describe('SessionManager Integration', () => {

    test('complete login-chat-logout flow', async () => {
        const sessionManager = new SessionManager();
        
        // 1. Login creates new session
        const sessionId = await sessionManager.startNewSessionOnLogin('token', 'user123');
        expect(sessionManager.currentSession).toBe(sessionId);
        expect(sessionManager.messages).toHaveLength(0);
        
        // 2. Add some chat messages
        sessionManager.addMessage('Hello', 'Hi there');
        sessionManager.addMessage('How are you?', 'I am fine');
        expect(sessionManager.messages).toHaveLength(2);
        
        // 3. Mock successful save on logout
        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ success: true })
        });
        
        // 4. Logout saves session
        const saveResult = await sessionManager.saveSessionOnLogout();
        expect(saveResult.success).toBe(true);
        expect(saveResult.reason).toBe('saved');
        
        // 5. Session is cleared after save
        expect(sessionManager.currentSession).toBeNull();
        expect(sessionManager.messages).toHaveLength(0);
        
        // 6. New login creates fresh session
        const newSessionId = await sessionManager.startNewSessionOnLogin('token', 'user123');
        expect(newSessionId).not.toBe(sessionId);
        expect(sessionManager.messages).toHaveLength(0);
    });

});

console.log('🧪 SessionManager tests loaded');
