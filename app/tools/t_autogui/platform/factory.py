"""Platform adapter factory with automatic OS detection."""
import platform
import threading
from typing import Optional

from .base import PlatformAdapter
from .windows import WindowsAdapter
from .macos import MacOSAdapter
from .linux import LinuxAdapter

# Singleton adapter instance with thread-safe lock
_adapter: Optional[PlatformAdapter] = None
_lock = threading.Lock()


def get_platform_adapter() -> PlatformAdapter:
    """Get the platform adapter for the current system (singleton, thread-safe).

    Automatically detects the operating system and returns the
    appropriate adapter instance.

    Returns:
        PlatformAdapter instance for the current platform.

    Raises:
        RuntimeError: If the platform is not supported.
    """
    global _adapter
    if _adapter is None:
        with _lock:
            # Double-check locking pattern
            if _adapter is None:
                _adapter = create_platform_adapter()
    return _adapter


def create_platform_adapter() -> PlatformAdapter:
    """Create a platform adapter based on the current operating system.

    Returns:
        PlatformAdapter instance for the current platform.

    Raises:
        RuntimeError: If the platform is not supported.
    """
    system = platform.system().lower()

    if system == "windows":
        return WindowsAdapter()
    elif system == "darwin":
        return MacOSAdapter()
    elif system == "linux":
        return LinuxAdapter()
    else:
        raise RuntimeError(
            f"Unsupported platform: {system}. "
            f"Supported platforms: Windows, macOS, Linux."
        )


def get_platform_name() -> str:
    """Get the human-readable name of the current platform.

    Returns:
        Platform name string (e.g., "Windows", "macOS", "Linux").
    """
    return get_platform_adapter().info.name


def get_modifier_key() -> str:
    """Get the primary modifier key name for the current platform.

    Returns:
        Modifier key name (e.g., "ctrl", "command").
    """
    return get_platform_adapter().info.modifier_key


def reset_adapter():
    """Reset the singleton adapter instance (thread-safe).

    Useful for testing or when the platform detection needs to be re-run.
    """
    global _adapter
    with _lock:
        _adapter = None