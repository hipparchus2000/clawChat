/**
 * ClawChat Node.js WebSocket Server
 * 
 * A production-ready WebSocket server with connection management,
 * keepalive ping/pong, and robust error handling.
 */

const WebSocket = require('ws');
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

class ConnectionInfo {
    constructor(id, ws, remoteAddress) {
        this.id = id;
        this.ws = ws;
        this.remoteAddress = remoteAddress;
        this.connectedAt = Date.now();
        this.messageCount = 0;
        this.lastActivity = Date.now();
        this.username = `user_${id.substring(0, 8)}`;
    }
}

class ClawChatServer {
    constructor(config = {}) {
        this.config = {
            host: config.host || '0.0.0.0',
            port: config.port || 8765,
            maxConnections: config.maxConnections || 100,
            pingInterval: config.pingInterval || 20000,
            pingTimeout: config.pingTimeout || 10000,
            ...config
        };
        
        this.connections = new Map();
        this.server = null;
        this.pingInterval = null;
        this.isShuttingDown = false;
        
        this.setupLogging();
    }
    
    setupLogging() {
        this.logger = {
            info: (msg, ...args) => console.log(`[INFO] ${msg}`, ...args),
            warn: (msg, ...args) => console.warn(`[WARN] ${msg}`, ...args),
            error: (msg, ...args) => console.error(`[ERROR] ${msg}`, ...args),
            debug: (msg, ...args) => console.debug(`[DEBUG] ${msg}`, ...args)
        };
    }
    
    async start() {
        this.logger.info(`Starting ClawChat server on ${this.config.host}:${this.config.port}`);
        this.logger.info(`Max connections: ${this.config.maxConnections || 'unlimited'}`);
        
        try {
            this.server = new WebSocket.Server({
                host: this.config.host,
                port: this.config.port,
                maxPayload: 100 * 1024 * 1024, // 100MB
                clientTracking: false
            });
            
            this.server.on('connection', this.handleConnection.bind(this));
            this.server.on('error', this.handleServerError.bind(this));
            this.server.on('close', this.handleServerClose.bind(this));
            
            // Start ping interval
            this.startPingInterval();
            
            this.logger.info('Server started successfully');
            
            // Handle graceful shutdown
            process.on('SIGINT', this.gracefulShutdown.bind(this));
            process.on('SIGTERM', this.gracefulShutdown.bind(this));
            
        } catch (error) {
            this.logger.error(`Server error: ${error.message}`, error);
            throw error;
        }
    }
    
    startPingInterval() {
        this.pingInterval = setInterval(() => {
            this.connections.forEach((connInfo, connectionId) => {
                if (connInfo.ws.readyState === WebSocket.OPEN) {
                    try {
                        connInfo.ws.ping();
                    } catch (error) {
                        this.logger.debug(`Failed to ping ${connectionId}: ${error.message}`);
                    }
                }
            });
        }, this.config.pingInterval);
    }
    
    handleConnection(ws, request) {
        // Check connection limit
        if (this.config.maxConnections > 0 && 
            this.connections.size >= this.config.maxConnections) {
            this.logger.warn('Connection rejected: max connections reached');
            ws.close(1013, 'Server at capacity');
            return;
        }
        
        const remoteAddress = request.socket.remoteAddress;
        const connectionId = `${remoteAddress}:${request.socket.remotePort}`;
        const connInfo = new ConnectionInfo(connectionId, ws, remoteAddress);
        
        this.connections.set(connectionId, connInfo);
        
        this.logger.info(`Client connected: ${connectionId} (total: ${this.connections.size})`);
        
        // Setup WebSocket event handlers
        ws.on('message', (data) => this.handleMessage(connInfo, data));
        ws.on('close', (code, reason) => this.handleClose(connInfo, code, reason));
        ws.on('error', (error) => this.handleError(connInfo, error));
        ws.on('pong', () => {
            connInfo.lastActivity = Date.now();
        });
        
        // Send welcome message
        this.sendMessage(connInfo, {
            type: 'welcome',
            message: 'Welcome to ClawChat!',
            connectionId: connectionId,
            username: connInfo.username,
            timestamp: Date.now()
        });
        
        // Broadcast user join
        this.broadcast({
            type: 'user_join',
            user: {
                id: connectionId,
                name: connInfo.username,
                connectionId: connectionId
            },
            timestamp: Date.now()
        }, connectionId);
    }
    
