"""远程 GUI Agent 服务 — 部署在需要被操控的目标电脑上。

提供截图和鼠标键盘操作的 HTTP API，供控制端远程调用。

部署方式:
    1. 将 t_autogui 目录复制到目标电脑
    2. 安装依赖: pip install fastapi uvicorn pyautogui pillow pyperclip
    3. 在 t_autogui 的上级目录运行:
       python -m t_autogui.remote_agent_server --host 0.0.0.0 --port 8765
"""
import argparse
import base64
import io
import sys
import time
import logging
from typing import Optional
from pathlib import Path

# 防止同目录下的 platform/ 包遮蔽标准库 platform 模块
# 当直接运行此脚本时，Python 会将脚本所在目录加入 sys.path[0]
_script_dir = str(Path(__file__).resolve().parent)
if _script_dir in sys.path:
    sys.path.remove(_script_dir)

import pyautogui
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
from PIL import Image

# ── 平台相关 ──────────────────────────────────────────
# 当独立部署时需要 platform adapter，尝试从包内导入；
# 若失败则提供一个最简实现。
try:
    from .platform.factory import get_platform_adapter
    _HAS_PLATFORM = True
except ImportError:
    _HAS_PLATFORM = False

# ── 日志 ─────────────────────────────────────────────
logger = logging.getLogger("remote_gui_agent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s - %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(_handler)


# =====================================================================
# Action Models（自包含，无需依赖 schemas.actions）
# =====================================================================

class ClickAction(BaseModel):
    type: str = "click"
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    button: str = "left"
    clicks: int = Field(default=1, ge=1, le=3)


class TypeAction(BaseModel):
    type: str = "type"
    text: str = Field(min_length=1)


class HotkeyAction(BaseModel):
    type: str = "hotkey"
    keys: list[str] = Field(min_length=1)


class ScrollAction(BaseModel):
    type: str = "scroll"
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    direction: str = "down"
    amount: int = Field(default=3, ge=1)


class DragAction(BaseModel):
    type: str = "drag"
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(ge=0)
    y2: float = Field(ge=0)
    button: str = "left"


class WaitAction(BaseModel):
    type: str = "wait"
    seconds: float = Field(default=1.0, ge=0.1, le=10.0)


_ACTION_MAP = {
    "click": ClickAction,
    "type": TypeAction,
    "hotkey": HotkeyAction,
    "scroll": ScrollAction,
    "drag": DragAction,
    "wait": WaitAction,
}


class ActionRequest(BaseModel):
    """通用动作请求体 — 所有字段可选，根据 type 解析。"""
    type: str
    x: Optional[float] = None
    y: Optional[float] = None
    button: Optional[str] = None
    clicks: Optional[int] = None
    text: Optional[str] = None
    keys: Optional[list[str]] = None
    direction: Optional[str] = None
    amount: Optional[int] = None
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    seconds: Optional[float] = None


# =====================================================================
# 本地 GUI 操作（精简版，不依赖 config 模块）
# =====================================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


class _LocalGUIExecutor:
    """目标机器上实际执行截图和鼠标键盘操作的执行器。"""

    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        # 平台适配器（用于剪贴板文字输入）
        if _HAS_PLATFORM:
            self.platform = get_platform_adapter()
        else:
            self.platform = None
        logger.info(f"LocalGUIExecutor initialized. Screen: {self.screen_width}x{self.screen_height}")

    def take_screenshot(self) -> Image.Image:
        return pyautogui.screenshot()

    def get_screen_info(self) -> dict:
        mx, my = pyautogui.position()
        return {
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "mouse_x": mx,
            "mouse_y": my,
        }

    def _to_abs(self, x: float, y: float) -> tuple[int, int]:
        if x > 1.0 or y > 1.0:
            return int(x), int(y)
        ax = max(0, min(int(x * self.screen_width), self.screen_width - 1))
        ay = max(0, min(int(y * self.screen_height), self.screen_height - 1))
        return ax, ay

    def execute_action(self, action) -> bool:
        t = action.type
        try:
            if t == "click":
                x, y = self._to_abs(action.x, action.y)
                pyautogui.click(x=x, y=y, button=action.button, clicks=action.clicks)
            elif t == "type":
                self._type_text(action.text)
            elif t == "hotkey":
                pyautogui.hotkey(*action.keys)
            elif t == "scroll":
                x, y = self._to_abs(action.x, action.y)
                pyautogui.moveTo(x, y, duration=0.1)
                time.sleep(0.1)
                is_up = action.direction == "up"
                if action.amount <= 3:
                    for _ in range(action.amount):
                        pyautogui.scroll(100 if is_up else -100)
                        time.sleep(0.05)
                else:
                    pyautogui.scroll(action.amount if is_up else -action.amount)
                time.sleep(0.3)
            elif t == "drag":
                x1, y1 = self._to_abs(action.x1, action.y1)
                x2, y2 = self._to_abs(action.x2, action.y2)
                pyautogui.moveTo(x1, y1, duration=0.2)
                time.sleep(0.1)
                pyautogui.mouseDown(button=action.button)
                time.sleep(0.1)
                pyautogui.moveTo(x2, y2, duration=0.5)
                time.sleep(0.1)
                pyautogui.mouseUp(button=action.button)
                time.sleep(0.3)
            elif t == "wait":
                time.sleep(action.seconds)
            else:
                logger.error(f"Unknown action type: {t}")
                return False
            return True
        except Exception as e:
            logger.error(f"Action '{t}' failed: {e}")
            return False

    def _type_text(self, text: str):
        """通过剪贴板粘贴文字（支持中文）。"""
        if self.platform and hasattr(self.platform, 'copy_to_clipboard'):
            self.platform.copy_to_clipboard(text)
            time.sleep(0.1)
            paste_keys = getattr(self.platform.info, 'paste_keys', ['ctrl', 'v'])
            pyautogui.hotkey(*paste_keys)
        else:
            # 简单回退：pyperclip + ctrl+v
            try:
                import pyperclip
                pyperclip.copy(text)
            except ImportError:
                pass
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)


