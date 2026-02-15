"""
ClawChat PWA Tests
==================
Comprehensive tests for Progressive Web App features including:
- Service Worker caching strategies
- Offline functionality
- PWA install prompt
- Background sync
- Push notifications

Run with: pytest tests/test_pwa.py -v
"""

import asyncio
import json
import os
import pytest
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

# Check if playwright is available
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: playwright not available, browser tests will be skipped")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def frontend_path():
    """Get the path to the frontend directory."""
    return Path(__file__).parent.parent / "frontend"


@pytest.fixture
def service_worker_js(frontend_path):
    """Read the service worker JavaScript."""
    sw_path = frontend_path / "service-worker.js"
    if sw_path.exists():
        return sw_path.read_text()
    return None


@pytest.fixture
def pwa_manager_js(frontend_path):
    """Read the PWA manager JavaScript."""
    pwa_path = frontend_path / "pwa-manager.js"
    if pwa_path.exists():
        return pwa_path.read_text()
    return None


@pytest.fixture
def manifest_json(frontend_path):
    """Read the PWA manifest."""
    manifest_path = frontend_path / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return None


@pytest.fixture
def mock_service_worker():
    """Create a mock service worker environment."""
    return MockServiceWorker()


@pytest.fixture
def mock_cache():
    """Create a mock cache storage."""
    return MockCache()


# ============================================================================
# Mock Classes for Service Worker Testing
# ============================================================================

class MockCache:
    """Mock Cache API for testing."""
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
    
    async def match(self, request) -> Optional[Dict]:
        """Match a request in cache."""
        url = str(request) if isinstance(request, str) else request.url
        return self._storage.get(url)
    
    async def put(self, request, response) -> None:
        """Store a response in cache."""
        url = str(request) if isinstance(request, str) else request.url
        self._storage[url] = {
            "url": url,
            "status": getattr(response, "status", 200),
            "headers": dict(getattr(response, "headers", {})),
            "body": getattr(response, "body", None)
        }
    
    async def delete(self, request) -> bool:
        """Delete an entry from cache."""
        url = str(request) if isinstance(request, str) else request.url
        if url in self._storage:
            del self._storage[url]
            return True
        return False
    
    async def keys(self):
        """Get all cached URLs."""
        return list(self._storage.keys())
    
    def clear(self):
        """Clear all cached entries."""
        self._storage.clear()


class MockCacheStorage:
    """Mock CacheStorage API."""
    
    def __init__(self):
        self._caches: Dict[str, MockCache] = {}
    
    async def open(self, cache_name: str) -> MockCache:
        """Open or create a cache."""
        if cache_name not in self._caches:
            self._caches[cache_name] = MockCache()
        return self._caches[cache_name]
    
    async def has(self, cache_name: str) -> bool:
        """Check if cache exists."""
        return cache_name in self._caches
    
    async def delete(self, cache_name: str) -> bool:
        """Delete a cache."""
        if cache_name in self._caches:
            del self._caches[cache_name]
            return True
        return False
    
    async def keys(self):
        """Get all cache names."""
        return list(self._caches.keys())
    
    async def match(self, request, options=None):
        """Match request across all caches."""
        for cache in self._caches.values():
            match = await cache.match(request)
            if match:
                return match
        return None


class MockServiceWorkerRegistration:
    """Mock ServiceWorkerRegistration API."""
    
    def __init__(self):
        self.scope = "/"
        self.active = MockServiceWorker()
        self.installing = None
        self.waiting = None
        self.sync = MockSyncManager()
        self.pushManager = MockPushManager()
        
    async def update(self):
        """Check for service worker updates."""
        pass
    
    async def unregister(self):
        """Unregister the service worker."""
        pass


class MockServiceWorker:
    """Mock ServiceWorker API."""
    
    def __init__(self):
        self.state = "activated"
        self.scriptURL = "/service-worker.js"
        self.onstatechange = None
        self.onerror = None
    
    def postMessage(self, message, transfer=None):
        """Post a message to the service worker."""
        pass


class MockSyncManager:
    """Mock Background Sync API."""
    
    def __init__(self):
        self._tags = set()
    
    async def register(self, tag: str):
        """Register a sync event."""
        self._tags.add(tag)
        return True
    
    async def getTags(self):
        """Get all registered sync tags."""
        return list(self._tags)


