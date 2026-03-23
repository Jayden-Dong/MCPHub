"""
MCP 中间件
提供工具启用状态检查、描述检查等功能
使用 SQLModel ORM 操作数据库
"""
import time
from typing import Any
from collections.abc import Sequence

from fastmcp.server.middleware import Middleware
from fastmcp.server.middleware import MiddlewareContext, CallNext
from fastmcp.tools.tool import Tool
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError
import mcp.types as mt

from config_py.logger import app_logger, mcp_logger
from config_py.prompt import prompt_manager
from managers.stats_manager import stats_manager
from db.database import engine
from db.models.module import Tool
from db.models.proxy import ProxyTool
from db.models.group import ModuleGroupLink, ProxyGroupLink
from sqlmodel import Session, select

HEADER_NAME = "x-group-id"

def get_tools_for_group(group_id: str):
    # 用户上传了组ID信息，那根据组ID查询该组下有哪些工具，并过滤掉不是该组下的工具
    with Session(engine) as session:
        # 查询该组下所有模块名
        module_links = session.exec(
            select(ModuleGroupLink).where(ModuleGroupLink.group_id == group_id)
        ).all()
        group_module_names = {link.module_name for link in module_links}

        # 查询该组下所有代理服务器ID
        proxy_links = session.exec(
            select(ProxyGroupLink).where(ProxyGroupLink.group_id == group_id)
        ).all()
        group_server_ids = {link.server_id for link in proxy_links}

        # 查询这些模块下的所有工具名
        if group_module_names:
            db_tools = session.exec(
                select(Tool).where(Tool.module_name.in_(group_module_names))
            ).all()
            group_tool_names = {t.tool_name for t in db_tools}
        else:
            group_tool_names = set()

        # 查询这些代理服务器下的所有代理工具名
        if group_server_ids:
            proxy_tools_in_group = session.exec(
                select(ProxyTool).where(ProxyTool.server_id.in_(group_server_ids))
            ).all()
            group_proxy_tool_names = {pt.raw_name for pt in proxy_tools_in_group}
        else:
            group_proxy_tool_names = set()

    allowed_tool_names = group_tool_names | group_proxy_tool_names
    return allowed_tool_names


class RequestMCPMiddleware(Middleware):
    def __init__(self, module_manager=None):
        self.module_manager = module_manager

    async def on_request(
        self,
        context: MiddlewareContext[mt.Request[Any, Any]],
        call_next: CallNext[mt.Request[Any, Any], Any],
    ) -> Any:

        group_id = (get_http_headers() or {}).get(HEADER_NAME, None)

        start_time = time.time()
        tool_name = None

        if 'tools/call' in context.method:
            tool_name = context.message.name
            msg = f'{context.method} <==== tool_name: {tool_name}, tool_arguments: {context.message.arguments}'
            mcp_logger.info(msg)

            allowed_tool_names = get_tools_for_group(group_id)
            if group_id and tool_name not in allowed_tool_names:
                raise ToolError(f"工具 {tool_name} 不在组 {group_id} 下，不具备调用权限.")

            # 检查工具是否处于启用状态
            with Session(engine) as session:
                db_tool = session.exec(select(Tool).where(Tool.tool_name == tool_name)).first()
                if db_tool is not None:
                    if not bool(db_tool.enabled):
                        raise ToolError(f"工具 {tool_name} 当前处于未启用状态，无法调用.")
                else:
                    proxy_tool = session.exec(select(ProxyTool).where(ProxyTool.raw_name == tool_name)).first()
                    if proxy_tool is not None and not bool(proxy_tool.enabled):
                        raise ToolError(f"工具 {tool_name} 当前处于未启用状态，无法调用.")

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

    async def on_list_tools(
            self,
            context: MiddlewareContext[mt.ListToolsRequest],
            call_next: CallNext[mt.ListToolsRequest, Sequence[Tool]]) -> Sequence[Tool]:
        """
        拦截工具列表获取请求，拦截不启用的工具
        """
        tools = await call_next(context)

        group_id = (get_http_headers() or {}).get(HEADER_NAME, None)
        allowed_tool_names = get_tools_for_group(group_id)

        if group_id:
            tools = [tool for tool in tools if tool.name in allowed_tool_names]

        enable_tools = list()

        # 预加载所有工具的启用状态
        tools_enabled_map = {}  # tool_name -> enabled
        proxy_tools_map = {}    # raw_name -> {enabled, custom_desc}

        with Session(engine) as session:
            # 查询 tools 表
            db_tools = session.exec(select(Tool)).all()
            for t in db_tools:
                tools_enabled_map[t.tool_name] = bool(t.enabled)

            # 查询 proxy_tools 表
            proxy_tools = session.exec(select(ProxyTool)).all()
            for pt in proxy_tools:
                proxy_tools_map[pt.raw_name] = {
                    'enabled': bool(pt.enabled),
                    'custom_desc': pt.custom_desc or ''
                }

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