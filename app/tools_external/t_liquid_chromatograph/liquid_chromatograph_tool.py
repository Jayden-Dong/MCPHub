import os
import time
import requests
import yaml
from typing import Dict, Any, Annotated, Tuple
from pydantic import Field

from config_py.config import settings

# 获取当前模块所在目录
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_task_prompt(task_name: str) -> str:
    """
    从 task_prompt.yaml 中读取指定任务的 prompt 模板

    :param task_name: 任务名称
    :return: 任务描述 prompt 模板，如果不存在则返回空字符串
    """
    prompt_file = os.path.join(_MODULE_DIR, "task_prompt.yaml")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompts = yaml.safe_load(f)
            return prompts.get(task_name, "")
    except Exception:
        return ""


class LiquidChromatographTool:

    def __init__(self):
        self.autogui_client = AutoGUIClient()

    def _wait_for_task(
        self,
        timeout: int = -1,
        poll_interval: float = 5.0
    ) -> tuple[bool | None, str, dict[str, Any]]:
        """
        等待任务完成

        :param timeout: 超时时间（秒），-1 表示无限等待
        :param poll_interval: 轮询间隔（秒）
        :return: [True:成功；False:失败；None:超时 | 失败原因 | 任务数据]
        """
        start_time = time.time()

        while True:
            # 检查超时
            if timeout != -1:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None, "任务执行超时", {}

            # 获取任务状态
            status, message, data = self.autogui_client.get_status()

            if status is True:
                # 任务正常完成
                return True, "", data
            elif status is False:
                # 任务异常结束
                return False, message, data
            elif status is None:
                # 任务执行中，等待后继续轮询
                time.sleep(poll_interval)
                continue

        # 理论上不会执行到这里
        return None, "未知状态", {}

    def set_threshold(
        self,
        protocol_name: str,
        threshold: float,
        timeout: int = -1
    ) -> tuple[bool | None, str, dict[str, Any]]:
        """
        设置收集阈值

        :param protocol_name: 脚本名称
        :param threshold: 收集阈值
        :param timeout: 超时时间（秒），-1 表示无限等待
        :return: [True:成功；False:失败；None:超时 | 失败原因 | 任务数据]
        """
        prompt_template = _load_task_prompt("set_threshold")
        task_description = prompt_template.format(protocol_name, threshold)

        # 启动任务
        success, message = self.autogui_client.start_task(task_description)
        if not success:
            return False, f"启动任务失败: {message}", {}

        # 等待任务完成
        return self._wait_for_task(timeout)

    def start_collect_protocol(
        self,
        protocol_name: str,
        result_file: str,
        timeout: int = -1
    ) -> tuple[bool | None, str, dict[str, Any]]:
        """
        运行收集馏分的脚本

        :param protocol_name: 脚本名称
        :param result_file: 结果文件
        :param timeout: 超时时间（秒），-1 表示无限等待
        :return: [True:成功；False:失败；None:超时 | 失败原因 | 任务数据]
        """
        prompt_template = _load_task_prompt("start_collect_protocol")
        task_description = prompt_template.format(protocol_name, result_file)

        # 启动任务
        success, message = self.autogui_client.start_task(task_description)
        if not success:
            return False, f"启动任务失败: {message}", {}

        # 等待任务完成
        return self._wait_for_task(timeout)

    def start_analyse_protocol(
        self,
        protocol_name: str,
        result_file: str,
        timeout: int = -1
    ) -> tuple[bool | None, str, dict[str, Any]]:
        """
        运行分析馏分的脚本

        :param protocol_name: 脚本名称
        :param result_file: 结果文件
        :param timeout: 超时时间（秒），-1 表示无限等待
        :return: [True:成功；False:失败；None:超时 | 失败原因 | 任务数据]
        """
        prompt_template = _load_task_prompt("start_analyse_protocol")
        task_description = prompt_template.format(protocol_name, result_file)

        # 启动任务
        success, message = self.autogui_client.start_task(task_description)
        if not success:
            return False, f"启动任务失败: {message}", {}

        # 等待任务完成
        return self._wait_for_task(timeout)

    def get_protocol_status(
        self,
        timeout: int = -1
    ) -> tuple[bool | None, str, dict[str, Any]]:
        """
        获取脚本执行状态

        :param timeout: 超时时间（秒），-1 表示无限等待
        :return: [True:成功；False:失败；None:超时 | 失败原因 | 任务数据]
        """
        prompt_template = _load_task_prompt("get_protocol_status")

        # 启动任务
        success, message = self.autogui_client.start_task(prompt_template)
        if not success:
            return False, f"启动任务失败: {message}", {}

        # 等待任务完成
        return self._wait_for_task(timeout)

    def get_purity(
        self,
        result_file: str,
        timeout: int = -1
    ) -> tuple[bool | None, str, dict[str, Any]]:
        """
        获取纯度

        :param result_file: 结果文件
        :param timeout: 超时时间（秒），-1 表示无限等待
        :return: [True:成功；False:失败；None:超时 | 失败原因 | 任务数据]
        """
        prompt_template = _load_task_prompt("get_purity")
        task_description = prompt_template.format( result_file)

        # 启动任务
        success, message = self.autogui_client.start_task(task_description)
        if not success:
            return False, f"启动任务失败: {message}", {}

        # 等待任务完成
        return self._wait_for_task(timeout)


