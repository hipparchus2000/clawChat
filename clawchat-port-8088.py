#!/usr/bin/env python3
"""
ClawChat Server on Port 8088
Less common port that's less likely to be blocked.
"""

import http.server
import socketserver
import json
import os
from datetime import datetime

PORT = 8088  # Changed from 8080 to 8088
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
                <title>ClawChat Server (Port 8088)</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .status {{ padding: 20px; background: #f0f0f0; border-radius: 5px; }}
                    .online {{ color: green; font-weight: bold; }}
                    .warning {{ color: orange; font-weight: bold; }}
                </style>
            </head>
            <body>
                <h1>🦀 ClawChat Server</h1>
                <div class="status">
                    <p><span class="online">● ONLINE</span> - Server is running on port 8088</p>
                    <p><strong>IP:</strong> 45.135.36.44</p>
                    <p><strong>Port:</strong> 8088 (HTTP - less common port)</p>
                    <p><strong>Previous port:</strong> 8080 (may be blocked)</p>
                    <p><strong>WebSocket Port:</strong> 8765 (coming soon)</p>
                    <p><strong>Status:</strong> Simple HTTP server running. WebSocket server requires dependencies.</p>
                    <p><strong>Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                <h3>Endpoints:</h3>
                <ul>
                    <li><a href="/">/</a> - This status page</li>
                    <li><a href="/status">/status</a> - JSON status API</li>
                    <li><a href="/chat">/chat</a> - Chat interface (placeholder)</li>
                    <li><a href="/test">/test</a> - Simple test endpoint</li>
                </ul>
                <p class="warning">⚠️ Note: Port 8080 may be blocked by firewalls. Using port 8088 instead.</p>
                <p><em>This is a temporary HTTP server. Full WebSocket server will run on port 8765 once dependencies are installed.</em></p>
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
                "port": 8088,
                "previous_port": 8080,
                "note": "Port 8088 used because 8080 may be blocked",
                "websocket_port": 8765,
                "websocket_status": "pending_dependencies",
                "timestamp": datetime.now().isoformat(),
                "endpoints": ["/", "/status", "/chat", "/test"]
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
            
        elif self.path == "/test":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ClawChat test endpoint - server is working!\n")
            
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
        print(f"🚀 ClawChat HTTP Server started on port {PORT}")
        print(f"📡 IP: {HOST} (public: 45.135.36.44)")
        print(f"🔌 Port: {PORT} (less common, less likely to be blocked)")
        print(f"🌐 Web: http://45.135.36.44:{PORT}/")
        print(f"📊 Status: http://45.135.36.44:{PORT}/status")
        print(f"🧪 Test: http://45.135.36.44:{PORT}/test")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📝 Note: Port 8080 may be blocked by firewalls/ISPs.")
        print(f"       Using port 8088 instead.")
        print(f"\nPress Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        finally:
            httpd.server_close()

if __name__ == "__main__":
    main()