# =====================================================================
# FastAPI 服务
# =====================================================================

app = FastAPI(title="Remote GUI Agent", version="1.0.0")

_executor: Optional[_LocalGUIExecutor] = None


def get_executor() -> _LocalGUIExecutor:
    global _executor
    if _executor is None:
        _executor = _LocalGUIExecutor()
    return _executor


@app.get("/api/gui-agent/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.get("/api/gui-agent/screenshot")
async def screenshot():
    """截取当前屏幕，返回 base64 编码的 PNG 图片。"""
    executor = get_executor()
    img = executor.take_screenshot()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {"image": image_b64, "width": img.width, "height": img.height}


@app.get("/api/gui-agent/screen_info")
async def screen_info():
    """返回屏幕尺寸和鼠标位置。"""
    executor = get_executor()
    return executor.get_screen_info()


@app.post("/api/gui-agent/execute_action")
async def execute_action(request: ActionRequest):
    """执行鼠标键盘操作。"""
    executor = get_executor()

    action_cls = _ACTION_MAP.get(request.type)
    if action_cls is None:
        return {"success": False, "error": f"Unknown action type: {request.type}"}

    try:
        action_data = {k: v for k, v in request.model_dump().items() if v is not None}
        action = action_cls.model_validate(action_data)
    except Exception as e:
        return {"success": False, "error": f"Invalid action data: {e}"}

    try:
        success = executor.execute_action(action)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =====================================================================
# CLI 入口
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Remote GUI Agent Server")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    args = parser.parse_args()

    print(f"Starting Remote GUI Agent on {args.host}:{args.port}")
    print(f"  截图接口: http://{args.host}:{args.port}/api/gui-agent/screenshot")
    print(f"  动作接口: http://{args.host}:{args.port}/api/gui-agent/execute_action")
    print(f"  屏幕信息: http://{args.host}:{args.port}/api/gui-agent/screen_info")
    print(f"  健康检查: http://{args.host}:{args.port}/api/gui-agent/health")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
