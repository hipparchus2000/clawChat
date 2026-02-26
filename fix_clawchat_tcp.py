#!/usr/bin/env python3
"""
Fix ClawChat server-LLM communication from UDP to TCP.
Preserves UDP hole punching for client-server communication.
"""

import os
import sys
from pathlib import Path

# Path to ClawChat directory
CLAWCHAT_DIR = "/home/openclaw/.openclaw/workspace/users/jeff/projects/clawchat/udp_hole_punching"

def fix_main_py():
    """Fix main.py server to use TCP for LLM communication."""
    
    main_py_path = Path(CLAWCHAT_DIR) / "src" / "server" / "main.py"
    
    if not main_py_path.exists():
        print(f"❌ main.py not found at {main_py_path}")
        return False
    
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Replace UDP socket creation for LLM communication with TCP
    old_llm_socket_code = '''        # LLM relay socket
        self.llm_socket: Optional[socket.socket] = None'''
    
    new_llm_socket_code = '''        # LLM relay socket (TCP for localhost reliability)
        self.llm_socket: Optional[socket.socket] = None
        self.llm_connected: bool = False'''
    
    if old_llm_socket_code in content:
        content = content.replace(old_llm_socket_code, new_llm_socket_code)
        print("✅ Updated LLM socket definition in main.py")
    else:
        print("⚠️  LLM socket definition not found in expected format")
    
    # Replace the _connect_to_llm_server method
    old_connect_method = '''    def _connect_to_llm_server(self) -> bool:
        """Connect to LLM server on localhost."""
        try:
            self.llm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.llm_socket.settimeout(2.0)
            
            # Send ping to verify connection
            ping_msg = Message(
                message_type=MessageType.PING,
                connection_id="server-ping",
                payload=b""
            )
            
            try:
                self.llm_socket.sendto(ping_msg.to_bytes(), 
                                     (self.llm_server_ip, self.llm_server_port))
                data, addr = self.llm_socket.recvfrom(1024)
                response = Message.from_bytes(data)
                
                if response.message_type == MessageType.PONG:
                    print(f"    [Server] Connected to LLM server at {addr}")
                    return True
                    
            except socket.timeout:
                print(f"    [Server] LLM server timeout at {self.llm_server_ip}:{self.llm_server_port}")
                self.llm_socket = None
                return False
                
        except Exception as e:
            print(f"    [Server] LLM connection error: {e}")
            self.llm_socket = None
            return False'''
    
    new_connect_method = '''    def _connect_to_llm_server(self) -> bool:
        """Connect to LLM server on localhost using TCP."""
        try:
            self.llm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.llm_socket.settimeout(5.0)
            
            # Connect to LLM server
            self.llm_socket.connect((self.llm_server_ip, self.llm_server_port))
            
            # Send ping to verify connection
            ping_msg = Message(
                message_type=MessageType.PING,
                connection_id="server-ping",
                payload=b""
            )
            
            self.llm_socket.send(ping_msg.to_bytes())
            
            # Receive response
            data = self.llm_socket.recv(1024)
            if not data:
                print(f"    [Server] LLM server closed connection")
                self.llm_socket.close()
                self.llm_socket = None
                return False
                
            response = Message.from_bytes(data)
            
            if response.message_type == MessageType.PONG:
                print(f"    [Server] Connected to LLM server at {self.llm_server_ip}:{self.llm_server_port}")
                self.llm_connected = True
                return True
            else:
                print(f"    [Server] Unexpected response from LLM server: {response.message_type}")
                self.llm_socket.close()
                self.llm_socket = None
                return False
                
        except socket.timeout:
            print(f"    [Server] LLM server timeout at {self.llm_server_ip}:{self.llm_server_port}")
            if self.llm_socket:
                self.llm_socket.close()
                self.llm_socket = None
            return False
            
        except ConnectionRefusedError:
            print(f"    [Server] LLM server refused connection at {self.llm_server_ip}:{self.llm_server_port}")
            if self.llm_socket:
                self.llm_socket.close()
                self.llm_socket = None
            return False
            
        except Exception as e:
            print(f"    [Server] LLM connection error: {e}")
            if self.llm_socket:
                self.llm_socket.close()
                self.llm_socket = None
            return False'''
    
    if old_connect_method in content:
        content = content.replace(old_connect_method, new_connect_method)
        print("✅ Updated _connect_to_llm_server method in main.py")
    else:
        print("⚠️  _connect_to_llm_server method not found in expected format")
    
    # Replace the _send_to_llm_server method
    old_send_method = '''    def _send_to_llm_server(self, msg: Message) -> Optional[Message]:
        """Send message to LLM server and wait for response."""
        if not self.llm_socket:
            if not self._connect_to_llm_server():
                return None
        
        try:
            self.llm_socket.sendto(msg.to_bytes(),
                                 (self.llm_server_ip, self.llm_server_port))
            
            # Wait for response (longer timeout for AI processing)
            self.llm_socket.settimeout(60.0)  # 60s for AI processing
            data, _ = self.llm_socket.recvfrom(8192)
            response = Message.from_bytes(data)
            return response
            
        except socket.timeout:
            print(f"    [Server] LLM response timeout")
            return None
        except Exception as e:
            print(f"    [Server] LLM communication error: {e}")
            self.llm_socket = None
            return None'''
    
    new_send_method = '''    def _send_to_llm_server(self, msg: Message) -> Optional[Message]:
        """Send message to LLM server and wait for response (TCP)."""
        if not self.llm_socket or not self.llm_connected:
            if not self._connect_to_llm_server():
                return None
        
        try:
            # Send message
            self.llm_socket.send(msg.to_bytes())
            
            # Wait for response (longer timeout for AI processing)
            self.llm_socket.settimeout(60.0)  # 60s for AI processing
            
            # Receive response
            data = self.llm_socket.recv(8192)
            if not data:
                print(f"    [Server] LLM server closed connection during response")
                self.llm_socket.close()
                self.llm_socket = None
                self.llm_connected = False
                return None
                
            response = Message.from_bytes(data)
            return response
            
        except socket.timeout:
            print(f"    [Server] LLM response timeout")
            # Don't close socket on timeout - might be processing
            return None
        except ConnectionError as e:
            print(f"    [Server] LLM connection error: {e}")
            if self.llm_socket:
                self.llm_socket.close()
                self.llm_socket = None
            self.llm_connected = False
            return None
        except Exception as e:
            print(f"    [Server] LLM communication error: {e}")
            if self.llm_socket:
                self.llm_socket.close()
                self.llm_socket = None
            self.llm_connected = False
            return None'''
    
    if old_send_method in content:
        content = content.replace(old_send_method, new_send_method)
        print("✅ Updated _send_to_llm_server method in main.py")
    else:
        print("⚠️  _send_to_llm_server method not found in expected format")
    
    # Write updated file
    with open(main_py_path, 'w') as f:
        f.write(content)
    
    return True

