"""
GUI自动化工具的MCP工具定义
提供GUI自动化任务的启动、状态查询、历史查询和停止等MCP工具
"""
from config_py.config import settings
from utils import com_utils
from mcp_service import mcp
from config_py.prompt import prompt_manager
from tools.t_autogui.autogui_tool import autogui_tool
from utils.com_utils import get_mcp_exposed_url


start_task_str = "autogui_start_task"
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{start_task_str}',
          enabled=com_utils.get_tool_enable(start_task_str),
          description=f"MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(start_task_str)}")
def autogui_start_task(task: str):
    """
    启动一个GUI自动化任务（后台异步运行）。

    Args:
        task: 自然语言描述的任务内容。

    Returns:
        dict: 包含success、err_msg字段。
            - success: 是否成功启动
            - err_msg: 失败时返回失败原因，成功时返回空字符串
    """
    return autogui_tool.start_task(task)


get_status_str = "autogui_get_status"
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_status_str}',
          enabled=com_utils.get_tool_enable(get_status_str),
          description=f"MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_status_str)}")
def autogui_get_status():
    """
    获取当前GUI自动化任务的运行状态。

    Returns:
        dict: 包含success、data、err_msg字段。
            - success: 始终为True
            - data: 状态详情，包含tool_status、task、current_step、max_steps、is_running、is_finished、finish_message、error_msg
            - err_msg: 空字符串
    """
    return autogui_tool.get_status()


get_history_str = "autogui_get_history"
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_history_str}',
          enabled=com_utils.get_tool_enable(get_history_str),
          description=f"MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_history_str)}")
def autogui_get_history():
    """
    获取当前GUI自动化任务的执行历史。

    Returns:
        dict: 包含success、data、err_msg字段。
            - success: 始终为True
            - data: 步骤记录列表，每项包含step_number、thought、action、success、error、screenshot_path
            - err_msg: 空字符串
    """
    return autogui_tool.get_history()


stop_task_str = "autogui_stop_task"
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{stop_task_str}',
          enabled=com_utils.get_tool_enable(stop_task_str),
          description=f"MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(stop_task_str)}")
def autogui_stop_task():
    """
    停止当前正在运行的GUI自动化任务。

    Returns:
        dict: 包含success、err_msg字段。
            - success: 是否成功停止
            - err_msg: 失败时返回失败原因，成功时返回空字符串
    """
    return autogui_tool.stop_task()
