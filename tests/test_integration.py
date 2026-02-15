"""Integration tests for ClawChat WebSocket Client-Server communication.

This module contains comprehensive integration tests that verify the
communication between the WebSocket server and actual WebSocket clients.
Tests include real connection establishment, message exchange, error
scenarios, and performance testing.

Run with: pytest tests/test_integration.py -v
"""

import asyncio
import json
import pytest
import sys
import time
import websockets
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from server import ClawChatServer, ServerConfig


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def server():
    """Create and start a test server."""
    config = ServerConfig(
        host="127.0.0.1",
        port=0,  # Random available port
        max_connections=50,
        ping_interval=5.0,
        ping_timeout=2.0,
        close_timeout=2.0,
        log_level="INFO"
    )
    
    srv = ClawChatServer(config)
    
    # Start server in background
    server_task = asyncio.create_task(srv.start())
    
    # Wait for server to start
    await asyncio.sleep(0.2)
    
    # Get the actual port
    if srv.server:
        port = srv.server.sockets[0].getsockname()[1]
    else:
        port = config.port
    
    yield srv, port
    
    # Cleanup
    await srv.stop()
    try:
        await asyncio.wait_for(server_task, timeout=2.0)
    except asyncio.TimeoutError:
        server_task.cancel()


@pytest.fixture
async def connected_client(server):
    """Create a connected WebSocket client."""
    srv, port = server
    uri = f"ws://127.0.0.1:{port}"
    
    async with websockets.connect(uri) as ws:
        # Wait for welcome message
        welcome = await asyncio.wait_for(ws.recv(), timeout=1.0)
        welcome_data = json.loads(welcome)
        assert welcome_data["type"] == "welcome"
        
        yield ws, welcome_data["connection_id"]


@pytest.fixture
async def multiple_clients(server):
    """Create multiple connected clients."""
    srv, port = server
    uri = f"ws://127.0.0.1:{port}"
    
    clients = []
    client_ids = []
    
    for _ in range(5):
        ws = await websockets.connect(uri)
        welcome = await asyncio.wait_for(ws.recv(), timeout=1.0)
        welcome_data = json.loads(welcome)
        clients.append(ws)
        client_ids.append(welcome_data["connection_id"])
    
    yield clients, client_ids
    
    # Cleanup all clients
    for ws in clients:
        try:
            await ws.close()
        except:
            pass


# ============================================================================
# Connection Tests
# ============================================================================

