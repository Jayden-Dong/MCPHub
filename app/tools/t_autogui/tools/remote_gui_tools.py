"""Remote GUI tools — 通过 HTTP 调用远程 agent 执行截图和鼠标键盘操作。

接口与 GUITools 保持一致，可直接注入 ReactAgent。
"""
import base64
import io

import requests
from PIL import Image

from ..config import setup_logging
from ..schemas.actions import ActionType, FinishedAction

logger = setup_logging("remote_tools")


class RemoteGUITools:
    """通过 HTTP 与远程 GUI Agent 通信，替代本地 GUITools。"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Args:
            base_url: 远程 agent 地址，如 "http://192.168.1.100:8765"
            timeout: HTTP 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

        # 初始化时获取远程屏幕信息
        info = self.get_screen_info()
        self.screen_width = info["screen_width"]
        self.screen_height = info["screen_height"]
        logger.info(
            f"RemoteGUITools connected to {self.base_url}, "
            f"Screen: {self.screen_width}x{self.screen_height}"
        )

    def take_screenshot(self) -> Image.Image:
        """从远程 agent 获取截图。

        Returns:
            PIL Image
        """
        logger.info("Requesting remote screenshot...")
        resp = self._session.get(
            f"{self.base_url}/api/gui-agent/screenshot",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        image_bytes = base64.b64decode(data["image"])
        screenshot = Image.open(io.BytesIO(image_bytes))
        logger.info(f"Remote screenshot received: {screenshot.size}")
        return screenshot

    def execute_action(self, action: ActionType) -> bool:
        """将动作发送到远程 agent 执行。

        Args:
            action: 动作对象

        Returns:
            True if successful
        """
        if isinstance(action, FinishedAction):
            logger.info(f"Task finished: {action.message}")
            return True

        action_data = action.model_dump()
        logger.info(f"Sending action to remote: {action_data}")
        resp = self._session.post(
            f"{self.base_url}/api/gui-agent/execute_action",
            json=action_data,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()
        success = result.get("success", False)
        if not success:
            logger.warning(f"Remote action failed: {result.get('error', 'unknown')}")
        return success

    def get_screen_info(self) -> dict:
        """从远程 agent 获取屏幕信息。

        Returns:
            Dict with screen_width, screen_height, mouse_x, mouse_y
        """
        resp = self._session.get(
            f"{self.base_url}/api/gui-agent/screen_info",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()
