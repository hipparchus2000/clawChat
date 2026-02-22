/**
 * ClawChat Service Worker
 * 
 * Features:
 * - Network-first strategy for API calls (WebSocket not cached)
 * - Cache-first strategy for static assets
 * - Offline fallback page
 * - Background sync for offline messages
 * - Push notification support
 * 
 * @version 1.0.0
 */

const CACHE_VERSION = 'v1.0.0';
const STATIC_CACHE = `clawchat-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `clawchat-dynamic-${CACHE_VERSION}`;
const IMAGE_CACHE = `clawchat-images-${CACHE_VERSION}`;

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/style.css',
  '/chat.css',
  '/app.js',
  '/websocket-client.js',
  '/chat-ui.js',
  '/file-browser.css',
  '/manifest.json'
];

// Routes that should use network-first strategy
const API_ROUTES = [
  '/api/',
  '/ws',
  '/socket'
];

// Image file extensions for cache-first strategy
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico'];

/**
 * Check if a request is an API call
 * @param {Request} request
 * @returns {boolean}
 */
function isApiRequest(request) {
  const url = new URL(request.url);
  return API_ROUTES.some(route => url.pathname.startsWith(route)) ||
         request.headers.get('Accept')?.includes('application/json');
}

/**
 * Check if a request is for an image
 * @param {Request} request
 * @returns {boolean}
 */
function isImageRequest(request) {
  const url = new URL(request.url);
  return IMAGE_EXTENSIONS.some(ext => url.pathname.toLowerCase().endsWith(ext));
}

/**
 * Check if request is for a static asset
 * @param {Request} request
 * @returns {boolean}
 */
function isStaticAsset(request) {
  const url = new URL(request.url);
  return STATIC_ASSETS.some(asset => url.pathname === asset) ||
         url.pathname.endsWith('.js') ||
         url.pathname.endsWith('.css') ||
         url.pathname.endsWith('.json');
}

// ============================================
// Install Event - Cache static assets
// ============================================
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static assets...');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Static assets cached successfully');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('[SW] Failed to cache static assets:', error);
      })
  );
});

// ============================================
// Activate Event - Clean up old caches
// ============================================
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(name => {
              // Delete caches that don't match current version
              return name.startsWith('clawchat-') && 
                     !name.includes(CACHE_VERSION);
            })
            .map(name => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

// ============================================
// Fetch Event - Handle all network requests
// ============================================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests for caching
  if (request.method !== 'GET') {
    // For WebSocket upgrade requests, just pass through
    if (request.headers.get('Upgrade') === 'websocket') {
      return;
    }
    return;
  }
  
  // Skip cross-origin requests (except for same-origin)
  if (url.origin !== self.location.origin) {
    // Allow external images with cache-first
    if (isImageRequest(request)) {
      event.respondWith(cacheFirstStrategy(request, IMAGE_CACHE));
    }
    return;
  }
  
  // API requests - Network First
  if (isApiRequest(request)) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }
  
  // Image requests - Cache First
  if (isImageRequest(request)) {
    event.respondWith(cacheFirstStrategy(request, IMAGE_CACHE));
    return;
  }
  
  // Static assets - Cache First
  if (isStaticAsset(request)) {
    event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
    return;
  }
  
  // All other requests - Stale While Revalidate
  event.respondWith(staleWhileRevalidateStrategy(request, DYNAMIC_CACHE));
});

// ============================================
// Caching Strategies
// ============================================

/**
 * Network First Strategy - Try network, fall back to cache
 * Best for: API calls, real-time data
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache...');
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline fallback for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }
    
    throw error;
  }
}

/**
 * Cache First Strategy - Try cache, fall back to network
 * Best for: Static assets, images
 * @param {Request} request
 * @param {string} cacheName
 * @returns {Promise<Response>}
 */
async function cacheFirstStrategy(request, cacheName) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    // Update cache in background (stale-while-revalidate pattern)
    fetch(request)
      .then(response => {
        if (response.ok) {
          caches.open(cacheName).then(cache => {
            cache.put(request, response);
          });
        }
      })
      .catch(() => {});
    
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    // Return placeholder for images
    if (isImageRequest(request)) {
      return new Response(
        `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
          <rect width="100" height="100" fill="#f1f5f9"/>
          <text x="50" y="50" text-anchor="middle" fill="#94a3b8" font-size="14">Image</text>
        </svg>`,
        { headers: { 'Content-Type': 'image/svg+xml' } }
      );
    }
    throw error;
  }
}

/**
 * Stale While Revalidate Strategy - Serve from cache, update in background
 * Best for: HTML pages that can be slightly outdated
 * @param {Request} request
 * @param {string} cacheName
 * @returns {Promise<Response>}
 */
async function staleWhileRevalidateStrategy(request, cacheName) {
  const cachedResponse = await caches.match(request);
  
  const fetchPromise = fetch(request)
    .then(networkResponse => {
      if (networkResponse.ok) {
        caches.open(cacheName).then(cache => {
          cache.put(request, networkResponse.clone());
        });
      }
      return networkResponse;
    })
    .catch(error => {
      console.log('[SW] Network fetch failed:', error);
      throw error;
    });
  
  // Return cached version immediately if available
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // Otherwise wait for network
  try {
    return await fetchPromise;
  } catch (error) {
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }
    throw error;
  }
}

// ============================================
// Background Sync - Queue offline operations
// ============================================
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  switch (event.tag) {
    case 'sync-messages':
      event.waitUntil(syncPendingMessages());
      break;
    case 'sync-all':
      event.waitUntil(syncAllPending());
      break;
    default:
      console.log('[SW] Unknown sync tag:', event.tag);
  }
});

/**
 * Sync pending messages from IndexedDB
 * This is a skeleton - implement with your actual IndexedDB logic
 */
async function syncPendingMessages() {
  console.log('[SW] Syncing pending messages...');
  
  // Notify all clients that sync is starting
  const clients = await self.clients.matchAll();
  clients.forEach(client => {
    client.postMessage({
      type: 'SYNC_STARTED',
      tag: 'sync-messages'
    });
  });
  
  // TODO: Implement actual sync logic with IndexedDB
  // This should:
  // 1. Open IndexedDB
  // 2. Get all pending messages
  // 3. Send them to server
  // 4. Mark as sent or handle failures
  
  // Notify clients that sync is complete
  clients.forEach(client => {
    client.postMessage({
      type: 'SYNC_COMPLETED',
      tag: 'sync-messages'
    });
  });
}

async function syncAllPending() {
  console.log('[SW] Syncing all pending operations...');
  await syncPendingMessages();
  // Add other sync operations here
}

// ============================================
// Push Notifications
// ============================================
self.addEventListener('push', (event) => {
  console.log('[SW] Push received:', event);
  
  let data = {};
  try {
    data = event.data?.json() || {};
  } catch (e) {
    data = { 
      title: 'ClawChat',
      body: event.data?.text() || 'New notification'
    };
  }
  
  const title = data.title || 'ClawChat';
  const options = {
    body: data.body || 'You have a new message',
    icon: data.icon || '/icons/icon-192x192.png',
    badge: data.badge || '/icons/badge-72x72.png',
    tag: data.tag || 'clawchat-notification',
    requireInteraction: data.requireInteraction || false,
    renotify: data.renotify || false,
    data: data.data || {},
    actions: data.actions || [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);
  
  event.notification.close();
  
  const { action, notification } = event;
  
  if (action === 'dismiss') {
    return;
  }
  
  // Open or focus the app
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        // Try to find an existing client
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window if none exists
        if (self.clients.openWindow) {
          const url = notification.data?.url || '/';
          return self.clients.openWindow(url);
        }
      })
  );
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed:', event);
});

// ============================================
// Message Handling - Communication with clients
// ============================================
self.addEventListener('message', (event) => {
  console.log('[SW] Message from client:', event.data);
  
  const { type, data } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'GET_VERSION':
      event.ports[0]?.postMessage({
        type: 'VERSION',
        version: CACHE_VERSION
      });
      break;
      
    case 'CLEAR_CACHES':
      event.waitUntil(
        caches.keys().then(names => {
          return Promise.all(names.map(name => caches.delete(name)));
        }).then(() => {
          event.ports[0]?.postMessage({
            type: 'CACHES_CLEARED',
            success: true
          });
        })
      );
      break;
      
    case 'REGISTER_SYNC':
      event.waitUntil(
        self.registration.sync.register(data.tag || 'sync-messages')
          .then(() => {
            console.log('[SW] Sync registered:', data.tag);
          })
          .catch(err => {
            console.error('[SW] Sync registration failed:', err);
          })
      );
      break;
      
    case 'SCHEDULE_NOTIFICATION':
      // Schedule a local notification
      if (data.delay) {
        setTimeout(() => {
          self.registration.showNotification(data.title, data.options);
        }, data.delay);
      }
      break;
      
    default:
      console.log('[SW] Unknown message type:', type);
  }
});

// ============================================
// Periodic Background Sync (if supported)
// ============================================
self.addEventListener('periodicsync', (event) => {
  console.log('[SW] Periodic sync triggered:', event.tag);
  
  if (event.tag === 'check-messages') {
    event.waitUntil(checkNewMessages());
  }
});

async function checkNewMessages() {
  // This would check for new messages in the background
  // Requires server support for offline message checking
  console.log('[SW] Checking for new messages...');
}

// ============================================
// Utility Functions
// ============================================

/**
 * Broadcast message to all clients
 * @param {Object} message
 */
async function broadcastToClients(message) {
  const clients = await self.clients.matchAll({ includeUncontrolled: true });
  clients.forEach(client => {
    client.postMessage(message);
  });
}

console.log('[SW] Service worker loaded');