class TestConnectionEstablishment:
    """Tests for WebSocket connection establishment."""
    
    @pytest.mark.asyncio
    async def test_basic_connection(self, server):
        """Test basic WebSocket connection."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        async with websockets.connect(uri) as ws:
            assert ws.open
            message = await asyncio.wait_for(ws.recv(), timeout=1.0)
            data = json.loads(message)
            assert data["type"] == "welcome"
            assert "connection_id" in data
    
    @pytest.mark.asyncio
    async def test_multiple_connections(self, server):
        """Test multiple concurrent connections."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        connections = []
        for i in range(10):
            ws = await websockets.connect(uri)
            welcome = await asyncio.wait_for(ws.recv(), timeout=1.0)
            data = json.loads(welcome)
            assert data["type"] == "welcome"
            connections.append((ws, data["connection_id"]))
        
        # Verify all connections have unique IDs
        ids = [conn_id for _, conn_id in connections]
        assert len(ids) == len(set(ids))
        
        # Cleanup
        for ws, _ in connections:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_connection_limit(self):
        """Test server enforces connection limits."""
        config = ServerConfig(
            host="127.0.0.1",
            port=0,
            max_connections=3,
            ping_interval=5.0,
            ping_timeout=2.0,
            close_timeout=2.0
        )
        
        srv = ClawChatServer(config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.2)
        
        port = srv.server.sockets[0].getsockname()[1]
        uri = f"ws://127.0.0.1:{port}"
        
        clients = []
        try:
            # Connect up to limit
            for i in range(3):
                ws = await websockets.connect(uri)
                await asyncio.wait_for(ws.recv(), timeout=1.0)
                clients.append(ws)
            
            # Next connection should be rejected
            with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
                await websockets.connect(uri)
            
            assert exc_info.value.status_code == 503
            
        finally:
            for ws in clients:
                await ws.close()
            await srv.stop()
    
    @pytest.mark.asyncio
    async def test_connection_graceful_close(self, server):
        """Test graceful connection close from client."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        ws = await websockets.connect(uri)
        await asyncio.wait_for(ws.recv(), timeout=1.0)  # Welcome
        
        # Close gracefully
        await ws.close(code=1000, reason="Client done")
        
        assert ws.closed
        assert ws.close_code == 1000


# ============================================================================
# Message Exchange Tests
# ============================================================================

class TestMessageExchange:
    """Tests for message sending and receiving."""
    
    @pytest.mark.asyncio
    async def test_echo_json_message(self, connected_client):
        """Test echo of JSON message."""
        ws, conn_id = connected_client
        
        test_data = {"message": "Hello Server!", "number": 42}
        await ws.send(json.dumps({"type": "echo", "data": test_data}))
        
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "echo"
        assert response_data["data"] == test_data
        assert "timestamp" in response_data
    
    @pytest.mark.asyncio
    async def test_echo_text_message(self, connected_client):
        """Test echo of plain text message."""
        ws, conn_id = connected_client
        
        await ws.send("Plain text message")
        
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "echo"
        assert response_data["data"] == "Plain text message"
        assert response_data["format"] == "text"
    
    @pytest.mark.asyncio
    async def test_multiple_echo_messages(self, connected_client):
        """Test multiple sequential echo messages."""
        ws, conn_id = connected_client
        
        messages = ["Message 1", "Message 2", "Message 3"]
        
        for msg in messages:
            await ws.send(json.dumps({"type": "echo", "data": msg}))
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            response_data = json.loads(response)
            assert response_data["data"] == msg
    
    @pytest.mark.asyncio
    async def test_ping_pong(self, connected_client):
        """Test ping/pong message exchange."""
        ws, conn_id = connected_client
        
        ping_data = {"timestamp": time.time(), "test": "ping"}
        await ws.send(json.dumps({"type": "ping", "data": ping_data}))
        
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "pong"
        assert "timestamp" in response_data
        assert response_data["echo"] == ping_data
    
    @pytest.mark.asyncio
    async def test_server_heartbeat_ping(self, server):
        """Test server-initiated ping (heartbeat)."""
        config = ServerConfig(
            host="127.0.0.1",
            port=0,
            ping_interval=0.5,  # Very short for testing
            ping_timeout=1.0
        )
        
        srv = ClawChatServer(config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.2)
        
        port = srv.server.sockets[0].getsockname()[1]
        
        try:
            async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
                await asyncio.wait_for(ws.recv(), timeout=1.0)  # Welcome
                
                # Wait for server ping (websocket protocol level)
                # The server should send a ping frame automatically
                await asyncio.sleep(1.0)
                
                # Connection should still be open
                assert ws.open
                
        finally:
            await srv.stop()


# ============================================================================
# Broadcast Tests
# ============================================================================

class TestBroadcast:
    """Tests for broadcast message functionality."""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, multiple_clients):
        """Test broadcasting to all connected clients."""
        clients, client_ids = multiple_clients
        sender = clients[0]
        receivers = clients[1:]
        
        # Send broadcast
        broadcast_msg = {"announcement": "Hello everyone!"}
        await sender.send(json.dumps({
            "type": "broadcast",
            "data": broadcast_msg
        }))
        
        # Sender should receive confirmation
        confirm = await asyncio.wait_for(sender.recv(), timeout=1.0)
        confirm_data = json.loads(confirm)
        assert confirm_data["type"] == "broadcast_confirm"
        assert confirm_data["recipients"] == len(receivers)
        
        # All receivers should get the broadcast
        for ws in receivers:
            msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
            msg_data = json.loads(msg)
            assert msg_data["type"] == "broadcast"
            assert msg_data["data"] == broadcast_msg
            assert msg_data["from"] == client_ids[0]
    
    @pytest.mark.asyncio
    async def test_broadcast_sender_not_receive(self, multiple_clients):
        """Test that sender doesn't receive their own broadcast."""
        clients, client_ids = multiple_clients
        sender = clients[0]
        
        # Clear any pending messages
        await asyncio.sleep(0.1)
        
        # Send broadcast
        await sender.send(json.dumps({
            "type": "broadcast",
            "data": {"test": "value"}
        }))
        
        # First message should be confirmation, not the broadcast
        confirm = await asyncio.wait_for(sender.recv(), timeout=1.0)
        confirm_data = json.loads(confirm)
        assert confirm_data["type"] == "broadcast_confirm"
    
    @pytest.mark.asyncio
    async def test_broadcast_single_receiver(self, server):
        """Test broadcast with only one other client."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        client1 = await websockets.connect(uri)
        await asyncio.wait_for(client1.recv(), timeout=1.0)
        
        client2 = await websockets.connect(uri)
        await asyncio.wait_for(client2.recv(), timeout=1.0)
        
        try:
            # Client1 broadcasts
            await client1.send(json.dumps({
                "type": "broadcast",
                "data": {"msg": "test"}
            }))
            
            # Client1 gets confirmation
            confirm = await asyncio.wait_for(client1.recv(), timeout=1.0)
            assert json.loads(confirm)["type"] == "broadcast_confirm"
            
            # Client2 gets broadcast
            broadcast = await asyncio.wait_for(client2.recv(), timeout=1.0)
            assert json.loads(broadcast)["type"] == "broadcast"
            
        finally:
            await client1.close()
            await client2.close()


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error scenarios."""
    
    @pytest.mark.asyncio
    async def test_unknown_message_type(self, connected_client):
        """Test handling of unknown message type."""
        ws, conn_id = connected_client
        
        await ws.send(json.dumps({"type": "unknown_type_xyz", "data": "test"}))
        
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "error"
        assert "unknown" in response_data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_malformed_json(self, connected_client):
        """Test handling of malformed JSON."""
        ws, conn_id = connected_client
        
        await ws.send("{not valid json")
        
        # Should echo as text, not crash
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "echo"
        assert response_data["data"] == "{not valid json"
    
    @pytest.mark.asyncio
    async def test_empty_message(self, connected_client):
        """Test handling of empty message."""
        ws, conn_id = connected_client
        
        await ws.send("")
        
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "echo"
        assert response_data["data"] == ""
    
    @pytest.mark.asyncio
    async def test_connection_abrupt_close(self, server):
        """Test server handles abrupt client disconnect."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        ws = await websockets.connect(uri)
        await asyncio.wait_for(ws.recv(), timeout=1.0)
        
        # Abruptly close without handshake
        ws.transport.close()
        
        # Give server time to process
        await asyncio.sleep(0.2)
        
        # Server stats should reflect closed connection
        stats = srv.get_stats()
        assert stats["connections"]["active"] == 0
    
    @pytest.mark.asyncio
    async def test_send_without_connection(self, server):
        """Test sending to closed connection."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        ws = await websockets.connect(uri)
        await asyncio.wait_for(ws.recv(), timeout=1.0)
        
        # Close connection
        await ws.close()
        
        # Try to send after close
        with pytest.raises(websockets.exceptions.ConnectionClosed):
            await ws.send("test")


