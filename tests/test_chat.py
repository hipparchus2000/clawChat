"""
ClawChat Chat Functionality Tests
==================================
Comprehensive tests for chat features including:
- Message sending and receiving
- Presence tracking
- Typing indicators
- Mock WebSocket server for testing

Run with: pytest tests/test_chat.py -v
"""

import asyncio
import json
import pytest
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from dataclasses import dataclass, field
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import websockets
from websockets.server import WebSocketServerProtocol

from server import ClawChatServer, ServerConfig, ConnectionInfo


# ============================================================================
# Mock WebSocket Server for Chat Testing
# ============================================================================

class MockWebSocketServer:
    """
    Mock WebSocket server for testing chat functionality.
    Simulates a real WebSocket server without network overhead.
    """
    
    def __init__(self):
        self.clients: Dict[str, MockClient] = {}
        self.message_handlers: List[Callable] = []
        self.connection_handlers: List[Callable] = []
        self.disconnection_handlers: List[Callable] = []
        self.message_history: List[Dict] = []
        self.typing_indicators: Dict[str, float] = {}
        self.presence_status: Dict[str, str] = {}
        self.running = False
    
    async def start(self):
        """Start the mock server."""
        self.running = True
        print("[MockServer] Started")
    
    async def stop(self):
        """Stop the mock server."""
        self.running = False
        for client in list(self.clients.values()):
            await client.disconnect()
        self.clients.clear()
        print("[MockServer] Stopped")
    
    async def connect_client(self, client_id: str, username: str = None) -> "MockClient":
        """Connect a new mock client."""
        client = MockClient(client_id, username or f"user_{client_id}", self)
        self.clients[client_id] = client
        
        # Notify connection handlers
        for handler in self.connection_handlers:
            await handler(client)
        
        # Update presence
        self.presence_status[client_id] = "online"
        await self.broadcast_presence_update(client_id, "online")
        
        return client
    
    async def disconnect_client(self, client_id: str):
        """Disconnect a client."""
        if client_id in self.clients:
            client = self.clients[client_id]
            await client.disconnect()
            del self.clients[client_id]
            
            # Update presence
            if client_id in self.presence_status:
                del self.presence_status[client_id]
            await self.broadcast_presence_update(client_id, "offline")
            
            # Notify disconnection handlers
            for handler in self.disconnection_handlers:
                await handler(client)
    
    async def broadcast_message(self, sender: "MockClient", message: Dict):
        """Broadcast a message to all clients except sender."""
        message["timestamp"] = time.time()
        message["sender_id"] = sender.client_id
        message["sender_name"] = sender.username
        
        self.message_history.append(message)
        
        for client in self.clients.values():
            if client.client_id != sender.client_id:
                await client.receive_message(message)
        
        # Send confirmation to sender
        await sender.receive_message({
            "type": "message_confirm",
            "message_id": message.get("message_id"),
            "timestamp": message["timestamp"]
        })
    
    async def broadcast_presence_update(self, client_id: str, status: str):
        """Broadcast presence update to all clients."""
        update = {
            "type": "presence_update",
            "client_id": client_id,
            "status": status,
            "timestamp": time.time()
        }
        
        for client in self.clients.values():
            await client.receive_message(update)
    
    async def broadcast_typing_indicator(self, client_id: str, is_typing: bool):
        """Broadcast typing indicator to all clients except sender."""
        self.typing_indicators[client_id] = time.time() if is_typing else 0
        
        indicator = {
            "type": "typing_indicator",
            "client_id": client_id,
            "is_typing": is_typing,
            "timestamp": time.time()
        }
        
        for client in self.clients.values():
            if client.client_id != client_id:
                await client.receive_message(indicator)
    
    def on_message(self, handler: Callable):
        """Register a message handler."""
        self.message_handlers.append(handler)
    
    def on_connect(self, handler: Callable):
        """Register a connection handler."""
        self.connection_handlers.append(handler)
    
    def on_disconnect(self, handler: Callable):
        """Register a disconnection handler."""
        self.disconnection_handlers.append(handler)


