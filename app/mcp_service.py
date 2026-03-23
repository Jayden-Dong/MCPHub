import threading

from fastmcp import FastMCP
from config_py.logger import app_logger, mcp_logger
from my_mcp_middleware import ToolEnabledCheckerMiddleware, ToolDescriptionCheckerMiddleware, RequestMCPMiddleware

from config_py.config import settings
from managers.module_manager import ModuleManager
from managers.proxy_manager import ProxyManager
from managers.group_manager import GroupManager

mcp = FastMCP(name=f"{settings.MCP_SERVICE_NAME}")

# 全局分组管理器实例
group_manager = GroupManager()

# 全局模块管理器实例
module_manager = ModuleManager(mcp, group_manager)

# 全局代理管理器实例
proxy_manager = ProxyManager(mcp, module_manager, group_manager)


# ----------- MCP 服务主线程启动（仅全局一个）--------------
def start_mcp_server(host: str, port: int, path: str) -> None:
    """在独立线程中启动 MCP streamable-http 服务。"""

    def _run():
        try:
            # 使用ModuleManager从配置加载所有模块
            module_manager.load_from_config()

            # 从数据库恢复代理服务器
            proxy_manager.load_from_db()

            # 增加工具启用检查中间件
            mcp.add_middleware(ToolEnabledCheckerMiddleware())

            # 增加工具描述变化检查中间件
            mcp.add_middleware(ToolDescriptionCheckerMiddleware())

            # 增加请求的日志
            mcp.add_middleware(RequestMCPMiddleware(module_manager))

            mcp.run(transport="streamable-http", host=host, port=port, path=path, stateless_http=True)
        except Exception as e:
            app_logger.exception("MCP 服务启动失败: %s", e)

    thread = threading.Thread(target=_run, name="mcp-http", daemon=True)
    thread.start()