    async handleMessage(connInfo, data) {
        connInfo.messageCount++;
        connInfo.lastActivity = Date.now();
        
        this.logger.debug(`Message from ${connInfo.id}: ${data.toString().substring(0, 200)}...`);
        
        try {
            let message;
            try {
                message = JSON.parse(data.toString());
            } catch {
                // If not JSON, treat as text message
                message = {
                    type: 'message',
                    content: data.toString(),
                    timestamp: Date.now()
                };
            }
            
            await this.processMessage(connInfo, message);
            
        } catch (error) {
            this.logger.error(`Error processing message from ${connInfo.id}: ${error.message}`, error);
            this.sendMessage(connInfo, {
                type: 'error',
                message: 'Internal server error',
                timestamp: Date.now()
            });
        }
    }
    
    async processMessage(connInfo, message) {
        const msgType = message.type || 'unknown';
        
        switch (msgType) {
            case 'message':
                await this.handleChatMessage(connInfo, message);
                break;
                
            case 'echo':
                await this.handleEcho(connInfo, message);
                break;
                
            case 'ping':
                await this.handlePing(connInfo, message);
                break;
                
            case 'broadcast':
                await this.handleBroadcast(connInfo, message);
                break;
                
            case 'set_username':
                await this.handleSetUsername(connInfo, message);
                break;
                
            case 'typing_start':
            case 'typing_stop':
                await this.handleTyping(connInfo, message);
                break;
                
            default:
                this.sendMessage(connInfo, {
                    type: 'error',
                    message: `Unknown message type: ${msgType}`,
                    timestamp: Date.now()
                });
        }
    }
    
    async handleChatMessage(connInfo, message) {
        const chatMessage = {
            type: 'message',
            id: `msg_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`,
            content: message.content || '',
            sender: {
                id: connInfo.id,
                name: connInfo.username,
                connectionId: connInfo.id
            },
            timestamp: message.timestamp || Date.now()
        };
        
        // Broadcast to all connected clients
        this.broadcast(chatMessage);
        
        // Send confirmation to sender
        this.sendMessage(connInfo, {
            type: 'message_sent',
            messageId: chatMessage.id,
            timestamp: Date.now()
        });
    }
    
    async handleEcho(connInfo, message) {
        this.sendMessage(connInfo, {
            type: 'echo',
            data: message.data,
            timestamp: Date.now(),
            format: 'json'
        });
    }
    
    async handlePing(connInfo, message) {
        this.sendMessage(connInfo, {
            type: 'pong',
            timestamp: Date.now(),
            echo: message.data
        });
    }
    
    async handleBroadcast(connInfo, message) {
        const broadcastData = {
            type: 'broadcast',
            from: connInfo.id,
            fromUsername: connInfo.username,
            data: message.data,
            timestamp: Date.now()
        };
        
        // Send to all connected clients except sender
        this.broadcast(broadcastData, connInfo.id);
        
        // Confirm to sender
        this.sendMessage(connInfo, {
            type: 'broadcast_confirm',
            recipients: this.connections.size - 1,
            timestamp: Date.now()
        });
    }
    
    async handleSetUsername(connInfo, message) {
        const oldUsername = connInfo.username;
        const newUsername = (message.username || '').trim().substring(0, 32) || connInfo.username;
        
        if (newUsername !== oldUsername) {
            connInfo.username = newUsername;
            
            // Broadcast username change
            this.broadcast({
                type: 'username_changed',
                user: {
                    id: connInfo.id,
                    oldName: oldUsername,
                    newName: newUsername
                },
                timestamp: Date.now()
            });
            
            this.sendMessage(connInfo, {
                type: 'username_set',
                username: newUsername,
                timestamp: Date.now()
            });
        }
    }
    
