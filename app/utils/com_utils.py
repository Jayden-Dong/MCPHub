from config_py.config import settings
from config_py.logger import app_logger

def get_tool_enable(tool_name: str):
    """
    获取此工具是否启用
    :param tool_name:
    :return:
    """
    for mcp_module in settings.MCP_ENABLE_MODULE:
        tool_names = mcp_module.get("disable_tool", [])

        if tool_name in tool_names:
            return False

    return True

def get_mcp_exposed_url() -> str:
    url = f'{settings.MCP_HOST}:{settings.MCP_PORT}{settings.MCP_PATH}'

    return url


def get_module_config(module_name_postfix: str):
    mcp_modules = settings.MCP_ENABLE_MODULE

    config = {}
    for module in mcp_modules:
        module_name = module.get("module_name", "")
        if not module_name.endswith(module_name_postfix):
            continue

        config = module.get("config", {})
        break

    return config


def get_external_module_config(module_name: str) -> dict:
    """
    获取外部插件的运行时配置（从模块管理器中读取）。
    外部插件在 init_config / update_config 之外也可通过此函数主动拉取配置。

    Args:
        module_name: 外部模块的完整名称，如 "t_my_tool.my_tool_mcp"，
                     或父包名称，如 "t_my_tool"

    Returns:
        配置字典，未找到时返回 {}
    """
    try:
        from mcp_service import module_manager
        # 精确匹配
        info = module_manager._modules.get(module_name)
        if info:
            return info.config or {}
        # 前缀匹配（传入父包名时）
        for name, info in module_manager._modules.items():
            if name.startswith(module_name + '.') or name == module_name:
                return info.config or {}
    except Exception as e:
        app_logger.debug(f"获取外部模块配置失败 (module_name={module_name}): {e}")
    return {}