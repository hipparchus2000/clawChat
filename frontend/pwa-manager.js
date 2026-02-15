/**
 * ClawChat PWA Manager
 * 
 * Handles PWA features:
 * - Service Worker registration
 * - Install prompt (beforeinstallprompt)
 * - Background sync
 * - Push notifications
 * - Offline/Online state management
 * - App updates
 * 
 * @module pwa-manager
 * @version 1.0.0
 */

class PWAManager {
    constructor() {
        this.swRegistration = null;
        this.deferredPrompt = null;
        this.isInstallable = false;
        this.isStandalone = false;
        this.offlineQueue = [];
        
        this.init();
    }

    /**
     * Initialize PWA features
     */
    init() {
        // Check if running as standalone PWA
        this.isStandalone = window.matchMedia('(display-mode: standalone)').matches 
            || window.navigator.standalone === true;

        // Register service worker
        if ('serviceWorker' in navigator) {
            this.registerServiceWorker();
        }

        // Listen for install prompt
        this.handleInstallPrompt();

        // Monitor connection status
        this.monitorConnectionStatus();

        // Handle app updates
        this.handleAppUpdates();

        console.log('[PWA] Manager initialized', { 
            isStandalone: this.isStandalone,
            swSupported: 'serviceWorker' in navigator
        });
    }

