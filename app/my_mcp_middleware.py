import sqlite3
import time
from pathlib import Path

from config_py.logger import app_logger, mcp_logger
from config_py.config import settings

from typing import Any
from fastmcp.server.middleware import Middleware
from fastmcp.server.middleware import MiddlewareContext, CallNext
from collections.abc import Sequence
from fastmcp.tools.tool import Tool
import mcp.types as mt

from config_py.prompt import prompt_manager
from managers.stats_manager import stats_manager

class RequestMCPMiddleware(Middleware):
    def __init__(self, module_manager=None):
        self.module_manager = module_manager

    async def on_request(
        self,
        context: MiddlewareContext[mt.Request[Any, Any]],
        call_next: CallNext[mt.Request[Any, Any], Any],
    ) -> Any:

        start_time = time.time()
        tool_name = None

        if 'tools/call' in context.method:
            tool_name = context.message.name
            msg = f'{context.method} <==== tool_name: {tool_name}, tool_arguments: {context.message.arguments}'
            mcp_logger.info(msg)

        requests = await call_next(context)

        if 'tools/call' in context.method:
            duration_ms = (time.time() - start_time) * 1000
            success = not hasattr(requests, 'isError') or not requests.isError

            msg = f'{context.method} ====> tool_name: {tool_name}, tool_result: {requests.structured_content}'
            mcp_logger.info(msg)

            # 记录统计数据
            module_name = self.module_manager._tool_to_module.get(tool_name, 'unknown')
            try:
                stats_manager.record_call(tool_name, module_name, success, duration_ms)
            except Exception as e:
                app_logger.warning(f"记录统计数据失败: {e}")

        return requests


class ToolDescriptionCheckerMiddleware(Middleware):
    """
    工具描述检查中间件
    """

    async def on_list_tools(
            self,
            context: MiddlewareContext[mt.ListToolsRequest],
            call_next: CallNext[mt.ListToolsRequest, Sequence[Tool]]) -> Sequence[Tool]:
        """
        拦截工具列表获取请求，检查工具描述是否被修改
        """
        tools = await call_next(context)

        if not prompt_manager.prompts_is_changed():
            return tools

        mcp_logger.info("发现工具描述变化，更新工具描述")
        for tool in tools:
            tool_name = tool.name

            new_description = prompt_manager.get(tool_name)
            if new_description:
                tool.description = new_description

        return tools


class ToolEnabledCheckerMiddleware(Middleware):
    """
    工具启用状态检查
    """

    DB_PATH = Path(settings.DB_PATH)

    def _get_conn(self):
        """获取数据库连接"""
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    async def on_list_tools(
            self,
            context: MiddlewareContext[mt.ListToolsRequest],
            call_next: CallNext[mt.ListToolsRequest, Sequence[Tool]]) -> Sequence[Tool]:
        """
        拦截工具列表获取请求，拦截不启用的工具
        """
        tools = await call_next(context)

        enable_tools = list()

        # 预加载所有工具的启用状态
        tools_enabled_map = {}  # tool_name -> enabled
        proxy_tools_map = {}    # raw_name -> {enabled, custom_desc}

        conn = self._get_conn()
        try:
            # 查询 tools 表
            rows = conn.execute("SELECT tool_name, enabled FROM tools").fetchall()
            for row in rows:
                tools_enabled_map[row['tool_name']] = bool(row['enabled'])

            # 查询 proxy_tools 表
            rows = conn.execute("SELECT raw_name, enabled, custom_desc FROM proxy_tools").fetchall()
            for row in rows:
                proxy_tools_map[row['raw_name']] = {
                    'enabled': bool(row['enabled']),
                    'custom_desc': row['custom_desc'] or ''
                }
        finally:
            conn.close()

        for tool in tools:
            tool_name = tool.name

            # 1.通过工具tool_name查表tools，如果存在，且enable==1，则将此工具加入到enable_tools中，否则不加入
            if tool_name in tools_enabled_map:
                if tools_enabled_map[tool_name]:
                    enable_tools.append(tool)
                continue

            # 2.通过工具tool_name查表proxy_tools，如果存在，且enable==1，则将此工具加入到enable_tools中，否则不加入
            if tool_name in proxy_tools_map:
                proxy_info = proxy_tools_map[tool_name]
                if proxy_info['enabled']:
                    # 2.1.如果从表proxy_tools中查到此工具的custom_desc不为空，则将tool.description设置为custom_desc
                    if proxy_info['custom_desc']:
                        tool.description = proxy_info['custom_desc']
                    enable_tools.append(tool)
                continue

            # 工具不在任何表中，默认启用
            enable_tools.append(tool)

        return enable_tools
