"""
笔记本工具的MCP工具定义
提供笔记本的添加、读取等MCP工具
"""
from config_py.config import settings
from utils import com_utils
from mcp_service import mcp
from config_py.prompt import prompt_manager
from tools.t_notebook.notebook_tool import notebook_tool
from utils.com_utils import get_mcp_exposed_url

add_note_str = "add_note"
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{add_note_str}',
          enabled=com_utils.get_tool_enable(add_note_str),
          description=f"MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(add_note_str)}")
def add_note(note: str, note_file_name):
    """
    将笔记添加到指定文件中。

    Args:
        note: 要添加的笔记内容。
        note_file_name: 笔记文件名称。

    Returns:
        str: JSON格式字符串，包含success、err_msg字段。
            - success: 布尔值，表示添加是否成功
            - err_msg: 失败时返回失败原因，成功时返回空字符串
    """
    return notebook_tool.add_note(note, note_file_name)


read_note_str = "read_note"
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{read_note_str}',
          enabled=com_utils.get_tool_enable(read_note_str),
          description=f"MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(read_note_str)}")
def read_note(note_file_name):
    """
    读取指定文件本中的笔记。

    Args:
        note_file_name: 笔记本名称。

    Returns:
        str: JSON格式字符串，包含success、note_content、err_msg字段。
            - success: 布尔值，表示读取是否成功
            - note_content: 成功时返回笔记内容，失败时返回空字符串
            - err_msg: 失败时返回失败原因，成功时返回空字符串
    """
    return notebook_tool.read_note(note_file_name)