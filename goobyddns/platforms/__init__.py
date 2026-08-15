"""Platform abstraction helpers for GoobyDDNS."""

from .base import PlatformAdapter, RuntimeEnvironment
from .windows import WindowsPlatformAdapter

def get_platform_adapter():
    """Return the platform-specific adapter for the current operating system.

    Returns:
        PlatformAdapter: The adapter instance matching the host runtime.
    """
    import sys

    if sys.platform.startswith("win"):
        return WindowsPlatformAdapter()
    return PlatformAdapter()

__all__ = ["PlatformAdapter", "RuntimeEnvironment", "WindowsPlatformAdapter", "get_platform_adapter",]
