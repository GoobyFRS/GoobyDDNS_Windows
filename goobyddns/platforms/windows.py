"""Windows-specific platform adapter for GoobyDDNS."""

from __future__ import annotations

import os
from pathlib import Path

from .base import PlatformAdapter

class WindowsPlatformAdapter(PlatformAdapter):
    """Windows-specific runtime adapter."""

    name = "windows"

    def get_config_directory(self) -> Path:
        """Return the default per-user config folder on Windows.
        Returns:
            Path: The AppData directory used by the application.
        """
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / self.app_name
        return Path.home() / "AppData" / "Local" / self.app_name

    def supports_tray(self) -> bool:
        """Return whether this platform supports a system tray icon.
        Returns:
            bool: True for Windows tray support.
        """
        return True

    def get_ui_backend(self) -> str:
        """Return the UI toolkit for the Windows implementation.
        Returns:
            str: The backend name, which is Tkinter.
        """
        return "tkinter"