def fix_llm_server_py():
    """Fix llm_server.py to use TCP for server communication."""
    
    llm_server_path = Path(CLAWCHAT_DIR) / "src" / "server" / "llm_server.py"
    
    if not llm_server_path.exists():
        print(f"❌ llm_server.py not found at {llm_server_path}")
        return False
    
    with open(llm_server_path, 'r') as f:
        content = f.read()
    
    # Replace UDP socket creation with TCP
    old_socket_code = '''        # Create socket (for hole punching server only - localhost)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('127.0.0.1', self.server_port))
        self.socket.settimeout(1.0)'''
    
    new_socket_code = '''        # Create TCP socket (for hole punching server only - localhost)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('127.0.0.1', self.server_port))
        self.socket.listen(1)  # Listen for incoming connections
        self.socket.settimeout(1.0)
        self.client_socket = None
        self.client_address = None'''
    
    if old_socket_code in content:
        content = content.replace(old_socket_code, new_socket_code)
        print("✅ Updated socket creation in llm_server.py")
    else:
        print("⚠️  Socket creation code not found in expected format")
    
    # Replace the _accept_connection method or add it
    old_accept_check = '''            # Check for incoming messages from hole punching server
            try:
                data, addr = self.socket.recvfrom(8192)
            except socket.timeout:
                continue'''
    
    new_accept_check = '''            # Check for incoming connections from hole punching server
            if not self.client_socket:
                try:
                    self.socket.settimeout(1.0)
                    self.client_socket, self.client_address = self.socket.accept()
                    self.client_socket.settimeout(1.0)
                    print(f"    [LLM Server] Accepted connection from {self.client_address}")
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"    [LLM Server] Accept error: {e}")
                    continue
            
            # Check for incoming messages from connected client
            try:
                data = self.client_socket.recv(8192)
                if not data:
                    # Client disconnected
                    print(f"    [LLM Server] Client {self.client_address} disconnected")
                    self.client_socket.close()
                    self.client_socket = None
                    self.client_address = None
                    continue
                    
                addr = self.client_address  # Use stored address
            except socket.timeout:
                continue'''
    
    if old_accept_check in content:
        content = content.replace(old_accept_check, new_accept_check)
        print("✅ Updated connection acceptance in llm_server.py")
    else:
        print("⚠️  Connection acceptance code not found in expected format")
    
    # Replace send response code
    old_send_response = '''            # Send response back to hole punching server
            self.socket.sendto(msg.to_bytes(), addr)'''
    
    new_send_response = '''            # Send response back to connected client
            if self.client_socket:
                self.client_socket.send(msg.to_bytes())'''
    
    if old_send_response in content:
        content = content.replace(old_send_response, new_send_response)
        print("✅ Updated send response in llm_server.py")
    else:
        print("⚠️  Send response code not found in expected format")
    
    # Update cleanup method
    old_cleanup = '''        if self.socket:
            self.socket.close()'''
    
    new_cleanup = '''        if self.client_socket:
            self.client_socket.close()
        if self.socket:
            self.socket.close()'''
    
    if old_cleanup in content:
        content = content.replace(old_cleanup, new_cleanup)
        print("✅ Updated cleanup in llm_server.py")
    else:
        print("⚠️  Cleanup code not found in expected format")
    
    # Write updated file
    with open(llm_server_path, 'w') as f:
        f.write(content)
    
    return True

