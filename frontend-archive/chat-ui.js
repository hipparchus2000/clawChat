/**
 * ClawChat UI Module
 * 
 * Full-featured chat interface with:
 * - Message bubbles with sender distinction
 * - Message history with scroll management
 * - User presence indicators
 * - Typing indicators with debouncing
 * - Relative timestamps
 * - Message status indicators
 * - Rich message support
 * 
 * @module chat-ui
 */

/**
 * Message status enum
 * @readonly
 * @enum {string}
 */
export const MessageStatus = {
    SENDING: 'sending',
    SENT: 'sent',
    DELIVERED: 'delivered',
    READ: 'read',
    ERROR: 'error'
};

/**
 * User presence enum
 * @readonly
 * @enum {string}
 */
export const UserPresence = {
    ONLINE: 'online',
    OFFLINE: 'offline',
    AWAY: 'away',
    TYPING: 'typing'
};

/**
 * ChatUI class - Complete chat interface
 */
export class ChatUI {
    /**
     * Creates a new ChatUI instance
     * @param {Object} options - Configuration options
     * @param {HTMLElement} options.container - Messages container element
     * @param {WebSocketClient} options.wsClient - WebSocket client instance
     * @param {Object} [options.currentUser] - Current user info
     * @param {string} [options.currentUser.id] - User ID
     * @param {string} [options.currentUser.name] - User name
     * @param {string} [options.currentUser.avatar] - User avatar URL
     * @param {Object} [options.config] - UI configuration
     */
    constructor(options = {}) {
        this.container = options.container;
        this.wsClient = options.wsClient;
        this.currentUser = options.currentUser || { id: 'me', name: 'You' };
        this.config = {
            autoScroll: true,
            showAvatars: true,
            showTimestamps: true,
            showStatusIndicators: true,
            maxMessages: 500,
            typingDebounceMs: 300,
            typingIndicatorTimeout: 3000,
            ...options.config
        };

        // State
        this.messages = new Map();
        this.users = new Map();
        this.scrollState = {
            isAtBottom: true,
            isUserScrolling: false,
            scrollTimeout: null
        };
        this.typingState = {
            isTyping: false,
            typingTimeout: null,
            indicatorTimeout: null
        };

        // Event handlers
        this.eventHandlers = {
            messageSent: [],
            messageReceived: [],
            messageStatusChanged: [],
            userPresenceChanged: [],
            typingStarted: [],
            typingStopped: []
        };

        // Bind methods
        this.handleScroll = this.handleScroll.bind(this);
        this.handleResize = this.handleResize.bind(this);
        this.formatTime = this.formatTime.bind(this);

        // Initialize
        this.init();
    }

    /**
     * Initialize the chat UI
     * @private
     */
    init() {
        this.setupContainer();
        this.bindEvents();
        this.startTimestampUpdater();
    }

