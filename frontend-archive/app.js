/**
 * ClawChat Main Application Module
 * 
 * Initializes the chat application, manages UI state,
 * and coordinates between the WebSocket client and ChatUI components.
 * 
 * @module app
 */

import { WebSocketClient, ConnectionState } from './websocket-client.js';
import { pwaManager } from './pwa-manager.js';
import { ChatUI, MessageStatus, UserPresence } from './chat-ui.js';

/**
 * Application state management
 * @type {Object}
 */
const appState = {
    wsClient: null,
    chatUI: null,
    currentUser: { id: 'me', name: 'You' },
    isSettingsOpen: false,
    currentTab: 'messages'
};

/**
 * DOM element references
 * @type {Object}
 */
const elements = {};

/**
 * PWA deferred install prompt
 * @type {Event|null}
 */
let deferredPrompt = null;

/**
 * Initialize the application
 */
function init() {
    cacheElements();
    createChatUI();
    createWebSocketClient();
    bindEvents();
    
    // Show settings modal on first load to encourage connection
    openSettings();
    
    console.log('ClawChat initialized with full chat interface');
}

/**
 * Cache DOM element references for performance
 */
function cacheElements() {
    // Connection status
    elements.connectionStatus = document.getElementById('connection-status');
    elements.statusDot = elements.connectionStatus?.querySelector('.status-dot');
    elements.statusText = elements.connectionStatus?.querySelector('.status-text');
    
    // Tabs
    elements.tabMessages = document.getElementById('tab-messages');
    elements.tabFiles = document.getElementById('tab-files');
    elements.panelMessages = document.getElementById('panel-messages');
    elements.panelFiles = document.getElementById('panel-files');
    
    // Messages
    elements.messagesContainer = document.getElementById('messages-container');
    elements.emptyMessages = document.getElementById('empty-messages');
    elements.messageForm = document.getElementById('message-form');
    elements.messageInput = document.getElementById('message-input');
    elements.sendBtn = document.getElementById('send-btn');
    
    // Settings modal
    elements.settingsModal = document.getElementById('settings-modal');
    elements.settingsBtn = document.getElementById('settings-btn');
    elements.closeModalBtn = document.getElementById('close-modal');
    elements.connectionForm = document.getElementById('connection-form');
    elements.wsHost = document.getElementById('ws-host');
    elements.wsPort = document.getElementById('ws-port');
    elements.useSSL = document.getElementById('use-ssl');
    elements.connectBtn = document.getElementById('connect-btn');
    elements.disconnectBtn = document.getElementById('disconnect-btn');
    elements.connectionError = document.getElementById('connection-error');
    
    // Install button
    elements.installBtn = document.getElementById('install-btn');
    
    // Toast container
    elements.toastContainer = document.getElementById('toast-container');
}

/**
 * Create and initialize the ChatUI
 */
function createChatUI() {
    if (!elements.messagesContainer) return;
    
    appState.chatUI = new ChatUI({
        container: elements.messagesContainer,
        wsClient: null, // Will be set after WebSocket client is created
        currentUser: appState.currentUser,
        config: {
            autoScroll: true,
            showAvatars: true,
            showTimestamps: true,
            showStatusIndicators: true,
            maxMessages: 500,
            typingDebounceMs: 300,
            typingIndicatorTimeout: 3000
        }
    });
    
    // Listen for chat events
    appState.chatUI.on('messageSent', ({ message }) => {
        console.log('Message sent:', message.id);
    });
    
    appState.chatUI.on('messageReceived', ({ message }) => {
        // Play notification sound if enabled and tab is not focused
        if (document.hidden && message.sender.id !== appState.currentUser.id) {
            showToast(`New message from ${message.sender.name}`, 'info');
        }
    });
    
    appState.chatUI.on('messageStatusChanged', ({ messageId, status }) => {
        console.log(`Message ${messageId} status: ${status}`);
    });
    
    appState.chatUI.on('userPresenceChanged', ({ userId, presence }) => {
        console.log(`User ${userId} is now ${presence}`);
    });
}

