#!/usr/bin/env python3
"""
Two-Process Test - Run server and client simultaneously
"""

import os
import sys
import time
import subprocess
import tempfile
import signal
from pathlib import Path

def main():
    print("="*60)
    print("Two-Process Test: Server + Client")
    print("="*60)
    print()
    
    # Setup
    bootstrap_key = "test-key-32bytes-long!!!"
    temp_dir = tempfile.mkdtemp(prefix="clawchat_")
    security_dir = os.path.join(temp_dir, "security")
    os.makedirs(security_dir)
    
    print(f"Temp directory: {temp_dir}")
    print()
    
    # Environment for both processes
    env = os.environ.copy()
    env["CLAWCHAT_BOOTSTRAP_KEY"] = bootstrap_key
    env["PYTHONPATH"] = str(Path(__file__).parent / "src")
    
    # Start server
    print("[1] Starting server...")
    server_cmd = [
        sys.executable, "run_server.py",
        "--ip", "127.0.0.1",
        "--port", "55555"
    ]
    
    server_process = subprocess.Popen(
        server_cmd,
        cwd=str(Path(__file__).parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    
    # Wait for server to create security file
    print("    Waiting for server to create security file...")
    sec_file = None
    timeout = 10
    start = time.time()
    
    while time.time() - start < timeout:
        # Check for security file
        for f in os.listdir(security_dir):
            if f.endswith(".sec"):
                sec_file = os.path.join(security_dir, f)
                break
        if sec_file:
            break
        time.sleep(0.5)
    
    if not sec_file:
        print("ERROR: Server didn't create security file!")
        server_process.terminate()
        return
    
    print(f"    Security file created: {sec_file}")
    print()
    
    # Give server a moment to start listening
    time.sleep(1)
    
    # Start client with automated input
    print("[2] Starting client...")
    
    # Create a simple client script that auto-sends messages
    client_script = f"""
import sys
import time
sys.path.insert(0, 'src')

from src.client.main import ClawChatClient

client = ClawChatClient(bootstrap_key=b"{bootstrap_key}")

if not client.load_security_file("{sec_file}"):
    print("Failed to load security file")
    sys.exit(1)

print("[Client] Connecting...")
if not client.connect():
    print("[Client] Failed to connect")
    sys.exit(1)

print("[Client] Connected!")
print()

# Send test messages
test_messages = ["Hello!", "Test message 2", "Final test"]
for msg in test_messages:
    print(f"[Client] Sending: {{msg}}")
    client._send_chat(msg)
    time.sleep(0.5)

# Wait a bit for responses
time.sleep(2)

print()
print(f"[Client] Messages sent: {{client.messages_sent}}")
print(f"[Client] Messages received: {{client.messages_received}}")

client.stop()
print("[Client] Done!")
"""
    
    client_path = os.path.join(temp_dir, "auto_client.py")
    with open(client_path, "w") as f:
        f.write(client_script)
    
    # Run client
    client_process = subprocess.Popen(
        [sys.executable, client_path],
        cwd=str(Path(__file__).parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Stream output from both
    print("[3] Running... (10 seconds)")
    print("-" * 60)
    
    server_output = []
    client_output = []
    
    start_time = time.time()
    while time.time() - start_time < 10:
        # Read server output
        import select
        
        # Check if processes are still running
        if server_process.poll() is not None and client_process.poll() is not None:
            break
        
        # Try to read output (non-blocking)
        try:
            if server_process.stdout:
                line = server_process.stdout.readline()
                if line:
                    print(f"[SERVER] {line.rstrip()}")
                    server_output.append(line)
        except:
            pass
        
        try:
            if client_process.stdout:
                line = client_process.stdout.readline()
                if line:
                    print(f"[CLIENT] {line.rstrip()}")
                    client_output.append(line)
        except:
            pass
        
        time.sleep(0.1)
    
    print("-" * 60)
    print()
    
    # Cleanup
    print("[4] Cleaning up...")
    
    try:
        client_process.terminate()
        client_process.wait(timeout=2)
    except:
        client_process.kill()
    
    try:
        server_process.terminate()
        server_process.wait(timeout=2)
    except:
        server_process.kill()
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print()
    print("="*60)
    print("Test complete!")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
