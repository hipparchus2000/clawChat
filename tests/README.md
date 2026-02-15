# ClawChat Testing Framework

This directory contains comprehensive tests for the ClawChat WebSocket server, File API, Chat functionality, and PWA features.

## Test Files

### Phase 1: Core WebSocket

#### 1. `test_websocket.py` - Unit Tests
Unit tests for the WebSocket server functionality:

- **Server Configuration Tests**: Config loading, defaults, YAML parsing
- **Connection Management Tests**: Connection limits, cleanup, adding/removing clients
- **Message Handling Tests**: Echo, ping/pong, broadcast, unknown types
- **Message Sending Tests**: Success/failure scenarios, closed connections
- **Server Statistics Tests**: Stats reporting, connection tracking
- **Connection Handling Tests**: Welcome messages, graceful/error closes
- **Server Lifecycle Tests**: Start/stop, signal handling
- **Error Handling Tests**: Malformed data, exceptions, edge cases

**Key Features:**
- Comprehensive mocking of WebSocket protocol
- Async test patterns with pytest-asyncio
- Connection limit enforcement testing
- Error scenario coverage

#### 2. `test_integration.py` - Integration Tests
Full client-server integration tests:

- **Connection Tests**: Basic connections, multiple clients, connection limits
- **Message Exchange Tests**: Echo, ping/pong, JSON/text messages
- **Broadcast Tests**: Multi-client broadcasts, confirmation messages
- **Error Handling Tests**: Unknown types, malformed JSON, abrupt disconnects
- **Concurrent Operations Tests**: Parallel message handling, stress tests
- **Server Statistics Tests**: Real-time stats verification
- **Performance Tests**: Latency and throughput measurement
- **Edge Case Tests**: Unicode, nested JSON, null values, large messages
- **Real Client Simulation**: Chat scenarios, reconnection testing

**Key Features:**
- Real WebSocket connections (not mocked)
- Actual server startup/shutdown per test
- Concurrent client testing
- Performance benchmarks

### Phase 2: File Operations, Chat & PWA

#### 3. `test_file_operations.py` - File System API Tests
Comprehensive tests for file operations (Phase 2 Feature 1, 4, 5, 6):

- **File Metadata Tests**: Get file/directory metadata, error handling
- **Directory Listing Tests**: List contents, filtering, pagination
- **File Download Tests**: Full/range downloads, permission checks
- **Path Traversal Security Tests**: Double-dot, URL encoding, null byte injection
- **Permission Security Tests**: Rate limiting, auth token validation
- **WebSocket Integration Tests**: File operations via WebSocket
- **Performance Tests**: Large directory listing, file chunk reading, concurrent access
- **Edge Case Tests**: Empty paths, unicode, symlinks, binary files
- **Data Model Tests**: FileMetadata, DirectoryListing, APIResponse validation

**Coverage:**
- `backend/file_api.py` - Main file API module
- `backend/path_validator.py` - Path validation and security
- `backend/security.py` - Permission and authentication

#### 4. `test_chat.py` - Chat Functionality Tests
Tests for chat features (Phase 2 Feature 2, 7):

- **Message Sending Tests**: Text, unicode, long, multiline messages
- **Mock WebSocket Server**: Full mock server for isolated testing
- **Presence Tests**: Online/offline tracking, status updates
- **Typing Indicators**: Start/stop typing broadcasts
- **Message History**: Storage and retrieval
- **Concurrent Operations**: Simultaneous messages, rapid connect/disconnect
- **Error Handling**: Disconnected clients, invalid formats
- **Message Types**: Text, system, direct messages
- **Real Server Integration**: Tests with actual WebSocket server

**Key Features:**
- MockWebSocketServer for isolated testing
- MockClient for simulating users
- Presence and typing indicator simulation
- Message history verification
- Stress testing with 100+ concurrent messages

#### 5. `test_pwa.py` - Progressive Web App Tests
Tests for PWA features (Phase 2 Feature 3, 8):

- **Service Worker Tests**: Event handlers, cache version, static assets
- **Caching Strategy Tests**: Cache-first, network-first, stale-while-revalidate
- **Offline Functionality Tests**: Offline page serving, fallback behavior
- **Browser Automation Tests** (Playwright): Page loading, manifest validation
- **Background Sync Tests**: Sync registration, event handling
- **Push Notification Tests**: Subscription, permission state
- **Install Prompt Tests**: Manifest validation, icon requirements
- **Performance Tests**: Cache read/write performance

**Coverage:**
- `frontend/service-worker.js` - Service worker implementation
- `frontend/pwa-manager.js` - PWA manager class
- `frontend/manifest.json` - PWA manifest

### Supporting Files

#### `mock_mega.py` - Mock Mega.nz Service
Mock implementation of Mega.nz API for testing:

- **File Operations**: Upload, download, delete
- **Folder Operations**: Create, list, navigate
- **JSON Support**: Automatic JSON serialization/deserialization
- **Storage Quota**: Configurable limits
- **Error Simulation**: Configurable failure modes
- **Async Wrapper**: Async-compatible API

## Running Tests

### Using the Test Runner Script

```bash
# Run all tests with coverage
./run_tests.sh

# Run only unit tests
./run_tests.sh unit

# Run only integration tests
./run_tests.sh integration

# Run Phase 2 tests only
./run_tests.sh phase2

# Run security tests only
./run_tests.sh security

# Run performance tests only
./run_tests.sh performance

# Quick run without coverage
./run_tests.sh quick

# Verbose output
./run_tests.sh verbose

# CI mode (strict, fail-fast)
./run_tests.sh ci
```

