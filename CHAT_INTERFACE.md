# ClawChat Complete Chat Interface

This document describes the full-featured chat interface implementation for ClawChat.

## Files Created/Modified

### Frontend
- `/frontend/chat-ui.js` - Main chat UI module with all features
- `/frontend/chat.css` - Chat-specific styles with dark/light theme support
- `/frontend/app.js` - Updated to integrate ChatUI
- `/frontend/index.html` - Updated to include chat.css

### Backend
- `/backend/chat_handler.py` - Server-side chat handling
- `/backend/chat_server_integration.py` - Integration example

## Features

### 1. Message Bubbles with Sender Distinction
- **Sent messages**: Right-aligned, primary color gradient background
- **Received messages**: Left-aligned, card-style with border
- User avatars with initials fallback
- Message grouping for consecutive messages from same sender

### 2. Message History Display
- Scrollable message container
- Automatic loading of history on join
- Message pruning to prevent memory issues (configurable max)
- Empty state with friendly welcome message

### 3. User Presence Indicators
- **Online**: Green dot with glow effect
- **Offline**: Gray dot
- **Away**: Orange/amber dot
- **Typing**: Blue pulsing dot
- Shows next to sender name in messages

### 4. Typing Indicators
- Client-side debouncing (300ms default)
- Animated "..." dots indicator
- Shows which user(s) are typing
- Auto-clears after timeout (3s default)
- Server-side typing state management

### 5. Message Timestamps
- Relative time formatting:
  - "just now" (< 1 min)
  - "Xm ago" (< 1 hour)
  - "Xh ago" (< 24 hours)
  - "Xd ago" (< 7 days)
  - Date for older messages
- Auto-updates every minute
- Full datetime on hover (title attribute)

### 6. Scroll Management
- Auto-scrolls to new messages when at bottom
- Manual scroll indicator button appears when scrolled up
- Badge shows count of new messages
- Smooth scrolling animations
- Respects user's scroll position
- Keyboard shortcut support

### 7. Message Status Indicators
- **Sending**: Spinning loader
- **Sent**: Single checkmark
- **Delivered**: Double checkmark (gray)
- **Read**: Double checkmark (blue)
- **Error**: Warning icon
- Real-time updates as status changes

### 8. Rich Message Support
- **URLs**: Auto-linked with styling
- **Emojis**: Common emoticons converted (:) → 😊)
- **Text formatting**:
  - `**bold**` → **bold**
  - `*italic*` or `_italic_` → *italic*
  - `` `code` `` → `code`
  - `~~strikethrough~~` → ~~strikethrough~~
- Newlines preserved as `<br>`
- XSS-safe HTML escaping

## Usage

### Basic Setup

```javascript
import { ChatUI } from './chat-ui.js';

const chatUI = new ChatUI({
    container: document.getElementById('messages-container'),
    wsClient: webSocketClient,
    currentUser: { 
        id: 'user123', 
        name: 'John Doe',
        avatar: 'https://example.com/avatar.jpg'
    },
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
```

### Sending Messages

```javascript
// Send a message
const messageId = chatUI.sendMessage('Hello, World!', {
    replyTo: 'msg_123' // Optional: reply to another message
});
```

### Receiving Messages

```javascript
// When WebSocket receives a message
wsClient.on('message', ({ data }) => {
    chatUI.receiveMessage({
        id: data.id,
        content: data.content,
        sender: data.sender,
        timestamp: data.timestamp
    });
});
```

### Typing Indicators

```javascript
// On input event
textInput.addEventListener('input', () => {
    chatUI.handleTypingInput();
});

// Handle remote typing
wsClient.on('typing_start', ({ user_id }) => {
    chatUI.handleRemoteTyping(user_id, true);
});
```

### Event Handling

```javascript
// Listen for events
chatUI.on('messageSent', ({ message }) => {
    console.log('Message sent:', message.id);
});

chatUI.on('messageReceived', ({ message }) => {
    playNotificationSound();
});

chatUI.on('messageStatusChanged', ({ messageId, status }) => {
    console.log(`Message ${messageId} is now ${status}`);
});

chatUI.on('userPresenceChanged', ({ userId, presence }) => {
    updateUserList(userId, presence);
});
```

## Backend Integration

### Python Chat Handler

```python
from chat_handler import ChatHandler, UserPresence

# Initialize
chat = ChatHandler(max_history=1000)
await chat.start()

# Register connection
user = chat.register_connection(
    connection_id="conn_123",
    user_id="user_456",
    user_name="John Doe"
)

# Handle incoming message
message = await chat.handle_message(connection_id, {
    "id": "msg_789",
    "content": "Hello!",
    "timestamp": time.time()
})

# Handle typing indicator
await chat.handle_typing(connection_id, is_typing=True)

# Update presence
chat.update_presence(user.id, UserPresence.AWAY)

# Handle read receipt
receipt = chat.handle_read_receipt(connection_id, message_id="msg_789")

# Get history
history = chat.get_message_history(room_id="default", limit=50)

# Cleanup on disconnect
chat.unregister_connection(connection_id)
```

## Styling

The chat interface uses CSS custom properties (variables) that inherit from the main design system:

### Dark Mode Support
Automatic dark mode via `prefers-color-scheme: dark`:

```css
@media (prefers-color-scheme: dark) {
    :root {
        --bg-primary: #0f172a;
        --bg-secondary: #1e293b;
        --text-primary: #f8fafc;
        /* ... */
    }
}
```

### Customizing

Override CSS variables to customize:

```css
:root {
    --color-primary: #your-color;
    --border-radius: 12px;
    /* etc */
}
```

## Accessibility

- **ARIA labels** on interactive elements
- **Live regions** for new messages
- **Keyboard navigation** support
- **Focus indicators** visible
- **Reduced motion** support via `prefers-reduced-motion`
- **High contrast** support via `prefers-contrast`

## Responsive Design

### Mobile (< 640px)
- Larger tap targets
- Simplified avatar display
- Optimized spacing
- Bottom-positioned scroll indicator

### Tablet (640px - 1024px)
- Standard layout
- Increased padding

### Desktop (> 1024px)
- Centered chat container with max-width
- Larger message bubbles
- Side-by-side elements where applicable

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

Requires:
- ES6 Modules
- IntersectionObserver API (for read receipts)
- CSS Custom Properties

## Performance Considerations

- Message pruning (default: 500 max)
- Debounced scroll handling
- IntersectionObserver for efficient visibility tracking
- Passive event listeners where appropriate
- CSS animations use `transform` and `opacity` for GPU acceleration

## Future Enhancements

Potential additions:
- File attachments
- Message reactions
- Threaded replies
- Message search
- Voice messages
- Video calls