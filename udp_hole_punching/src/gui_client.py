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
        self.cron_pending = False
        
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
        ttk.Button(toolbar, text="🗑️ Delete", command=self.file_delete).pack(side='left', padx=2)
        ttk.Button(toolbar, text="✏️ Rename", command=self.file_rename).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📁 New Folder", command=self.file_mkdir).pack(side='left', padx=2)
        
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
        """Refresh file list from server."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        # Clear current
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        self.file_status_var.set(f"Loading: {self.path_var.get()}")
        
        # Request directory listing from server
        try:
            path = self.path_var.get()
            # Remove leading slash for server
            server_path = path.lstrip('/')
            if not server_path:
                server_path = '.'
            
            msg = Message(
                msg_type=MessageType.FILE_LIST,
                payload={'path': server_path}
            )
            encrypted = self.crypto.encrypt_packet(msg.to_bytes())
            self.socket.sendto(encrypted, self.server_address)
            
            # Response will be handled in receive loop
        except Exception as e:
            self.file_status_var.set(f"Error: {e}")
    
    def _handle_file_list(self, payload):
        """Handle file list response from server."""
        if not payload.get('success'):
            error = payload.get('error', 'Unknown error')
            self.root.after(0, lambda: self.file_status_var.set(f"Error: {error}"))
            return
        
        items = payload.get('items', [])
        
        # Clear current
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Add items to tree
        for item in items:
            name = item.get('name', '')
            size = item.get('size', 0)
            modified_ts = item.get('modified', 0)
            is_dir = item.get('is_dir', False)
            
            # Format size
            if is_dir:
                size_str = '-'
                ftype = 'Directory'
            else:
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024*1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                ftype = 'File'
            
            # Format time
            modified_str = datetime.fromtimestamp(modified_ts).strftime('%Y-%m-%d %H:%M')
            
            self.file_tree.insert('', 'end', values=(name, size_str, modified_str, ftype))
        
        self.file_status_var.set(f"Listed {len(items)} items in {self.path_var.get()}")
    
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
        ftype = item['values'][3]
        
        if ftype == 'Directory':
            messagebox.showinfo("Directory", "Cannot download directories yet")
            return
        
        # Ask where to save
        save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=name)
        if not save_path:
            return
        
        # Request download from server in background thread
        self.file_status_var.set(f"Downloading {name}...")
        threading.Thread(
            target=self._do_file_download,
            args=(name, save_path),
            daemon=True
        ).start()
    
    def _do_file_download(self, filename, save_path):
        """Download file in background."""
        try:
            remote_path = str(Path(self.path_var.get().lstrip('/')) / filename)
            if remote_path.startswith('.'):
                remote_path = remote_path[2:] if remote_path.startswith('./') else remote_path[1:]
            
            offset = 0
            total_size = 0
            
            with open(save_path, 'wb') as f:
                while True:
                    # Request chunk
                    msg = Message(
                        msg_type=MessageType.FILE_DOWNLOAD,
                        payload={'path': remote_path, 'offset': offset}
                    )
                    encrypted = self.crypto.encrypt_packet(msg.to_bytes())
                    self.socket.sendto(encrypted, self.server_address)
                    
                    # Wait for response
                    self.socket.settimeout(10.0)
                    data, addr = self.socket.recvfrom(16384)
                    
                    plaintext = self.crypto.decrypt_packet(data)
                    response = Message.from_bytes(plaintext)
                    
                    if response.msg_type != MessageType.FILE_DOWNLOAD:
                        continue
                    
                    payload = response.payload
                    if not payload.get('success'):
                        error = payload.get('error', 'Unknown error')
                        self.root.after(0, lambda e=error: self.file_status_var.set(f"Download failed: {e}"))
                        return
                    
                    # Write chunk
                    import base64
                    chunk_data = base64.b64decode(payload['data'])
                    f.write(chunk_data)
                    
                    offset = payload.get('offset', 0) + payload.get('size', 0)
                    total_size = payload.get('total_size', 0)
                    eof = payload.get('eof', False)
                    
                    # Update status
                    progress = f"{offset}/{total_size} bytes"
                    self.root.after(0, lambda p=progress: self.file_status_var.set(f"Downloading... {p}"))
                    
                    if eof:
                        break
            
            self.root.after(0, lambda: self.file_status_var.set(f"Downloaded {filename} ({total_size} bytes)"))
            
        except Exception as e:
            self.root.after(0, lambda e=str(e): self.file_status_var.set(f"Download error: {e}"))
    
    def file_upload(self):
        """Upload file to server."""
        filepath = filedialog.askopenfilename()
        if not filepath:
            return
        
        filename = Path(filepath).name
        
        # Upload in background thread
        self.file_status_var.set(f"Uploading {filename}...")
        threading.Thread(
            target=self._do_file_upload,
            args=(filepath, filename),
            daemon=True
        ).start()
    
    def _do_file_upload(self, filepath, filename):
        """Upload file in background."""
        try:
            remote_path = str(Path(self.path_var.get().lstrip('/')) / filename)
            
            import base64
            
            file_size = Path(filepath).stat().st_size
            offset = 0
            chunk_size = 4096  # 4KB chunks
            
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Send chunk
                    msg = Message(
                        msg_type=MessageType.FILE_UPLOAD,
                        payload={
                            'path': remote_path,
                            'data': base64.b64encode(chunk).decode('ascii'),
                            'offset': offset,
                            'append': offset > 0
                        }
                    )
                    encrypted = self.crypto.encrypt_packet(msg.to_bytes())
                    self.socket.sendto(encrypted, self.server_address)
                    
                    # Wait for ack
                    self.socket.settimeout(10.0)
                    data, addr = self.socket.recvfrom(2048)
                    
                    plaintext = self.crypto.decrypt_packet(data)
                    response = Message.from_bytes(plaintext)
                    
                    if response.msg_type != MessageType.FILE_UPLOAD:
                        continue
                    
                    payload = response.payload
                    if not payload.get('success'):
                        error = payload.get('error', 'Unknown error')
                        self.root.after(0, lambda e=error: self.file_status_var.set(f"Upload failed: {e}"))
                        return
                    
                    offset += len(chunk)
                    
                    # Update status
                    progress = f"{offset}/{file_size} bytes"
                    self.root.after(0, lambda p=progress: self.file_status_var.set(f"Uploading... {p}"))
            
            self.root.after(0, lambda: [
                self.file_status_var.set(f"Uploaded {filename} ({file_size} bytes)"),
                self.file_refresh()
            ])
            
        except Exception as e:
            self.root.after(0, lambda e=str(e): self.file_status_var.set(f"Upload error: {e}"))
    
    def file_delete(self):
        """Delete selected file or directory."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showinfo("Select", "Please select a file or directory to delete")
            return
        
        item = self.file_tree.item(selection[0])
        name = item['values'][0]
        ftype = item['values'][3]
        
        if not messagebox.askyesno("Confirm Delete", f"Delete {ftype.lower()}: {name}?"):
            return
        
        try:
            remote_path = str(Path(self.path_var.get().lstrip('/')) / name)
            
            msg = Message(
                msg_type=MessageType.FILE_DELETE,
                payload={'path': remote_path}
            )
            encrypted = self.crypto.encrypt_packet(msg.to_bytes())
            self.socket.sendto(encrypted, self.server_address)
            
            self.file_status_var.set(f"Deleting {name}...")
        except Exception as e:
            self.file_status_var.set(f"Delete error: {e}")
    
    def file_rename(self):
        """Rename selected file or directory."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showinfo("Select", "Please select a file or directory to rename")
            return
        
        item = self.file_tree.item(selection[0])
        old_name = item['values'][0]
        ftype = item['values'][3]
        
        new_name = simpledialog.askstring("Rename", f"New name for {old_name}:", initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        
        try:
            remote_path = str(Path(self.path_var.get().lstrip('/')) / old_name)
            
            msg = Message(
                msg_type=MessageType.FILE_RENAME,
                payload={'path': remote_path, 'new_name': new_name}
            )
            encrypted = self.crypto.encrypt_packet(msg.to_bytes())
            self.socket.sendto(encrypted, self.server_address)
            
            self.file_status_var.set(f"Renaming {old_name} to {new_name}...")
        except Exception as e:
            self.file_status_var.set(f"Rename error: {e}")
    
    def file_mkdir(self):
        """Create new directory."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        name = simpledialog.askstring("New Folder", "Enter folder name:")
        if not name:
            return
        
        try:
            remote_path = str(Path(self.path_var.get().lstrip('/')) / name)
            
            msg = Message(
                msg_type=MessageType.FILE_MKDIR,
                payload={'path': remote_path}
            )
            encrypted = self.crypto.encrypt_packet(msg.to_bytes())
            self.socket.sendto(encrypted, self.server_address)
            
            self.file_status_var.set(f"Creating folder {name}...")
        except Exception as e:
            self.file_status_var.set(f"Mkdir error: {e}")
    
    # ============== Crontab Tab ==============
    
    def _init_cron_tab(self):
        """Initialize crontab tab."""
        # Toolbar
        toolbar = ttk.Frame(self.cron_frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self.cron_refresh).pack(side='left', padx=5)
        ttk.Button(toolbar, text="▶️ Run Now", command=self.cron_run_now).pack(side='left', padx=5)
        ttk.Button(toolbar, text="🔄 Reload File", command=self.cron_reload).pack(side='left', padx=5)
        
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
        """Refresh crontab list from server."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        # Clear current
        for item in self.cron_tree.get_children():
            self.cron_tree.delete(item)
        
        # Request cron list from server
        self.cron_status_var.set("Loading cron jobs from server...")
        
        try:
            msg = Message(msg_type=MessageType.CRON_LIST, payload={})
            encrypted = self.crypto.encrypt_packet(msg.to_bytes())
            self.socket.sendto(encrypted, self.server_address)
            
            # Response will be handled in receive loop
            self.cron_pending = True
        except Exception as e:
            self.cron_status_var.set(f"Error: {e}")
    
    def _handle_cron_list(self, payload):
        """Handle cron list response from server."""
        jobs = payload.get('jobs', [])
        
        # Clear current
        for item in self.cron_tree.get_children():
            self.cron_tree.delete(item)
        
        # Add jobs to tree
        for job in jobs:
            schedule = job.get('schedule', '')
            command = job.get('command', '')[:60]  # Truncate long commands
            status = 'enabled' if job.get('enabled', True) else 'disabled'
            
            # Add last run info
            last_run = job.get('last_run')
            if last_run:
                from datetime import datetime
                last_run_str = datetime.fromtimestamp(last_run).strftime('%m-%d %H:%M')
                status += f' (last: {last_run_str})'
            
            self.cron_tree.insert('', 'end', values=(schedule, command, status))
        
        self.cron_status_var.set(f"Loaded {len(jobs)} cron jobs")
        self.cron_pending = False
    
    def cron_run_now(self):
        """Run selected cron job immediately."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        selection = self.cron_tree.selection()
        if not selection:
            messagebox.showinfo("Select", "Please select a job to run")
            return
        
        # Get job name from selected item
        item = self.cron_tree.item(selection[0])
        schedule, command, _ = item['values']
        
        # Find job name (we need to store this - simplified for now)
        if messagebox.askyesno("Confirm", f"Run job now?\n{command[:50]}..."):
            try:
                msg = Message(
                    msg_type=MessageType.CRON_RUN,
                    payload={'job_name': command[:30]}  # Using command as identifier
                )
                encrypted = self.crypto.encrypt_packet(msg.to_bytes())
                self.socket.sendto(encrypted, self.server_address)
                self.cron_status_var.set("Job execution requested...")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run job: {e}")
    
    def cron_reload(self):
        """Reload cron file on server."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        
        try:
            msg = Message(msg_type=MessageType.CRON_RELOAD, payload={})
            encrypted = self.crypto.encrypt_packet(msg.to_bytes())
            self.socket.sendto(encrypted, self.server_address)
            self.cron_status_var.set("Reloading cron file...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload: {e}")
    
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
                elif msg.msg_type == MessageType.CRON_LIST:
                    self.root.after(0, lambda p=msg.payload: self._handle_cron_list(p))
                elif msg.msg_type == MessageType.CRON_RUN:
                    success = msg.payload.get('success', False)
                    job_name = msg.payload.get('job_name', 'unknown')
                    status = "started" if success else "failed"
                    self.root.after(0, lambda: self.cron_status_var.set(f"Run {job_name}: {status}"))
                elif msg.msg_type == MessageType.CRON_RELOAD:
                    success = msg.payload.get('success', False)
                    count = msg.payload.get('job_count', 0)
                    if success:
                        self.root.after(0, lambda: self.cron_status_var.set(f"Reloaded {count} jobs"))
                    else:
                        self.root.after(0, lambda: self.cron_status_var.set("Reload failed"))
                # File protocol responses
                elif msg.msg_type == MessageType.FILE_LIST:
                    self.root.after(0, lambda p=msg.payload: self._handle_file_list(p))
                elif msg.msg_type == MessageType.FILE_DOWNLOAD:
                    # Handled synchronously in _do_file_download
                    pass
                elif msg.msg_type == MessageType.FILE_UPLOAD:
                    # Handled synchronously in _do_file_upload
                    pass
                elif msg.msg_type == MessageType.FILE_DELETE:
                    success = msg.payload.get('success', False)
                    if success:
                        self.root.after(0, lambda: [
                            self.file_status_var.set("Deleted successfully"),
                            self.file_refresh()
                        ])
                    else:
                        error = msg.payload.get('error', 'Unknown error')
                        self.root.after(0, lambda e=error: self.file_status_var.set(f"Delete failed: {e}"))
                elif msg.msg_type == MessageType.FILE_RENAME:
                    success = msg.payload.get('success', False)
                    if success:
                        self.root.after(0, lambda: [
                            self.file_status_var.set("Renamed successfully"),
                            self.file_refresh()
                        ])
                    else:
                        error = msg.payload.get('error', 'Unknown error')
                        self.root.after(0, lambda e=error: self.file_status_var.set(f"Rename failed: {e}"))
                elif msg.msg_type == MessageType.FILE_MKDIR:
                    success = msg.payload.get('success', False)
                    if success:
                        self.root.after(0, lambda: [
                            self.file_status_var.set("Directory created"),
                            self.file_refresh()
                        ])
                    else:
                        error = msg.payload.get('error', 'Unknown error')
                        self.root.after(0, lambda e=error: self.file_status_var.set(f"Mkdir failed: {e}"))
                    
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