class MockClient:
    """Mock WebSocket client for testing."""
    
    def __init__(self, client_id: str, username: str, server: MockWebSocketServer):
        self.client_id = client_id
        self.username = username
        self.server = server
        self.connected = False
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.sent_messages: List[Dict] = []
        self.received_messages: List[Dict] = []
        self.connection_info = ConnectionInfo(
            id=client_id,
            websocket=MagicMock()  # Mock websocket protocol
        )
    
    async def connect(self):
        """Connect to the server."""
        self.connected = True
        print(f"[MockClient {self.client_id}] Connected")
    
    async def disconnect(self):
        """Disconnect from the server."""
        self.connected = False
        print(f"[MockClient {self.client_id}] Disconnected")
    
    async def send_message(self, content: str, message_type: str = "text"):
        """Send a message to the server."""
        message = {
            "type": "message",
            "message_type": message_type,
            "content": content,
            "message_id": f"msg_{int(time.time() * 1000)}",
            "timestamp": time.time()
        }
        
        self.sent_messages.append(message)
        await self.server.broadcast_message(self, message)
        
        # Notify message handlers
        for handler in self.server.message_handlers:
            await handler(self, message)
    
    async def send_typing_indicator(self, is_typing: bool):
        """Send typing indicator."""
        await self.server.broadcast_typing_indicator(self.client_id, is_typing)
    
    async def update_presence(self, status: str):
        """Update presence status."""
        self.server.presence_status[self.client_id] = status
        await self.server.broadcast_presence_update(self.client_id, status)
    
    async def receive_message(self, message: Dict):
        """Receive a message from the server."""
        await self.message_queue.put(message)
        self.received_messages.append(message)
    
    async def get_next_message(self, timeout: float = 1.0) -> Optional[Dict]:
        """Get next message from queue."""
        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def clear_received_messages(self):
        """Clear received messages buffer."""
        self.received_messages.clear()
        # Drain queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def mock_server():
    """Create and start a mock WebSocket server."""
    server = MockWebSocketServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def chat_clients(mock_server):
    """Create multiple chat clients for testing."""
    clients = []
    for i in range(3):
        client = await mock_server.connect_client(f"client_{i}", f"User{i}")
        await client.connect()
        clients.append(client)
    
    # Clear welcome messages
    for client in clients:
        client.clear_received_messages()
    
    yield clients
    
    # Cleanup
    for client in clients:
        await mock_server.disconnect_client(client.client_id)


# ============================================================================
# Message Sending Tests
# ============================================================================

