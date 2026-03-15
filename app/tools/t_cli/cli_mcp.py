from config_py.config import settings
from utils import com_utils
from config_py.prompt import prompt_manager
from utils.com_utils import get_mcp_exposed_url

from mcp_service import mcp
from tools.t_cli.cli_tool import cli_tool


run_cli_command_str = 'run_cli_command'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{run_cli_command_str}',
          enabled=com_utils.get_tool_enable(run_cli_command_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(run_cli_command_str)}')
def run_cli_command(command: str, timeout: int = 30, work_dir: str = '') -> dict:
    return cli_tool.run_command(command, timeout=timeout, work_dir=work_dir or None)


list_directory_str = 'list_directory'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{list_directory_str}',
          enabled=com_utils.get_tool_enable(list_directory_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(list_directory_str)}')
def list_directory(path: str = '.') -> dict:
    return cli_tool.list_directory(path)


get_system_info_str = 'get_system_info'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_system_info_str}',
          enabled=com_utils.get_tool_enable(get_system_info_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_system_info_str)}')
def get_system_info() -> dict:
    return cli_tool.get_system_info()


get_disk_usage_str = 'get_disk_usage'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_disk_usage_str}',
          enabled=com_utils.get_tool_enable(get_disk_usage_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_disk_usage_str)}')
def get_disk_usage() -> dict:
    return cli_tool.get_disk_usage()


get_running_processes_str = 'get_running_processes'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_running_processes_str}',
          enabled=com_utils.get_tool_enable(get_running_processes_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_running_processes_str)}')
def get_running_processes(filter_name: str = '') -> dict:
    return cli_tool.get_running_processes(filter_name)


get_network_info_str = 'get_network_info'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_network_info_str}',
          enabled=com_utils.get_tool_enable(get_network_info_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_network_info_str)}')
def get_network_info() -> dict:
    return cli_tool.get_network_info()


find_files_str = 'find_files'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{find_files_str}',
          enabled=com_utils.get_tool_enable(find_files_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(find_files_str)}')
def find_files(search_dir: str = '.', pattern: str = '*') -> dict:
    return cli_tool.find_files(search_dir, pattern)


kill_process_str = 'kill_process'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{kill_process_str}',
          enabled=com_utils.get_tool_enable(kill_process_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(kill_process_str)}')
def kill_process(pid: int) -> dict:
    return cli_tool.kill_process(pid)


get_env_vars_str = 'get_env_vars'
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{get_env_vars_str}',
          enabled=com_utils.get_tool_enable(get_env_vars_str),
          description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(get_env_vars_str)}')
def get_env_vars(filter_prefix: str = '') -> dict:
    return cli_tool.get_env_vars(filter_prefix)
