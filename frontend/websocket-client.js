/**
 * ClawChat WebSocket Client Module
 * 
 * Handles WebSocket connection management, message sending/receiving,
 * and connection state events.
 * 
 * @module websocket-client
 */

/**
 * WebSocket connection states
 * @readonly
 * @enum {string}
 */
export const ConnectionState = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    RECONNECTING: 'reconnecting',
    ERROR: 'error'
};

/**
 * Default WebSocket configuration
 * @constant {Object}
 */
export const DEFAULT_CONFIG = {
    host: 'localhost',
    port: 8080,
    useSSL: false,
    reconnectAttempts: 5,
    reconnectDelay: 3000,
    heartbeatInterval: 30000
};

/**
 * WebSocketClient class for managing WebSocket connections
 */
export class WebSocketClient {
    /**
     * Creates a new WebSocketClient instance
     * @param {Object} options - Configuration options
     * @param {string} [options.host='localhost'] - WebSocket server host
     * @param {number} [options.port=8080] - WebSocket server port
     * @param {boolean} [options.useSSL=false] - Whether to use WSS instead of WS
     * @param {number} [options.reconnectAttempts=5] - Maximum reconnection attempts
     * @param {number} [options.reconnectDelay=3000] - Delay between reconnection attempts (ms)
     * @param {number} [options.heartbeatInterval=30000] - Heartbeat interval in ms
     */
    constructor(options = {}) {
        this.config = { ...DEFAULT_CONFIG, ...options };
        this.socket = null;
        this.state = ConnectionState.DISCONNECTED;
        this.reconnectCount = 0;
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
        
        // Event handlers registry
        this.eventHandlers = {
            open: [],
            close: [],
            message: [],
            error: [],
            stateChange: []
        };
    }

    /**
     * Gets the current WebSocket URL based on configuration
     * @returns {string} WebSocket URL
     * @private
     */
    _getWebSocketURL() {
        const protocol = this.config.useSSL ? 'wss' : 'ws';
        return `${protocol}://${this.config.host}:${this.config.port}`;
    }

    /**
     * Sets the connection state and triggers state change event
     * @param {string} newState - New connection state
     * @param {Object} [details={}] - Additional state details
     * @private
     */
    _setState(newState, details = {}) {
        const oldState = this.state;
        this.state = newState;
        
        if (oldState !== newState) {
            this._emit('stateChange', { 
                state: newState, 
                previousState: oldState,
                ...details 
            });
        }
    }