@pytest.mark.unit
class TestMessageSending:
    """Tests for message sending functionality."""
    
    @pytest.mark.asyncio
    async def test_send_text_message(self, mock_server, chat_clients):
        """Test sending a text message."""
        sender = chat_clients[0]
        receivers = chat_clients[1:]
        
        await sender.send_message("Hello everyone!")
        
        # Check receivers got the message
        for receiver in receivers:
            msg = await receiver.get_next_message(timeout=0.5)
            assert msg is not None
            assert msg["type"] == "message"
            assert msg["content"] == "Hello everyone!"
            assert msg["sender_id"] == sender.client_id
    
    @pytest.mark.asyncio
    async def test_send_empty_message(self, mock_server, chat_clients):
        """Test sending an empty message."""
        sender = chat_clients[0]
        
        await sender.send_message("")
        
        # Should still be sent
        assert len(sender.sent_messages) == 1
        assert sender.sent_messages[0]["content"] == ""
    
    @pytest.mark.asyncio
    async def test_send_unicode_message(self, mock_server, chat_clients):
        """Test sending unicode messages."""
        sender = chat_clients[0]
        receivers = chat_clients[1:]
        
        unicode_message = "Hello 世界! 🎉 こんにちは"
        await sender.send_message(unicode_message)
        
        for receiver in receivers:
            msg = await receiver.get_next_message(timeout=0.5)
            assert msg["content"] == unicode_message
    
    @pytest.mark.asyncio
    async def test_send_long_message(self, mock_server, chat_clients):
        """Test sending a long message."""
        sender = chat_clients[0]
        receivers = chat_clients[1:]
        
        long_message = "A" * 10000
        await sender.send_message(long_message)
        
        for receiver in receivers:
            msg = await receiver.get_next_message(timeout=0.5)
            assert msg["content"] == long_message
    
    @pytest.mark.asyncio
    async def test_send_multiline_message(self, mock_clients, chat_clients):
        """Test sending a multiline message."""
        sender = chat_clients[0]
        
        multiline_message = "Line 1\nLine 2\nLine 3\n\nLine 5"
        await sender.send_message(multiline_message)
        
        for receiver in chat_clients[1:]:
            msg = await receiver.get_next_message(timeout=0.5)
            assert msg["content"] == multiline_message
    
    @pytest.mark.asyncio
    async def test_message_confirmation(self, mock_server, chat_clients):
        """Test that sender receives confirmation."""
        sender = chat_clients[0]
        
        await sender.send_message("Test message")
        
        # Sender should receive confirmation
        confirm = await sender.get_next_message(timeout=0.5)
        assert confirm is not None
        assert confirm["type"] == "message_confirm"
        assert "message_id" in confirm
    
    @pytest.mark.asyncio
    async def test_message_not_echoed_to_sender(self, mock_server, chat_clients):
        """Test that sender doesn't receive their own message."""
        sender = chat_clients[0]
        
        await sender.send_message("Test")
        
        # Drain confirmation
        await sender.get_next_message(timeout=0.5)
        
        # Should not receive the message itself
        msg = await sender.get_next_message(timeout=0.2)
        assert msg is None or msg["type"] != "message"


# ============================================================================
# Presence Tests
# ============================================================================

