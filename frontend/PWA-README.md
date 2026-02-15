# ClawChat PWA Setup

This folder contains the Progressive Web App (PWA) configuration for ClawChat.

## Files

- `manifest.json` - Web App Manifest with PWA configuration
- `service-worker.js` - Service Worker with caching strategies
- `offline.html` - Offline fallback page
- `pwa-manager.js` - PWA management module
- `browserconfig.xml` - Microsoft browser configuration
- `icons/` - App icons in various sizes

## Icons

The icons folder contains SVG icons. For production, convert these to PNG format:

- icon-72x72.png
- icon-96x96.png
- icon-128x128.png
- icon-144x144.png
- icon-152x152.png
- icon-192x192.png
- icon-384x384.png
- icon-512x512.png
- badge-72x72.png

## Features

### Service Worker
- **Network-first** strategy for API calls
- **Cache-first** strategy for static assets and images
- **Stale-while-revalidate** for HTML pages
- Automatic cache cleanup on update
- Offline fallback to cached content

### Background Sync
- Messages queued when offline are sent when connection returns
- Automatic sync registration on connection restore

### Push Notifications
- Support for Web Push API
- Notification click handling to open app
- Custom notification actions

### Install Prompt
- Custom install button in header
- Detects when app is installable
- Tracks installation status

### Offline Support
- Offline page with connection retry
- Graceful degradation of features
- Cached messages available offline

## PWA Manager API

```javascript
import { pwaManager } from './pwa-manager.js';

// Check if app can be installed
if (pwaManager.canInstall()) {
    // Show install button
}

// Trigger install prompt
await pwaManager.promptInstall();

// Request push notifications
await pwaManager.requestNotificationPermission();

// Subscribe to push
await pwaManager.subscribeToPush('/api/push-subscribe');

// Trigger background sync
await pwaManager.triggerBackgroundSync('sync-messages');

// Check for updates
await pwaManager.checkForUpdates();
```

## Testing PWA

1. Use Chrome DevTools > Application tab
2. Check Manifest section for validity
3. Test Service Worker registration
4. Test offline functionality in Network tab
5. Test install prompt in Lighthouse audit

## Browser Support

- Chrome/Edge 80+
- Firefox 75+
- Safari 14+ (iOS 14.5+)
- Samsung Internet 12+