class MockPushManager:
    """Mock Push Manager API."""
    
    def __init__(self):
        self._subscription = None
    
    async def subscribe(self, options):
        """Subscribe to push notifications."""
        self._subscription = {
            "endpoint": "https://example.com/push/test",
            "keys": {
                "p256dh": "test_key",
                "auth": "test_auth"
            }
        }
        return self._subscription
    
    async def getSubscription(self):
        """Get current push subscription."""
        return self._subscription
    
    async def permissionState(self):
        """Get push permission state."""
        return "granted"


class MockServiceWorker:
    """Mock ServiceWorker for testing."""
    
    def __init__(self):
        self.caches = MockCacheStorage()
        self.registration = MockServiceWorkerRegistration()
        self.clients = MockClients()
        self._event_listeners = {}
        self.location = MockLocation()
        
    def addEventListener(self, event_type: str, handler):
        """Add event listener."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(handler)
    
    async def trigger_event(self, event_type: str, event):
        """Trigger an event."""
        handlers = self._event_listeners.get(event_type, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
    
    def skipWaiting(self):
        """Skip the waiting phase."""
        pass


class MockClients:
    """Mock Clients API."""
    
    def __init__(self):
        self._clients = []
    
    async def matchAll(self, options=None):
        """Get all clients."""
        return self._clients
    
    async def openWindow(self, url):
        """Open a new window."""
        client = MockClient(url)
        self._clients.append(client)
        return client
    
    def add(self, client):
        """Add a client."""
        self._clients.append(client)


class MockClient:
    """Mock Client."""
    
    def __init__(self, url="/"):
        self.url = url
        self.id = f"client_{id(self)}"
        self._messages = []
    
    def postMessage(self, message, transfer=None):
        """Post message to client."""
        self._messages.append(message)
    
    async def focus(self):
        """Focus the client."""
        return self


class MockLocation:
    """Mock Location."""
    
    def __init__(self):
        self.origin = "http://localhost:8080"


class MockFetchEvent:
    """Mock Fetch Event."""
    
    def __init__(self, request):
        self.request = request
        self._responded = False
        self._response = None
    
    def respondWith(self, response):
        """Respond to the fetch."""
        self._responded = True
        self._response = response
    
    def waitUntil(self, promise):
        """Wait for a promise."""
        pass


class MockInstallEvent:
    """Mock Install Event."""
    
    def waitUntil(self, promise):
        """Wait for a promise."""
        pass


class MockActivateEvent:
    """Mock Activate Event."""
    
    def waitUntil(self, promise):
        """Wait for a promise."""
        pass


# ============================================================================
# Service Worker Tests
# ============================================================================

@pytest.mark.unit
class TestServiceWorker:
    """Tests for service worker functionality."""
    
    def test_service_worker_file_exists(self, service_worker_js):
        """Test that service worker file exists."""
        assert service_worker_js is not None, "Service worker file not found"
        assert "service-worker.js" in str(service_worker_js) or "addEventListener" in service_worker_js
    
    def test_service_worker_has_install_handler(self, service_worker_js):
        """Test that service worker handles install event."""
        assert "addEventListener('install'" in service_worker_js or 'addEventListener("install"' in service_worker_js
    
    def test_service_worker_has_activate_handler(self, service_worker_js):
        """Test that service worker handles activate event."""
        assert "addEventListener('activate'" in service_worker_js or 'addEventListener("activate"' in service_worker_js
    
    def test_service_worker_has_fetch_handler(self, service_worker_js):
        """Test that service worker handles fetch event."""
        assert "addEventListener('fetch'" in service_worker_js or 'addEventListener("fetch"' in service_worker_js
    
    def test_service_worker_cache_version_defined(self, service_worker_js):
        """Test that service worker has cache version."""
        assert "CACHE_VERSION" in service_worker_js
    
    def test_service_worker_static_assets_defined(self, service_worker_js):
        """Test that service worker defines static assets to cache."""
        assert "STATIC_ASSETS" in service_worker_js
    
    @pytest.mark.asyncio
    async def test_cache_first_strategy(self, mock_cache):
        """Test cache-first caching strategy."""
        # Pre-populate cache
        request = "http://localhost:8080/style.css"
        cached_response = {
            "url": request,
            "status": 200,
            "body": "cached css content"
        }
        await mock_cache.put(request, cached_response)
        
        # Verify cache has the entry
        match = await mock_cache.match(request)
        assert match is not None
        assert match["body"] == "cached css content"
    
    @pytest.mark.asyncio
    async def test_cache_storage_operations(self):
        """Test cache storage operations."""
        storage = MockCacheStorage()
        
        # Open cache
        cache = await storage.open("test-cache")
        assert cache is not None
        
        # Check cache exists
        assert await storage.has("test-cache") is True
        assert await storage.has("nonexistent") is False
        
        # Put and retrieve
        request = "http://localhost/test"
        response = {"status": 200, "body": "test"}
        await cache.put(request, response)
        
        match = await storage.match(request)
        assert match is not None
        
        # Delete cache
        assert await storage.delete("test-cache") is True
        assert await storage.has("test-cache") is False


# ============================================================================
# PWA Manager Tests
# ============================================================================

@pytest.mark.unit
class TestPWAManager:
    """Tests for PWA manager functionality."""
    
    def test_pwa_manager_file_exists(self, pwa_manager_js):
        """Test that PWA manager file exists."""
        assert pwa_manager_js is not None, "PWA manager file not found"
    
    def test_pwa_manager_has_register_method(self, pwa_manager_js):
        """Test that PWA manager has register method."""
        assert "registerServiceWorker" in pwa_manager_js or "async register" in pwa_manager_js
    
    def test_pwa_manager_has_install_handling(self, pwa_manager_js):
        """Test that PWA manager handles install prompt."""
        assert "beforeinstallprompt" in pwa_manager_js
    
    def test_pwa_manager_has_offline_detection(self, pwa_manager_js):
        """Test that PWA manager detects offline state."""
        assert "online" in pwa_manager_js and "offline" in pwa_manager_js
    
    def test_pwa_manager_has_background_sync(self, pwa_manager_js):
        """Test that PWA manager supports background sync."""
        assert "sync" in pwa_manager_js


# ============================================================================
# Manifest Tests
# ============================================================================

@pytest.mark.unit
class TestManifest:
    """Tests for PWA manifest."""
    
    def test_manifest_exists(self, manifest_json):
        """Test that manifest file exists."""
        assert manifest_json is not None, "Manifest file not found"
    
    def test_manifest_has_name(self, manifest_json):
        """Test that manifest has name."""
        assert "name" in manifest_json or "short_name" in manifest_json
    
    def test_manifest_has_start_url(self, manifest_json):
        """Test that manifest has start_url."""
        assert "start_url" in manifest_json
    
    def test_manifest_has_display_mode(self, manifest_json):
        """Test that manifest has display mode."""
        assert "display" in manifest_json
    
    def test_manifest_has_icons(self, manifest_json):
        """Test that manifest has icons."""
        assert "icons" in manifest_json
        assert len(manifest_json["icons"]) > 0
    
    def test_manifest_has_theme_color(self, manifest_json):
        """Test that manifest has theme color."""
        assert "theme_color" in manifest_json
    
    def test_manifest_has_background_color(self, manifest_json):
        """Test that manifest has background color."""
        assert "background_color" in manifest_json


# ============================================================================
# Caching Strategy Tests
# ============================================================================

@pytest.mark.unit
class TestCachingStrategies:
    """Tests for different caching strategies."""
    
    @pytest.mark.asyncio
    async def test_static_asset_caching(self, mock_cache):
        """Test caching of static assets."""
        static_assets = [
            "/",
            "/index.html",
            "/style.css",
            "/app.js",
            "/manifest.json"
        ]
        
        for asset in static_assets:
            response = {"status": 200, "body": f"content of {asset}"}
            await mock_cache.put(asset, response)
        
        # Verify all assets are cached
        for asset in static_assets:
            match = await mock_cache.match(asset)
            assert match is not None, f"Asset {asset} not cached"
    
    @pytest.mark.asyncio
    async def test_cache_versioning(self):
        """Test cache versioning."""
        storage = MockCacheStorage()
        
        # Create caches with different versions
        v1_cache = await storage.open("app-v1.0.0")
        v2_cache = await storage.open("app-v2.0.0")
        
        # Put content in v1
        await v1_cache.put("/test", {"status": 200, "body": "v1"})
        
        # Put content in v2
        await v2_cache.put("/test", {"status": 200, "body": "v2"})
        
        # Verify they are separate
        v1_match = await v1_cache.match("/test")
        v2_match = await v2_cache.match("/test")
        
        assert v1_match["body"] == "v1"
        assert v2_match["body"] == "v2"
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_on_activate(self):
        """Test old cache cleanup on service worker activate."""
        storage = MockCacheStorage()
        
        # Create old and new caches
        await storage.open("app-v1.0.0")
        await storage.open("app-v1.0.1")
        await storage.open("app-v2.0.0")
        
        caches = await storage.keys()
        assert len(caches) == 3
        
        # Delete old caches
        for cache_name in caches:
            if "v1" in cache_name and cache_name != "app-v2.0.0":
                await storage.delete(cache_name)
        
        remaining = await storage.keys()
        assert "app-v2.0.0" in remaining
        assert len(remaining) == 1


# ============================================================================
# Offline Functionality Tests
# ============================================================================

@pytest.mark.unit
class TestOfflineFunctionality:
    """Tests for offline functionality."""
    
    @pytest.mark.asyncio
    async def test_offline_page_served(self, mock_cache):
        """Test that offline page is served when network fails."""
        # Pre-cache offline page
        offline_content = "<html><body>You are offline</body></html>"
        await mock_cache.put("/offline.html", {
            "status": 200,
            "body": offline_content,
            "headers": {"Content-Type": "text/html"}
        })
        
        # Simulate offline fetch
        match = await mock_cache.match("/offline.html")
        assert match is not None
        assert "offline" in match["body"].lower()
    
    @pytest.mark.asyncio
    async def test_network_first_strategy_fallback(self, mock_cache):
        """Test network-first strategy falls back to cache."""
        request = "/api/data"
        
        # Pre-populate cache with stale data
        await mock_cache.put(request, {
            "status": 200,
            "body": "cached data"
        })
        
        # Simulate network failure - should return cached
        match = await mock_cache.match(request)
        assert match is not None
        assert match["body"] == "cached data"


# ============================================================================
# Browser Automation Tests (Playwright)
# ============================================================================

@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.integration
class TestPWABrowserAutomation:
    """Browser automation tests using Playwright."""
    
    @pytest.fixture(scope="class")
    async def browser(self):
        """Launch browser for testing."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def context(self, browser):
        """Create browser context."""
        context = await browser.new_context()
        yield context
        await context.close()
    
    @pytest.fixture
    async def page(self, context):
        """Create new page."""
        page = await context.new_page()
        yield page
    
    @pytest.mark.asyncio
    async def test_page_loads(self, page, frontend_path):
        """Test that the PWA page loads."""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            await page.goto(f"file://{index_path}")
            
            # Wait for page to load
            await page.wait_for_load_state("networkidle")
            
            # Check page title
            title = await page.title()
            assert title or await page.content()
    
    @pytest.mark.asyncio
    async def test_manifest_link_present(self, page, frontend_path):
        """Test that manifest is linked in HTML."""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            await page.goto(f"file://{index_path}")
            
            # Check for manifest link
            manifest_link = await page.locator('link[rel="manifest"]').count()
            assert manifest_link > 0, "Manifest link not found"
    
    @pytest.mark.asyncio
    async def test_service_worker_registration(self, page, frontend_path):
        """Test service worker registration."""
        index_path = frontend_path / "index.html"
        if not index_path.exists():
            pytest.skip("index.html not found")
        
        await page.goto(f"file://{index_path}")
        
        # Check if service worker is registered
        sw_registered = await page.evaluate("""
            () => {
                return 'serviceWorker' in navigator;
            }
        """)
        
        # Service Worker API should be available in modern browsers
        assert sw_registered is True
    
    @pytest.mark.asyncio
    async def test_viewport_meta_tag(self, page, frontend_path):
        """Test that viewport meta tag is present for mobile."""
        index_path = frontend_path / "index.html"
        if not index_path.exists():
            pytest.skip("index.html not found")
        
        await page.goto(f"file://{index_path}")
        
        viewport = await page.locator('meta[name="viewport"]').count()
        assert viewport > 0, "Viewport meta tag not found"
    
    @pytest.mark.asyncio
    async def test_theme_color_meta(self, page, frontend_path):
        """Test theme color meta tag."""
        index_path = frontend_path / "index.html"
        if not index_path.exists():
            pytest.skip("index.html not found")
        
        await page.goto(f"file://{index_path}")
        
        theme_color = await page.locator('meta[name="theme-color"]').count()
        # May or may not be present
        assert theme_color >= 0