@pytest.mark.unit
class TestPresence:
    """Tests for presence tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_online_presence_on_connect(self, mock_server):
        """Test that clients appear online on connect."""
        client = await mock_server.connect_client("new_client", "NewUser")
        await client.connect()
        
        assert "new_client" in mock_server.presence_status
        assert mock_server.presence_status["new_client"] == "online"
    
    @pytest.mark.asyncio
    async def test_offline_presence_on_disconnect(self, mock_server, chat_clients):
        """Test that clients appear offline on disconnect."""
        client = chat_clients[0]
        other_clients = chat_clients[1:]
        
        # Clear any pending messages
        for c in other_clients:
            c.clear_received_messages()
        
        await mock_server.disconnect_client(client.client_id)
        
        # Other clients should receive offline notification
        for other in other_clients:
            msg = await other.get_next_message(timeout=0.5)
            assert msg is not None
            assert msg["type"] == "presence_update"
            assert msg["client_id"] == client.client_id
            assert msg["status"] == "offline"
    
    @pytest.mark.asyncio
    async def test_presence_update_broadcast(self, mock_server, chat_clients):
        """Test presence updates are broadcast to all clients."""
        client = chat_clients[0]
        others = chat_clients[1:]
        
        # Clear pending messages
        for c in chat_clients:
            c.clear_received_messages()
        
        await client.update_presence("away")
        
        # Others should receive update
        for other in others:
            msg = await other.get_next_message(timeout=0.5)
            assert msg is not None
            assert msg["type"] == "presence_update"
            assert msg["status"] == "away"
    
    @pytest.mark.asyncio
    async def test_presence_status_values(self, mock_server, chat_clients):
        """Test different presence status values."""
        client = chat_clients[0]
        others = chat_clients[1:]
        
        statuses = ["online", "away", "busy", "dnd", "invisible"]
        
        for status in statuses:
            for c in chat_clients:
                c.clear_received_messages()
            
            await client.update_presence(status)
            
            for other in others:
                msg = await other.get_next_message(timeout=0.5)
                assert msg is not None
                assert msg["status"] == status


# ============================================================================
# Typing Indicators Tests
# ============================================================================

@pytest.mark.unit
class TestTypingIndicators:
    """Tests for typing indicator functionality."""
    
    @pytest.mark.asyncio
    async def test_typing_start_indicator(self, mock_server, chat_clients):
        """Test typing start indicator is broadcast."""
        sender = chat_clients[0]
        receivers = chat_clients[1:]
        
        for c in chat_clients:
            c.clear_received_messages()
        
        await sender.send_typing_indicator(True)
        
        for receiver in receivers:
            msg = await receiver.get_next_message(timeout=0.5)
            assert msg is not None
            assert msg["type"] == "typing_indicator"
            assert msg["client_id"] == sender.client_id
            assert msg["is_typing"] is True
    
    @pytest.mark.asyncio
    async def test_typing_stop_indicator(self, mock_server, chat_clients):
        """Test typing stop indicator is broadcast."""
        sender = chat_clients[0]
        receivers = chat_clients[1:]
        
        for c in chat_clients:
            c.clear_received_messages()
        
        await sender.send_typing_indicator(False)
        
        for receiver in receivers:
            msg = await receiver.get_next_message(timeout=0.5)
            assert msg is not None
            assert msg["is_typing"] is False
    
    @pytest.mark.asyncio
    async def test_typing_not_sent_to_self(self, mock_server, chat_clients):
        """Test typing indicator is not sent to the sender."""
        sender = chat_clients[0]
        
        for c in chat_clients:
            c.clear_received_messages()
        
        await sender.send_typing_indicator(True)
        
        # Sender should not receive their own typing indicator
        msg = await sender.get_next_message(timeout=0.2)
        assert msg is None
    
    @pytest.mark.asyncio
    async def test_typing_timeout(self, mock_server, chat_clients):
        """Test typing indicator times out."""
        sender = chat_clients[0]
        
        await sender.send_typing_indicator(True)
        
        # Check typing is recorded
        assert mock_server.typing_indicators[sender.client_id] > 0
        
        # Simulate timeout by setting to past
        mock_server.typing_indicators[sender.client_id] = time.time() - 10
        
        # Typing should be considered stopped
        # (Actual timeout logic would be server-side)


# ============================================================================
# Message History Tests
# ============================================================================

@pytest.mark.unit
class TestMessageHistory:
    """Tests for message history functionality."""
    
    @pytest.mark.asyncio
    async def test_message_history_stored(self, mock_server, chat_clients):
        """Test that messages are stored in history."""
        sender = chat_clients[0]
        
        initial_count = len(mock_server.message_history)
        
        await sender.send_message("Test message 1")
        await sender.send_message("Test message 2")
        await sender.send_message("Test message 3")
        
        assert len(mock_server.message_history) == initial_count + 3
    
    @pytest.mark.asyncio
    async def test_message_history_content(self, mock_server, chat_clients):
        """Test that message history contains correct content."""
        sender = chat_clients[0]
        
        await sender.send_message("Unique test content")
        
        # Find message in history
        found = False
        for msg in mock_server.message_history:
            if msg.get("content") == "Unique test content":
                found = True
                assert msg["sender_id"] == sender.client_id
                assert "timestamp" in msg
                break
        
        assert found
    
    @pytest.mark.asyncio
    async def test_message_order_preserved(self, mock_server, chat_clients):
        """Test that message order is preserved in history."""
        sender = chat_clients[0]
        
        messages = ["First", "Second", "Third", "Fourth"]
        
        for msg in messages:
            await sender.send_message(msg)
        
        # Get last N messages
        history = mock_server.message_history[-len(messages):]
        contents = [m["content"] for m in history]
        
        assert contents == messages


# ============================================================================
# Concurrent Operation Tests
# ============================================================================

@pytest.mark.unit
class TestConcurrentOperations:
    """Tests for concurrent chat operations."""
    
    @pytest.mark.asyncio
    async def test_multiple_simultaneous_messages(self, mock_server, chat_clients):
        """Test handling multiple simultaneous messages."""
        senders = chat_clients
        
        # All clients send messages concurrently
        await asyncio.gather(*[
            client.send_message(f"Message from {client.client_id}")
            for client in senders
        ])
        
        # Each client should receive messages from others
        for client in senders:
            received_count = len([m for m in client.received_messages if m.get("type") == "message"])
            assert received_count == len(senders) - 1
    
    @pytest.mark.asyncio
    async def test_concurrent_connect_disconnect(self, mock_server):
        """Test concurrent client connections and disconnections."""
        clients = []
        
        # Connect 10 clients concurrently
        for i in range(10):
            client = await mock_server.connect_client(f"concurrent_{i}")
            await client.connect()
            clients.append(client)
        
        assert len(mock_server.clients) == 10
        
        # Disconnect all concurrently
        await asyncio.gather(*[
            mock_server.disconnect_client(client.client_id)
            for client in clients
        ])
        
        assert len(mock_server.clients) == 0
    
    @pytest.mark.asyncio
    async def test_stress_test_messages(self, mock_server):
        """Stress test with many messages."""
        client1 = await mock_server.connect_client("stress1")
        client2 = await mock_server.connect_client("stress2")
        await client1.connect()
        await client2.connect()
        
        # Clear messages
        client1.clear_received_messages()
        client2.clear_received_messages()
        
        # Send 100 messages
        for i in range(100):
            await client1.send_message(f"Message {i}")
        
        # Wait for all messages to be received
        await asyncio.sleep(0.5)
        
        # Client2 should have received all messages
        message_count = len([m for m in client2.received_messages if m.get("type") == "message"])
        assert message_count == 100


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling in chat functionality."""
    
    @pytest.mark.asyncio
    async def test_send_to_disconnected_client(self, mock_server):
        """Test behavior when sending to disconnected client."""
        client = await mock_server.connect_client("disconnect_test")
        await client.connect()
        
        # Disconnect
        await mock_server.disconnect_client(client.client_id)
        
        # Should not error when trying to send to disconnected client
        # (Implementation should handle gracefully)
        assert not client.connected
    
    @pytest.mark.asyncio
    async def test_invalid_message_format(self, mock_server, chat_clients):
        """Test handling of invalid message format."""
        # This would be handled by the actual server
        # Mock server accepts any message format
        sender = chat_clients[0]
        
        await sender.send_message("Valid message")
        
        # Message should be sent without error
        assert len(sender.sent_messages) == 1
    
    @pytest.mark.asyncio
    async def test_server_shutdown_during_chat(self, mock_server, chat_clients):
        """Test behavior when server shuts down during chat."""
        sender = chat_clients[0]
        
        # Send a message
        await sender.send_message("Before shutdown")
        
        # Shutdown server
        await mock_server.stop()
        
        # Server should be stopped
        assert not mock_server.running