def create_test_script():
    """Create a test script to verify TCP communication."""
    
    test_script = '''#!/usr/bin/env python3
"""
Test TCP communication between main server and LLM server.
"""

import socket
import time
import threading
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from protocol.messages import Message, MessageType

def run_llm_server_mock(port=55556):
    """Mock LLM server that accepts TCP connections."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SOCK_REUSEADDR, 1)
    sock.bind(('127.0.0.1', port))
    sock.listen(1)
    sock.settimeout(5.0)
    
    print(f"[Mock LLM Server] Listening on 127.0.0.1:{port}")
    
    try:
        client_sock, addr = sock.accept()
        print(f"[Mock LLM Server] Accepted connection from {addr}")
        client_sock.settimeout(2.0)
        
        # Receive ping
        data = client_sock.recv(1024)
            if data:
            msg = Message.from_bytes(data)
            print(f"[Mock LLM Server] Received: {msg.message_type}")
            
            # Send pong
            pong = Message(
                message_type=MessageType.PONG,
                connection_id=msg.connection_id,
                payload=b"pong"
            )
            client_sock.send(pong.to_bytes())
            print("[Mock LLM Server] Sent PONG")
        
        client_sock.close()
    except socket.timeout:
        print("[Mock LLM Server] Timeout waiting for connection")
    finally:
        sock.close()

def test_tcp_connection():
    """Test TCP connection from main server to LLM server."""
    
    # Start mock LLM server in background thread
    llm_thread = threading.Thread(target=run_llm_server_mock)
    llm_thread.daemon = True
    llm_thread.start()
    
    time.sleep(1)  # Give server time to start
    
    # Try to connect (like main.py would)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        print("[Test Client] Connecting to 127.0.0.1:55556...")
        sock.connect(('127.0.0.1', 55556))
        print("[Test Client] Connected!")
        
        # Send ping
        ping = Message(
            message_type=MessageType.PING,
            connection_id="test-connection",
            payload=b"ping"
        )
        sock.send(ping.to_bytes())
        print("[Test Client] Sent PING")
        
        # Receive pong
        data = sock.recv(1024)
        if data:
            response = Message.from_bytes(data)
            print(f"[Test Client] Received: {response.message_type}")
            if response.message_type == MessageType.PONG:
                print("✅ TCP communication test PASSED!")
            else:
                print(f"❌ Unexpected response: {response.message_type}")
        else:
            print("❌ No response received")
        
        sock.close()
        
    except ConnectionRefusedError:
        print("❌ Connection refused - LLM server not running")
    except socket.timeout:
        print("❌ Connection timeout")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    llm_thread.join(timeout=3)

if __name__ == "__main__":
    print("🔧 Testing TCP communication fix...")
    test_tcp_connection()'''
    
    test_path = Path(CLAWCHAT_DIR) / "test_tcp_fix.py"
    with open(test_path, 'w') as f:
        f.write(test_script)
    
    print(f"✅ Created test script at {test_path}")
    return test_path

def main():
    print("🔧 Fixing ClawChat server-LLM communication from UDP to TCP...")
    print("=" * 60)
    
    # Apply fixes
    if fix_main_py():
        print("✅ main.py updated successfully")
    else:
        print("❌ Failed to update main.py")
        return False
    
    print()
    
    if fix_llm_server_py():
        print("✅ llm_server.py updated successfully")
    else:
        print("❌ Failed to update llm_server.py")
        return False
    
    print()
    
    # Create test script
    test_path = create