    async handleTyping(connInfo, message) {
        this.broadcast({
            type: message.type,
            user_id: connInfo.id,
            user: {
                id: connInfo.id,
                name: connInfo.username
            },
            timestamp: Date.now()
        }, connInfo.id);
    }
    
    handleClose(connInfo, code, reason) {
        this.connections.delete(connInfo.id);
        
        const duration = Date.now() - connInfo.connectedAt;
        this.logger.info(
            `Client disconnected: ${connInfo.id} ` +
            `(messages: ${connInfo.messageCount}, duration: ${(duration / 1000).toFixed(1)}s, ` +
            `remaining: ${this.connections.size})`
        );
        
        // Broadcast user leave
        this.broadcast({
            type: 'user_leave',
            user: {
                id: connInfo.id,
                name: connInfo.username,
                connectionId: connInfo.id
            },
            timestamp: Date.now()
        }, connInfo.id);
    }
    
    handleError(connInfo, error) {
        this.logger.error(`WebSocket error for ${connInfo.id}: ${error.message}`, error);
    }
    
    handleServerError(error) {
        this.logger.error(`Server error: ${error.message}`, error);
    }
    
    handleServerClose() {
        this.logger.info('WebSocket server closed');
    }
    
    sendMessage(connInfo, data) {
        if (connInfo.ws.readyState === WebSocket.OPEN) {
            try {
                connInfo.ws.send(JSON.stringify(data));
                return true;
            } catch (error) {
                this.logger.debug(`Failed to send message to ${connInfo.id}: ${error.message}`);
                return false;
            }
        }
        return false;
    }
    
    broadcast(data, excludeConnectionId = null) {
        let sentCount = 0;
        
        this.connections.forEach((connInfo, connectionId) => {
            if (connectionId !== excludeConnectionId && connInfo.ws.readyState === WebSocket.OPEN) {
                if (this.sendMessage(connInfo, data)) {
                    sentCount++;
                }
            }
        });
        
        return sentCount;
    }
    
    getStats() {
        return {
            connections: {
                active: this.connections.size,
                max: this.config.maxConnections
            },
            clients: Array.from(this.connections.values()).map(conn => ({
                id: conn.id,
                username: conn.username,
                connectedAt: conn.connectedAt,
                messageCount: conn.messageCount,
                lastActivity: conn.lastActivity,
                remoteAddress: conn.remoteAddress
            }))
        };
    }
    
    async gracefulShutdown() {
        if (this.isShuttingDown) return;
        
        this.isShuttingDown = true;
        this.logger.info('Shutting down server gracefully...');
        
        // Clear ping interval
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        
        // Close all connections
        const closePromises = [];
        this.connections.forEach((connInfo) => {
            closePromises.push(new Promise(resolve => {
                connInfo.ws.close(1001, 'Server shutting down');
                connInfo.ws.once('close', resolve);
            }));
        });
        
        await Promise.allSettled(closePromises);
        
        // Close server
        if (this.server) {
            this.server.close();
        }
        
        this.logger.info('Server shutdown complete');
        process.exit(0);
    }
}

// Load configuration from file or environment
async function loadConfig() {
    const configPath = path.join(__dirname, 'config.json');
    
    try {
        const data = await fs.readFile(configPath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        // Default configuration
        return {
            host: process.env.HOST || '0.0.0.0',
            port: parseInt(process.env.PORT || '8765', 10),
            maxConnections: parseInt(process.env.MAX_CONNECTIONS || '100', 10),
            pingInterval: parseInt(process.env.PING_INTERVAL || '20000', 10),
            pingTimeout: parseInt(process.env.PING_TIMEOUT || '10000', 10)
        };
    }
}

// Main function
async function main() {
    try {
        const config = await loadConfig();
        const server = new ClawChatServer(config);
        
        await server.start();
        
        // Log server stats periodically
        setInterval(() => {
            const stats = server.getStats();
            console.log(`[STATS] Active connections: ${stats.connections.active}/${stats.connections.max}`);
        }, 60000); // Every minute
        
    } catch (error) {
        console.error(`Failed to start server: ${error.message}`, error);
        process.exit(1);
    }
}

// Run if this file is executed directly
if (require.main === module) {
    main();
}

module.exports = ClawChatServer;