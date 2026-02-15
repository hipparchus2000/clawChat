"""Unit tests for ClawChat WebSocket Server.

This module contains comprehensive unit tests for the WebSocket server
functionality including connection handling, message types, error cases,
ping/pong, echo functionality, and broadcast messages.

Run with: pytest tests/test_websocket.py -v
"""

import asyncio
import json
import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import websockets
from websockets.server import WebSocketServerProtocol

from server import ClawChatServer, ServerConfig, ConnectionInfo


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def server_config():
    """Create a test server configuration."""
    return ServerConfig(
        host="127.0.0.1",
        port=0,  # Random port
        max_connections=10,
        ping_interval=20.0,
        ping_timeout=10.0,
        close_timeout=10.0,
        log_level="DEBUG"
    )


@pytest.fixture
def test_server(server_config):
    """Create a test server instance."""
    return ClawChatServer(server_config)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket protocol."""
    ws = AsyncMock(spec=WebSocketServerProtocol)
    ws.remote_address = ("127.0.0.1", 12345)
    ws.close = AsyncMock()
    ws.send = AsyncMock()
    ws.__aiter__ = Mock(return_value=iter([]))
    return ws


@pytest.fixture
def mock_connection_info(mock_websocket):
    """Create a mock ConnectionInfo."""
    return ConnectionInfo(
        id="127.0.0.1:12345",
        websocket=mock_websocket
    )


# ============================================================================
# Server Configuration Tests
# ============================================================================

class TestServerConfig:
    """Tests for ServerConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8765
        assert config.max_connections == 100
        assert config.ping_interval == 20.0
        assert config.ping_timeout == 10.0
        assert config.close_timeout == 10.0
        assert config.log_level == "INFO"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ServerConfig(
            host="localhost",
            port=9999,
            max_connections=50,
            ping_interval=30.0,
            log_level="DEBUG"
        )
        assert config.host == "localhost"
        assert config.port == 9999
        assert config.max_connections == 50
        assert config.ping_interval == 30.0
        assert config.log_level == "DEBUG"
    
    def test_config_from_yaml(self, tmp_path):
        """Test loading configuration from YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
server:
  host: "192.168.1.1"
  port: 8080
  max_connections: 200
keepalive:
  ping_interval: 15.0
  ping_timeout: 5.0
logging:
  level: "WARNING"
""")
        
        config = ServerConfig.from_yaml(str(config_file))
        assert config.host == "192.168.1.1"
        assert config.port == 8080
        assert config.max_connections == 200
        assert config.ping_interval == 15.0
        assert config.ping_timeout == 5.0
        assert config.log_level == "WARNING"
    
    def test_config_from_missing_yaml(self):
        """Test loading from non-existent YAML returns defaults."""
        config = ServerConfig.from_yaml("/nonexistent/config.yaml")
        assert config.host == "0.0.0.0"
        assert config.port == 8765


# ============================================================================
# Server Initialization Tests
# ============================================================================

class TestServerInitialization:
    """Tests for server initialization."""
    
    def test_server_creation(self, server_config):
        """Test server can be created with config."""
        server = ClawChatServer(server_config)
        assert server.config == server_config
        assert server.connections == {}
        assert server.server is None
    
    def test_server_has_logger(self, test_server):
        """Test server has a logger instance."""
        assert test_server.logger is not None


# ============================================================================
# Connection Management Tests
# ============================================================================