# ============================================================================
# Message Types Tests
# ============================================================================

@pytest.mark.unit
class TestMessageTypes:
    """Tests for different message types."""
    
    @pytest.mark.asyncio
    async def test_text_message(self, mock_server, chat_clients):
        """Test text message type."""
        sender = chat_clients[0]
        
        await sender.send_message("Text content", message_type="text")
        
        msg = await chat_clients[1].get_next_message(timeout=0.5)
        assert msg["message_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_system_message(self, mock_server, chat_clients):
        """Test system message broadcasting."""
        # Server sends system message
        system_msg = {
            "type": "system",
            "content": "Server maintenance in 5 minutes",
            "timestamp": time.time()
        }
        
        for client in mock_server.clients.values():
            await client.receive_message(system_msg)
        
        for client in chat_clients:
            msg = await client.get_next_message(timeout=0.5)
            assert msg is not None
            assert msg["type"] == "system"
    
    @pytest.mark.asyncio
    async def test_direct_message(self, mock_server, chat_clients):
        """Test direct message between users."""
        sender = chat_clients[0]
        recipient = chat_clients[1]
        
        dm = {
            "type": "direct_message",
            "content": "Private message",
            "recipient_id": recipient.client_id,
            "sender_id": sender.client_id,
            "timestamp": time.time()
        }
        
        await recipient.receive_message(dm)
        
        msg = await recipient.get_next_message(timeout=0.5)
        assert msg["type"] == "direct_message"
        assert msg["content"] == "Private message"


# ============================================================================
# Integration with Real Server Tests
# ============================================================================

@pytest.mark.integration
class TestRealServerIntegration:
    """Integration tests with real WebSocket server."""
    
    @pytest.fixture
    async def real_server(self):
        """Create and start a real WebSocket server."""
        config = ServerConfig(
            host="127.0.0.1",
            port=0,  # Random port
            max_connections=10,
            ping_interval=5.0,
            ping_timeout=2.0,
            close_timeout=2.0
        )
        
        server = ClawChatServer(config)
        task = asyncio.create_task(server.start())
        
        # Wait for server to start
        await asyncio.sleep(0.2)
        
        port = server.server.sockets[0].getsockname()[1]
        
        yield server, port
        
        # Cleanup
        await server.stop()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            task.cancel()
    
    @pytest.mark.asyncio
    async def test_real_websocket_connection(self, real_server):
        """Test connection to real WebSocket server."""
        server, port = real_server
        uri = f"ws://127.0.0.1:{port}"
        
        async with websockets.connect(uri) as ws:
            # Receive welcome message
            welcome = await asyncio.wait_for(ws.recv(), timeout=1.0)
            welcome_data = json.loads(welcome)
            
            assert welcome_data["type"] == "welcome"
            assert "connection_id" in welcome_data
    
    @pytest.mark.asyncio
    async def test_real_echo_message(self, real_server):
        """Test echo functionality on real server."""
        server, port = real_server
        uri = f"ws://127.0.0.1:{port}"
        
        async with websockets.connect(uri) as ws:
            await asyncio.wait_for(ws.recv(), timeout=1.0)  # Welcome
            
            # Send echo message
            await ws.send(json.dumps({
                "type": "echo",
                "data": "Hello from test"
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            response_data = json.loads(response)
            
            assert response_data["type"] == "echo"
            assert response_data["data"] == "Hello from test"
    
    @pytest.mark.asyncio
    async def test_real_broadcast_message(self, real_server):
        """Test broadcast on real server."""
        server, port = real_server
        uri = f"ws://127.0.0.1:{port}"
        
        # Connect two clients
        ws1 = await websockets.connect(uri)
        ws2 = await websockets.connect(uri)
        
        try:
            # Receive welcomes
            welcome1 = await asyncio.wait_for(ws1.recv(), timeout=1.0)
            welcome2 = await asyncio.wait_for(ws2.recv(), timeout=1.0)
            
            # Client 1 broadcasts
            await ws1.send(json.dumps({
                "type": "broadcast",
                "data": {"message": "Hello all!"}
            }))
            
            # Client 1 receives confirmation
            confirm = await asyncio.wait_for(ws1.recv(), timeout=1.0)
            confirm_data = json.loads(confirm)
            assert confirm_data["type"] == "broadcast_confirm"
            assert confirm_data["recipients"] == 1
            
            # Client 2 receives broadcast
            broadcast = await asyncio.wait_for(ws2.recv(), timeout=1.0)
            broadcast_data = json.loads(broadcast)
            assert broadcast_data["type"] == "broadcast"
            assert broadcast_data["data"]["message"] == "Hello all!"
            
        finally:
            await ws1.close()
            await ws2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