/**
 * Create and configure WebSocket client
 */
function createWebSocketClient() {
    appState.wsClient = new WebSocketClient({
        host: elements.wsHost?.value || 'localhost',
        port: parseInt(elements.wsPort?.value, 10) || 8080,
        useSSL: elements.useSSL?.checked || false
    });
    
    // Link WebSocket to ChatUI
    if (appState.chatUI) {
        appState.chatUI.wsClient = appState.wsClient;
    }

    // Bind WebSocket events
    appState.wsClient.on('stateChange', handleConnectionStateChange);
    appState.wsClient.on('message', handleIncomingMessage);
    appState.wsClient.on('error', handleConnectionError);
    appState.wsClient.on('open', () => {
        showToast('Connected to server', 'success');
        closeSettings();
        
        // Send join message
        appState.wsClient.send({
            type: 'join',
            user: appState.currentUser,
            timestamp: Date.now()
        });
    });
    appState.wsClient.on('close', ({ code, wasClean }) => {
        if (!wasClean) {
            showToast('Connection closed unexpectedly', 'warning');
        }
    });
}

/**
 * Bind event listeners
 */
function bindEvents() {
    // Tab switching
    elements.tabMessages?.addEventListener('click', () => switchTab('messages'));
    elements.tabFiles?.addEventListener('click', () => switchTab('files'));
    
    // Message form
    elements.messageForm?.addEventListener('submit', handleMessageSubmit);
    elements.messageInput?.addEventListener('keydown', handleInputKeydown);
    elements.messageInput?.addEventListener('input', handleInputChange);
    
    // Settings modal
    elements.settingsBtn?.addEventListener('click', openSettings);
    elements.closeModalBtn?.addEventListener('click', closeSettings);
    elements.settingsModal?.querySelector('.modal-overlay')?.addEventListener('click', closeSettings);
    elements.connectionForm?.addEventListener('submit', handleConnectionSubmit);
    elements.disconnectBtn?.addEventListener('click', handleDisconnect);
    
    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && appState.isSettingsOpen) {
            closeSettings();
        }
    });
    
    // Visibility change for presence updates
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // PWA Install button
    elements.installBtn?.addEventListener('click', handleInstallClick);
    
    // Listen for PWA installable event
    window.addEventListener('pwaInstallable', () => {
        console.log('[App] PWA installable');
        if (elements.installBtn) {
            elements.installBtn.hidden = false;
        }
    });
    
    // Listen for connection changes
    window.addEventListener('pwaConnectionChange', (e) => {
        const { isOnline } = e.detail;
        if (!isOnline) {
            updateConnectionStatus('offline');
            showToast('You are offline. Messages will be queued.', 'warning');
        } else {
            const wsState = appState.wsClient?.getState() || ConnectionState.DISCONNECTED;
            updateConnectionStatus(wsState);
            showToast('You are back online!', 'success');
            // Trigger background sync for pending messages
            pwaManager.triggerBackgroundSync('sync-messages');
        }
    });
    
    // Listen for PWA update available
    window.addEventListener('pwaUpdateAvailable', (e) => {
        showUpdateNotification(e.detail.applyUpdate);
    });
}

/**
 * Handle page visibility changes for presence
 */
function handleVisibilityChange() {
    if (!appState.wsClient?.isConnected()) return;
    
    const presence = document.hidden ? UserPresence.AWAY : UserPresence.ONLINE;
    
    appState.wsClient.send({
        type: 'presence',
        presence: presence,
        timestamp: Date.now()
    });
}

/**
 * Handle WebSocket connection state changes
 * @param {Object} event - State change event
 */
function handleConnectionStateChange({ state, previousState, attempt, maxAttempts }) {
    updateConnectionStatus(state, attempt, maxAttempts);
    updateInputState(state);
}

/**
 * Update connection status UI
 * @param {string} state - Connection state
 * @param {number} [attempt] - Reconnection attempt number
 * @param {number} [maxAttempts] - Max reconnection attempts
 */
