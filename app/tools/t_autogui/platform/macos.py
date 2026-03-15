"""macOS platform adapter."""
import subprocess
import logging

from .base import PlatformAdapter, PlatformInfo

logger = logging.getLogger(__name__)


class MacOSAdapter(PlatformAdapter):
    """Platform adapter for macOS systems."""

    def __init__(self):
        self._info: PlatformInfo | None = None

    @property
    def info(self) -> PlatformInfo:
        """Return macOS-specific platform information (cached)."""
        if self._info is None:
            self._info = PlatformInfo(
                name="macOS",
                modifier_key="command",
                modifier_display="Command (⌘)",
                select_all_keys=["command", "a"],
                copy_keys=["command", "c"],
                paste_keys=["command", "v"],
                delete_key="delete",  # Note: on Mac, this is Backspace key
            )
        return self._info

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to macOS clipboard using pbcopy.

        Args:
            text: Text to copy to clipboard.

        Returns:
            True if successful, False otherwise.
        """
        # Try pyperclip first
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.debug("Copied text via pyperclip")
            return True
        except ImportError:
            logger.debug("pyperclip not available, falling back to pbcopy")
        except Exception as e:
            logger.warning(f"pyperclip failed: {e}, falling back to pbcopy")

        # Fallback to pbcopy (macOS built-in)
        try:
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
            )
            process.communicate(text.encode("utf-8"))
            if process.returncode == 0:
                logger.debug("Copied text via pbcopy")
                return True
            else:
                logger.error(f"pbcopy returned non-zero: {process.returncode}")
                return False
        except FileNotFoundError:
            logger.error("pbcopy not found (this should not happen on macOS)")
            return False
        except Exception as e:
            logger.error(f"Clipboard operation failed: {e}")
            return False

    def get_system_prompt_addon(self) -> str:
        """Return macOS-specific prompt additions."""
        return """## 平台特定说明
- 当前系统: macOS
- 使用 Command (⌘) 键作为主要修饰键
- 复制: Command+C
- 粘贴: Command+V
- 全选: Command+A
- 清空输入框: Command+A 全选后按 Delete 删除
- 打开应用程序: 可以按 Command+Space 打开 Spotlight 搜索
- 注意: macOS 的 delete 键实际上是退格键，向前删除需要使用 fn+delete"""