    /**
     * Register the service worker
     */
    async registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/service-worker.js', {
                scope: '/'
            });

            this.swRegistration = registration;
            console.log('[PWA] Service Worker registered:', registration.scope);

            // Listen for updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                console.log('[PWA] Service Worker update found');

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // New update available
                        this.showUpdateNotification(newWorker);
                    }
                });
            });

            // Listen for messages from SW
            navigator.serviceWorker.addEventListener('message', (event) => {
                this.handleSWMessage(event.data);
            });

            // Check for updates periodically
            setInterval(() => {
                registration.update();
            }, 60 * 60 * 1000); // Check every hour

        } catch (error) {
            console.error('[PWA] Service Worker registration failed:', error);
        }
    }

    /**
     * Handle install prompt events
     */
    handleInstallPrompt() {
        // Prevent default mini-infobar
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('[PWA] Install prompt available');
            e.preventDefault();
            this.deferredPrompt = e;
            this.isInstallable = true;
            
            // Dispatch custom event so app can show install button
            window.dispatchEvent(new CustomEvent('pwaInstallable', {
                detail: { prompt: e }
            }));
        });

        // Handle successful install
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed');
            this.isInstallable = false;
            this.deferredPrompt = null;
            
            window.dispatchEvent(new CustomEvent('pwaInstalled'));
        });
    }

    /**
     * Monitor connection status
     */
    monitorConnectionStatus() {
        const updateStatus = () => {
            const isOnline = navigator.onLine;
            console.log('[PWA] Connection status:', isOnline ? 'online' : 'offline');
            
            window.dispatchEvent(new CustomEvent('pwaConnectionChange', {
                detail: { isOnline }
            }));

            if (isOnline) {
                this.triggerBackgroundSync();
            }
        };

        window.addEventListener('online', updateStatus);
        window.addEventListener('offline', updateStatus);
    }

    /**
     * Handle messages from service worker
     */
    handleSWMessage(data) {
        console.log('[PWA] Message from SW:', data);
        
        switch (data.type) {
            case 'SYNC_STARTED':
                window.dispatchEvent(new CustomEvent('pwaSyncStarted', {
                    detail: { tag: data.tag }
                }));
                break;
                
            case 'SYNC_COMPLETED':
                window.dispatchEvent(new CustomEvent('pwaSyncCompleted', {
                    detail: { tag: data.tag }
                }));
                break;
                
            case 'VERSION':
                console.log('[PWA] Service Worker version:', data.version);
                break;
                
            case 'CACHES_CLEARED':
                console.log('[PWA] Caches cleared');
                break;
        }
    }

    /**
     * Handle app updates
     */
    handleAppUpdates() {
        // Listen for controller change (new SW activated)
        navigator.serviceWorker?.addEventListener('controllerchange', () => {
            console.log('[PWA] Service Worker controller changed');
            window.location.reload();
        });
    }

    /**
     * Show update notification
     */
    showUpdateNotification(worker) {
        window.dispatchEvent(new CustomEvent('pwaUpdateAvailable', {
            detail: { 
                applyUpdate: () => {
                    worker.postMessage({ type: 'SKIP_WAITING' });
                }
            }
        }));
    }

    // ============================================
    // Public API
    // ============================================

    /**
     * Trigger the install prompt
     * @returns {Promise<boolean>} Whether the prompt was shown
     */
    async promptInstall() {
        if (!this.deferredPrompt) {
            console.log('[PWA] No install prompt available');
            return false;
        }

        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;
        
        console.log('[PWA] Install prompt outcome:', outcome);
        
        this.deferredPrompt = null;
        this.isInstallable = false;
        
        return outcome === 'accepted';
    }

    /**
     * Check if app is installable
     * @returns {boolean}
     */
    canInstall() {
        return this.isInstallable && !!this.deferredPrompt;
    }

    /**
     * Check if running as standalone PWA
     * @returns {boolean}
     */
    isAppStandalone() {
        return this.isStandalone;
    }

    /**
     * Request push notification permission
     * @returns {Promise<boolean>}
     */
    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('[PWA] Notifications not supported');
            return false;
        }

        const permission = await Notification.requestPermission();
        return permission === 'granted';
    }

    /**
     * Subscribe to push notifications
     * @param {string} serverUrl - Server endpoint for push subscription
     * @returns {Promise<PushSubscription|null>}
     */
    async subscribeToPush(serverUrl) {
        try {
            if (!this.swRegistration) {
                throw new Error('Service Worker not registered');
            }

            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                throw new Error('Notification permission denied');
            }

            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(
                    // Replace with your VAPID public key
                    'BEl62iOMsSUtrZv7Mn3UOe4U4YQoE6bNhr14zABwB8y3x7yQJ-3mV5z9q7p7P7P7P7P7P7P7P7P7P7P7P7P7P'
                )
            });

            // Send subscription to server
            if (serverUrl) {
                await fetch(serverUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subscription)
                });
            }

            console.log('[PWA] Push subscription created');
            return subscription;

        } catch (error) {
            console.error('[PWA] Push subscription failed:', error);
            return null;
        }
    }

    /**
     * Trigger background sync
     * @param {string} tag - Sync tag
     */
    async triggerBackgroundSync(tag = 'sync-messages') {
        if (!this.swRegistration) {
            console.log('[PWA] Service Worker not available for sync');
            return false;
        }

        try {
            if ('sync' in this.swRegistration) {
                await this.swRegistration.sync.register(tag);
                console.log('[PWA] Background sync registered:', tag);
                return true;
            } else {
                // Fallback: trigger sync manually
                this.swRegistration.active?.postMessage({
                    type: 'REGISTER_SYNC',
                    data: { tag }
                });
                return true;
            }
        } catch (error) {
            console.error('[PWA] Background sync failed:', error);
            return false;
        }
    }

    /**
     * Queue an action for when online
     * @param {Function} action - Action to queue
     */
    queueWhenOnline(action) {
        if (navigator.onLine) {
            action();
        } else {
            this.offlineQueue.push(action);
            console.log('[PWA] Action queued for when online');
        }
    }

    /**
     * Process queued actions when coming back online
     */
    processOfflineQueue() {
        if (this.offlineQueue.length === 0) return;
        
        console.log('[PWA] Processing offline queue:', this.offlineQueue.length);
        
        while (this.offlineQueue.length > 0) {
            const action = this.offlineQueue.shift();
            try {
                action();
            } catch (error) {
                console.error('[PWA] Failed to process queued action:', error);
            }
        }
    }

    /**
     * Check for app updates
     */
    async checkForUpdates() {
        if (!this.swRegistration) return;
        
        try {
            await this.swRegistration.update();
            console.log('[PWA] Update check triggered');
        } catch (error) {
            console.error('[PWA] Update check failed:', error);
        }
    }

    /**
     * Get service worker version
     * @returns {Promise<string|null>}
     */
    async getVersion() {
        if (!this.swRegistration?.active) return null;
        
        return new Promise((resolve) => {
            const channel = new MessageChannel();
            channel.port1.onmessage = (event) => {
                resolve(event.data?.version || null);
            };
            
            this.swRegistration.active.postMessage(
                { type: 'GET_VERSION' },
                [channel.port2]
            );
        });
    }

    /**
     * Clear all caches
     * @returns {Promise<boolean>}
     */
    async clearCaches() {
        if (!this.swRegistration?.active) return false;
        
        return new Promise((resolve) => {
            const channel = new MessageChannel();
            channel.port1.onmessage = (event) => {
                resolve(event.data?.success || false);
            };
            
            this.swRegistration.active.postMessage(
                { type: 'CLEAR_CACHES' },
                [channel.port2]
            );
        });
    }

    /**
     * Share content using Web Share API
     * @param {Object} data - Share data
     * @returns {Promise<boolean>}
     */
    async share(data) {
        if (!navigator.share) {
            console.log('[PWA] Web Share API not supported');
            return false;
        }

        try {
            await navigator.share(data);
            return true;
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('[PWA] Share failed:', error);
            }
            return false;
        }
    }

    // ============================================
    // Utility Methods
    // ============================================

    /**
     * Convert base64 to Uint8Array for VAPID key
     */
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }
}

// Create singleton instance
const pwaManager = new PWAManager();

// Export for module usage
export { PWAManager, pwaManager };
export default pwaManager;
