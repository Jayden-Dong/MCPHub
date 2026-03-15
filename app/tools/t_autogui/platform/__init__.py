"""Platform adaptation layer for cross-platform GUI automation.

This module provides automatic OS detection and platform-specific adapters
for keyboard shortcuts, clipboard operations, and system prompts.
"""

from .factory import get_platform_adapter, get_platform_name
from .base import PlatformAdapter, PlatformInfo

__all__ = [
    "get_platform_adapter",
    "get_platform_name",
    "PlatformAdapter",
    "PlatformInfo",
]