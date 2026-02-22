#!/usr/bin/env python3
"""
Simple ClawChat HTTP Server (Temporary)
Runs on unprivileged port 8080 until WebSocket dependencies are installed.
"""

import http.server
import socketserver
import json
import os
from datetime import datetime

PORT = 8080
HOST = "0.0.0.0"

class ClawChatHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - serve status page."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>ClawChat Server</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .status {{ padding: 20px; background: #f0f0f0; border-radius: 5px; }}
                    .online {{ color: green; font-weight: bold; }}
                </style>
            </head>
            <body>
                <h1>🦀 ClawChat Server</h1>
                <div class="status">
                    <p><span class="online">● ONLINE</span> - Server is running</p>
                    <p><strong>IP:</strong> 45.135.36.44</p>
                    <p><strong>Port:</strong> 8080 (HTTP)</p>
                    <p><strong>WebSocket Port:</strong> 8765 (coming soon)</p>
                    <p><strong>Status:</strong> Simple HTTP server running. WebSocket server requires dependencies.</p>
                    <p><strong>Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                <h3>Endpoints:</h3>
                <ul>
                    <li><a href="/">/</a> - This status page</li>
                    <li><a href="/status">/status</a> - JSON status API</li>
                    <li><a href="/chat">/chat</a> - Chat interface (placeholder)</li>
                </ul>
                <p><em>Note: This is a temporary HTTP server. Full WebSocket server will run on port 8765 once dependencies are installed.</em></p>
            </body>
            </html>
            """
            
            self.wfile.write(html.encode())
            
        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            status = {
                "service": "ClawChat",
                "status": "running",
                "server": "simple_http",
                "ip": "45.135.36.44",
                "port": 8080,
                "websocket_port": 8765,
                "websocket_status": "pending_dependencies",
                "timestamp": datetime.now().isoformat(),
                "message": "Temporary HTTP server. WebSocket server requires websockets and pyyaml packages."
            }
            
            self.wfile.write(json.dumps(status, indent=2).encode())
            
        elif self.path == "/chat":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>ClawChat - Coming Soon</title>
            </head>
            <body>
                <h1>ClawChat Interface</h1>
                <p>WebSocket-based chat interface coming soon.</p>
                <p>Once dependencies are installed, the full WebSocket server will run on port 8765.</p>
                <p><a href="/">← Back to status</a></p>
            </body>
            </html>
            """
            
            self.wfile.write(html.encode())
            
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 - Not Found</h1><p>Return to <a href='/'>status page</a></p>")
    
    def log_message(self, format, *args):
        """Override to reduce log noise."""
        pass

def main():
    """Start the HTTP server."""
    with socketserver.TCPServer((HOST, PORT), ClawChatHandler) as httpd:
        print(f"🚀 ClawChat HTTP Server started")
        print(f"📡 IP: {HOST} (public: 45.135.36.44)")
        print(f"🔌 Port: {PORT}")
        print(f"🌐 Web: http://45.135.36.44:{PORT}/")
        print(f"📊 Status: http://45.135.36.44:{PORT}/status")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📝 Note: This is a temporary HTTP server.")
        print(f"       Full WebSocket server will run on port 8765 once dependencies are installed.")
        print(f"       Dependencies needed: websockets, pyyaml")
        print(f"\nPress Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        finally:
            httpd.server_close()

if __name__ == "__main__":
    main()