function updateConnectionStatus(state, attempt, maxAttempts) {
    if (!elements.connectionStatus) return;

    const statusConfig = {
        [ConnectionState.DISCONNECTED]: { 
            text: 'Disconnected', 
            className: 'disconnected' 
        },
        [ConnectionState.CONNECTING]: { 
            text: 'Connecting...', 
            className: 'connecting' 
        },
        [ConnectionState.CONNECTED]: { 
            text: 'Connected', 
            className: 'connected' 
        },
        [ConnectionState.RECONNECTING]: { 
            text: `Reconnecting (${attempt}/${maxAttempts})...`, 
            className: 'reconnecting' 
        },
        [ConnectionState.ERROR]: { 
            text: 'Connection Error', 
            className: 'error' 
        },
        'offline': {
            text: 'Offline',
            className: 'offline'
        }
    };

    const config = statusConfig[state];
    if (config) {
        elements.connectionStatus.className = `connection-status ${config.className}`;
        elements.statusText.textContent = config.text;
    }
}

/**
 * Update input field state based on connection
 * @param {string} state - Connection state
 */
function updateInputState(state) {
    const isConnected = state === ConnectionState.CONNECTED;
    
    if (elements.messageInput) {
        elements.messageInput.disabled = !isConnected;
        elements.messageInput.placeholder = isConnected 
            ? 'Type a message... (Shift+Enter for new line)' 
            : 'Connect to start messaging...';
    }
    
    if (elements.sendBtn) {
        elements.sendBtn.disabled = !isConnected;
    }

    if (elements.connectBtn) {
        elements.connectBtn.textContent = isConnected ? 'Reconnect' : 'Connect';
    }

    if (elements.disconnectBtn) {
        elements.disconnectBtn.disabled = !isConnected;
    }
}

/**
 * Handle incoming WebSocket messages
 * @param {Object} event - Message event
 */
function handleIncomingMessage({ data, timestamp }) {
    // Skip ping/pong messages
    if (data.type === 'pong' || data.type === 'ping') return;

    // Handle different message types
    switch (data.type) {
        case 'message':
            // Receive message through ChatUI
            appState.chatUI?.receiveMessage({
                id: data.id,
                content: data.content,
                sender: data.sender || { id: 'unknown', name: 'Unknown' },
                timestamp: data.timestamp || timestamp
            });
            break;
            
        case 'welcome':
            showToast(data.message || 'Connected!', 'success');
            break;
            
        case 'system':
            displaySystemMessage(data.content);
            break;
            
        case 'typing_start':
            if (data.user_id && data.user_id !== appState.currentUser.id) {
                appState.chatUI?.handleRemoteTyping(data.user_id, true);
            }
            break;
            
        case 'typing_stop':
            if (data.user_id && data.user_id !== appState.currentUser.id) {
                appState.chatUI?.handleRemoteTyping(data.user_id, false);
            }
            break;
            
        case 'presence':
            if (data.user_id && data.presence) {
                appState.chatUI?.updateUserPresence(data.user_id, data.presence, data.user);
            }
            break;
            
        case 'read_receipt':
            if (data.message_id) {
                appState.chatUI?.updateMessageStatus(data.message_id, MessageStatus.READ);
            }
            break;
            
        case 'user_join':
            if (data.user) {
                appState.chatUI?.updateUserPresence(
                    data.user.id, 
                    UserPresence.ONLINE, 
                    data.user
                );
                if (data.user.id !== appState.currentUser.id) {
                    displaySystemMessage(`${data.user.name} joined the chat`);
                }
            }
            break;
            
        case 'user_leave':
            if (data.user) {
                appState.chatUI?.updateUserPresence(
                    data.user.id, 
                    UserPresence.OFFLINE, 
                    data.user
                );
                if (data.user.id !== appState.currentUser.id) {
                    displaySystemMessage(`${data.user.name} left the chat`);
                }
            }
            break;
            
        case 'history':
            // Load message history
            if (data.messages && Array.isArray(data.messages)) {
                data.messages.forEach(msg => {
                    appState.chatUI?.receiveMessage(msg);
                });
            }
            break;
            
        default:
            // Handle unknown message types as regular messages
            if (data.content) {
                appState.chatUI?.receiveMessage({
                    id: data.id || generateId(),
                    content: data.content,
                    sender: data.sender || { id: 'server', name: 'Server' },
                    timestamp: data.timestamp || timestamp
                });
            }
    }
}