    /**
     * Setup the messages container
     * @private
     */
    setupContainer() {
        if (!this.container) return;

        // Add chat-specific classes
        this.container.classList.add('chat-messages');
        
        // Create scroll indicator
        this.scrollIndicator = document.createElement('button');
        this.scrollIndicator.className = 'scroll-to-bottom';
        this.scrollIndicator.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
            <span class="scroll-indicator-badge"></span>
        `;
        this.scrollIndicator.addEventListener('click', () => this.scrollToBottom(true));
        
        // Insert after container
        this.container.parentNode.insertBefore(this.scrollIndicator, this.container.nextSibling);
    }

    /**
     * Bind DOM events
     * @private
     */
    bindEvents() {
        if (!this.container) return;

        // Scroll events with debounce
        let scrollDebounce;
        this.container.addEventListener('scroll', () => {
            clearTimeout(scrollDebounce);
            scrollDebounce = setTimeout(() => this.handleScroll(), 50);
        });

        // Resize handler
        window.addEventListener('resize', this.handleResize);

        // Intersection observer for read receipts
        this.setupIntersectionObserver();
    }

    /**
     * Setup intersection observer for read receipts
     * @private
     */
    setupIntersectionObserver() {
        if (!('IntersectionObserver' in window)) return;

        this.observer = new IntersectionObserver(
            (entries) => this.handleIntersection(entries),
            { 
                root: this.container,
                threshold: 0.8
            }
        );
    }

    /**
     * Handle intersection changes for read receipts
     * @param {IntersectionObserverEntry[]} entries
     * @private
     */
    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const messageId = entry.target.dataset.messageId;
                const message = this.messages.get(messageId);
                
                if (message && !message.isOwn && message.status !== MessageStatus.READ) {
                    this.markMessageAsRead(messageId);
                }
            }
        });
    }

    /**
     * Handle scroll events
     * @private
     */
    handleScroll() {
        if (!this.container) return;

        const { scrollTop, scrollHeight, clientHeight } = this.container;
        const scrollBottom = scrollHeight - scrollTop - clientHeight;
        
        this.scrollState.isAtBottom = scrollBottom < 50;
        this.scrollState.isUserScrolling = true;

        // Update scroll indicator visibility
        this.updateScrollIndicator();

        // Clear scroll timeout
        clearTimeout(this.scrollState.scrollTimeout);
        this.scrollState.scrollTimeout = setTimeout(() => {
            this.scrollState.isUserScrolling = false;
        }, 150);
    }

    /**
     * Handle resize events
     * @private
     */
    handleResize() {
        if (this.scrollState.isAtBottom) {
            this.scrollToBottom();
        }
    }

    /**
     * Update scroll indicator visibility
     * @private
     */
    updateScrollIndicator() {
        if (!this.scrollIndicator) return;
        
        const hasNewMessages = this.scrollIndicator.dataset.newMessages === 'true';
        this.scrollIndicator.classList.toggle('visible', !this.scrollState.isAtBottom || hasNewMessages);
    }

    /**
     * Scroll to bottom of messages
     * @param {boolean} [force=false] - Force scroll even if user is scrolling
     * @param {boolean} [smooth=true] - Use smooth scrolling
     */
    scrollToBottom(force = false, smooth = true) {
        if (!this.container) return;

        if (!force && this.scrollState.isUserScrolling) return;
        if (!force && !this.config.autoScroll) return;

        const scrollOptions = smooth ? { behavior: 'smooth' } : {};
        this.container.scrollTo({
            top: this.container.scrollHeight,
            ...scrollOptions
        });

        this.scrollState.isAtBottom = true;
        this.scrollIndicator.dataset.newMessages = 'false';
        this.scrollIndicator.classList.remove('visible');
    }

    /**
     * Send a message
     * @param {string} content - Message content
     * @param {Object} [metadata={}] - Additional message metadata
     * @returns {string|null} Message ID if sent, null otherwise
     */
    sendMessage(content, metadata = {}) {
        if (!content.trim()) return null;

        const messageId = this.generateId();
        const message = {
            id: messageId,
            content: this.parseContent(content),
            rawContent: content,
            sender: this.currentUser,
            timestamp: Date.now(),
            isOwn: true,
            status: MessageStatus.SENDING,
            ...metadata
        };

        // Add to UI immediately
        this.addMessageToUI(message);

        // Store message
        this.messages.set(messageId, message);

        // Send via WebSocket
        if (this.wsClient?.isConnected()) {
            const sent = this.wsClient.send({
                type: 'message',
                id: messageId,
                content: content,
                timestamp: message.timestamp,
                sender: {
                    id: this.currentUser.id,
                    name: this.currentUser.name
                }
            });

            if (sent) {
                this.updateMessageStatus(messageId, MessageStatus.SENT);
            } else {
                this.updateMessageStatus(messageId, MessageStatus.ERROR);
            }
        } else {
            this.updateMessageStatus(messageId, MessageStatus.ERROR);
        }

        this.emit('messageSent', { message });
        this.pruneOldMessages();

        return messageId;
    }

    /**
     * Receive a message
     * @param {Object} data - Message data from server
     */
    receiveMessage(data) {
        const messageId = data.id || this.generateId();
        
        // Check if message already exists (e.g., echo from server)
        if (this.messages.has(messageId)) {
            this.updateMessageStatus(messageId, MessageStatus.DELIVERED);
            return;
        }

        const message = {
            id: messageId,
            content: this.parseContent(data.content),
            rawContent: data.content,
            sender: data.sender || { id: 'unknown', name: 'Unknown' },
            timestamp: data.timestamp || Date.now(),
            isOwn: data.sender?.id === this.currentUser.id,
            status: MessageStatus.DELIVERED
        };

        this.messages.set(messageId, message);
        this.addMessageToUI(message);

        // Show scroll indicator if not at bottom
        if (!this.scrollState.isAtBottom) {
            this.scrollIndicator.dataset.newMessages = 'true';
            this.scrollIndicator.classList.add('visible');
        }

        this.emit('messageReceived', { message });
        this.pruneOldMessages();
    }

    /**
     * Add a message to the UI
     * @param {Object} message - Message object
     * @private
     */
    addMessageToUI(message) {
        if (!this.container) return;

        // Hide empty state if present
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.style.display = 'none';
        }

        const messageEl = this.createMessageElement(message);
        this.container.appendChild(messageEl);

        // Observe for read receipts
        if (this.observer && !message.isOwn) {
            this.observer.observe(messageEl);
        }

        // Scroll to bottom if appropriate
        if (message.isOwn || this.scrollState.isAtBottom) {
            this.scrollToBottom();
        }

        // Animate in
        requestAnimationFrame(() => {
            messageEl.classList.add('visible');
        });
    }

    /**
     * Create a message DOM element
     * @param {Object} message - Message object
     * @returns {HTMLElement}
     * @private
     */
    createMessageElement(message) {
        const el = document.createElement('div');
        el.className = `chat-message ${message.isOwn ? 'message-own' : 'message-other'}`;
        el.dataset.messageId = message.id;

        const showAvatar = this.config.showAvatars && !message.isOwn;
        const timeStr = this.formatTime(message.timestamp);
        const statusIcon = this.getStatusIcon(message.status);

        const avatarHtml = showAvatar ? `
            <div class="message-avatar" title="${this.escapeHtml(message.sender.name)}">
                ${message.sender.avatar ? 
                    `<img src="${this.escapeHtml(message.sender.avatar)}" alt="">` :
                    `<span>${this.getInitials(message.sender.name)}</span>`
                }
            </div>
        ` : '<div class="message-avatar-spacer"></div>';

        const presenceIndicator = !message.isOwn ? `
            <span class="presence-indicator ${this.getUserPresence(message.sender.id)}"></span>
        ` : '';

        el.innerHTML = `
            ${avatarHtml}
            <div class="message-content-wrapper">
                <div class="message-bubble">
                    ${!message.isOwn ? `
                        <div class="message-header">
                            <span class="message-sender">${this.escapeHtml(message.sender.name)}</span>
                            ${presenceIndicator}
                        </div>
                    ` : ''}
                    <div class="message-text">${message.content}</div>
                    <div class="message-footer">
                        <time class="message-time" datetime="${new Date(message.timestamp).toISOString()}" title="${new Date(message.timestamp).toLocaleString()}">
                            ${timeStr}
                        </time>
                        ${message.isOwn ? `
                            <span class="message-status" data-status="${message.status}">
                                ${statusIcon}
                            </span>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        return el;
    }

    /**
     * Update message status
     * @param {string} messageId - Message ID
     * @param {string} status - New status
     */
    updateMessageStatus(messageId, status) {
        const message = this.messages.get(messageId);
        if (!message) return;

        const previousStatus = message.status;
        message.status = status;

        // Update UI
        const messageEl = this.container?.querySelector(`[data-message-id="${messageId}"]`);
        if (messageEl) {
            const statusEl = messageEl.querySelector('.message-status');
            if (statusEl) {
                statusEl.dataset.status = status;
                statusEl.innerHTML = this.getStatusIcon(status);
            }
        }

        if (previousStatus !== status) {
            this.emit('messageStatusChanged', { messageId, status, previousStatus });
        }
    }

    /**
     * Mark message as read
     * @param {string} messageId - Message ID
     * @private
     */
    markMessageAsRead(messageId) {
        this.updateMessageStatus(messageId, MessageStatus.READ);
        
        // Notify server if connected
        if (this.wsClient?.isConnected()) {
            this.wsClient.send({
                type: 'read_receipt',
                messageId: messageId,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Get status icon SVG
     * @param {string} status - Message status
     * @returns {string}
     * @private
     */
    getStatusIcon(status) {
        const icons = {
            [MessageStatus.SENDING]: `
                <svg class="status-icon sending" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="20">
                        <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
                    </circle>
                </svg>
            `,
            [MessageStatus.SENT]: `
                <svg class="status-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            `,
            [MessageStatus.DELIVERED]: `
                <svg class="status-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                    <polyline points="20 12 9 23 4 18" style="opacity: 0.5;"></polyline>
                </svg>
            `,
            [MessageStatus.READ]: `
                <svg class="status-icon read" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                    <polyline points="20 12 9 23 4 18"></polyline>
                </svg>
            `,
            [MessageStatus.ERROR]: `
                <svg class="status-icon error" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
            `
        };
        return icons[status] || icons[MessageStatus.SENDING];
    }