### Using pytest directly

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=backend --cov-report=html --cov-report=term

# Run only unit tests
pytest tests/test_websocket.py -v

# Run Phase 2 file operations tests
pytest tests/test_file_operations.py -v

# Run chat tests
pytest tests/test_chat.py -v

# Run PWA tests
pytest tests/test_pwa.py -v

# Run security tests
pytest tests/test_file_operations.py -k "security or traversal" -v

# Run with specific markers
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "performance"

# Run with timeout
pytest tests/ --timeout=60
```

## Test Configuration

### pytest.ini
Configuration file with:
- Default test paths
- Async mode settings
- Custom markers (unit, integration, slow, performance, security)
- Coverage settings (80% minimum)
- Warning filters

### conftest.py
Shared fixtures:
- `event_loop`: Session-scoped event loop
- `temp_config_file`: Temporary YAML configuration

## Test Markers

- `@pytest.mark.unit`: Unit tests (fast, isolated)
- `@pytest.mark.integration`: Integration tests (requires server)
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.performance`: Performance benchmarks
- `@pytest.mark.security`: Security-related tests

## Coverage Reports

After running tests with coverage:

```
htmlcov/
├── index.html           # HTML coverage report
└── ...
coverage.xml             # XML report for CI integration
```

Open `htmlcov/index.html` in a browser for detailed coverage analysis.

**Coverage Requirements:**
- Minimum 80% code coverage
- All critical paths must be covered
- Security checks must have 100% coverage

## CI/CD Integration

### GitHub Actions
The `.github/workflows/tests.yml` file provides:
- Unit tests on every push/PR
- Integration tests
- Security tests with bandit
- PWA tests with Playwright
- Performance tests (scheduled)
- Coverage reporting with Codecov
- Code quality checks (black, flake8, mypy)

### Running in CI Mode
```bash
./run_tests.sh ci
```

This mode:
- Fails on coverage below 80%
- Stops on first failure
- Generates XML reports
- Uses shorter traceback formatting
- Enforces strict test isolation

## Best Practices

### Writing Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### Using Fixtures

```python
@pytest.fixture
def temp_root_dir():
    """Create a temporary root directory."""
    temp_dir = tempfile.mkdtemp(prefix="clawchat_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
```

### Testing Security

```python
@pytest.mark.asyncio
async def test_path_traversal_blocked(file_service):
    """Test that path traversal is blocked."""
    context = SecurityContext(permissions={PermissionLevel.ADMIN})
    response = await file_service.get_file_metadata("../etc/passwd", context)
    assert response.success is False
    assert response.error_code == ERROR_CODES['DIRECTORY_TRAVERSAL']
```

### Mocking WebSocket

```python
class MockWebSocketServer:
    """Mock server for testing."""
    def __init__(self):
        self.clients = {}
        self.messages = []
    
    async def broadcast(self, message):
        for client in self.clients.values():
            await client.receive(message)
```

## Troubleshooting

### Connection Refused Errors
Integration tests need the server port to be available. If tests fail with connection errors:
- Check if port is in use: `lsof -i :8765`
- Tests use random ports (port 0) to avoid conflicts

### Async Test Failures
Ensure pytest-asyncio is installed and configured:
```bash
pip install pytest-asyncio
```

### Coverage Not Working
Install pytest-cov:
```bash
pip install pytest-cov
```

### Playwright Not Found
Install Playwright for PWA tests:
```bash
pip install pytest-playwright playwright
python -m playwright install chromium
```

### Permission Denied Errors
Ensure test directories are writable:
```bash
chmod -R +w /path/to/test/dir
```

## Phase 2 Test Summary

| Feature | Test File | Coverage |
|---------|-----------|----------|
| File Operations (upload, delete, create, rename, move) | test_file_operations.py | >85% |
| Chat (messages, presence, typing) | test_chat.py | >80% |
| PWA Service Worker | test_pwa.py | >75% |
| File Upload/Download Integration | test_file_operations.py | >85% |
| Security (permissions, path traversal) | test_file_operations.py | >90% |
| Performance (large files) | test_file_operations.py | >80% |
| Mock WebSocket Server | test_chat.py | N/A |
| Browser Automation (PWA) | test_pwa.py | >70% |

## Adding New Tests

1. Choose the appropriate test file based on feature
2. Create a test class with descriptive name
3. Add async test methods with proper fixtures
4. Include both positive and negative test cases
5. Add security tests for any new endpoints
6. Document the test with docstrings
7. Run tests and verify coverage

Example:
```python
@pytest.mark.unit
class TestNewFeature:
    """Tests for new feature X."""
    
    @pytest.mark.asyncio
    async def test_success_case(self, fixture):
        """Test successful operation."""
        result = await operation()
        assert result.success is True
    
    @pytest.mark.asyncio  
    async def test_error_case(self, fixture):
        """Test error handling."""
        result = await operation(invalid_input)
        assert result.success is False
```

## Dependencies

See `requirements.txt` for complete list. Key dependencies:
- pytest: Testing framework
- pytest-asyncio: Async test support
- pytest-cov: Coverage reporting
- pytest-playwright: Browser automation
- websockets: WebSocket client for testing
- pyyaml: Configuration file parsing
- aiofiles: Async file operations