class TestConnectionManagement:
    """Tests for connection handling."""
    
    @pytest.mark.asyncio
    async def test_add_connection(self, test_server, mock_websocket):
        """Test adding a new connection."""
        conn_id = "127.0.0.1:12345"
        conn_info = ConnectionInfo(id=conn_id, websocket=mock_websocket)
        
        test_server.connections[conn_id] = conn_info
        
        assert conn_id in test_server.connections
        assert test_server.connections[conn_id] == conn_info
    
    @pytest.mark.asyncio
    async def test_cleanup_connection(self, test_server, mock_websocket):
        """Test connection cleanup."""
        conn_id = "127.0.0.1:12345"
        conn_info = ConnectionInfo(id=conn_id, websocket=mock_websocket)
        
        test_server.connections[conn_id] = conn_info
        await test_server._cleanup_connection(conn_id)
        
        assert conn_id not in test_server.connections
    
    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_connection(self, test_server):
        """Test cleanup of non-existent connection doesn't error."""
        await test_server._cleanup_connection("nonexistent")
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_connection_limit_check(self, test_server):
        """Test connection limit enforcement."""
        # Fill up to max connections
        for i in range(test_server.config.max_connections):
            mock_ws = AsyncMock(spec=WebSocketServerProtocol)
            mock_ws.remote_address = ("127.0.0.1", 50000 + i)
            conn_id = f"127.0.0.1:{50000 + i}"
            test_server.connections[conn_id] = ConnectionInfo(
                id=conn_id, websocket=mock_ws
            )
        
        # Try to add one more
        result = await test_server._process_request("/", {})
        
        assert result is not None
        assert result[0] == 503  # Service Unavailable
    
    @pytest.mark.asyncio
    async def test_no_connection_limit(self):
        """Test with unlimited connections (max_connections = 0)."""
        config = ServerConfig(max_connections=0)
        server = ClawChatServer(config)
        
        result = await server._process_request("/", {})
        assert result is None  # Should accept
    
    @pytest.mark.asyncio
    async def test_close_connection(self, test_server, mock_connection_info):
        """Test closing a connection gracefully."""
        await test_server._close_connection(mock_connection_info, "Test reason")
        
        mock_connection_info.websocket.close.assert_called_once_with(
            code=1001, reason="Test reason"
        )
    
    @pytest.mark.asyncio
    async def test_close_connection_error_handling(self, test_server, mock_connection_info):
        """Test close handles errors gracefully."""
        mock_connection_info.websocket.close.side_effect = Exception("Already closed")
        
        # Should not raise
        await test_server._close_connection(mock_connection_info, "Test reason")


# ============================================================================
# Message Handling Tests
# ============================================================================