    /**
     * Parse message content for rich formatting
     * @param {string} content - Raw content
     * @returns {string} - Parsed HTML content
     * @private
     */
    parseContent(content) {
        if (!content) return '';

        let parsed = this.escapeHtml(content);

        // URLs
        parsed = parsed.replace(
            /(https?:\/\/[^\s]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer" class="message-link">$1</a>'
        );

        // Emojis (simple detection)
        parsed = this.parseEmojis(parsed);

        // Bold: **text**
        parsed = parsed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italic: *text* or _text_
        parsed = parsed.replace(/(^|\s)\*([^*]+)\*(?=\s|$)/g, '$1<em>$2</em>');
        parsed = parsed.replace(/(^|\s)_([^_]+)_(?=\s|$)/g, '$1<em>$2</em>');

        // Code: `text`
        parsed = parsed.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Strikethrough: ~~text~~
        parsed = parsed.replace(/~~([^~]+)~~/g, '<del>$1</del>');

        // Newlines to <br>
        parsed = parsed.replace(/\n/g, '<br>');

        return parsed;
    }

    /**
     * Parse emojis in text
     * @param {string} text - Text to parse
     * @returns {string}
     * @private
     */
    parseEmojis(text) {
        const emojiMap = {
            ':)': '😊', ':-)': '😊',
            ':(': '😢', ':-(': '😢',
            ':D': '😄', ':-D': '😄',
            ':P': '😛', ':-P': '😛',
            ':p': '😛', ':-p': '😛',
            ';)': '😉', ';-)': '😉',
            '<3': '❤️',
            ':fire:': '🔥',
            ':thumbsup:': '👍',
            ':thumbsdown:': '👎',
            ':rocket:': '🚀',
            ':wave:': '👋',
            ':clap:': '👏',
            ':tada:': '🎉',
            ':thinking:': '🤔',
            ':heart:': '❤️',
            ':star:': '⭐',
            ':check:': '✅',
            ':x:': '❌',
            ':warning:': '⚠️',
            ':info:': 'ℹ️',
            ':coffee:': '☕',
            ':code:': '💻',
            ':bug:': '🐛'
        };

        let result = text;
        for (const [code, emoji] of Object.entries(emojiMap)) {
            const regex = new RegExp(this.escapeRegex(code), 'g');
            result = result.replace(regex, `<span class="emoji">${emoji}</span>`);
        }

        return result;
    }

    /**
     * Format timestamp to relative time
     * @param {number|string} timestamp - Timestamp
     * @returns {string}
     */
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        // Less than 1 minute ago
        if (diffSecs < 60) {
            return 'just now';
        }

        // Less than 1 hour ago
        if (diffMins < 60) {
            return `${diffMins}m ago`;
        }

        // Less than 24 hours ago
        if (diffHours < 24) {
            return `${diffHours}h ago`;
        }

        // Less than 7 days ago
        if (diffDays < 7) {
            return `${diffDays}d ago`;
        }

        // Format date
        return date.toLocaleDateString([], { 
            month: 'short', 
            day: 'numeric' 
        });
    }

