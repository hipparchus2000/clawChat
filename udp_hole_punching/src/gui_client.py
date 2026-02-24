#!/usr/bin/env python3
"""
ClawChat GUI Client
Three-tab interface: Chat, File Browser, Crontab
"""

import os
import sys
import time
import threading
import socket
import subprocess
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog

from security.encryption import CryptoManager, derive_session_keys
from security.file_manager import SecurityFileManager, SecurityFile
from networking.udp_hole_punch import UDPHolePuncher
from protocol.messages import Message, MessageType


class ClawChatGUI:
    """Main GUI application with three tabs."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ClawChat - Secure P2P Communication")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        # Connection state
        self.connected = False
        self.socket = None
        self.crypto = None
        self.server_address = None
        self.receive_thread = None
        self.running = False
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.chat_frame = ttk.Frame(self.notebook)
        self.file_frame = ttk.Frame(self.notebook)
        self.cron_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.chat_frame, text="💬 Chat")
        self.notebook.add(self.file_frame, text="📁 Files")
        self.notebook.add(self.cron_frame, text="⏰ Crontab")
        
        # Initialize tabs
        self._init_chat_tab()
        self._init_file_tab()
        self._init_cron_tab()
        
        # Menu bar
        self._create_menu()
        
        # Status bar
        self.status_var = tk.StringVar(value="Not connected")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief='sunken')
        self.status_bar.pack(fill='x', side='bottom')
        
        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    # ============== Chat Tab ==============
    
    def _init_chat_tab(self):
        """Initialize chat tab."""
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame, wrap=tk.WORD, state='disabled', height=20
        )
        self.chat_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Input frame
        input_frame = ttk.Frame(self.chat_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        self.msg_entry = ttk.Entry(input_frame)
        self.msg_entry.pack(side='left', fill='x', expand=True)
        self.msg_entry.bind('<Return>', lambda e: self.send_chat())
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self.send_chat)
        self.send_btn.pack(side='right', padx=5)
        
        # Connection buttons
        btn_frame = ttk.Frame(self.chat_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Connect", command=self.connect_dialog).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Disconnect", command=self.disconnect).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Compromised", command=self.trigger_compromised).pack(side='right', padx=5)
    
    def add_chat_message(self, sender, message, timestamp=None):
        """Add message to chat display."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.chat_display.config(state='normal')
        self.chat_display.insert('end', f"[{timestamp}] {sender}: {message}\n")
        self.chat_display.see('end')
        self.chat_display.config(state='disabled')
    
    def send_chat(self):
        """Send chat message."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        text = self.msg_entry.get().strip()
        if not text:
            return
        
        # Add to display
        self.add_chat_message("You", text)
        self.msg_entry.delete(0, 'end')
        
        # Send over network
        if self.socket and self.crypto:
            try:
                msg = Message(
                    msg_type=MessageType.CHAT,
                    payload={'text': text, 'sender': 'client'}
                )
                encrypted = self.crypto.encrypt_packet(msg.to_bytes())
                self.socket.sendto(encrypted, self.server_address)
            except Exception as e:
                self.add_chat_message("System", f"Send error: {e}")
    
    # ============== File Browser Tab ==============
    
    def _init_file_tab(self):
        """Initialize file browser tab."""
        # Toolbar
        toolbar = ttk.Frame(self.file_frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="⬆️ Up", command=self.file_go_up).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔄 Refresh", command=self.file_refresh).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📥 Download", command=self.file_download).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📤 Upload", command=self.file_upload).pack(side='left', padx=2)
        
        # Path bar
        path_frame = ttk.Frame(self.file_frame)
        path_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(path_frame, text="Path:").pack(side='left')
        self.path_var = tk.StringVar(value="/home/openclaw")
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(path_frame, text="Go", command=self.file_go).pack(side='left')
        
        # File list
        columns = ('name', 'size', 'modified', 'type')
        self.file_tree = ttk.Treeview(self.file_frame, columns=columns, show='headings')
        
        self.file_tree.heading('name', text='Name')
        self.file_tree.heading('size', text='Size')
        self.file_tree.heading('modified', text='Modified')
        self.file_tree.heading('type', text='Type')
        
        self.file_tree.column('name', width=300)
        self.file_tree.column('size', width=100)
        self.file_tree.column('modified', width=150)
        self.file_tree.column('type', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.file_frame, orient='vertical', command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        self.file_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)
        
        # Double click to navigate
        self.file_tree.bind('<Double-1>', self.file_double_click)
        
        # Status
        self.file_status_var = tk.StringVar(value="Not connected to file server")
        ttk.Label(self.file_frame, textvariable=self.file_status_var).pack(fill='x', padx=5, pady=2)
    
    def file_refresh(self):
        """Refresh file list."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        # Clear current
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Request directory listing from server
        # TODO: Implement file protocol
        self.file_status_var.set(f"Listing: {self.path_var.get()}")
        
        # Mock data for now
        mock_files = [
            ('documents', '-', '2024-01-15 10:30', 'Directory'),
            ('downloads', '-', '2024-01-14 16:45', 'Directory'),
            ('file1.txt', '1.2 KB', '2024-01-15 09:00', 'Text'),
            ('image.png', '245 KB', '2024-01-14 12:30', 'Image'),
        ]
        
        for name, size, modified, ftype in mock_files:
            self.file_tree.insert('', 'end', values=(name, size, modified, ftype))
    
    def file_go_up(self):
        """Go to parent directory."""
        current = self.path_var.get()
        parent = str(Path(current).parent)
        if parent != current:
            self.path_var.set(parent)
            self.file_refresh()
    
    def file_go(self):
        """Go to entered path."""
        self.file_refresh()
    
    def file_double_click(self, event):
        """Handle double click on file."""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = self.file_tree.item(selection[0])
        name, size, modified, ftype = item['values']
        
        if ftype == 'Directory':
            new_path = str(Path(self.path_var.get()) / name)
            self.path_var.set(new_path)
            self.file_refresh()
        else:
            self.file_download()
    
    def file_download(self):
        """Download selected file."""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showinfo("Select File", "Please select a file to download")
            return
        
        item = self.file_tree.item(selection[0])
        name = item['values'][0]
        
        # Ask where to save
        save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=name)
        if save_path:
            messagebox.showinfo("Download", f"Downloading {name} to {save_path}...")
            # TODO: Implement actual download
    
    def file_upload(self):
        """Upload file to server."""
        filepath = filedialog.askopenfilename()
        if filepath:
            filename = Path(filepath).name
            messagebox.showinfo("Upload", f"Uploading {filename}...")
            # TODO: Implement actual upload
    
    # ============== Crontab Tab ==============
    
    def _init_cron_tab(self):
        """Initialize crontab tab."""
        # Toolbar
        toolbar = ttk.Frame(self.cron_frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self.cron_refresh).pack(side='left', padx=5)
        ttk.Button(toolbar, text="➕ Add Task", command=self.cron_add).pack(side='left', padx=5)
        ttk.Button(toolbar, text="❌ Remove Selected", command=self.cron_remove).pack(side='left', padx=5)
        
        # Crontab list
        columns = ('schedule', 'command', 'comment')
        self.cron_tree = ttk.Treeview(self.cron_frame, columns=columns, show='headings')
        
        self.cron_tree.heading('schedule', text='Schedule')
        self.cron_tree.heading('command', text='Command')
        self.cron_tree.heading('comment', text='Comment')
        
        self.cron_tree.column('schedule', width=150)
        self.cron_tree.column('command', width=400)
        self.cron_tree.column('comment', width=200)
        
        scrollbar = ttk.Scrollbar(self.cron_frame, orient='vertical', command=self.cron_tree.yview)
        self.cron_tree.configure(yscrollcommand=scrollbar.set)
        
        self.cron_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)
        
        # Status
        self.cron_status_var = tk.StringVar(value="Not connected")
        ttk.Label(self.cron_frame, textvariable=self.cron_status_var).pack(fill='x', padx=5, pady=2)
    
    def cron_refresh(self):
        """Refresh crontab list."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        # Clear current
        for item in self.cron_tree.get_children():
            self.cron_tree.delete(item)
        
        # Request crontab from server
        # TODO: Implement crontab protocol
        self.cron_status_var.set("Loading crontab...")
        
        # Mock data
        mock_cron = [
            ('0 * * * *', '/home/openclaw/backup.sh', 'Hourly backup'),
            ('0 0 * * *', '/home/openclaw/daily-report.sh', 'Daily report'),
            ('*/5 * * * *', '/home/openclaw/check-status.sh', 'Status check'),
        ]
        
        for schedule, command, comment in mock_cron:
            self.cron_tree.insert('', 'end', values=(schedule, command, comment))
        
        self.cron_status_var.set("Crontab loaded")
    
    def cron_add(self):
        """Add new crontab entry."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        # Simple dialog
        schedule = simpledialog.askstring("Schedule", "Enter cron schedule (e.g., '0 * * * *'):")
        if not schedule:
            return
        
        command = simpledialog.askstring("Command", "Enter command:")
        if not command:
            return
        
        comment = simpledialog.askstring("Comment", "Enter comment (optional):") or ""
        
        # Add to list
        self.cron_tree.insert('', 'end', values=(schedule, command, comment))
        
        # TODO: Send to server
        messagebox.showinfo("Added", "Crontab entry added (not yet sent to server)")
    
    def cron_remove(self):
        """Remove selected crontab entry."""
        selection = self.cron_tree.selection()
        if not selection:
            messagebox.showinfo("Select", "Please select an entry to remove")
            return
        
        if messagebox.askyesno("Confirm", "Remove selected crontab entry?"):
            for item in selection:
                self.cron_tree.delete(item)
            # TODO: Send removal to server
    
    # ============== Connection ==============
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Connect...", command=self.connect_dialog)
        file_menu.add_command(label="Disconnect", command=self.disconnect)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def connect_dialog(self):
        """Open connection dialog."""
        # Ask for security file
        filepath = filedialog.askopenfilename(
            title="Select Security File",
            filetypes=[("Security Files", "*.sec"), ("All Files", "*.*")]
        )
        
        if not filepath:
            return
        
        # Connect in background thread
        threading.Thread(target=self._do_connect, args=(filepath,), daemon=True).start()
    
    def _do_connect(self, sec_filepath):
        """Perform connection."""
        # Read from environment or use default
        import os
        bootstrap_key = os.environ.get('CLAWCHAT_BOOTSTRAP_KEY', 'default-key-32bytes-for-testing!').encode()[:32]
        
        try:
            # Load security file
            self.add_chat_message("System", f"Loading security file: {sec_filepath}")
            
            manager = SecurityFileManager(bootstrap_key=bootstrap_key)
            sec_file = manager.load_security_file(sec_filepath)
            
            import base64
            shared_secret = base64.b64decode(sec_file.shared_secret)
            server_ip = sec_file.server_public_ip
            server_port = sec_file.server_udp_port
            
            self.root.after(0, lambda: self.add_chat_message("System", f"Connecting to {server_ip}:{server_port}..."))
            
            # Setup crypto
            self.crypto = CryptoManager()
            keys = derive_session_keys(shared_secret, sec_file.connection_id, int(time.time()))
            self.crypto.set_session_keys(keys)
            
            # Direct connection (hole punching not needed on localhost)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(3.0)
            self.server_address = (server_ip, server_port)
            self.connected = True
            self.running = True
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Send a test message to establish connection
            test_msg = Message(
                msg_type=MessageType.CHAT,
                payload={'text': 'Hello!', 'sender': 'client'}
            )
            enc = self.crypto.encrypt_packet(test_msg.to_bytes())
            self.socket.sendto(enc, self.server_address)
            
            self.root.after(0, lambda: [
                self.add_chat_message("System", f"Connected to {server_ip}:{server_port}"),
                self.status_var.set(f"Connected to {server_ip}:{server_port}"),
                self.file_status_var.set("Connected - Click Refresh"),
                self.cron_status_var.set("Connected - Click Refresh")
            ])
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.add_chat_message("System", f"Error: {msg}"))
    
    def _receive_loop(self):
        """Background receive loop."""
        while self.running and self.socket:
            try:
                self.socket.settimeout(1.0)
                data, addr = self.socket.recvfrom(2048)
                
                # Decrypt
                plaintext = self.crypto.decrypt_packet(data)
                msg = Message.from_bytes(plaintext)
                
                # Handle message
                if msg.msg_type == MessageType.CHAT:
                    text = msg.payload.get('text', '')
                    sender = msg.payload.get('sender', 'server')
                    self.root.after(0, lambda s=sender, t=text: self.add_chat_message(s, t))
                    
            except socket.timeout:
                continue
            except Exception:
                break
    
    def disconnect(self):
        """Disconnect from server."""
        self.running = False
        self.connected = False
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        self.status_var.set("Disconnected")
        self.file_status_var.set("Not connected")
        self.cron_status_var.set("Not connected")
        self.add_chat_message("System", "Disconnected")
    
    def trigger_compromised(self):
        """Trigger compromised protocol."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        if messagebox.askyesno("⚠️ WARNING", "This will destroy all keys on both sides!\n\nType 'YES' to confirm:", icon='warning'):
            # Send compromised signal
            # TODO: Implement
            messagebox.showinfo("Compromised", "Compromised protocol triggered")
            self.disconnect()
    
    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About ClawChat",
            "ClawChat v2.0\n\nSecure P2P Communication\n\nFeatures:\n- End-to-end encryption\n- File browser\n- Crontab management"
        )
    
    def on_close(self):
        """Handle window close."""
        self.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ClawChatGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