class TestMessageHandling:
    """Tests for message processing."""
    
    @pytest.mark.asyncio
    async def test_handle_echo_message(self, test_server, mock_connection_info):
        """Test echo message handling."""
        data = {"type": "echo", "data": "Hello World"}
        message = json.dumps(data)
        
        await test_server._handle_message(mock_connection_info, message)
        
        # Check that send was called
        mock_connection_info.websocket.send.assert_called()
        sent_message = json.loads(mock_connection_info.websocket.send.call_args[0][0])
        assert sent_message["type"] == "echo"
        assert sent_message["data"] == "Hello World"
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, test_server, mock_connection_info):
        """Test ping message handling."""
        data = {"type": "ping", "data": {"timestamp": time.time()}}
        message = json.dumps(data)
        
        await test_server._handle_message(mock_connection_info, message)
        
        mock_connection_info.websocket.send.assert_called()
        sent_message = json.loads(mock_connection_info.websocket.send.call_args[0][0])
        assert sent_message["type"] == "pong"
        assert "timestamp" in sent_message
    
    @pytest.mark.asyncio
    async def test_handle_broadcast_message(self, test_server, mock_websocket):
        """Test broadcast message handling."""
        # Create sender
        sender_ws = AsyncMock(spec=WebSocketServerProtocol)
        sender_ws.remote_address = ("127.0.0.1", 11111)
        sender = ConnectionInfo(id="127.0.0.1:11111", websocket=sender_ws)
        
        # Create receivers
        receiver1_ws = AsyncMock(spec=WebSocketServerProtocol)
        receiver1_ws.remote_address = ("127.0.0.1", 22222)
        receiver1 = ConnectionInfo(id="127.0.0.1:22222", websocket=receiver1_ws)
        
        receiver2_ws = AsyncMock(spec=WebSocketServerProtocol)
        receiver2_ws.remote_address = ("127.0.0.1", 33333)
        receiver2 = ConnectionInfo(id="127.0.0.1:33333", websocket=receiver2_ws)
        
        # Add to server
        test_server.connections[sender.id] = sender
        test_server.connections[receiver1.id] = receiver1
        test_server.connections[receiver2.id] = receiver2
        
        # Send broadcast
        data = {"type": "broadcast", "data": "Hello everyone!"}
        await test_server._handle_broadcast(sender, data)
        
        # Check receivers got the message
        assert receiver1_ws.send.called
        assert receiver2_ws.send.called
        
        # Check sender got confirmation
        assert sender_ws.send.called
        sent_to_sender = json.loads(sender_ws.send.call_args[0][0])
        assert sent_to_sender["type"] == "broadcast_confirm"
        assert sent_to_sender["recipients"] == 2
    
    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, test_server, mock_connection_info):
        """Test handling of unknown message type."""
        data = {"type": "unknown_type", "data": "test"}
        message = json.dumps(data)
        
        await test_server._handle_message(mock_connection_info, message)
        
        mock_connection_info.websocket.send.assert_called()
        sent_message = json.loads(mock_connection_info.websocket.send.call_args[0][0])
        assert sent_message["type"] == "error"
        assert "unknown" in sent_message["message"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_non_json_message(self, test_server, mock_connection_info):
        """Test handling of non-JSON messages."""
        message = "Plain text message"
        
        await test_server._handle_message(mock_connection_info, message)
        
        mock_connection_info.websocket.send.assert_called()
        sent_message = json.loads(mock_connection_info.websocket.send.call_args[0][0])
        assert sent_message["type"] == "echo"
        assert sent_message["data"] == message
        assert sent_message["format"] == "text"
    
    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, test_server, mock_connection_info):
        """Test handling of invalid JSON."""
        message = "{invalid json"
        
        await test_server._handle_message(mock_connection_info, message)
        
        # Should echo as text
        mock_connection_info.websocket.send.assert_called()
        sent_message = json.loads(mock_connection_info.websocket.send.call_args[0][0])
        assert sent_message["type"] == "echo"


# ============================================================================
# Message Sending Tests
# ============================================================================

class TestMessageSending:
    """Tests for sending messages to clients."""
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, test_server, mock_connection_info):
        """Test successful message sending."""
        data = {"type": "test", "message": "Hello"}
        
        result = await test_server._send_message(mock_connection_info, data)
        
        assert result is True
        mock_connection_info.websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_closed_connection(self, test_server, mock_connection_info):
        """Test sending to closed connection."""
        mock_connection_info.websocket.send.side_effect = \
            websockets.exceptions.ConnectionClosed(1000, "Closed")
        
        result = await test_server._send_message(mock_connection_info, {"type": "test"})
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_other_error(self, test_server, mock_connection_info):
        """Test handling of other send errors."""
        mock_connection_info.websocket.send.side_effect = Exception("Network error")
        
        result = await test_server._send_message(mock_connection_info, {"type": "test"})
        
        assert result is False


# ============================================================================
# Server Statistics Tests
# ============================================================================

class TestServerStatistics:
    """Tests for server statistics."""
    
    def test_get_stats_empty(self, test_server):
        """Test stats with no connections."""
        stats = test_server.get_stats()
        
        assert stats["connections"]["active"] == 0
        assert stats["connections"]["max"] == test_server.config.max_connections
        assert stats["clients"] == []
    
    def test_get_stats_with_connections(self, test_server):
        """Test stats with active connections."""
        # Add mock connections
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocketServerProtocol)
            mock_ws.remote_address = ("127.0.0.1", 50000 + i)
            conn_id = f"127.0.0.1:{50000 + i}"
            test_server.connections[conn_id] = ConnectionInfo(
                id=conn_id,
                websocket=mock_ws,
                message_count=i * 5
            )
        
        stats = test_server.get_stats()
        
        assert stats["connections"]["active"] == 3
        assert len(stats["clients"]) == 3
        assert stats["clients"][0]["message_count"] == 0
        assert stats["clients"][1]["message_count"] == 5
        assert stats["clients"][2]["message_count"] == 10


