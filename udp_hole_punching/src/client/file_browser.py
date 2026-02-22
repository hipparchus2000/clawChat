"""
File browser for selecting security files.

Uses Tkinter for cross-platform GUI.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable


class FileBrowser:
    """
    Tkinter-based file browser for selecting security files.
    """
    
    def __init__(self, on_file_selected: Optional[Callable] = None):
        """
        Initialize file browser.
        
        Args:
            on_file_selected: Callback when file is selected
        """
        self.on_file_selected = on_file_selected
        self.selected_file: Optional[str] = None
        self.root: Optional[tk.Tk] = None
    
    def show_dialog(self, title: str = "Select Security File") -> Optional[str]:
        """
        Show file browser dialog.
        
        Args:
            title: Dialog title
            
        Returns:
            Selected file path or None if cancelled
        """
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("600x400")
        self.root.minsize(400, 300)
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Build UI
        self._build_ui()
        
        # Run
        self.root.mainloop()
        
        return self.selected_file
    
    def _build_ui(self):
        """Build the user interface."""
        # Header
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill='x')
        
        ttk.Label(
            header,
            text="ClawChat Security File Selection",
            font=('Helvetica', 14, 'bold')
        ).pack(anchor='w')
        
        ttk.Label(
            header,
            text="Select the .sec file provided by the server administrator.",
            wraplength=500
        ).pack(anchor='w', pady=(5, 0))
        
        # File info
        info_frame = ttk.LabelFrame(self.root, text="Selected File", padding="10")
        info_frame.pack(fill='x', padx=10, pady=10)
        
        self.file_label = ttk.Label(info_frame, text="No file selected")
        self.file_label.pack(anchor='w')
        
        self.details_label = ttk.Label(info_frame, text="")
        self.details_label.pack(anchor='w', pady=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill='x', side='bottom')
        
        ttk.Button(
            button_frame,
            text="Browse...",
            command=self._browse
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Use Selected File",
            command=self._confirm,
            state='disabled'
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side='right', padx=5)
        
        self.confirm_button = button_frame.winfo_children()[1]
    
    def _browse(self):
        """Open file browser."""
        filename = filedialog.askopenfilename(
            title="Select Security File",
            filetypes=[
                ("Security Files", "*.sec"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            self.selected_file = filename
            self.file_label.config(text=Path(filename).name)
            
            # Show file details
            try:
                size = os.path.getsize(filename)
                self.details_label.config(
                    text=f"Path: {filename}\nSize: {size} bytes"
                )
                self.confirm_button.config(state='normal')
            except Exception as e:
                self.details_label.config(text=f"Error: {e}")
    
    def _confirm(self):
        """Confirm selection."""
        if self.selected_file and self.on_file_selected:
            self.on_file_selected(self.selected_file)
        self.root.destroy()
    
    def _cancel(self):
        """Cancel selection."""
        self.selected_file = None
        self.root.destroy()


class SimpleFilePrompt:
    """
    Simple command-line file prompt (fallback if GUI unavailable).
    """
    
    @staticmethod
    def prompt(title: str = "Select Security File") -> Optional[str]:
        """
        Prompt user for file path.
        
        Args:
            title: Prompt title
            
        Returns:
            File path or None
        """
        print(f"\n{title}")
        print("=" * 50)
        print("Enter the full path to the security file (.sec)")
        print("Or drag and drop the file here")
        print("Press Enter to cancel\n")
        
        filepath = input("File path: ").strip()
        
        # Handle drag-and-drop (quotes removed)
        filepath = filepath.strip('"\'')
        
        if not filepath:
            return None
        
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}")
            return None
        
        return filepath


def select_security_file(use_gui: bool = True) -> Optional[str]:
    """
    Select security file using GUI or CLI.
    
    Args:
        use_gui: Try GUI first if True
        
    Returns:
        Selected file path or None
    """
    if use_gui:
        try:
            browser = FileBrowser()
            result = browser.show_dialog()
            if result:
                return result
        except Exception as e:
            print(f"GUI failed: {e}")
            print("Falling back to command-line prompt...")
    
    return SimpleFilePrompt.prompt()


# Example usage
if __name__ == "__main__":
    print("File Browser Example")
    print("=" * 50)
    
    filepath = select_security_file()
    
    if filepath:
        print(f"\nSelected: {filepath}")
    else:
        print("\nNo file selected")