/**
 * Handle connection errors
 * @param {Error} error - Connection error
 */
function handleConnectionError(error) {
    console.error('WebSocket error:', error);
    showToast('Connection error. Check settings and try again.', 'error');
    
    if (elements.connectionError) {
        elements.connectionError.textContent = 'Failed to connect. Please check your settings.';
    }
}

/**
 * Handle message form submission
 * @param {Event} e - Submit event
 */
function handleMessageSubmit(e) {
    e.preventDefault();
    
    const content = elements.messageInput?.value;
    if (!content || !content.trim()) return;

    if (!appState.wsClient?.isConnected()) {
        showToast('Not connected to server', 'error');
        return;
    }

    // Send message through ChatUI
    const messageId = appState.chatUI?.sendMessage(content.trim());
    
    if (messageId) {
        // Clear input and focus
        elements.messageInput.value = '';
        elements.messageInput.focus();
    }
}

/**
 * Handle input changes for typing indicators
 */
function handleInputChange() {
    appState.chatUI?.handleTypingInput();
}

/**
 * Handle input keydown for special shortcuts
 * @param {KeyboardEvent} e - Keyboard event
 */
function handleInputKeydown(e) {
    // Send on Enter (without Shift for multiline)
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        elements.messageForm?.dispatchEvent(new Event('submit'));
    }
}

/**
 * Display a system message
 * @param {string} content - System message content
 */
function displaySystemMessage(content) {
    const messageEl = document.createElement('div');
    messageEl.className = 'chat-message message-system';
    messageEl.innerHTML = `
        <div class="system-text">${escapeHtml(content)}</div>
    `;
    
    elements.messagesContainer?.appendChild(messageEl);
    
    // Auto-scroll
    if (appState.chatUI?.scrollState?.isAtBottom) {
        appState.chatUI?.scrollToBottom();
    }
    
    // Remove after delay
    setTimeout(() => {
        messageEl.style.opacity = '0';
        messageEl.style.transition = 'opacity 0.5s';
        setTimeout(() => messageEl.remove(), 500);
    }, 10000);
}

/**
 * Switch between tabs
 * @param {string} tabName - Tab name ('messages' or 'files')
 */
function switchTab(tabName) {
    appState.currentTab = tabName;

    // Update tab buttons
    elements.tabMessages?.classList.toggle('active', tabName === 'messages');
    elements.tabMessages?.setAttribute('aria-selected', tabName === 'messages');
    elements.tabMessages?.setAttribute('tabindex', tabName === 'messages' ? '0' : '-1');

    elements.tabFiles?.classList.toggle('active', tabName === 'files');
    elements.tabFiles?.setAttribute('aria-selected', tabName === 'files');
    elements.tabFiles?.setAttribute('tabindex', tabName === 'files' ? '0' : '-1');

    // Update panels
    if (elements.panelMessages) {
        elements.panelMessages.classList.toggle('active', tabName === 'messages');
        elements.panelMessages.hidden = tabName !== 'messages';
    }

    if (elements.panelFiles) {
        elements.panelFiles.classList.toggle('active', tabName === 'files');
        elements.panelFiles.hidden = tabName !== 'files';
    }
}

/**
 * Open settings modal
 */
function openSettings() {
    appState.isSettingsOpen = true;
    elements.settingsModal?.classList.add('open');
    elements.settingsModal?.setAttribute('aria-hidden', 'false');
    elements.wsHost?.focus();
    
    // Clear previous errors
    if (elements.connectionError) {
        elements.connectionError.textContent = '';
    }
}

/**
 * Close settings modal
 */
function closeSettings() {
    appState.isSettingsOpen = false;
    elements.settingsModal?.classList.remove('open');
    elements.settingsModal?.setAttribute('aria-hidden', 'true');
}