# ============================================================================
# Connection Handling Tests
# ============================================================================

class TestConnectionHandling:
    """Tests for the main connection handler."""
    
    @pytest.mark.asyncio
    async def test_connection_welcome_message(self, test_server, mock_websocket):
        """Test that new connections receive welcome message."""
        # Mock the message iterator
        mock_websocket.__aiter__ = Mock(return_value=iter([]))
        
        # Run connection handler
        await test_server._handle_connection(mock_websocket, "/")
        
        # Check welcome message was sent
        mock_websocket.send.assert_called()
        calls = mock_websocket.send.call_args_list
        
        # First call should be welcome
        welcome_msg = json.loads(calls[0][0][0])
        assert welcome_msg["type"] == "welcome"
        assert "connection_id" in welcome_msg
    
    @pytest.mark.asyncio
    async def test_connection_message_processing(self, test_server, mock_websocket):
        """Test that messages are processed during connection."""
        messages = [
            json.dumps({"type": "echo", "data": "msg1"}),
            json.dumps({"type": "echo", "data": "msg2"}),
        ]
        
        mock_websocket.__aiter__ = Mock(return_value=iter(messages))
        
        await test_server._handle_connection(mock_websocket, "/")
        
        # Should have sent welcome + 2 echo responses
        assert mock_websocket.send.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_connection_graceful_close(self, test_server, mock_websocket):
        """Test handling of graceful connection close."""
        from websockets.exceptions import ConnectionClosedOK
        
        # Make iterator raise ConnectionClosedOK
        async def async_iter():
            raise ConnectionClosedOK(1000, "Normal closure")
            yield  # Make it an async generator
        
        mock_websocket.__aiter__ = async_iter
        
        # Should not raise
        await test_server._handle_connection(mock_websocket, "/")
    
    @pytest.mark.asyncio
    async def test_connection_error_close(self, test_server, mock_websocket):
        """Test handling of connection close with error."""
        from websockets.exceptions import ConnectionClosedError
        
        async def async_iter():
            raise ConnectionClosedError(1006, "Abnormal closure")
            yield
        
        mock_websocket.__aiter__ = async_iter
        
        # Should not raise
        await test_server._handle_connection(mock_websocket, "/")


# ============================================================================
# Server Lifecycle Tests
# ============================================================================

