"""
ClawChat File System API - WebSocket Server Integration Example
================================================================
Example showing how to integrate the File System API with a WebSocket server.

This module demonstrates integration with both:
1. Built-in asyncio WebSocket server
2. External WebSocket frameworks (like FastAPI, aiohttp, etc.)
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import websockets
from websockets.server import WebSocketServerProtocol

from file_api import create_file_api, FileSystemAPI
from file_api_config import FileAPIConfig

logger = logging.getLogger(__name__)


class FileAPIServer:
    """
    Standalone WebSocket server with File System API integration.
    """
    
    def __init__(self, api: FileSystemAPI, host: str = "0.0.0.0", port: int = 8766):
        self.api = api
        self.host = host
        self.port = port
        self.clients: Dict[str, WebSocketServerProtocol] = {}
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a WebSocket client connection."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients[client_id] = websocket
        
        client_info = {
            'client_id': client_id,
            'ip_address': websocket.remote_address[0],
            'port': websocket.remote_address[1],
            'path': path
        }
        
        logger.info(f"Client connected: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    # Define send callback
                    async def send_response(data: Dict[str, Any]):
                        await websocket.send(json.dumps(data))
                    
                    # Handle message through File API
                    await self.api.handle_websocket_message(
                        message=message,
                        client_info=client_info,
                        send_callback=send_response
                    )
                    
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await websocket.send(json.dumps({
                        'success': False,
                        'error': f'Internal error: {str(e)}',
                        'error_code': 'E999'
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            del self.clients[client_id]
    
    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting File API WebSocket server on {self.host}:{self.port}")
        
        async with websockets.serve(self._handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever


class FastAPIIntegration:
    """
    Example integration with FastAPI WebSocket endpoints.
    """
    
    def __init__(self, api: FileSystemAPI):
        self.api = api
    
    async def handle_websocket(self, websocket, client_info: Dict[str, Any]):
        """
        Handle WebSocket connection in FastAPI.
        
        Usage in FastAPI:
        
            from fastapi import FastAPI, WebSocket
            from file_api_integration import FastAPIIntegration, create_file_api
            
            app = FastAPI()
            file_api = create_file_api()
            integration = FastAPIIntegration(file_api)
            
            @app.websocket("/ws/files")
            async def websocket_endpoint(websocket: WebSocket):
                await websocket.accept()
                client_info = {
                    'ip_address': websocket.client.host,
                    'port': websocket.client.port
                }
                await integration.handle_websocket(websocket, client_info)
        """
        try:
            while True:
                # Receive message
                message = await websocket.receive_text()
                
                # Define send callback
                async def send_response(data: Dict[str, Any]):
                    await websocket.send_text(json.dumps(data))
                
                # Handle through File API
                await self.api.handle_websocket_message(
                    message=message,
                    client_info=client_info,
                    send_callback=send_response
                )
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close()


class AioHTTPIntegration:
    """
    Example integration with aiohttp WebSocket endpoints.
    """
    
    def __init__(self, api: FileSystemAPI):
        self.api = api
    
    async def handle_websocket(self, request, ws):
        """
        Handle WebSocket connection in aiohttp.
        
        Usage in aiohttp:
        
            from aiohttp import web
            from file_api_integration import AioHTTPIntegration, create_file_api
            
            file_api = create_file_api()
            integration = AioHTTPIntegration(file_api)
            
            async def websocket_handler(request):
                ws = web.WebSocketResponse()
                await ws.prepare(request)
                await integration.handle_websocket(request, ws)
                return ws
            
            app = web.Application()
            app.router.add_get('/ws/files', websocket_handler)
        """
        client_info = {
            'ip_address': request.remote,
            'headers': dict(request.headers)
        }
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    # Define send callback
                    async def send_response(data: Dict[str, Any]):
                        await ws.send_str(json.dumps(data))
                    
                    # Handle through File API
                    await self.api.handle_websocket_message(
                        message=msg.data,
                        client_info=client_info,
                        send_callback=send_response
                    )
                    
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")


# ============== Convenience Functions ==============

def create_server(
    config: Optional[FileAPIConfig] = None,
    host: str = "0.0.0.0",
    port: int = 8766
) -> FileAPIServer:
    """
    Create a File API WebSocket server.
    
    Args:
        config: Configuration (uses default if None)
        host: Server host
        port: Server port
        
    Returns:
        Configured FileAPIServer instance
    """
    if config is None:
        config = FileAPIConfig.from_environment()
    
    # Create API with config
    api = create_file_api(
        root_directory=config.ROOT_DIRECTORY,
        allow_hidden=config.ALLOW_HIDDEN_FILES,
        require_auth=config.REQUIRE_AUTHENTICATION,
        secret_key=config.SECRET_KEY
    )
    
    return FileAPIServer(api, host=host, port=port)


# ============== Main Entry Point ==============

async def main():
    """Main entry point for standalone server."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start server
    server = create_server()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
