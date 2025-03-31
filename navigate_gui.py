import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class NIFTINavigator:
    def __init__(self, root):
        self.root = root
        self.root.title("NIfTI File Navigator")
        self.root.geometry("800x600")
        
        # Initialize UI components
        self.create_widgets()
        self.scan_directory(os.path.join(os.path.dirname(__file__), 'data'))
    
    def create_widgets(self):
        # File list frame
        list_frame = ttk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File list treeview
        self.tree = ttk.Treeview(list_frame, columns=('fullpath', 'size'), show='tree')
        self.tree.heading('#0', text='NIfTI File Structure')
        self.tree.column('#0', width=400)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Control button frame
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Open File", command=self.run_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Open Directory", command=self.open_directory).pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind double-click event
        self.tree.bind('<Double-1>', self.run_selected)
    
    def scan_directory(self, path):
        """Scan for NIfTI files in the specified directory"""
        self.tree.delete(*self.tree.get_children())
        self.file_list = []
        
        for root_dir, _, files in os.walk(path):
            for filename in files:
                if filename.lower().endswith('.nii.gz'):
                    full_path = os.path.join(root_dir, filename)
                    parent = os.path.dirname(full_path).replace(path, '').lstrip(os.sep)
                    parent_node = self._get_parent_node(parent) or ''
                    self.tree.insert(
                        parent_node, 'end', 
                        values=(full_path, f"{os.path.getsize(full_path)//1024} KB"),
                        text=filename,
                        tags=('nii_file',)
                    )
                    self.file_list.append(full_path)
    
    def _get_parent_node(self, path):
        """Build tree directory structure"""
        if not path:
            return ''
            
        parts = path.split(os.sep)
        parent_node = ''
        for part in parts:
            children = self.tree.get_children(parent_node)
            found = False
            for child in children:
                if self.tree.item(child, 'text') == part:
                    parent_node = child
                    found = True
                    break
            if not found:
                parent_node = self.tree.insert(
                    parent_node, 'end', 
                    text=part,
                    tags=('directory',)
                )
        return parent_node
    
    def run_selected(self, event=None):
        """Run selected file"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a NIfTI file first")
            return
            
        item = self.tree.item(selected[0])
        if 'nii_file' not in item['tags']:
            return
            
        file_path = item['values'][0]
        file_name = file_path.replace("\\", "/")
        file_name = os.path.basename(file_name)
        self.status.config(text=f"Opening: {os.path.basename(file_path)}...")
        print(f'==========={file_name}===========')
        try:
            subprocess.Popen([
            sys.executable,
            os.path.join(os.path.dirname(__file__), '3viewers_screen_recording.py'),  # Dynamic path acquisition
            file_name  # Remove outer quotes
        ], shell=False)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot start program:\n{str(e)}")
        finally:
            self.status.config(text="Ready")
    
    def refresh_list(self):
        """Refresh file list"""
        self.scan_directory(os.path.dirname(__file__))
    
    def open_directory(self):
        """Select another directory"""
        path = filedialog.askdirectory()
        if path:
            self.scan_directory(path)

if __name__ == "__main__":
    root = tk.Tk()
    app = NIFTINavigator(root)
    root.mainloop()