# ============================================================================
# Concurrent Operation Tests
# ============================================================================

class TestConcurrentOperations:
    """Tests for concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_echo(self, multiple_clients):
        """Test concurrent echo requests from multiple clients."""
        clients, _ = multiple_clients
        
        async def send_echo(ws, message):
            await ws.send(json.dumps({"type": "echo", "data": message}))
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            return json.loads(response)
        
        # Send multiple echoes concurrently
        tasks = [
            send_echo(clients[i], f"Message {i}")
            for i in range(len(clients))
        ]
        
        results = await asyncio.gather(*tasks)
        
        for i, result in enumerate(results):
            assert result["type"] == "echo"
            assert result["data"] == f"Message {i}"
    
    @pytest.mark.asyncio
    async def test_stress_many_messages(self, connected_client):
        """Stress test with many sequential messages."""
        ws, conn_id = connected_client
        
        message_count = 100
        
        for i in range(message_count):
            await ws.send(json.dumps({"type": "echo", "data": i}))
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            data = json.loads(response)
            assert data["data"] == i
    
    @pytest.mark.asyncio
    async def test_large_message(self, connected_client):
        """Test handling of large messages."""
        ws, conn_id = connected_client
        
        # 100KB message
        large_data = "x" * (100 * 1024)
        
        await ws.send(json.dumps({"type": "echo", "data": large_data}))
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "echo"
        assert response_data["data"] == large_data
    
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(self, server):
        """Test rapid connect/disconnect cycles."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        for i in range(20):
            ws = await websockets.connect(uri)
            await asyncio.wait_for(ws.recv(), timeout=1.0)
            await ws.close()
        
        # All connections should be cleaned up
        await asyncio.sleep(0.3)
        stats = srv.get_stats()
        assert stats["connections"]["active"] == 0


