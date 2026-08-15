#!/usr/bin/env python3
"""Main application window and tray lifecycle for GoobyDDNS."""

import threading
import time
import webbrowser
from datetime import datetime

try:
    import pystray
except ImportError:  # pragma: no cover - optional in some environments
    pystray = None

import tkinter as tk

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - optional in some environments
    Image = None
    ImageDraw = None
from tkinter import messagebox, ttk

from .config import APP_NAME, CONFIG_NAME, get_default_config_directory, load_runtime_config, save_runtime_config
from .network import get_my_wan_ipv4, update_dns_record

APP_VERSION = "v0.9.5"
CHECK_INTERVAL = 600
GITHUB_URL = "https://github.com/GoobyFRS/GoobyDDNS-Windows"
ISSUES_URL = "https://github.com/GoobyFRS/GoobyDDNS-Windows/issues"
WIKI_URL = "https://github.com/GoobyFRS/GoobyDDNS-Windows/wiki"

def create_tray_image():
    """Create the tray icon image for the system tray.
    Returns:
        Image.Image | None: A green circle icon when Pillow is available; otherwise None.
    """
    if Image is None or ImageDraw is None:
        return None
    image = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 48, 48), fill="green")
    return image

class DDNSApp:
    """Manage the main Tkinter window, status updates, and DNS refresh loop."""

    def __init__(self, root):
        """Initialize the desktop application and start background tasks.
        Args:
            root: The Tkinter root window used by the application.
        """
        self.root = root
        self.config = load_runtime_config()
        self.root.title(f"GoobyDDNS - {APP_VERSION}")
        self.root.geometry("360x150")
        self.root.iconbitmap(default="icon.ico")
        self.root.minsize(260, 110)
        self.root.maxsize(600, 200)

        self.last_ip = None
        self.tray_icon = None

        self.build_ui()
        self.build_menu()
        self.update_clock()
        self.start_ddns_thread()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    def check_updates(self):
        """Open the project's GitHub releases page in the default browser."""
        webbrowser.open(GITHUB_URL)

    def github_report_issue(self):
        """Open the issue tracker in the default browser."""
        webbrowser.open(ISSUES_URL)

    def goto_wiki(self):
        """Open the project wiki in the default browser."""
        webbrowser.open(WIKI_URL)

    def build_ui(self):
        """Build the main status panel and labels for the application."""
        frame = ttk.Frame(self.root, padding=10)
        frame.grid()

        self.status_canvas = tk.Canvas(frame, width=20, height=20, highlightthickness=0)
        self.status_dot = self.status_canvas.create_oval(2, 2, 18, 18, fill="gray")
        self.status_canvas.grid(row=0, column=0, rowspan=2, padx=5)

        ttk.Label(frame, text="FQDN:").grid(row=0, column=1, sticky="w")
        self.fqdn_label = ttk.Label(frame, text=self.config.fqdn)
        self.fqdn_label.grid(row=0, column=2, sticky="w")

        ttk.Label(frame, text="Last IP:").grid(row=1, column=1, sticky="w")
        self.ip_label = ttk.Label(frame, text="—")
        self.ip_label.grid(row=1, column=2, sticky="w")

        ttk.Label(frame, text="Last Check:").grid(row=2, column=1, sticky="w")
        self.last_check_label = ttk.Label(frame, text="—")
        self.last_check_label.grid(row=2, column=2, sticky="w")

        ttk.Label(frame, text="Local Time:").grid(row=3, column=1, sticky="w")
        self.clock_label = ttk.Label(frame, text="—")
        self.clock_label.grid(row=3, column=2, sticky="w")

    def build_menu(self):
        """Create the top-level file and help menus for the desktop app."""
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Configuration", command=self.open_configuration_dialog)
        file_menu.add_command(label="Check for Updates", command=self.check_updates)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit_app)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Report Issue", command=self.github_report_issue)
        help_menu.add_command(label="Go to Wiki", command=self.goto_wiki)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def open_configuration_dialog(self):
        """Open a modal window for editing the saveable runtime configuration."""
        config_window = tk.Toplevel(self.root)
        config_window.title("GoobyDDNS Configuration")
        config_window.resizable(False, False)
        config_window.transient(self.root)
        config_window.grab_set()

        config_path = get_default_config_directory() / CONFIG_NAME
        current_config = load_runtime_config(config_path)

        fields = {
            "LINODE_API_KEY": tk.StringVar(value=current_config.linode_api_key or ""),
            "LINODE_API_VERSION": tk.StringVar(value=current_config.linode_api_version or "v4"),
            "DOMAIN_RECORD_ID": tk.StringVar(value=current_config.domain_record_id or ""),
            "SUBDOMAIN_RECORD_ID": tk.StringVar(value=current_config.subdomain_record_id or ""),
            "FQDN": tk.StringVar(value=current_config.fqdn),
        }

        frame = ttk.Frame(config_window, padding=12)
        frame.grid()

        row = 0
        for label_text, variable in fields.items():
            ttk.Label(frame, text=f"{label_text}:").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            entry = ttk.Entry(frame, width=45, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            row += 1

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=2, sticky="e", pady=(10, 0))

        def save_configuration():
            new_config = current_config.__class__(
                linode_api_key=fields["LINODE_API_KEY"].get().strip() or None,
                linode_api_version=fields["LINODE_API_VERSION"].get().strip() or "v4",
                domain_record_id=fields["DOMAIN_RECORD_ID"].get().strip() or None,
                subdomain_record_id=fields["SUBDOMAIN_RECORD_ID"].get().strip() or None,
                fqdn=fields["FQDN"].get().strip(),
            )
            try:
                save_runtime_config(new_config, config_path)
                self.config = new_config
                self.fqdn_label.config(text=new_config.fqdn)
                config_window.destroy()
            except ValueError as error:
                messagebox.showerror("Invalid Configuration", str(error))

        def cancel_configuration():
            config_window.destroy()

        ttk.Button(button_frame, text="Save", command=save_configuration).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(button_frame, text="Cancel", command=cancel_configuration).grid(row=0, column=1)

        config_window.protocol("WM_DELETE_WINDOW", cancel_configuration)

    def set_status(self, color):
        """Update the status indicator color for the current DNS check result.
        Args:
            color: A Tkinter-compatible color name such as green, yellow, or red.
        """
        self.status_canvas.itemconfig(self.status_dot, fill=color)

    def update_clock(self):
        """Refresh the displayed clock in the UI and reschedule the next tick."""
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(10_000, self.update_clock)

    def hide_to_tray(self):
        """Minimize the app to the system tray when available.
        If the optional tray package is unavailable, the app exits instead of crashing.
        """
        if pystray is None:
            self.exit_app()
            return

        self.root.withdraw()
        if self.tray_icon:
            return

        menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_from_tray),
            pystray.MenuItem("Exit", self.exit_app),
        )
        self.tray_icon = pystray.Icon(APP_NAME, create_tray_image(), f"{APP_NAME} {APP_VERSION}", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self, icon=None, item=None):
        """Restore the application window from the tray icon.
        Args:
            icon: Optional tray icon instance.
            item: Optional menu item that triggered this callback.
        """
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.deiconify)

    def exit_app(self, icon=None, item=None):
        """Stop the tray icon and close the application window.
        Args:
            icon: Optional tray icon instance.
            item: Optional menu item that triggered this callback.
        """
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def start_ddns_thread(self):
        """Start the background thread responsible for periodic DNS checks."""
        thread = threading.Thread(target=self.ddns_loop, daemon=True)
        thread.start()

    def ddns_loop(self):
        """Run repeated DDNS update checks on a fixed interval."""
        while True:
            self.run_ddns_check()
            time.sleep(CHECK_INTERVAL)

    def run_ddns_check(self):
        """Fetch the current public IP and update the DNS record if it changed.
        Returns:
            None: The UI is updated asynchronously through Tkinter callbacks.
        """
        ip = get_my_wan_ipv4()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not ip:
            self.root.after(0, lambda: self.set_status("red"))
            return

        def update_ui():
            """Apply the latest IP and timestamp values to the UI labels."""
            self.ip_label.config(text=ip)
            self.last_check_label.config(text=timestamp)

        self.root.after(0, update_ui)
        if ip == self.last_ip:
            self.root.after(0, lambda: self.set_status("yellow"))
            return

        success = update_dns_record(self.config, ip)
        if success:
            self.last_ip = ip
            self.root.after(0, lambda: self.set_status("green"))
        else:
            self.root.after(0, lambda: self.set_status("red"))

def main():
    """Launch the desktop application main loop."""
    root = tk.Tk()
    DDNSApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
