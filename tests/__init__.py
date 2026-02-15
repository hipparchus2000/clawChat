"""ClawChat Test Suite.

This package contains comprehensive tests for the ClawChat WebSocket
server and client implementation.

Modules:
    test_websocket: Unit tests for WebSocket server functionality
    test_integration: Integration tests for client-server communication
    mock_mega: Mock Mega.nz API for testing file operations

Usage:
    Run all tests:
        pytest tests/

    Run with coverage:
        pytest tests/ --cov=backend --cov-report=html

    Run specific test file:
        pytest tests/test_websocket.py -v

    Use the test runner script:
        ./run_tests.sh
"""

__version__ = "1.0.0"
__all__ = ["mock_mega"]
