"""ClawChat WebSocket Server.

A production-ready WebSocket server with connection management,
keepalive ping/pong, and robust error handling.
"""

import asyncio
import json
import signal
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

import yaml
import websockets
from websockets.server import WebSocketServerProtocol

from logging_config import setup_logging, get_logger


@dataclass
class ServerConfig:
    """Server configuration container."""
    host: str = "0.0.0.0"
    port: int = 8765
    max_connections: int = 100
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    close_timeout: float = 10.0
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, filepath: str) -> "ServerConfig":
        """Load configuration from YAML file."""
        path = Path(filepath)
        if not path.exists():
            return cls()

        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        server = data.get('server', {})
        keepalive = data.get('keepalive', {})
        logging = data.get('logging', {})

        return cls(
            host=server.get('host', cls.host),
            port=server.get('port', cls.port),
            max_connections=server.get('max_connections', cls.max_connections),
            ping_interval=keepalive.get('ping_interval', cls.ping_interval),
            ping_timeout=keepalive.get('ping_timeout', cls.ping_timeout),
            close_timeout=keepalive.get('close_timeout', cls.close_timeout),
            log_level=logging.get('level', cls.log_level)
        )


@dataclass
class ConnectionInfo:
    """Information about a connected client."""
    id: str
    websocket: WebSocketServerProtocol
    connected_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    message_count: int = 0
    last_activity: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class ClawChatServer:
    """WebSocket server for ClawChat.

    Handles multiple concurrent connections, implements ping/pong keepalive,
    and provides echo functionality for testing.
    """

    def __init__(self, config: ServerConfig):
        """Initialize the server with configuration.

        Args:
            config: Server configuration instance.
        """
        self.config = config
        self.logger = get_logger('server')
        self.connections: Dict[str, ConnectionInfo] = {}
        self.server: Optional[websockets.WebSocketServer] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the WebSocket server."""
        self.logger.info(
            f"Starting ClawChat server on {self.config.host}:{self.config.port}"
        )
        self.logger.info(f"Max connections: {self.config.max_connections or 'unlimited'}")

        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.config.host,
                self.config.port,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                close_timeout=self.config.close_timeout,
                process_request=self._process_request
            )

            self.logger.info("Server started successfully")

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            self.logger.error(f"Server error: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Gracefully stop the server."""
        self.logger.info("Shutting down server...")

        # Close all active connections
        close_tasks = []
        for conn_info in list(self.connections.values()):
            close_tasks.append(self._close_connection(conn_info, "Server shutting down"))

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        # Stop the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self._shutdown_event.set()
        self.logger.info("Server stopped")

    async def _process_request(
        self,
        path: str,
        request_headers: websockets.Headers
    ) -> Optional[tuple]:
        """Process incoming connection requests.

        Args:
            path: Request path.
            request_headers: HTTP headers from the request.

        Returns:
            None to accept connection, or (status, headers, body) to reject.
        """
        # Check connection limit
        if self.config.max_connections > 0:
            if len(self.connections) >= self.config.max_connections:
                self.logger.warning(f"Connection rejected: max connections reached")
                return (
                    503,
                    [('Content-Type', 'application/json')],
                    json.dumps({"error": "Server at capacity"}).encode()
                )

        return None

    async def _handle_connection(
        self,
        websocket: WebSocketServerProtocol,
        path: str
    ) -> None:
        """Handle a new WebSocket connection.

        Args:
            websocket: WebSocket protocol instance.
            path: Connection path.
        """
        connection_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        conn_info = ConnectionInfo(id=connection_id, websocket=websocket)
        self.connections[connection_id] = conn_info

        self.logger.info(f"Client connected: {connection_id} (total: {len(self.connections)})")

        try:
            # Send welcome message
            await self._send_message(conn_info, {
                "type": "welcome",
                "message": "Welcome to ClawChat!",
                "connection_id": connection_id
            })

            # Handle messages
            async for message in websocket:
                await self._handle_message(conn_info, message)

        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info(f"Connection closed gracefully: {connection_id}")
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.warning(f"Connection closed with error: {connection_id} - {e}")
        except Exception as e:
            self.logger.error(f"Error handling connection {connection_id}: {e}", exc_info=True)
        finally:
            await self._cleanup_connection(connection_id)

    async def _handle_message(self, conn_info: ConnectionInfo, message: str) -> None:
        """Process an incoming message.

        Args:
            conn_info: Connection information.
            message: Raw message string.
        """
        conn_info.message_count += 1
        conn_info.last_activity = asyncio.get_event_loop().time()

        self.logger.debug(f"Message from {conn_info.id}: {message[:200]}...")

        try:
            # Try to parse as JSON
            data = json.loads(message)
            msg_type = data.get('type', 'unknown')

            # Handle different message types
            if msg_type == 'echo':
                await self._handle_echo(conn_info, data)
            elif msg_type == 'ping':
                await self._handle_ping(conn_info, data)
            elif msg_type == 'broadcast':
                await self._handle_broadcast(conn_info, data)
            else:
                await self._send_message(conn_info, {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })

        except json.JSONDecodeError:
            # Echo raw text back for non-JSON messages
            await self._send_message(conn_info, {
                "type": "echo",
                "data": message,
                "format": "text"
            })
        except Exception as e:
            self.logger.error(f"Error processing message from {conn_info.id}: {e}")
            await self._send_message(conn_info, {
                "type": "error",
                "message": "Internal server error"
            })

    async def _handle_echo(self, conn_info: ConnectionInfo, data: dict) -> None:
        """Handle echo message type.

        Args:
            conn_info: Connection information.
            data: Parsed JSON message data.
        """
        response = {
            "type": "echo",
            "data": data.get('data'),
            "timestamp": asyncio.get_event_loop().time(),
            "format": "json"
        }
        await self._send_message(conn_info, response)

    async def _handle_ping(self, conn_info: ConnectionInfo, data: dict) -> None:
        """Handle ping message type.

        Args:
            conn_info: Connection information.
            data: Parsed JSON message data.
        """
        await self._send_message(conn_info, {
            "type": "pong",
            "timestamp": asyncio.get_event_loop().time(),
            "echo": data.get('data')
        })

    async def _handle_broadcast(self, conn_info: ConnectionInfo, data: dict) -> None:
        """Handle broadcast message type.

        Args:
            conn_info: Connection information.
            data: Parsed JSON message data.
        """
        broadcast_data = {
            "type": "broadcast",
            "from": conn_info.id,
            "data": data.get('data'),
            "timestamp": asyncio.get_event_loop().time()
        }

        # Send to all connected clients except sender
        tasks = []
        for other_conn in self.connections.values():
            if other_conn.id != conn_info.id:
                tasks.append(self._send_message(other_conn, broadcast_data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Confirm to sender
        await self._send_message(conn_info, {
            "type": "broadcast_confirm",
            "recipients": len(tasks)
        })

    async def _send_message(self, conn_info: ConnectionInfo, data: dict) -> bool:
        """Send a JSON message to a client.

        Args:
            conn_info: Connection information.
            data: Message data to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            message = json.dumps(data)
            await conn_info.websocket.send(message)
            return True
        except websockets.exceptions.ConnectionClosed:
            self.logger.debug(f"Cannot send to closed connection: {conn_info.id}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending message to {conn_info.id}: {e}")
            return False

    async def _close_connection(self, conn_info: ConnectionInfo, reason: str) -> None:
        """Close a connection gracefully.

        Args:
            conn_info: Connection information.
            reason: Reason for closing.
        """
        try:
            await conn_info.websocket.close(code=1001, reason=reason)
        except Exception:
            pass  # Connection may already be closed

    async def _cleanup_connection(self, connection_id: str) -> None:
        """Clean up after a connection closes.

        Args:
            connection_id: ID of the closed connection.
        """
        if connection_id in self.connections:
            conn_info = self.connections.pop(connection_id)
            duration = asyncio.get_event_loop().time() - conn_info.connected_at
            self.logger.info(
                f"Client disconnected: {connection_id} "
                f"(messages: {conn_info.message_count}, duration: {duration:.1f}s, "
                f"remaining: {len(self.connections)})"
            )

    def get_stats(self) -> dict:
        """Get server statistics.

        Returns:
            Dictionary containing server statistics.
        """
        return {
            "connections": {
                "active": len(self.connections),
                "max": self.config.max_connections
            },
            "clients": [
                {
                    "id": conn.id,
                    "connected_at": conn.connected_at,
                    "message_count": conn.message_count,
                    "last_activity": conn.last_activity
                }
                for conn in self.connections.values()
            ]
        }


def load_config(config_path: str = "config.yaml") -> ServerConfig:
    """Load server configuration from YAML file.

    Args:
        config_path: Path to configuration file.

    Returns:
        ServerConfig instance.
    """
    return ServerConfig.from_yaml(config_path)


def setup_signal_handlers(server: ClawChatServer) -> None:
    """Setup graceful shutdown on signals.

    Args:
        server: Server instance to shutdown.
    """
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        """Handle shutdown signals."""
        logger = get_logger()
        logger.info(f"Received signal {sig.name}, initiating shutdown...")
        asyncio.create_task(server.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))


async def main():
    """Main entry point."""
    # Load configuration
    config = load_config()

    # Setup logging
    log_config = {
        'level': config.log_level,
        'file': 'logs/clawchat.log',
        'console_output': True
    }
    logger = setup_logging(log_config)

    logger.info("=" * 50)
    logger.info("ClawChat WebSocket Server")
    logger.info("=" * 50)

    # Create and start server
    server = ClawChatServer(config)
    setup_signal_handlers(server)

    try:
        await server.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