/**
 * Handle connection form submission
 * @param {Event} e - Submit event
 */
async function handleConnectionSubmit(e) {
    e.preventDefault();

    const host = elements.wsHost?.value.trim();
    const port = parseInt(elements.wsPort?.value, 10);
    const useSSL = elements.useSSL?.checked || false;

    if (!host || !port) {
        if (elements.connectionError) {
            elements.connectionError.textContent = 'Please enter valid host and port';
        }
        return;
    }

    // Update client config
    appState.wsClient.updateConfig({ host, port, useSSL });

    // Clear error
    if (elements.connectionError) {
        elements.connectionError.textContent = '';
    }

    // Show connecting state
    elements.connectBtn.disabled = true;
    elements.connectBtn.textContent = 'Connecting...';

    try {
        await appState.wsClient.connect();
    } catch (error) {
        console.error('Connection failed:', error);
        if (elements.connectionError) {
            elements.connectionError.textContent = `Connection failed: ${error.message || 'Unknown error'}`;
        }
    } finally {
        elements.connectBtn.disabled = false;
        updateInputState(appState.wsClient.getState());
    }
}

/**
 * Handle disconnect button click
 */
function handleDisconnect() {
    appState.wsClient?.disconnect();
    showToast('Disconnected from server', 'info');
}

/**
 * Show toast notification
 * @param {string} message - Toast message
 * @param {string} [type='info'] - Toast type ('info', 'success', 'warning', 'error')
 */
function showToast(message, type = 'info') {
    if (!elements.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.textContent = message;

    elements.toastContainer.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Remove after delay
    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    }, 4000);
}

/**
 * Generate unique ID
 * @returns {string}
 */
function generateId() {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Raw text
 * @returns {string}
 */
function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// PWA Functions
// ============================================

/**
 * Handle PWA install button click
 */
async function handleInstallClick() {
    if (!deferredPrompt) {
        // If no deferred prompt, try using the pwaManager
        const installed = await pwaManager.promptInstall();
        if (installed) {
            showToast('App installed successfully!', 'success');
            if (elements.installBtn) {
                elements.installBtn.hidden = true;
            }
        }
        return;
    }
    
    // Show the install prompt
    deferredPrompt.prompt();
    
    // Wait for the user to respond
    const { outcome } = await deferredPrompt.userChoice;
    console.log('[App] Install prompt outcome:', outcome);
    
    // Clear the deferred prompt
    deferredPrompt = null;
    
    // Hide the install button
    if (elements.installBtn) {
        elements.installBtn.hidden = true;
    }
    
    if (outcome === 'accepted') {
        showToast('App installed successfully!', 'success');
    }
}

/**
 * Show update notification
 * @param {Function} applyUpdate - Function to apply the update
 */
function showUpdateNotification(applyUpdate) {
    // Create update notification
    const updateToast = document.createElement('div');
    updateToast.className = 'update-toast';
    updateToast.innerHTML = `
        <span class="update-text">A new version is available!</span>
        <button id="update-btn">Update Now</button>
    `;
    
    document.body.appendChild(updateToast);
    
    // Animate in
    requestAnimationFrame(() => {
        updateToast.classList.add('show');
    });
    
    // Handle update button click
    updateToast.querySelector('#update-btn').addEventListener('click', () => {
        updateToast.classList.remove('show');
        setTimeout(() => updateToast.remove(), 300);
        applyUpdate();
    });
}

/**
 * Queue message for offline sync
 * @param {Object} message - Message to queue
 */
function queueOfflineMessage(message) {
    // Add to offline queue via PWA manager
    pwaManager.queueWhenOnline(() => {
        if (appState.wsClient?.isConnected()) {
            appState.wsClient.sendMessage(message.content, {
                sender: message.sender
            });
        }
    });
    
    // Also trigger background sync
    pwaManager.triggerBackgroundSync('sync-messages');
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', init);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    appState.chatUI?.destroy();
    appState.wsClient?.disconnect();
});