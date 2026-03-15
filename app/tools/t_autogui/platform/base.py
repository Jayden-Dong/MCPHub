"""Platform adapter abstract base class and data types."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class PlatformInfo:
    """Platform-specific information.

    Attributes:
        name: Human-readable platform name (e.g., "Windows", "macOS", "Linux")
        modifier_key: The primary modifier key name for hotkeys (e.g., "ctrl", "command")
        modifier_display: Display name for the modifier key (e.g., "Ctrl", "Command")
        select_all_keys: Key sequence for select-all action (e.g., ["ctrl", "a"])
        copy_keys: Key sequence for copy action
        paste_keys: Key sequence for paste action
        delete_key: Key name for delete action
    """
    name: str
    modifier_key: str
    modifier_display: str
    select_all_keys: List[str]
    copy_keys: List[str]
    paste_keys: List[str]
    delete_key: str = "delete"


class PlatformAdapter(ABC):
    """Abstract base class for platform-specific adapters.

    Each platform (Windows, macOS, Linux) should implement this interface
    to provide platform-specific keyboard shortcuts and clipboard operations.
    """

    @property
    @abstractmethod
    def info(self) -> PlatformInfo:
        """Return platform-specific information.

        Returns:
            PlatformInfo with modifier keys and display names.
        """
        pass

    @abstractmethod
    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard.

        Args:
            text: Text to copy to clipboard.

        Returns:
            True if successful, False otherwise.
        """
        pass

    def get_clear_input_sequence(self) -> tuple[List[str], str]:
        """Get the key sequence to clear an input field.

        Returns:
            Tuple of (select_all_keys, delete_key).
        """
        return (self.info.select_all_keys, self.info.delete_key)

    def get_system_prompt_addon(self) -> str:
        """Return platform-specific additions to the system prompt.

        Returns:
            String with platform-specific instructions.
        """
        info = self.info
        return f"""## 平台特定说明
- 当前系统: {info.name}
- 使用 {info.modifier_display} 键作为主要修饰键
- 复制: {info.modifier_display}+C
- 粘贴: {info.modifier_display}+V
- 全选: {info.modifier_display}+A
- 清空输入框: {info.modifier_display}+A 全选后按 Delete 删除"""