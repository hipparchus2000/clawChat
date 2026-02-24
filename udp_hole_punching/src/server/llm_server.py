#!/usr/bin/env python3
"""
ClawChat LLM Server with Cron Support

Integrates with LLM Bridge and Cron Scheduler for persistent
AI conversations and scheduled tasks.
"""

import os
import sys
import time
import socket
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from security.encryption import CryptoManager, derive_session_keys
from security.file_manager import SecurityFileManager
from protocol.messages import Message, MessageType
from llm_bridge import LLMBridge, LLMConfig
from cron_scheduler import CronScheduler
from file_protocol_handler import FileProtocolHandler


class ClawChatLLMServer:
    """ClawChat Server with LLM Bridge and Cron Scheduler."""
    
    def __init__(
        self,
        security_directory: str,
        bootstrap_key: bytes,
        server_ip: str,
        server_port: int = None,
        server_id: str = "clawchat-llm-server",
        llm_provider: str = 'deepseek',
        llm_save_file: str = 'llm_session.json',
        cron_file: str = './context/CRON.md'
    ):
        self.security_directory = security_directory
        self.bootstrap_key = bootstrap_key
        self.server_ip = server_ip
        self.server_port = server_port or self._select_random_port()
        self.server_id = server_id
        
        # LLM Bridge
        self.llm_config = LLMConfig(llm_provider)
        self.llm_bridge = LLMBridge(self.llm_config, llm_save_file)
        
        # Cron Scheduler
        self.cron_scheduler = None
        self.cron_file = cron_file
        
        # File Protocol Handler
        base_path = os.environ.get('CLAWCHAT_BASE_PATH', './clawchat_data')
        self.file_handler = FileProtocolHandler(base_path, allow_write=True)
        
        # Crypto
        self.crypto = None
        
        # State
        self.running = False
        self.socket = None
        self.shared_secret = None
        self.connection_id = None
        self.peer_address = None
        
        # Stats
        self.messages_received = 0
        self.messages_sent = 0
    
    def _select_random_port(self) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def generate_initial_security_file(self) -> str:
        from server.file_generator import SecurityFileGenerator
        
        generator = SecurityFileGenerator(
            self.security_directory,
            self.bootstrap_key,
            self.server_id
        )
        generator.set_server_info(self.server_ip, self.server_port)
        
        filepath = generator.generate_file()
        self.shared_secret = generator.get_current_secret()
        
        return filepath
    
    def _setup_context(self):
        """Load context files and set system prompt."""
        context_dir = os.environ.get('CLAWCHAT_CONTEXT_DIR', './context')
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from context_loader import ContextLoader, create_default_context_files
        
        # Create default files if they don't exist
        create_default_context_files(context_dir)
        
        # Load context
        loader = ContextLoader(context_dir)
        system_prompt = loader.load_all()
        
        self.llm_bridge.set_system_prompt(system_prompt)
        print(f"[Server] Loaded context from {context_dir}")
        for name in loader.get_loaded_files():
            print(f"[Server]   - {name}")
    
    def _setup_cron(self):
        """Setup cron scheduler."""
        self.cron_scheduler = CronScheduler(
            cron_file=self.cron_file,
            llm_bridge=self.llm_bridge
        )
        
        # Set up callbacks
        self.cron_scheduler.on_job_execute = lambda job: print(f"[Cron] Starting: {job.name}")
        self.cron_scheduler.on_job_complete = lambda job, result: print(f"[Cron] Completed: {job.name}")
        
        self.cron_scheduler.start()
    
    def start(self):
        print(f"\n{'='*60}")
        print(f"  ClawChat LLM Server")
        print(f"  Provider: {self.llm_config.provider}")
        print(f"{'='*60}\n")
        
        # Generate security file
        if not self.shared_secret:
            filepath = self.generate_initial_security_file()
            print(f"[Server] Security file: {filepath}")
        
        # Setup crypto
        self.connection_id = f"{self.server_id}-{int(time.time())}"
        self.crypto = CryptoManager()
        keys = derive_session_keys(
            self.shared_secret,
            self.connection_id,
            int(time.time())
        )
        self.crypto.set_session_keys(keys)
        
        # Create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.server_port))
        self.socket.settimeout(1.0)
        
        # Setup LLM with context
        self._setup_context()
        self.llm_bridge.start()
        
        # Setup cron
        self._setup_cron()
        
        print(f"[Server] Listening on UDP {self.server_ip}:{self.server_port}")
        print(f"[Server] LLM Bridge: {self.llm_config.provider}")
        print(f"[Server] Cron Scheduler: {len(self.cron_scheduler.jobs)} jobs")
        print(f"[Server] Press Ctrl+C to stop\n")
        
        self.running = True
        
        try:
            while self.running:
                self._process_loop()
        except KeyboardInterrupt:
            print("\n[Server] Stopping...")
        finally:
            self.stop()
    
    def _process_loop(self):
        try:
            data, addr = self.socket.recvfrom(2048)
            self._handle_packet(data, addr)
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[Server] Error: {e}")
    
    def _handle_packet(self, data, addr):
        try:
            plaintext = self.crypto.decrypt_packet(data)
        except:
            return
        
        msg = Message.from_bytes(plaintext)
        self.messages_received += 1
        
        if not self.peer_address:
            self.peer_address = addr
            print(f"[Server] Client connected: {addr}")
        
        if msg.msg_type == MessageType.CHAT:
            self._handle_chat(msg, addr)
        elif msg.msg_type == MessageType.KEEPALIVE:
            self._send_message(MessageType.KEEPALIVE, {'pong': True})
        # Handle cron API requests
        elif msg.msg_type == MessageType.CRON_LIST:
            self._handle_cron_list(msg, addr)
        elif msg.msg_type == MessageType.CRON_RUN:
            self._handle_cron_run(msg, addr)
        elif msg.msg_type == MessageType.CRON_RELOAD:
            self._handle_cron_reload(msg, addr)
        # Handle file protocol requests
        elif msg.msg_type == MessageType.FILE_LIST:
            self._handle_file_list(msg, addr)
        elif msg.msg_type == MessageType.FILE_DOWNLOAD:
            self._handle_file_download(msg, addr)
        elif msg.msg_type == MessageType.FILE_UPLOAD:
            self._handle_file_upload(msg, addr)
        elif msg.msg_type == MessageType.FILE_DELETE:
            self._handle_file_delete(msg, addr)
        elif msg.msg_type == MessageType.FILE_RENAME:
            self._handle_file_rename(msg, addr)
        elif msg.msg_type == MessageType.FILE_MKDIR:
            self._handle_file_mkdir(msg, addr)
    
    def _handle_chat(self, msg, addr):
        text = msg.payload.get('text', '')
        sender = msg.payload.get('sender', 'unknown')
        
        print(f"[Chat] {sender}: {text}")
        
        # Send to LLM
        self.llm_bridge.write(text)
        
        # Wait for response
        max_wait = 60
        start = time.time()
        
        while time.time() - start < max_wait:
            response = self.llm_bridge.read(timeout=0.5)
            if response:
                self._send_message(MessageType.CHAT, {
                    'text': response,
                    'sender': 'assistant'
                })
                print(f"[Chat] Assistant: {response[:80]}...")
                return
            
            if not self.llm_bridge.is_processing():
                break
        
        self._send_message(MessageType.CHAT, {
            'text': '[No response from AI]',
            'sender': 'system'
        })
    
    def _handle_cron_list(self, msg, addr):
        """Handle request for cron job list."""
        if not self.cron_scheduler:
            return
        
        jobs = self.cron_scheduler.get_jobs()
        self._send_message(MessageType.CRON_LIST, {'jobs': jobs})
        print(f"[Cron API] Sent job list ({len(jobs)} jobs)")
    
    def _handle_cron_run(self, msg, addr):
        """Handle request to run a job immediately."""
        if not self.cron_scheduler:
            return
        
        job_name = msg.payload.get('job_name')
        success = self.cron_scheduler.run_job_now(job_name)
        
        self._send_message(MessageType.CRON_RUN, {
            'job_name': job_name,
            'success': success
        })
        print(f"[Cron API] Manual run: {job_name} ({'ok' if success else 'not found'})")
    
    def _handle_cron_reload(self, msg, addr):
        """Handle request to reload cron file."""
        if not self.cron_scheduler:
            return
        
        self.cron_scheduler.reload()
        jobs = self.cron_scheduler.get_jobs()
        
        self._send_message(MessageType.CRON_RELOAD, {
            'success': True,
            'job_count': len(jobs)
        })
        print(f"[Cron API] Reloaded ({len(jobs)} jobs)")
    
    # ============== File Protocol Handlers ==============
    
    def _handle_file_list(self, msg, addr):
        """Handle file list request."""
        path = msg.payload.get('path', '.')
        result = self.file_handler.handle_list(path)
        self._send_message(MessageType.FILE_LIST, result)
        if result.get('success'):
            print(f"[File API] Listed: {path} ({result.get('count', 0)} items)")
    
    def _handle_file_download(self, msg, addr):
        """Handle file download request."""
        path = msg.payload.get('path', '')
        offset = msg.payload.get('offset', 0)
        result = self.file_handler.handle_download(path, offset)
        self._send_message(MessageType.FILE_DOWNLOAD, result)
        if result.get('success'):
            print(f"[File API] Download: {path} ({result.get('size', 0)} bytes)")
    
    def _handle_file_upload(self, msg, addr):
        """Handle file upload request."""
        path = msg.payload.get('path', '')
        data = msg.payload.get('data', '')
        offset = msg.payload.get('offset', 0)
        append = msg.payload.get('append', False)
        result = self.file_handler.handle_upload(path, data, offset, append)
        self._send_message(MessageType.FILE_UPLOAD, result)
        if result.get('success'):
            print(f"[File API] Upload: {path} ({result.get('bytes_written', 0)} bytes)")
    
    def _handle_file_delete(self, msg, addr):
        """Handle file delete request."""
        path = msg.payload.get('path', '')
        result = self.file_handler.handle_delete(path)
        self._send_message(MessageType.FILE_DELETE, result)
        status = 'deleted' if result.get('success') else 'failed'
        print(f"[File API] Delete: {path} ({status})")
    
    def _handle_file_rename(self, msg, addr):
        """Handle file rename request."""
        path = msg.payload.get('path', '')
        new_name = msg.payload.get('new_name', '')
        result = self.file_handler.handle_rename(path, new_name)
        self._send_message(MessageType.FILE_RENAME, result)
        status = 'renamed' if result.get('success') else 'failed'
        print(f"[File API] Rename: {path} -> {new_name} ({status})")
    
    def _handle_file_mkdir(self, msg, addr):
        """Handle mkdir request."""
        path = msg.payload.get('path', '')
        result = self.file_handler.handle_mkdir(path)
        self._send_message(MessageType.FILE_MKDIR, result)
        status = 'created' if result.get('success') else 'failed'
        print(f"[File API] Mkdir: {path} ({status})")
    
    def _send_message(self, msg_type, payload):
        if not self.peer_address:
            return
        
        msg = Message(msg_type=msg_type, payload=payload)
        encrypted = self.crypto.encrypt_packet(msg.to_bytes())
        
        try:
            self.socket.sendto(encrypted, self.peer_address)
            self.messages_sent += 1
        except Exception as e:
            print(f"[Server] Send error: {e}")
    
    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
        if self.llm_bridge:
            self.llm_bridge.stop()
        if self.cron_scheduler:
            self.cron_scheduler.stop()
        print(f"\n[Server] Stopped. Rx: {self.messages_received}, Tx: {self.messages_sent}")


def main():
    parser = argparse.ArgumentParser(description='ClawChat LLM Server')
    parser.add_argument('--ip', default='127.0.0.1', help='Server IP')
    parser.add_argument('--port', type=int, default=None, help='Server port')
    parser.add_argument('--security-dir', default='C:/temp/clawchat/security',
                        help='Security files directory')
    parser.add_argument('--llm-provider', default='deepseek',
                        choices=['deepseek', 'openai', 'anthropic'],
                        help='LLM provider')
    parser.add_argument('--llm-session', default='llm_session.json',
                        help='LLM session save file')
    parser.add_argument('--cron-file', default='./context/CRON.md',
                        help='Cron jobs file')
    
    args = parser.parse_args()
    
    bootstrap_key = os.environ.get(
        'CLAWCHAT_BOOTSTRAP_KEY',
        'default-key-32bytes-for-testing!'
    ).encode()[:32]
    
    server = ClawChatLLMServer(
        security_directory=args.security_dir,
        bootstrap_key=bootstrap_key,
        server_ip=args.ip,
        server_port=args.port,
        llm_provider=args.llm_provider,
        llm_save_file=args.llm_session,
        cron_file=args.cron_file
    )
    
    server.start()


if __name__ == "__main__":
    main()