class TestServerLifecycle:
    """Tests for server start/stop lifecycle."""
    
    @pytest.mark.asyncio
    @patch('server.websockets.serve')
    async def test_server_start(self, mock_serve, test_server):
        """Test server start."""
        mock_server = AsyncMock()
        mock_serve.return_value = mock_server
        
        # Create task to start server
        start_task = asyncio.create_task(test_server.start())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Trigger shutdown
        await test_server.stop()
        
        # Wait for start to complete
        try:
            await asyncio.wait_for(start_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass
        
        mock_serve.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_server_stop_closes_connections(self, test_server):
        """Test that stop closes all connections."""
        # Add mock connections
        connections = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocketServerProtocol)
            mock_ws.remote_address = ("127.0.0.1", 50000 + i)
            conn_id = f"127.0.0.1:{50000 + i}"
            conn_info = ConnectionInfo(id=conn_id, websocket=mock_ws)
            test_server.connections[conn_id] = conn_info
            connections.append(mock_ws)
        
        test_server.server = AsyncMock()
        
        await test_server.stop()
        
        # Check all connections were closed
        for conn in connections:
            conn.close.assert_called()


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_message_processing_error(self, test_server, mock_connection_info):
        """Test handling of errors during message processing."""
        # Send invalid JSON that triggers an exception
        message = "{\"type\": \"echo",  # Incomplete JSON
        
        # Should not raise, should echo as text
        await test_server._handle_message(mock_connection_info, message)
        
        mock_connection_info.websocket.send.assert_called()
    
    @pytest.mark.asyncio
    async def test_broadcast_with_closed_connection(self, test_server):
        """Test broadcast when some connections are closed."""
        import websockets
        
        # Create sender
        sender_ws = AsyncMock(spec=WebSocketServerProtocol)
        sender_ws.remote_address = ("127.0.0.1", 11111)
        sender = ConnectionInfo(id="127.0.0.1:11111", websocket=sender_ws)
        
        # Create receiver that will fail
        receiver_ws = AsyncMock(spec=WebSocketServerProtocol)
        receiver_ws.remote_address = ("127.0.0.1", 22222)
        receiver_ws.send.side_effect = websockets.exceptions.ConnectionClosed(1000, "Closed")
        receiver = ConnectionInfo(id="127.0.0.1:22222", websocket=receiver_ws)
        
        test_server.connections[sender.id] = sender
        test_server.connections[receiver.id] = receiver
        
        # Should not raise despite closed connection
        data = {"type": "broadcast", "data": "test"}
        await test_server._handle_broadcast(sender, data)
    
    @pytest.mark.asyncio
    async def test_message_handler_exception(self, test_server, mock_connection_info):
        """Test general exception handling in message handler."""
        # Create a message that will cause an issue
        message = "{\"type\": 123}"  # type is int, not string
        
        # Should handle gracefully
        await test_server._handle_message(mock_connection_info, message)
        
        # Should send an error response
        mock_connection_info.websocket.send.assert_called()


# ============================================================================
# Async Testing Best Practices Examples
# ============================================================================

class TestAsyncPatterns:
    """Examples of async testing patterns."""
    
    @pytest.mark.asyncio
    async def test_async_timeout(self, test_server):
        """Test using asyncio timeout."""
        async def slow_operation():
            await asyncio.sleep(10)
            return True
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.01)
    
    @pytest.mark.asyncio
    async def test_async_gather(self, test_server):
        """Test using asyncio.gather for concurrent operations."""
        async def task(n):
            await asyncio.sleep(0.01)
            return n * 2
        
        results = await asyncio.gather(
            task(1), task(2), task(3)
        )
        
        assert results == [2, 4, 6]
    
    @pytest.mark.asyncio
    async def test_async_event(self, test_server):
        """Test using asyncio.Event."""
        event = asyncio.Event()
        
        async def waiter():
            await asyncio.wait_for(event.wait(), timeout=0.5)
            return True
        
        async def setter():
            await asyncio.sleep(0.01)
            event.set()
        
        results = await asyncio.gather(waiter(), setter())
        assert results[0] is True


# ============================================================================
# Integration Preparation Tests
# ============================================================================

class TestIntegrationPreparation:
    """Tests to verify the server is ready for integration tests."""
    
    def test_server_imports(self):
        """Test that server module imports correctly."""
        from server import ClawChatServer, ServerConfig, ConnectionInfo
        assert ClawChatServer is not None
        assert ServerConfig is not None
        assert ConnectionInfo is not None
    
    def test_config_immutable(self, server_config):
        """Test that config dataclass works correctly."""
        original_port = server_config.port
        
        # Config should be modifiable
        server_config.port = 9999
        assert server_config.port == 9999
        assert original_port != server_config.port
    
    @pytest.mark.asyncio
    async def test_connection_info_tracking(self):
        """Test that ConnectionInfo tracks message counts."""
        mock_ws = AsyncMock(spec=WebSocketServerProtocol)
        mock_ws.remote_address = ("127.0.0.1", 12345)
        
        conn = ConnectionInfo(id="test", websocket=mock_ws)
        
        assert conn.message_count == 0
        
        conn.message_count += 1
        assert conn.message_count == 1
        
        conn.message_count += 5
        assert conn.message_count == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
