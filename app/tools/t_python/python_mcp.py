from config_py.config import settings
from utils import com_utils
from config_py.prompt import prompt_manager
from utils.com_utils import get_mcp_exposed_url

from mcp_service import mcp
from tools.t_python.python_tool import python_tool

# save_python_script_str = 'save_python_script'
# @mcp.tool(name=f'{save_python_script_str}',
#           enabled=utils.com_utils.get_tool_enable(save_python_script_str),
#           description=f'所属主机：{get_machine_code_simple()}。{prompt_manager.get(save_python_script_str)}')
# def save_python_script(file_name: str, script_content: str) -> dict:
#     f"""
#     保存Python脚本到指定文件路径。
#
#     Args:
#         file_name: 保存文件的名称，不包含路径。
#         script_content: 脚本内容，python解释器的版本是>=3.10。
#
#     Returns:
#         包含保存结果信息的字典：
#             - success: 是否保存成功
#             - error: 错误信息（成功时为None）
#     """
#     return python_tool.save_python_script(file_name, script_content)
#
#
# run_python_script_str = 'run_python_script'
# @mcp.tool(name=f'{run_python_script_str}',
#           enabled=utils.com_utils.get_tool_enable(run_python_script_str),
#           description=f'所属主机：{get_machine_code_simple()}。{prompt_manager.get(run_python_script_str)}')
# def run_python_script(file_path: str) -> dict:
#     f"""
#     运行指定的Python脚本。
#
#     Args:
#         file_path: 要运行的Python脚本路径。
#
#     Returns:
#         包含运行结果信息的字典：
#             - success: 是否运行成功
#             - output: 脚本输出
#             - error: 错误信息（成功时为None）
#     """
#     return python_tool.run_python_script(file_path)


run_python_script_str = 'run_python_script'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{run_python_script_str}',
          enabled=com_utils.get_tool_enable(run_python_script_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(run_python_script_str)}')
def run_python_script(script_content: str, file_name: str):
    save_script_result = python_tool.save_python_script(file_name, script_content)

    if not save_script_result['success']:
        return save_script_result

    file_path = save_script_result['path']
    return python_tool.run_python_script(file_path)


install_package_str = 'install_package'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{install_package_str}',
          enabled=com_utils.get_tool_enable(install_package_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(install_package_str)}')
def install_package(package_name: str) -> dict:
    f"""
    通过pip安装指定的Python包。

    Args:
        package_name: 要安装的包名，可附带版本号，如 "requests" 或 "numpy==1.21.0"

    Returns:
        包含安装结果信息的字典：
            - success: 是否安装成功
            - message: 安装过程的输出或错误信息
    """
    return python_tool.install_package(package_name)



run_python_script_async_str = 'run_python_script_async'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{run_python_script_async_str}',
          enabled=com_utils.get_tool_enable(run_python_script_async_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(run_python_script_async_str)}')
def run_python_script_async(script_content: str, file_name: str):
    save_script_result = python_tool.save_python_script(file_name, script_content)

    if not save_script_result['success']:
        return save_script_result

    file_path = save_script_result['path']
    return python_tool.run_python_script_async(file_path)


get_script_status_str = 'get_script_status'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_script_status_str}',
          enabled=com_utils.get_tool_enable(get_script_status_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_script_status_str)}')
def get_script_status(session_id: str):
    return python_tool.get_script_status(session_id)