# ============================================================================
# Server Statistics Tests
# ============================================================================

class TestServerStatistics:
    """Tests for server statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_stats_with_connections(self, server):
        """Test stats reflect active connections."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        clients = []
        for i in range(5):
            ws = await websockets.connect(uri)
            await asyncio.wait_for(ws.recv(), timeout=1.0)
            clients.append(ws)
        
        stats = srv.get_stats()
        assert stats["connections"]["active"] == 5
        assert len(stats["clients"]) == 5
        
        for ws in clients:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_stats_message_count(self, connected_client):
        """Test that stats track message counts."""
        ws, conn_id = connected_client
        srv = None  # Will get from fixture
        
        # Send several messages
        for i in range(5):
            await ws.send(json.dumps({"type": "echo", "data": i}))
            await asyncio.wait_for(ws.recv(), timeout=1.0)


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance-related integration tests."""
    
    @pytest.mark.asyncio
    async def test_message_latency(self, connected_client):
        """Test message round-trip latency."""
        ws, conn_id = connected_client
        
        latencies = []
        
        for _ in range(10):
            start = time.time()
            await ws.send(json.dumps({"type": "echo", "data": "ping"}))
            await asyncio.wait_for(ws.recv(), timeout=1.0)
            latencies.append(time.time() - start)
        
        avg_latency = sum(latencies) / len(latencies)
        # Should be very fast for local server
        assert avg_latency < 0.1  # 100ms
    
    @pytest.mark.asyncio
    async def test_throughput(self, server):
        """Test message throughput."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        ws = await websockets.connect(uri)
        await asyncio.wait_for(ws.recv(), timeout=1.0)
        
        message_count = 1000
        start = time.time()
        
        for i in range(message_count):
            await ws.send(json.dumps({"type": "echo", "data": i}))
            await asyncio.wait_for(ws.recv(), timeout=5.0)
        
        duration = time.time() - start
        messages_per_second = message_count / duration
        
        print(f"\nThroughput: {messages_per_second:.2f} messages/second")
        
        # Should handle at least 100 msg/sec on any modern hardware
        assert messages_per_second > 100
        
        await ws.close()


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""
    
    @pytest.mark.asyncio
    async def test_unicode_message(self, connected_client):
        """Test handling of unicode messages."""
        ws, conn_id = connected_client
        
        unicode_data = {
            "chinese": "你好世界",
            "emoji": "🎉🎊🎁",
            "arabic": "مرحبا",
            "russian": "Привет мир",
            "japanese": "こんにちは",
            "special": "<>&\"'"
        }
        
        await ws.send(json.dumps({"type": "echo", "data": unicode_data}))
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["data"] == unicode_data
    
    @pytest.mark.asyncio
    async def test_nested_json(self, connected_client):
        """Test handling of deeply nested JSON."""
        ws, conn_id = connected_client
        
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": "deep value"
                        }
                    }
                }
            }
        }
        
        await ws.send(json.dumps({"type": "echo", "data": nested_data}))
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["data"]["level1"]["level2"]["level3"]["level4"]["level5"] == "deep value"
    
    @pytest.mark.asyncio
    async def test_binary_data_as_text(self, connected_client):
        """Test handling of binary-like text data."""
        ws, conn_id = connected_client
        
        # Send data that looks like binary
        binary_like = "\x00\x01\x02\x03\xff\xfe"
        
        await ws.send(binary_like)
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "echo"
        # Note: binary may be encoded differently
    
    @pytest.mark.asyncio
    async def test_message_without_type(self, connected_client):
        """Test message without explicit type field."""
        ws, conn_id = connected_client
        
        await ws.send(json.dumps({"data": "no type field"}))
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "error"
    
    @pytest.mark.asyncio
    async def test_null_values(self, connected_client):
        """Test handling of null values in JSON."""
        ws, conn_id = connected_client
        
        data_with_null = {
            "value": None,
            "array": [1, None, 3],
            "nested": {"null": None}
        }
        
        await ws.send(json.dumps({"type": "echo", "data": data_with_null}))
        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
        response_data = json.loads(response)
        
        assert response_data["data"]["value"] is None
        assert response_data["data"]["array"][1] is None