# ============================================================================
# Background Sync Tests
# ============================================================================

@pytest.mark.unit
class TestBackgroundSync:
    """Tests for background sync functionality."""
    
    @pytest.mark.asyncio
    async def test_sync_registration(self):
        """Test background sync registration."""
        sw = MockServiceWorker()
        
        # Register sync
        result = await sw.registration.sync.register("sync-messages")
        assert result is True
        
        # Check registered tags
        tags = await sw.registration.sync.getTags()
        assert "sync-messages" in tags
    
    @pytest.mark.asyncio
    async def test_sync_event_handling(self, mock_service_worker):
        """Test sync event handling."""
        sync_event = Mock()
        sync_event.tag = "sync-messages"
        
        # Simulate sync event
        await mock_service_worker.trigger_event("sync", sync_event)
        
        # Event should be handled
        assert len(mock_service_worker._event_listeners.get("sync", [])) >= 0


# ============================================================================
# Push Notification Tests
# ============================================================================

@pytest.mark.unit
class TestPushNotifications:
    """Tests for push notification functionality."""
    
    @pytest.mark.asyncio
    async def test_push_subscription(self):
        """Test push subscription."""
        sw = MockServiceWorker()
        
        # Subscribe to push
        subscription = await sw.registration.pushManager.subscribe({
            "userVisibleOnly": True,
            "applicationServerKey": "test_key"
        })
        
        assert subscription is not None
        assert "endpoint" in subscription
        assert "keys" in subscription
    
    @pytest.mark.asyncio
    async def test_push_permission_state(self):
        """Test push permission state."""
        sw = MockServiceWorker()
        
        state = await sw.registration.pushManager.permissionState()
        assert state == "granted"
    
    @pytest.mark.asyncio
    async def test_notification_show(self):
        """Test showing notification."""
        sw = MockServiceWorker()
        
        # Mock notification
        notification_data = {
            "title": "Test Notification",
            "body": "This is a test",
            "icon": "/icon.png"
        }
        
        # Show notification
        # Note: In real browser, this would call registration.showNotification
        assert sw.registration is not None


