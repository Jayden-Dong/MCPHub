"""Linux platform adapter."""
import subprocess
import logging
import shutil

from .base import PlatformAdapter, PlatformInfo

logger = logging.getLogger(__name__)


class LinuxAdapter(PlatformAdapter):
    """Platform adapter for Linux systems.

    Supports multiple clipboard managers: pyperclip, xclip, xsel, wl-copy (Wayland).
    """

    def __init__(self):
        self._info: PlatformInfo | None = None

    @property
    def info(self) -> PlatformInfo:
        """Return Linux-specific platform information (cached)."""
        if self._info is None:
            self._info = PlatformInfo(
                name="Linux",
                modifier_key="ctrl",
                modifier_display="Ctrl",
                select_all_keys=["ctrl", "a"],
                copy_keys=["ctrl", "c"],
                paste_keys=["ctrl", "v"],
                delete_key="delete",
            )
        return self._info

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to Linux clipboard.

        Tries multiple methods in order:
        1. pyperclip (Python library)
        2. wl-copy (Wayland)
        3. xclip (X11)
        4. xsel (X11 alternative)

        Args:
            text: Text to copy to clipboard.

        Returns:
            True if successful, False otherwise.
        """
        # Method 1: Try pyperclip
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.debug("Copied text via pyperclip")
            return True
        except ImportError:
            logger.debug("pyperclip not available")
        except Exception as e:
            logger.debug(f"pyperclip failed: {e}")

        # Method 2: Try wl-copy (Wayland)
        if shutil.which("wl-copy"):
            try:
                process = subprocess.Popen(
                    ["wl-copy"],
                    stdin=subprocess.PIPE,
                )
                process.communicate(text.encode("utf-8"))
                if process.returncode == 0:
                    logger.debug("Copied text via wl-copy")
                    return True
            except Exception as e:
                logger.debug(f"wl-copy failed: {e}")

        # Method 3: Try xclip (X11)
        if shutil.which("xclip"):
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode("utf-8"),
                    check=True,
                )
                logger.debug("Copied text via xclip")
                return True
            except subprocess.CalledProcessError as e:
                logger.debug(f"xclip failed: {e}")
            except Exception as e:
                logger.debug(f"xclip error: {e}")

        # Method 4: Try xsel (X11 alternative)
        if shutil.which("xsel"):
            try:
                subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text.encode("utf-8"),
                    check=True,
                )
                logger.debug("Copied text via xsel")
                return True
            except subprocess.CalledProcessError as e:
                logger.debug(f"xsel failed: {e}")
            except Exception as e:
                logger.debug(f"xsel error: {e}")

        logger.error("No clipboard method available. Install pyperclip, xclip, xsel, or wl-copy.")
        return False

    def get_system_prompt_addon(self) -> str:
        """Return Linux-specific prompt additions."""
        return """## 平台特定说明
- 当前系统: Linux
- 使用 Ctrl 键作为主要修饰键
- 复制: Ctrl+C
- 粘贴: Ctrl+V
- 全选: Ctrl+A
- 清空输入框: Ctrl+A 全选后按 Delete 删除
- 打开应用程序: 可以按 Super 键（Windows键）打开应用程序菜单"""