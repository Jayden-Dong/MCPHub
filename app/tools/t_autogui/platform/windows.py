"""Windows platform adapter."""
import subprocess
import logging

from .base import PlatformAdapter, PlatformInfo

logger = logging.getLogger(__name__)


class WindowsAdapter(PlatformAdapter):
    """Platform adapter for Windows systems."""

    def __init__(self):
        self._info: PlatformInfo | None = None

    @property
    def info(self) -> PlatformInfo:
        """Return Windows-specific platform information (cached)."""
        if self._info is None:
            self._info = PlatformInfo(
                name="Windows",
                modifier_key="ctrl",
                modifier_display="Ctrl",
                select_all_keys=["ctrl", "a"],
                copy_keys=["ctrl", "c"],
                paste_keys=["ctrl", "v"],
                delete_key="delete",
            )
        return self._info

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to Windows clipboard.

        Tries pyperclip first, falls back to PowerShell if unavailable.

        Args:
            text: Text to copy to clipboard.

        Returns:
            True if successful, False otherwise.
        """
        # Try pyperclip first (more reliable for Unicode)
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.debug("Copied text via pyperclip")
            return True
        except ImportError:
            logger.debug("pyperclip not available, falling back to PowerShell")
        except Exception as e:
            logger.warning(f"pyperclip failed: {e}, falling back to PowerShell")

        # Fallback to PowerShell with proper escaping
        try:
            # Use Base64 encoding to avoid all escaping issues
            import base64
            encoded = base64.b64encode(text.encode("utf-16le")).decode("ascii")
            ps_command = (
                f"[System.Text.Encoding]::Unicode.GetString("
                f"[Convert]::FromBase64String('{encoded}')"
                f") | Set-Clipboard"
            )
            subprocess.run(
                ["powershell", "-Command", ps_command],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug("Copied text via PowerShell (Base64)")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"PowerShell clipboard failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Clipboard operation failed: {e}")
            return False

    def get_system_prompt_addon(self) -> str:
        """Return Windows-specific prompt additions."""
        return """## 平台特定说明
- 当前系统: Windows
- 使用 Ctrl 键作为主要修饰键
- 复制: Ctrl+C
- 粘贴: Ctrl+V
- 全选: Ctrl+A
- 清空输入框: Ctrl+A 全选后按 Delete 删除
- 打开应用程序: 可以按 Win 键打开开始菜单搜索"""