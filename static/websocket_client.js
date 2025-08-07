/**
 * WebSocket Chat Client for MEFAPEX AI Assistant
 * Replaces HTTP polling with efficient real-time communication
 */

class WebSocketChatClient {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 1000; // Start with 1 second
        this.heartbeatInterval = null;
        this.messageQueue = [];
        this.userId = null;
        
        // Event listeners
        this.onMessageReceived = null;
        this.onConnectionStatusChanged = null;
        this.onTypingStatusChanged = null;
        this.onError = null;
        
        console.log('🔌 WebSocket client initialized');
    }
    
    /**
     * Connect to WebSocket server
     */
    connect(userId = 'demo') {
        if (this.isConnected) {
            console.log('WebSocket already connected');
            return;
        }
        
        this.userId = userId;
        
        // Determine WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${userId}`;
        
        console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupEventHandlers();
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.handleError('Connection failed: ' + error.message);
        }
    }
    
    /**
     * Setup WebSocket event handlers
     */
    setupEventHandlers() {
        this.ws.onopen = (event) => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectInterval = 1000;
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Process queued messages
            this.processMessageQueue();
            
            // Notify connection status change
            if (this.onConnectionStatusChanged) {
                this.onConnectionStatusChanged(true);
            }
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('❌ WebSocket disconnected:', event.code, event.reason);
            this.isConnected = false;
            this.stopHeartbeat();
            
            // Notify connection status change
            if (this.onConnectionStatusChanged) {
                this.onConnectionStatusChanged(false);
            }
            
            // Attempt reconnection if not intentional
            if (event.code !== 1000) { // 1000 = normal closure
                this.attemptReconnect();
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.handleError('WebSocket error occurred');
        };
    }
    
    /**
     * Handle incoming messages
     */
    handleMessage(data) {
        console.log('📥 Received message:', data.type);
        
        switch (data.type) {
            case 'connection_established':
                console.log('🎉 Connection established:', data);
                break;
                
            case 'chat_response':
                if (this.onMessageReceived) {
                    this.onMessageReceived({
                        type: 'bot_response',
                        message: data.response,
                        source: data.source,
                        timestamp: data.timestamp,
                        cached: data.cached || false
                    });
                }
                break;
                
            case 'bot_typing':
                if (this.onTypingStatusChanged) {
                    this.onTypingStatusChanged(data.typing);
                }
                break;
                
            case 'chat_history':
                if (this.onMessageReceived) {
                    this.onMessageReceived({
                        type: 'history',
                        messages: data.messages,
                        timestamp: data.timestamp
                    });
                }
                break;
                
            case 'error':
                console.error('Server error:', data.message);
                this.handleError(data.message);
                break;
                
            case 'pong':
                // Heartbeat response
                console.debug('💗 Heartbeat acknowledged');
                break;
                
            default:
                console.log('Unknown message type:', data.type, data);
        }
    }
    
    /**
     * Send chat message
     */
    sendMessage(message) {
        const messageData = {
            type: 'chat_message',
            message: message,
            timestamp: new Date().toISOString()
        };
        
        this.sendData(messageData);
    }
    
    /**
     * Request chat history
     */
    requestHistory() {
        const messageData = {
            type: 'get_history',
            timestamp: new Date().toISOString()
        };
        
        this.sendData(messageData);
    }
    
    /**
     * Send typing indicator
     */
    sendTyping(isTyping) {
        const messageData = {
            type: isTyping ? 'typing_start' : 'typing_stop',
            timestamp: new Date().toISOString()
        };
        
        this.sendData(messageData);
    }
    
    /**
     * Send data via WebSocket with queuing support
     */
    sendData(data) {
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(data));
                console.log('📤 Sent message:', data.type);
            } catch (error) {
                console.error('Failed to send message:', error);
                this.messageQueue.push(data);
            }
        } else {
            console.log('📦 Queuing message (not connected):', data.type);
            this.messageQueue.push(data);
        }
    }
    
    /**
     * Process queued messages
     */
    processMessageQueue() {
        while (this.messageQueue.length > 0 && this.isConnected) {
            const message = this.messageQueue.shift();
            this.sendData(message);
        }
    }
    
    /**
     * Start heartbeat to keep connection alive
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
                this.sendData({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, 30000); // Ping every 30 seconds
    }
    
    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    /**
     * Attempt to reconnect with exponential backoff
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Max reconnection attempts reached');
            this.handleError('Connection lost. Please refresh the page.');
            return;
        }
        
        this.reconnectAttempts++;
        console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${this.reconnectInterval}ms`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                this.connect(this.userId);
            }
        }, this.reconnectInterval);
        
        // Exponential backoff
        this.reconnectInterval = Math.min(this.reconnectInterval * 2, 30000);
    }
    
    /**
     * Handle errors
     */
    handleError(message) {
        console.error('💥 WebSocket error:', message);
        if (this.onError) {
            this.onError(message);
        }
    }
    
    /**
     * Disconnect WebSocket
     */
    disconnect() {
        console.log('🔌 Disconnecting WebSocket');
        this.isConnected = false;
        this.stopHeartbeat();
        
        if (this.ws) {
            this.ws.close(1000, 'User disconnected');
            this.ws = null;
        }
    }
    
    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            readyState: this.ws ? this.ws.readyState : WebSocket.CLOSED,
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length
        };
    }
}

// Global WebSocket client instance
window.wsClient = new WebSocketChatClient();
