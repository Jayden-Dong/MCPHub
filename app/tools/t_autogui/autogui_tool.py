"""
GUI自动化工具模块
提供GUI自动化任务的启动、状态查询、历史查询和停止等操作
"""
import threading
from typing import Dict

from config_py.logger import app_logger
from tools.t_autogui.agent import ReactAgent
from tools.t_autogui.config import GUI_MODE, REMOTE_GUI_URL


class AutoGUITool:
    """GUI自动化工具类"""

    def __init__(self):
        self._lock = threading.Lock()

        # 根据配置选择本地或远程 GUI 操作模式
        gui_tools = None
        if GUI_MODE == "remote":
            if not REMOTE_GUI_URL:
                raise ValueError("gui_mode 为 remote 时必须配置 remote_gui_url")
            from tools.t_autogui.tools.remote_gui_tools import RemoteGUITools
            gui_tools = RemoteGUITools(REMOTE_GUI_URL)
            app_logger.info(f"AutoGUI 使用远程模式: {REMOTE_GUI_URL}")
        else:
            app_logger.info("AutoGUI 使用本地模式")

        self._agent = ReactAgent(gui_tools=gui_tools)
        self._thread: threading.Thread = None
        # idle | running | finished | error
        self._status = "idle"
        self._error_msg = ""

    def start_task(self, task: str) -> Dict:
        """
        启动一个GUI自动化任务（后台异步运行）。

        Args:
            task: 自然语言描述的任务内容。

        Returns:
            包含启动结果的字典：
                - success: 是否成功启动
                - err_msg: 错误信息（成功时为空字符串）
        """
        with self._lock:
            if self._status == "running":
                return {
                    "success": False,
                    "err_msg": "当前有任务正在运行，请先停止或等待任务完成。"
                }
            self._status = "running"
            self._error_msg = ""

        def _run():
            try:
                self._agent.run(task)
                with self._lock:
                    self._status = "finished"
            except Exception as e:
                app_logger.error(f"GUI自动化任务异常: {e}", exc_info=True)
                with self._lock:
                    self._status = "error"
                    self._error_msg = str(e)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

        app_logger.info(f"已启动GUI自动化任务: {task}")
        return {
            "success": True,
            "err_msg": ""
        }

    def get_status(self) -> Dict:
        """
        获取当前任务的运行状态。

        Returns:
            包含状态信息的字典：
                - success: 始终为True
                - data: 状态详情（tool_status、task、current_step等）
                - err_msg: 空字符串
        """
        with self._lock:
            agent_status = self._agent.get_status()
            agent_status["tool_status"] = self._status
            agent_status["error_msg"] = self._error_msg

        return {
            "success": True,
            "data": agent_status,
            "err_msg": ""
        }

    def get_history(self) -> Dict:
        """
        获取当前任务的执行历史。

        Returns:
            包含历史记录的字典：
                - success: 始终为True
                - data: 步骤记录列表，每项包含step_number、thought、action、success、error、screenshot_path
                - err_msg: 空字符串
        """
        with self._lock:
            history = [
                {
                    "step_number": r.step_number,
                    "thought": r.thought,
                    "action": r.action.model_dump(),
                    "success": r.success,
                    "error": r.error,
                    "screenshot_path": r.screenshot_path,
                    "duration": r.duration,
                }
                for r in self._agent.history
            ]

        return {
            "success": True,
            "data": history,
            "err_msg": ""
        }

    def stop_task(self) -> Dict:
        """
        停止当前正在运行的任务。

        Returns:
            包含停止结果的字典：
                - success: 是否成功停止
                - err_msg: 错误信息（成功时为空字符串）
        """
        with self._lock:
            if self._status != "running":
                return {
                    "success": False,
                    "err_msg": f"当前没有正在运行的任务（状态: {self._status}）"
                }
            self._agent.is_running = False
            self._status = "finished"

        app_logger.info("已请求停止GUI自动化任务")
        return {
            "success": True,
            "err_msg": ""
        }


# 创建单例实例
autogui_tool = AutoGUITool()