    /**
     * Emits an event to all registered handlers
     * @param {string} event - Event name
     * @param {*} data - Event data
     * @private
     */
    _emit(event, data) {
        const handlers = this.eventHandlers[event] || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in ${event} handler:`, error);
            }
        });
    }

    /**
     * Starts the heartbeat interval to keep connection alive
     * @private
     */
    _startHeartbeat() {
        this._stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected()) {
                this.send({ type: 'ping', timestamp: Date.now() });
            }
        }, this.config.heartbeatInterval);
    }

    /**
     * Stops the heartbeat interval
     * @private
     */
    _stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    /**
     * Attempts to reconnect to the WebSocket server
     * @private
     */
    _reconnect() {
        if (this.reconnectCount >= this.config.reconnectAttempts) {
            this._setState(ConnectionState.ERROR, { 
                error: new Error('Max reconnection attempts reached') 
            });
            return;
        }

        this.reconnectCount++;
        this._setState(ConnectionState.RECONNECTING, { 
            attempt: this.reconnectCount,
            maxAttempts: this.config.reconnectAttempts 
        });

        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, this.config.reconnectDelay);
    }

    /**
     * Handles incoming WebSocket messages
     * @param {MessageEvent} event - WebSocket message event
     * @private
     */
    _handleMessage(event) {
        let data;
        
        try {
            data = JSON.parse(event.data);
        } catch {
            // If not JSON, treat as plain text
            data = { type: 'text', content: event.data };
        }

        // Handle ping/pong for heartbeat
        if (data.type === 'ping') {
            this.send({ type: 'pong', timestamp: Date.now() });
            return;
        }

        this._emit('message', { 
            data, 
            raw: event.data,
            timestamp: new Date().toISOString() 
        });
    }

    /**
     * Registers an event handler
     * @param {string} event - Event name ('open', 'close', 'message', 'error', 'stateChange')
     * @param {Function} handler - Event handler function
     * @returns {Function} Unsubscribe function
     */
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);

        // Return unsubscribe function
        return () => {
            this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
        };
    }

    /**
     * Establishes WebSocket connection
     * @returns {Promise<void>}
     */
    async connect() {
        if (this.socket?.readyState === WebSocket.OPEN) {
            console.warn('WebSocket already connected');
            return;
        }

        this._setState(ConnectionState.CONNECTING);
        const url = this._getWebSocketURL();

        return new Promise((resolve, reject) => {
            try {
                this.socket = new WebSocket(url);

                this.socket.onopen = (event) => {
                    this.reconnectCount = 0;
                    this._setState(ConnectionState.CONNECTED);
                    this._startHeartbeat();
                    this._emit('open', event);
                    resolve();
                };

                this.socket.onclose = (event) => {
                    this._stopHeartbeat();
                    
                    if (this.state === ConnectionState.CONNECTED) {
                        // Unexpected disconnect, try to reconnect
                        this._setState(ConnectionState.DISCONNECTED, { code: event.code });
                        this._reconnect();
                    } else {
                        this._setState(ConnectionState.DISCONNECTED, { code: event.code });
                    }
                    
                    this._emit('close', { 
                        code: event.code, 
                        reason: event.reason,
                        wasClean: event.wasClean 
                    });
                };

                this.socket.onerror = (error) => {
                    this._setState(ConnectionState.ERROR, { error });
                    this._emit('error', error);
                    reject(error);
                };

                this.socket.onmessage = (event) => this._handleMessage(event);

            } catch (error) {
                this._setState(ConnectionState.ERROR, { error });
                this._emit('error', error);
                reject(error);
            }
        });
    }

    /**
     * Closes the WebSocket connection
     * @param {number} [code=1000] - Close code
     * @param {string} [reason='Client disconnected'] - Close reason
     */
    disconnect(code = 1000, reason = 'Client disconnected') {
        // Clear any pending reconnect
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        this._stopHeartbeat();
        this.reconnectCount = this.config.reconnectAttempts; // Prevent auto-reconnect

        if (this.socket) {
            this.socket.close(code, reason);
            this.socket = null;
        }

        this._setState(ConnectionState.DISCONNECTED);
    }

    /**
     * Sends data through the WebSocket connection
     * @param {Object|string} data - Data to send
     * @returns {boolean} Whether the message was sent
     */
    send(data) {
        if (!this.isConnected()) {
            console.warn('Cannot send: WebSocket not connected');
            return false;
        }

        const message = typeof data === 'string' ? data : JSON.stringify(data);
        
        try {
            this.socket.send(message);
            return true;
        } catch (error) {
            console.error('Error sending message:', error);
            this._emit('error', error);
            return false;
        }
    }

    /**
     * Sends a chat message
     * @param {string} content - Message content
     * @param {Object} [metadata={}] - Additional message metadata
     * @returns {boolean} Whether the message was sent
     */
    sendMessage(content, metadata = {}) {
        return this.send({
            type: 'message',
            content,
            timestamp: new Date().toISOString(),
            ...metadata
        });
    }

    /**
     * Checks if the WebSocket is connected
     * @returns {boolean}
     */
    isConnected() {
        return this.socket?.readyState === WebSocket.OPEN;
    }

    /**
     * Gets current connection state
     * @returns {string}
     */
    getState() {
        return this.state;
    }

    /**
     * Updates configuration
     * @param {Object} newConfig - New configuration options
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
    }

    /**
     * Gets current configuration
     * @returns {Object}
     */
    getConfig() {
        return { ...this.config };
    }
}

/**
 * Creates and returns a new WebSocketClient instance
 * @param {Object} options - Configuration options
 * @returns {WebSocketClient}
 */
export function createWebSocketClient(options = {}) {
    return new WebSocketClient(options);
}

export default WebSocketClient;