    /**
     * Start timestamp updater
     * @private
     */
    startTimestampUpdater() {
        setInterval(() => {
            const timeElements = this.container?.querySelectorAll('time.message-time');
            timeElements?.forEach(el => {
                const isoTime = el.getAttribute('datetime');
                if (isoTime) {
                    el.textContent = this.formatTime(new Date(isoTime));
                }
            });
        }, 60000); // Update every minute
    }

    /**
     * Handle typing input
     * Call this on input events
     */
    handleTypingInput() {
        // Debounce typing indicator
        clearTimeout(this.typingState.typingTimeout);
        
        if (!this.typingState.isTyping) {
            this.typingState.isTyping = true;
            this.sendTypingIndicator(true);
        }

        this.typingState.typingTimeout = setTimeout(() => {
            this.typingState.isTyping = false;
            this.sendTypingIndicator(false);
        }, this.config.typingDebounceMs);
    }

    /**
     * Send typing indicator to server
     * @param {boolean} isTyping - Whether user is typing
     * @private
     */
    sendTypingIndicator(isTyping) {
        if (!this.wsClient?.isConnected()) return;

        this.wsClient.send({
            type: isTyping ? 'typing_start' : 'typing_stop',
            timestamp: Date.now()
        });
    }

    /**
     * Handle typing indicator from other users
     * @param {string} userId - User ID
     * @param {boolean} isTyping - Whether user is typing
     */
    handleRemoteTyping(userId, isTyping) {
        const user = this.users.get(userId);
        if (!user) return;

        user.isTyping = isTyping;

        // Clear existing timeout
        if (user.typingTimeout) {
            clearTimeout(user.typingTimeout);
        }

        // Auto-stop typing after timeout
        if (isTyping) {
            user.typingTimeout = setTimeout(() => {
                user.isTyping = false;
                this.updateTypingIndicator();
            }, this.config.typingIndicatorTimeout);
        }

        this.updateTypingIndicator();
        this.emit(isTyping ? 'typingStarted' : 'typingStopped', { userId, user });
    }