class AutoGUIClient:
    """AutoGUI WebAPI 客户端"""

    def __init__(self, base_url: str = None):
        """
        初始化客户端
        :param base_url: API基础地址，默认从配置读取
        """
        self.base_url = base_url or f"http://localhost:{settings.PORT}"

    def start_task(self, task_description: str) -> tuple[bool, str]:
        """
        启动GUI自动化任务
        :param task_description: 自然语言描述的GUI自动化任务
        :return: [是否启动任务成功，启动失败的原因]
        """
        url = f"{self.base_url}/api/autogui/v1/start_task"
        try:
            response = requests.post(url, data={"task": task_description}, timeout=20)
            response.raise_for_status()
            result = response.json()

            if result.get("Code") == 12:
                return True, ""
            else:
                return False, result.get("Message", {}).get("Description", "启动失败")
        except requests.exceptions.RequestException as e:
            return False, f"请求失败: {str(e)}"
        except Exception as e:
            return False, f"未知错误: {str(e)}"

    def get_status(self) -> tuple[bool | None, str, dict]:
        """
        获取GUI自动化任务状态
        :return: [True:任务正常完成，False:任务异常结束，None:任务执行中 | 任务执行失败的原因 | 任务执行结束返回的数据]
        """
        url = f"{self.base_url}/api/autogui/v1/get_status"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            result = response.json()

            if result.get("Code") == 12:
                data = result.get("Data", {})
                # 根据状态映射返回值
                if data.get("is_running"):
                    # 任务执行中
                    return None, "", data
                elif data.get("is_finished") and not data.get("error_msg"):
                    # 任务正常完成
                    return True, "", data
                elif data.get("is_finished") and data.get("error_msg"):
                    # 任务异常结束
                    err_msg = data.get("error_msg", "任务执行失败")
                    return False, err_msg, data
                else:
                    # 未知状态
                    return None, "", data
            else:
                return False, result.get("Message", {}).get("Description", "获取状态失败"), {}
        except requests.exceptions.RequestException as e:
            return False, f"请求失败: {str(e)}", {}
        except Exception as e:
            return False, f"未知错误: {str(e)}", {}


liquid_chromatograph_tool = LiquidChromatographTool()


# # ============================================================================
# # 便捷函数 (MCP 工具函数)
# # ============================================================================
#
# def set_threshold(
#     protocol_name: Annotated[str, Field(description="脚本名称")],
#     threshold: Annotated[float, Field(description="收集阈值")],
#     timeout: Annotated[int, Field(description="超时时间（秒），-1表示无限等待")] = -1
# ) -> Tuple[bool | None, str, Dict[str, Any]]:
#     """
#     设置收集阈值便捷函数
#
#     Returns:
#         (True:成功；False:失败；None:超时, 失败原因, 任务数据)
#     """
#     return liquid_chromatograph_tool.set_threshold(protocol_name, threshold, timeout)
#
#
# def start_collect_protocol(
#     protocol_name: Annotated[str, Field(description="脚本名称")],
#     result_file: Annotated[str, Field(description="结果文件路径")],
#     timeout: Annotated[int, Field(description="超时时间（秒），-1表示无限等待")] = -1
# ) -> Tuple[bool | None, str, Dict[str, Any]]:
#     """
#     运行收集馏分脚本便捷函数
#
#     Returns:
#         (True:成功；False:失败；None:超时, 失败原因, 任务数据)
#     """
#     return liquid_chromatograph_tool.start_collect_protocol(protocol_name, result_file, timeout)
#
#
# def start_analyse_protocol(
#     protocol_name: Annotated[str, Field(description="脚本名称")],
#     result_file: Annotated[str, Field(description="结果文件路径")],
#     timeout: Annotated[int, Field(description="超时时间（秒），-1表示无限等待")] = -1
# ) -> Tuple[bool | None, str, Dict[str, Any]]:
#     """
#     运行分析馏分脚本便捷函数
#
#     Returns:
#         (True:成功；False:失败；None:超时, 失败原因, 任务数据)
#     """
#     return liquid_chromatograph_tool.start_analyse_protocol(protocol_name, result_file, timeout)
#
#
# def get_protocol_status(
#     timeout: Annotated[int, Field(description="超时时间（秒），-1表示无限等待")] = -1
# ) -> Tuple[bool | None, str, Dict[str, Any]]:
#     """
#     获取脚本执行状态便捷函数
#
#     Returns:
#         (True:成功；False:失败；None:超时, 失败原因, 任务数据)
#     """
#     return liquid_chromatograph_tool.get_protocol_status(timeout)
#
#
# def get_purity(
#     result_file: Annotated[str, Field(description="结果文件路径")],
#     timeout: Annotated[int, Field(description="超时时间（秒），-1表示无限等待")] = -1
# ) -> Tuple[bool | None, str, Dict[str, Any]]:
#     """
#     获取纯度便捷函数
#
#     Returns:
#         (True:成功；False:失败；None:超时, 失败原因, 任务数据)
#     """
#     return liquid_chromatograph_tool.get_purity(result_file, timeout)