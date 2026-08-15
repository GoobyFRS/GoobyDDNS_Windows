"""Shared abstractions for platform-specific runtime behavior."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeEnvironment:
    """Describe the current runtime environment for a platform adapter.

    Attributes:
        name: Human-readable platform name.
        platform: The underlying sys.platform string.
        config_directory: Directory used for stored configuration.
        app_directory: Directory containing the installed app files.
    """

    name: str
    platform: str
    config_directory: Path
    app_directory: Path


class PlatformAdapter:
    """Base adapter for platform-specific runtime behavior."""

    name = "generic"

    def __init__(self, app_name: str = "GoobyDDNS", app_directory: Path | None = None):
        """Initialize the platform adapter.

        Args:
            app_name: Human-readable application name used for config paths.
            app_directory: Optional path to the application installation directory.
        """
        self.app_name = app_name
        self.app_directory = app_directory or Path(__file__).resolve().parents[2]

    def get_config_directory(self) -> Path:
        """Return the default configuration directory for this platform.

        Returns:
            Path: The location on disk where app settings are stored.
        """
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / self.app_name
        return Path.home() / ".config" / self.app_name

    def supports_tray(self) -> bool:
        """Return whether the current platform supports the system tray UI.

        Returns:
            bool: True when the platform supports tray integration; otherwise False.
        """
        return False

    def get_ui_backend(self) -> str:
        """Return the preferred UI toolkit for this platform.

        Returns:
            str: The toolkit name, such as tkinter.
        """
        return "tkinter"

    def get_runtime_environment(self) -> RuntimeEnvironment:
        """Build the runtime metadata object for the current host platform.

        Returns:
            RuntimeEnvironment: The resolved environment for the app.
        """
        return RuntimeEnvironment(
            name=self.name,
            platform=sys.platform,
            config_directory=self.get_config_directory(),
            app_directory=self.app_directory,
        )