    /**
     * Update typing indicator UI
     * @private
     */
    updateTypingIndicator() {
        // Remove existing indicator
        const existing = this.container?.querySelector('.typing-indicator');
        if (existing) {
            existing.remove();
        }

        // Find typing users
        const typingUsers = Array.from(this.users.values()).filter(u => u.isTyping);
        if (typingUsers.length === 0) return;

        // Create indicator
        const indicator = document.createElement('div');
        indicator.className = 'chat-message typing-indicator message-other';
        
        const names = typingUsers.map(u => u.name).join(', ');
        const text = typingUsers.length === 1 
            ? `${names} is typing...`
            : `${names} are typing...`;

        indicator.innerHTML = `
            <div class="message-avatar-spacer"></div>
            <div class="message-content-wrapper">
                <div class="typing-bubble">
                    <span class="typing-text">${this.escapeHtml(text)}</span>
                    <span class="typing-dots">
                        <span></span><span></span><span></span>
                    </span>
                </div>
            </div>
        `;

        this.container?.appendChild(indicator);
        this.scrollToBottom();
    }

    /**
     * Update user presence
     * @param {string} userId - User ID
     * @param {string} presence - Presence status
     * @param {Object} [userData={}] - Additional user data
     */
    updateUserPresence(userId, presence, userData = {}) {
        const user = this.users.get(userId) || { id: userId };
        const previousPresence = user.presence;
        
        Object.assign(user, userData, { presence });
        this.users.set(userId, user);

        // Update UI for all messages from this user
        if (previousPresence !== presence) {
            const indicators = this.container?.querySelectorAll(
                `.chat-message:not(.message-own) .presence-indicator[data-user-id="${userId}"]`
            );
            indicators?.forEach(el => {
                el.className = `presence-indicator ${presence}`;
            });

            this.emit('userPresenceChanged', { userId, presence, previousPresence, user });
        }
    }

    /**
     * Get user presence
     * @param {string} userId - User ID
     * @returns {string}
     * @private
     */
    getUserPresence(userId) {
        const user = this.users.get(userId);
        return user?.presence || UserPresence.OFFLINE;
    }

    /**
     * Prune old messages to prevent memory issues
     * @private
     */
    pruneOldMessages() {
        if (this.messages.size <= this.config.maxMessages) return;

        const messagesToRemove = this.messages.size - this.config.maxMessages;
        const sortedMessages = Array.from(this.messages.entries())
            .sort((a, b) => a[1].timestamp - b[1].timestamp);

        for (let i = 0; i < messagesToRemove; i++) {
            const [id] = sortedMessages[i];
            this.messages.delete(id);
            
            const el = this.container?.querySelector(`[data-message-id="${id}"]`);
            if (el) el.remove();
        }
    }

    /**
     * Get initials from name
     * @param {string} name - Full name
     * @returns {string}
     * @private
     */
    getInitials(name) {
        if (!name) return '?';
        return name
            .split(' ')
            .map(n => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2);
    }

    /**
     * Escape HTML special characters
     * @param {string} text - Raw text
     * @returns {string}
     * @private
     */
    escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Escape regex special characters
     * @param {string} string - String to escape
     * @returns {string}
     * @private
     */
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Generate unique ID
     * @returns {string}
     * @private
     */
    generateId() {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Register event handler
     * @param {string} event - Event name
     * @param {Function} handler - Event handler
     * @returns {Function} Unsubscribe function
     */
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
        
        return () => {
            this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
        };
    }

    /**
     * Emit event to all handlers
     * @param {string} event - Event name
     * @param {*} data - Event data
     * @private
     */
    emit(event, data) {
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
     * Clear all messages
     */
    clear() {
        this.messages.clear();
        if (this.container) {
            this.container.innerHTML = `
                <div class="empty-state" id="empty-messages">
                    <div class="empty-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
                        </svg>
                    </div>
                    <p>No messages yet</p>
                    <p class="empty-subtitle">Start the conversation!</p>
                </div>
            `;
        }
    }

    /**
     * Destroy the chat UI and cleanup
     */
    destroy() {
        // Clear timeouts
        clearTimeout(this.typingState.typingTimeout);
        clearTimeout(this.typingState.indicatorTimeout);
        clearTimeout(this.scrollState.scrollTimeout);

        // Disconnect observer
        if (this.observer) {
            this.observer.disconnect();
        }

        // Remove event listeners
        window.removeEventListener('resize', this.handleResize);

        // Remove scroll indicator
        if (this.scrollIndicator) {
            this.scrollIndicator.remove();
        }

        // Clear data
        this.messages.clear();
        this.users.clear();
    }
}

export default ChatUI;