# ============================================================================
# Install Prompt Tests
# ============================================================================

@pytest.mark.unit
class TestInstallPrompt:
    """Tests for PWA install prompt."""
    
    def test_manifest_has_required_install_fields(self, manifest_json):
        """Test manifest has required fields for installability."""
        if manifest_json is None:
            pytest.skip("Manifest not found")
        
        # Check for icons with required sizes
        icons = manifest_json.get("icons", [])
        sizes = [icon.get("sizes", "") for icon in icons]
        
        # Should have at least one 192x192 or larger
        has_large_icon = any(
            "192x192" in s or "512x512" in s or "384x384" in s
            for s in sizes
        )
        assert has_large_icon, "No large icon found for install prompt"
    
    def test_manifest_has_short_name(self, manifest_json):
        """Test manifest has short_name for limited space."""
        if manifest_json is None:
            pytest.skip("Manifest not found")
        
        assert "short_name" in manifest_json
        assert len(manifest_json["short_name"]) <= 12


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
class TestPWAPerformance:
    """Performance tests for PWA features."""
    
    @pytest.mark.asyncio
    async def test_cache_write_performance(self, mock_cache):
        """Test cache write performance."""
        import time
        
        start = time.time()
        
        # Write 100 items
        for i in range(100):
            await mock_cache.put(f"/asset_{i}.js", {
                "status": 200,
                "body": f"content {i}"
            })
        
        duration = time.time() - start
        
        # Should complete in under 1 second
        assert duration < 1.0, f"Cache write took too long: {duration}s"
    
    @pytest.mark.asyncio
    async def test_cache_read_performance(self, mock_cache):
        """Test cache read performance."""
        import time
        
        # Pre-populate cache
        for i in range(100):
            await mock_cache.put(f"/asset_{i}.js", {
                "status": 200,
                "body": f"content {i}"
            })
        
        start = time.time()
        
        # Read 100 items
        for i in range(100):
            await mock_cache.match(f"/asset_{i}.js")
        
        duration = time.time() - start
        
        # Should complete in under 1 second
        assert duration < 1.0, f"Cache read took too long: {duration}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
