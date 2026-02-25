#!/usr/bin/env python3
"""
ClawChat LLM Server with Cron Support

Integrates with LLM Bridge and Cron Scheduler for persistent
AI conversations and scheduled tasks.
"""

import os
import re
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
from server.file_protocol_handler import FileProtocolHandler
from security.key_rotation import KeyRotator


class ClawChatLLMServer:
    """ClawChat Server with LLM Bridge and Cron Scheduler."""
    
    # Default port for LLM server (localhost only)
    DEFAULT_PORT = 55556
    
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
        # Use fixed default port (55556) unless explicitly overridden
        self.server_port = server_port if server_port is not None else self.DEFAULT_PORT
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
        
        # Security file generator for auto-regeneration
        self.file_generator = None
        
        # Key rotation
        self.key_rotator = None
    
    def _select_random_port(self) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def generate_initial_security_file(self) -> str:
        from server.file_generator import SecurityFileGenerator
        
        self.file_generator = SecurityFileGenerator(
            self.security_directory,
            self.bootstrap_key,
            self.server_id
        )
        self.file_generator.set_server_info(self.server_ip, self.server_port)
        
        filepath = self.file_generator.generate_file()
        self.shared_secret = self.file_generator.get_current_secret()
        
        # Start auto-regeneration (every 10 min if no client)
        self.file_generator.start_auto_regeneration()
        
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
        
        # Also send job results to chat
        def on_complete_with_chat(job, result):
            print(f"[Cron] Completed: {job.name}")
            self._handle_cron_result_to_chat(job, result)
        
        self.cron_scheduler.on_job_complete = on_complete_with_chat
        
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
        
        # Setup key rotation (1 hour interval)
        self.key_rotator = KeyRotator(
            self.shared_secret,
            self.connection_id,
            on_rotation=self._on_key_rotation
        )
        
        # Create socket (for hole punching server only - localhost)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('127.0.0.1', self.server_port))
        self.socket.settimeout(1.0)
        
        # Setup LLM with context
        self._setup_context()
        self.llm_bridge.start()
        
        # Setup cron
        self._setup_cron()
        
        print(f"[Server] Listening on UDP 127.0.0.1:{self.server_port}")
        print(f"[Server] LLM Bridge: {self.llm_config.provider}")
        print(f"[Server] Cron Scheduler: {len(self.cron_scheduler.jobs)} jobs")
        print(f"[Server] Security file valid for 11 minutes")
        print(f"[Server] Auto-regeneration: every 10 min until client connects")
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
        # Check for key rotation
        if self.key_rotator and self.key_rotator.check_rotation_needed():
            print("[Server] Key rotation due")
            # No key rotation for internal relay - hole punching server handles it
            pass
        
        # Receive message from hole punching server
        try:
            data, addr = self.socket.recvfrom(8192)
            self._handle_message(data, addr)
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[Server] Error: {e}")
    
    def _handle_message(self, data: bytes, addr):
        """Handle message from hole punching server."""
        try:
            msg = Message.from_bytes(data)
            
            if msg.msg_type == MessageType.CHAT:
                self._handle_chat(msg, addr)
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
            elif msg.msg_type == MessageType.CRON_LIST:
                self._handle_cron_list(msg, addr)
            elif msg.msg_type == MessageType.CRON_RUN:
                self._handle_cron_run(msg, addr)
            elif msg.msg_type == MessageType.CRON_RELOAD:
                self._handle_cron_reload(msg, addr)
            elif msg.msg_type == MessageType.CRON_ADD:
                self._handle_cron_add(msg, addr)
            elif msg.msg_type == MessageType.CRON_REMOVE:
                self._handle_cron_remove(msg, addr)
            elif msg.msg_type == MessageType.KEEPALIVE:
                self._send_message(MessageType.KEEPALIVE, {'pong': True}, addr)
            
        except Exception as e:
            print(f"[Server] Message error: {e}")
    
    def _send_message(self, msg_type: MessageType, payload: dict, addr):
        """Send response to hole punching server."""
        try:
            msg = Message(msg_type=msg_type, payload=payload)
            self.socket.sendto(msg.to_bytes(), addr)
        except Exception as e:
            print(f"[Server] Send error: {e}")
    
    def _handle_chat(self, msg: Message, addr):
        """Handle chat message from hole punching server."""
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
                }, addr)
                print(f"[Chat] Assistant: {response[:80]}...")
                return
            
            if not self.llm_bridge.is_processing():
                break
        
        self._send_message(MessageType.CHAT, {
            'text': '[No response from AI]',
            'sender': 'system'
        }, addr)
    
    def _handle_file_list(self, msg: Message, addr):
        """Handle file list request from hole punching server."""
        path = msg.payload.get('path', '.')
        result = self.file_handler.handle_list(path)
        self._send_message(MessageType.FILE_LIST, result, addr)
        if result.get('success'):
            print(f"[File API] Listed: {path} ({result.get('count', 0)} items)")
    
    def _handle_file_download(self, msg: Message, addr):
        """Handle file download request from hole punching server."""
        path = msg.payload.get('path', '')
        offset = msg.payload.get('offset', 0)
        result = self.file_handler.handle_download(path, offset)
        self._send_message(MessageType.FILE_DOWNLOAD, result, addr)
        if result.get('success'):
            print(f"[File API] Download: {path} ({result.get('size', 0)} bytes)")
    
    def _handle_file_upload(self, msg: Message, addr):
        """Handle file upload request from hole punching server."""
        path = msg.payload.get('path', '')
        data = msg.payload.get('data', '')
        offset = msg.payload.get('offset', 0)
        append = msg.payload.get('append', False)
        result = self.file_handler.handle_upload(path, data, offset, append)
        self._send_message(MessageType.FILE_UPLOAD, result, addr)
        if result.get('success'):
            print(f"[File API] Upload: {path} ({result.get('bytes_written', 0)} bytes)")
    
    def _handle_file_delete(self, msg: Message, addr):
        """Handle file delete request from hole punching server."""
        path = msg.payload.get('path', '')
        result = self.file_handler.handle_delete(path)
        self._send_message(MessageType.FILE_DELETE, result, addr)
        status = 'deleted' if result.get('success') else 'failed'
        print(f"[File API] Delete: {path} ({status})")
    
    def _handle_file_rename(self, msg: Message, addr):
        """Handle file rename request from hole punching server."""
        path = msg.payload.get('path', '')
        new_name = msg.payload.get('new_name', '')
        result = self.file_handler.handle_rename(path, new_name)
        self._send_message(MessageType.FILE_RENAME, result, addr)
        status = 'renamed' if result.get('success') else 'failed'
        print(f"[File API] Rename: {path} -> {new_name} ({status})")
    
    def _handle_file_mkdir(self, msg: Message, addr):
        """Handle mkdir request from hole punching server."""
        path = msg.payload.get('path', '')
        result = self.file_handler.handle_mkdir(path)
        self._send_message(MessageType.FILE_MKDIR, result, addr)
        status = 'created' if result.get('success') else 'failed'
        print(f"[File API] Mkdir: {path} ({status})")
    
    def _handle_cron_list(self, msg: Message, addr):
        """Handle cron list request from hole punching server."""
        if not self.cron_scheduler:
            return
        jobs = self.cron_scheduler.get_jobs()
        self._send_message(MessageType.CRON_LIST, {'jobs': jobs}, addr)
        print(f"[Cron API] Sent job list ({len(jobs)} jobs)")
    
    def _handle_cron_run(self, msg: Message, addr):
        """Handle cron run request from hole punching server."""
        if not self.cron_scheduler:
            return
        job_name = msg.payload.get('job_name')
        success = self.cron_scheduler.run_job_now(job_name)
        self._send_message(MessageType.CRON_RUN, {
            'job_name': job_name,
            'success': success
        }, addr)
        print(f"[Cron API] Manual run: {job_name} ({'ok' if success else 'not found'})")
    
    def _handle_cron_reload(self, msg: Message, addr):
        """Handle cron reload request from hole punching server."""
        if not self.cron_scheduler:
            return
        self.cron_scheduler.reload()
        jobs = self.cron_scheduler.get_jobs()
        self._send_message(MessageType.CRON_RELOAD, {
            'success': True,
            'job_count': len(jobs)
        }, addr)
        print(f"[Cron API] Reloaded ({len(jobs)} jobs)")
    
    def _handle_cron_add(self, msg: Message, addr):
        """Handle cron add request from hole punching server."""
        if not self.cron_scheduler:
            self._send_message(MessageType.CRON_ADD, {
                'success': False,
                'error': 'Cron scheduler not available',
                'job_name': 'unknown'
            }, addr)
            return
        
        schedule = msg.payload.get('schedule', '0 * * * *')
        command = msg.payload.get('command', '')
        comment = msg.payload.get('comment', '')
        enabled = msg.payload.get('enabled', True)
        
        # Generate unique job name from command
        name = self._generate_unique_job_name(command)
        
        success = self.cron_scheduler.add_job(name, schedule, command, comment, enabled)
        
        self._send_message(MessageType.CRON_ADD, {
            'success': success,
            'job_name': name,
            'error': None if success else 'Failed to add job'
        }, addr)
        print(f"[Cron API] Add job: {name} ({'ok' if success else 'failed'})")
    
    def _handle_cron_remove(self, msg: Message, addr):
        """Handle cron remove request from hole punching server."""
        if not self.cron_scheduler:
            self._send_message(MessageType.CRON_REMOVE, {
                'success': False,
                'error': 'Cron scheduler not available',
                'job_name': 'unknown'
            }, addr)
            return
        
        schedule = msg.payload.get('schedule', '')
        command = msg.payload.get('command', '')
        
        # Try to find job by command or schedule+command
        job_name = None
        for job in self.cron_scheduler.get_jobs():
            if job['command'] == command or (job['schedule'] == schedule and job['command'] == command):
                job_name = job['name']
                break
        
        if not job_name:
            self._send_message(MessageType.CRON_REMOVE, {
                'success': False,
                'error': 'Job not found',
                'job_name': command[:30] if command else 'unknown'
            }, addr)
            return
        
        success = self.cron_scheduler.remove_job(job_name)
        
        self._send_message(MessageType.CRON_REMOVE, {
            'success': success,
            'job_name': job_name,
            'error': None if success else 'Failed to remove job'
        }, addr)
        print(f"[Cron API] Remove job: {job_name} ({'ok' if success else 'failed'})")
    
    def _handle_cron_result_to_chat(self, job, result):
        """Send cron job result to chat (callback)."""
        if not self.peer_address:
            return
        
        # Send result to client via hole punching server
        self._send_message(MessageType.CRON_RESULT, {
            'job_name': job.name,
            'result': result,
            'success': not result.startswith('[') and not result.startswith('Error'),
            'timestamp': time.time()
        }, self.peer_address)
        print(f"[Cron] Result sent to chat: {job.name}")
    
    def _generate_unique_job_name(self, command: str) -> str:
        """Generate a unique job name from command string."""
        # Clean up command to create base name
        base = command[:30].strip() if command else 'unnamed_job'
        base = re.sub(r'[^\w\s]', '', base).strip().replace(' ', '_')
        
        # Ensure unique name
        name = base
        counter = 1
        existing_names = {j['name'] for j in self.cron_scheduler.get_jobs()}
        while name in existing_names:
            name = f"{base}_{counter}"
            counter += 1
        
        return name
    
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
            
            # Notify file generator to stop auto-regeneration
            if self.file_generator:
                self.file_generator.mark_client_connected()
        
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
        elif msg.msg_type == MessageType.CRON_ADD:
            self._handle_cron_add(msg, addr)
        elif msg.msg_type == MessageType.CRON_REMOVE:
            self._handle_cron_remove(msg, addr)
        # Handle key rotation
        elif msg.msg_type == MessageType.KEY_ROTATION:
            self._handle_key_rotation(msg, addr)
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
        if self.file_generator:
            self.file_generator.stop_auto_regeneration()
        print(f"\n[Server] Stopped. Rx: {self.messages_received}, Tx: {self.messages_sent}")


def main():
    # Get defaults from environment
    default_provider = os.environ.get('CLAWCHAT_LLM_PROVIDER', 'deepseek')
    
    parser = argparse.ArgumentParser(description='ClawChat LLM Server')
    parser.add_argument('--ip', default='127.0.0.1', help='Server IP')
    parser.add_argument('--port', type=int, default=None, help='Server port')
    parser.add_argument('--security-dir', default='C:/temp/clawchat/security',
                        help='Security files directory')
    parser.add_argument('--llm-provider', default=default_provider,
                        choices=['deepseek', 'openai', 'anthropic'],
                        help='LLM provider (default: from CLAWCHAT_LLM_PROVIDER env var)')
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