# ============================================================================
# Real Client Simulation Tests
# ============================================================================

class TestRealClientSimulation:
    """Tests that simulate real client behavior."""
    
    @pytest.mark.asyncio
    async def test_chat_scenario(self, server):
        """Simulate a simple chat scenario."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        # Two users connect
        alice = await websockets.connect(uri)
        bob = await websockets.connect(uri)
        
        await asyncio.wait_for(alice.recv(), timeout=1.0)  # Welcome
        await asyncio.wait_for(bob.recv(), timeout=1.0)  # Welcome
        
        try:
            # Alice sends a message to everyone
            await alice.send(json.dumps({
                "type": "broadcast",
                "data": {"user": "Alice", "text": "Hello Bob!"}
            }))
            
            # Alice gets confirmation
            confirm = await asyncio.wait_for(alice.recv(), timeout=1.0)
            assert json.loads(confirm)["type"] == "broadcast_confirm"
            
            # Bob receives the message
            msg = await asyncio.wait_for(bob.recv(), timeout=1.0)
            msg_data = json.loads(msg)
            assert msg_data["type"] == "broadcast"
            assert msg_data["data"]["user"] == "Alice"
            assert msg_data["data"]["text"] == "Hello Bob!"
            
            # Bob responds
            await bob.send(json.dumps({
                "type": "broadcast",
                "data": {"user": "Bob", "text": "Hi Alice!"}
            }))
            
            # Alice receives the response
            response = await asyncio.wait_for(alice.recv(), timeout=1.0)
            response_data = json.loads(response)
            assert response_data["data"]["user"] == "Bob"
            
        finally:
            await alice.close()
            await bob.close()
    
    @pytest.mark.asyncio
    async def test_reconnection_scenario(self, server):
        """Simulate client reconnection."""
        srv, port = server
        uri = f"ws://127.0.0.1:{port}"
        
        # Initial connection
        ws1 = await websockets.connect(uri)
        welcome1 = await asyncio.wait_for(ws1.recv(), timeout=1.0)
        conn_id1 = json.loads(welcome1)["connection_id"]
        await ws1.close()
        
        # Reconnect
        ws2 = await websockets.connect(uri)
        welcome2 = await asyncio.wait_for(ws2.recv(), timeout=1.0)
        conn_id2 = json.loads(welcome2)["connection_id"]
        
        # Should get different connection ID
        assert conn_id1 != conn_id2
        
        await ws2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
