"""
第三方 MCP Server 代理管理器
支持接入 HTTP Streamable 和 HTTP SSE 类型的第三方 MCP 服务器，
将远端工具透明代理到本地 FastMCP 实例。
使用 SQLModel ORM 操作数据库
"""
import asyncio
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from sqlmodel import Session, select

from config_py.logger import app_logger
from config_py.config import settings
from fastmcp.server.proxy import FastMCPProxy, ProxyClient
from db.database import engine, init_db
from db.models.proxy import ProxyServer, ProxyTool


class ProxyServerInfo:
    """代理服务器内存信息"""

    def __init__(self, id, name, url, transport, enabled, description, headers,
                 created_time, last_sync, timeout=60):
        self.id = int(id)
        self.name = name
        self.url = url
        self.transport = transport  # 'streamable-http' | 'sse'
        self.enabled = bool(enabled)
        self.description = description or ""
        self.headers: dict = json.loads(headers) if isinstance(headers, str) else (headers or {})
        self.created_time = created_time or ""
        self.last_sync = last_sync or ""
        self.timeout = int(timeout) if timeout else 60


class ProxyManager:
    """第三方 MCP Server 代理管理器"""

    def __init__(self, mcp_instance, module_manager, group_manager=None):
        self.mcp = mcp_instance
        self.module_manager = module_manager
        self._group_manager = group_manager

        # server_id -> ProxyServerInfo
        self._servers: dict[int, ProxyServerInfo] = {}
        # tool_name (generated from server_name + raw_name) -> server_id
        self._proxy_tool_to_server: dict[str, int] = {}
        # name -> FastMCPProxy（用于 FastMCPProxy 挂载方式）
        self._mounted_proxies: dict[str, FastMCPProxy] = {}

        self._init_db()

    # ================================================================
    #  数据库层
    # ================================================================

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return Session(engine)

    def _init_db(self):
        """初始化数据库"""
        init_db()

    # ================================================================
    #  内部辅助
    # ================================================================

    def _make_local_name(self, server_name: str, raw_name: str) -> str:
        """生成本地工具名"""
        safe = server_name.replace('-', '_').replace(' ', '_').replace('.', '_')
        return f"{safe}_{raw_name}"

    def _register_proxy_tool_in_fastmcp(self, server: ProxyServerInfo,
                                         raw_name: str, local_name: str,
                                         description: str, input_schema: dict,
                                         tool_enabled: bool = True):
        """在 FastMCP 中注册一个代理工具（同步）"""
        server_url = server.url
        transport = server.transport
        headers = server.headers.copy()

        timeout = server.timeout

        # 用工厂函数避免 closure 变量捕获问题
        def _make_fn(url, tp, rn, hdrs, tmt):
            async def proxy_fn(**kwargs):
                return await self._call_remote_tool(url, tp, rn, kwargs, hdrs, tmt)
            proxy_fn.__name__ = local_name
            proxy_fn.__doc__ = description
            return proxy_fn

        proxy_fn = _make_fn(server_url, transport, raw_name, headers, timeout)

        try:
            self.mcp.tool(name=local_name, description=description, enabled=tool_enabled)(proxy_fn)

            # 覆盖 FastMCP 自动推断的空 schema 为远端真实 schema
            if input_schema:
                tool_obj = self.mcp._tool_manager._tools.get(local_name)
                if tool_obj:
                    try:
                        tool_obj.parameters = input_schema
                    except Exception as e:
                        app_logger.debug(f"设置工具 {local_name} 参数 schema 失败: {e}")

            # 注册到 _tool_to_module（用于统计归属）
            module_key = f"proxy.{server.name}"
            self.module_manager._tool_to_module[local_name] = module_key
            self._proxy_tool_to_server[local_name] = server.id

            app_logger.info(f"代理工具注册成功: {local_name} (enabled={tool_enabled})")
        except Exception as e:
            app_logger.warning(f"注册代理工具失败 {local_name}: {e}", exc_info=True)

    def _unregister_server_tools(self, server_id: int):
        """从 FastMCP 中注销某服务器的全部代理工具"""
        to_remove = [k for k, v in self._proxy_tool_to_server.items() if v == server_id]
        for local_name in to_remove:
            try:
                self.mcp.remove_tool(local_name)
            except Exception as e:
                app_logger.debug(f"移除代理工具 {local_name}: {e}")
            self.module_manager._tool_to_module.pop(local_name, None)
            self._proxy_tool_to_server.pop(local_name, None)

    async def _call_remote_tool(self, url: str, transport: str,
                                 tool_name: str, arguments: dict,
                                 headers: dict, timeout: int = 60) -> Any:
        """调用远端 MCP 工具，返回 content 列表"""
        from mcp import ClientSession
        try:
            async def _do_call():
                if transport == 'streamable-http':
                    from mcp.client.streamable_http import streamablehttp_client
                    async with streamablehttp_client(url, headers=headers) as (read, write, _):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            return await session.call_tool(tool_name, arguments)
                else:  # sse
                    from mcp.client.sse import sse_client
                    async with sse_client(url, headers=headers) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            return await session.call_tool(tool_name, arguments)

            result = await asyncio.wait_for(_do_call(), timeout=timeout)

            if result.isError:
                error_text = " ".join(
                    c.text for c in result.content if hasattr(c, 'text')
                ) or "远端工具返回错误"
                raise RuntimeError(error_text)

            # 返回 content 列表（FastMCP 能处理 mcp.types Content 列表）
            return result.content if result.content else "ok"

        except Exception as e:
            app_logger.error(f"调用远端工具失败 {url}/{tool_name}: {e}", exc_info=True)
            raise

    async def _discover_tools(self, url: str, transport: str, headers: dict,
                               timeout: int = 60) -> list[dict]:
        """连接远端并获取工具列表"""
        from mcp import ClientSession

        async def _do_discover():
            if transport == 'streamable-http':
                from mcp.client.streamable_http import streamablehttp_client
                async with streamablehttp_client(url, headers=headers) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return result.tools
            else:
                from mcp.client.sse import sse_client
                async with sse_client(url, headers=headers) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return result.tools

        tools = await asyncio.wait_for(_do_discover(), timeout=timeout)

        out = []
        for t in tools:
            schema = t.inputSchema
            # 深度解析 schema，确保获取完整结构
            schema = self._deep_parse_schema(schema)

            out.append({
                'name': t.name,
                'description': t.description or '',
                'inputSchema': schema,
            })

            # 调试日志：打印工具参数信息
            if schema.get('properties'):
                props_info = []
                for pname, pval in schema.get('properties', {}).items():
                    pdesc = pval.get('description', '(无描述)')
                    ptype = pval.get('type', 'any')
                    props_info.append(f"{pname}({ptype}): {pdesc}")
                app_logger.debug(f"工具 {t.name} 参数: {', '.join(props_info)}")

        return out

    def _deep_parse_schema(self, schema) -> dict:
        """递归解析 schema 对象，确保转换为纯 dict"""
        if schema is None:
            return {}

        # Pydantic 模型
        if hasattr(schema, 'model_dump'):
            schema = schema.model_dump()

        # 不是字典，尝试转换
        if not isinstance(schema, dict):
            try:
                schema = dict(schema)
            except Exception as e:
                app_logger.debug(f"schema 转换为 dict 失败: {e}")
                return {}

        # 递归处理嵌套结构
        result = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                result[key] = self._deep_parse_schema(value)
            elif isinstance(value, list):
                result[key] = [
                    self._deep_parse_schema(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif hasattr(value, 'model_dump'):
                result[key] = value.model_dump()
            else:
                result[key] = value

        return result

    # ================================================================
    #  启动恢复
    # ================================================================

    def load_from_db(self):
        """服务启动时从数据库恢复已启用的代理服务器"""
        with self._get_session() as session:
            servers = session.exec(
                select(ProxyServer).where(ProxyServer.enabled == 1)
            ).all()
            for server in servers:
                server_info = ProxyServerInfo(
                    id=server.id,
                    name=server.name,
                    url=server.url,
                    transport=server.transport,
                    enabled=server.enabled,
                    description=server.description,
                    headers=server.headers,
                    created_time=server.created_time,
                    last_sync=server.last_sync,
                    timeout=server.timeout
                )
                # 调用 enable_server 完成完整的启用流程：
                # 注册工具、挂载 FastMCPProxy、添加中间件
                self.enable_server(server.id)

    # ================================================================
    #  服务器 CRUD
    # ================================================================

    def get_all_servers(self) -> list[dict]:
        with self._get_session() as session:
            servers = session.exec(select(ProxyServer).order_by(ProxyServer.id)).all()
            result = []
            for server in servers:
                s = {
                    "id": server.id,
                    "name": server.name,
                    "url": server.url,
                    "transport": server.transport,
                    "enabled": server.enabled,
                    "description": server.description,
                    "headers": json.loads(server.headers) if server.headers else {},
                    "created_time": server.created_time,
                    "last_sync": server.last_sync,
                    "timeout": server.timeout
                }
                # 获取工具统计
                tools = session.exec(
                    select(ProxyTool).where(ProxyTool.server_id == server.id)
                ).all()
                total = len(tools)
                enabled_count = sum(1 for t in tools if t.enabled)
                s['tool_count'] = total
                s['enabled_tool_count'] = enabled_count
                result.append(s)
            return result

    def get_server_detail(self, server_id: int) -> Optional[dict]:
        with self._get_session() as session:
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if not server:
                return None

            s = {
                "id": server.id,
                "name": server.name,
                "url": server.url,
                "transport": server.transport,
                "enabled": server.enabled,
                "description": server.description,
                "headers": json.loads(server.headers) if server.headers else {},
                "created_time": server.created_time,
                "last_sync": server.last_sync,
                "timeout": server.timeout
            }

            tools = session.exec(
                select(ProxyTool).where(ProxyTool.server_id == server_id).order_by(ProxyTool.raw_name)
            ).all()
            s['tools'] = []
            for t in tools:
                s['tools'].append({
                    "id": t.id,
                    "server_id": t.server_id,
                    "raw_name": t.raw_name,
                    "description": t.description,
                    "custom_desc": t.custom_desc,
                    "input_schema": json.loads(t.input_schema) if t.input_schema else {},
                    "enabled": t.enabled
                })
            return s

    def add_server(self, name: str, url: str, transport: str = 'streamable-http',
                   description: str = '', headers: dict = None, timeout: int = 60) -> dict:
        with self._get_session() as session:
            try:
                created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                server = ProxyServer(
                    name=name,
                    url=url,
                    transport=transport,
                    enabled=0,
                    description=description,
                    headers=json.dumps(headers or {}, ensure_ascii=False),
                    created_time=created_time,
                    timeout=timeout
                )
                session.add(server)
                session.commit()
                session.refresh(server)

                # 自动加入默认分组
                if self._group_manager:
                    try:
                        self._group_manager.add_proxy_to_default_group(server.id)
                    except Exception as e:
                        app_logger.warning(f"代理服务器 {name} 加入默认分组失败: {e}")

                return {"success": True, "message": f"服务器 {name} 添加成功", "server_id": server.id}
            except Exception as e:
                return {"success": False, "message": f"添加失败: {str(e)}"}

    def update_server(self, server_id: int, name: str = None, url: str = None,
                      transport: str = None, description: str = None,
                      headers: dict = None, timeout: int = None) -> dict:
        with self._get_session() as session:
            try:
                server = session.exec(
                    select(ProxyServer).where(ProxyServer.id == server_id)
                ).first()
                if not server:
                    return {"success": False, "message": "服务器不存在"}

                if name is not None:
                    server.name = name
                if url is not None:
                    server.url = url
                if transport is not None:
                    server.transport = transport
                if description is not None:
                    server.description = description
                if headers is not None:
                    server.headers = json.dumps(headers, ensure_ascii=False)
                if timeout is not None:
                    server.timeout = timeout

                session.add(server)
                session.commit()

                # 同步更新内存
                if server_id in self._servers:
                    s = self._servers[server_id]
                    s.name = server.name
                    s.url = server.url
                    s.transport = server.transport
                    s.description = server.description
                    s.headers = json.loads(server.headers) if server.headers else {}
                    s.timeout = server.timeout

                return {"success": True, "message": "服务器配置已更新"}
            except Exception as e:
                return {"success": False, "message": f"更新失败: {str(e)}"}

    def delete_server(self, server_id: int) -> dict:
        with self._get_session() as session:
            try:
                server = session.exec(
                    select(ProxyServer).where(ProxyServer.id == server_id)
                ).first()
                if not server:
                    return {"success": False, "message": "服务器不存在"}

                self._unregister_server_tools(server_id)

                # 清理分组关联
                from db.models.group import ProxyGroupLink
                links = session.exec(
                    select(ProxyGroupLink).where(ProxyGroupLink.server_id == server_id)
                ).all()
                for link in links:
                    session.delete(link)

                session.delete(server)
                session.commit()
                self._servers.pop(server_id, None)
                return {"success": True, "message": "服务器已删除"}
            except Exception as e:
                return {"success": False, "message": f"删除失败: {str(e)}"}

    # ================================================================
    #  同步工具列表（异步）
    # ================================================================

    async def sync_server(self, server_id: int) -> dict:
        """连接远端服务器并同步工具列表到数据库（不自动启用）"""
        with self._get_session() as session:
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if not server:
                return {"success": False, "message": "服务器不存在"}
            url = server.url
            transport = server.transport
            headers = json.loads(server.headers) if server.headers else {}
            timeout = server.timeout or 60

        try:
            tools = await self._discover_tools(url, transport, headers, timeout)
        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}

        with self._get_session() as session:
            sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 获取已存在的工具 raw_name
            existing_tools = session.exec(
                select(ProxyTool).where(ProxyTool.server_id == server_id)
            ).all()
            existing_raw = {t.raw_name for t in existing_tools}

            new_count = 0
            for tool in tools:
                raw_name = tool['name']
                description = tool['description']
                input_schema = json.dumps(tool['inputSchema'], ensure_ascii=False)

                if raw_name not in existing_raw:
                    new_tool = ProxyTool(
                        server_id=server_id,
                        raw_name=raw_name,
                        description=description,
                        input_schema=input_schema,
                        enabled=1
                    )
                    session.add(new_tool)
                    new_count += 1
                else:
                    # 仅更新描述和 schema，保留用户设置的 enabled 和 custom_desc
                    existing_tool = next(t for t in existing_tools if t.raw_name == raw_name)
                    existing_tool.description = description
                    existing_tool.input_schema = input_schema
                    session.add(existing_tool)

            # 更新同步时间
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if server:
                server.last_sync = sync_time
                session.add(server)

            session.commit()

        return {
            "success": True,
            "message": f"同步成功，共 {len(tools)} 个工具（新增 {new_count} 个）",
            "tool_count": len(tools),
            "new_count": new_count,
        }

    async def force_sync_server(self, server_id: int) -> dict:
        """覆盖同步：删除该服务器所有已有工具，重新从远端拉取并写入（不保留用户配置）"""
        with self._get_session() as session:
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if not server:
                return {"success": False, "message": "服务器不存在"}
            url = server.url
            transport = server.transport
            headers = json.loads(server.headers) if server.headers else {}
            timeout = server.timeout or 60

        try:
            tools = await self._discover_tools(url, transport, headers, timeout)
        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}

        with self._get_session() as session:
            # 删除该服务器所有已有工具
            existing_tools = session.exec(
                select(ProxyTool).where(ProxyTool.server_id == server_id)
            ).all()
            for t in existing_tools:
                session.delete(t)

            sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for tool in tools:
                raw_name = tool['name']
                description = tool['description']
                input_schema = json.dumps(tool['inputSchema'], ensure_ascii=False)
                new_tool = ProxyTool(
                    server_id=server_id,
                    raw_name=raw_name,
                    description=description,
                    input_schema=input_schema,
                    enabled=1
                )
                session.add(new_tool)

            # 更新同步时间
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if server:
                server.last_sync = sync_time
                session.add(server)

            session.commit()

        return {
            "success": True,
            "message": f"覆盖同步成功，共 {len(tools)} 个工具",
            "tool_count": len(tools),
        }

    # ================================================================
    #  服务器启用 / 禁用
    # ================================================================

    def enable_server(self, server_id: int) -> dict:
        with self._get_session() as session:
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if not server:
                return {"success": False, "message": "服务器不存在"}

            server_info = ProxyServerInfo(
                id=server.id,
                name=server.name,
                url=server.url,
                transport=server.transport,
                enabled=True,
                description=server.description,
                headers=server.headers,
                created_time=server.created_time,
                last_sync=server.last_sync,
                timeout=server.timeout
            )
            server_info.enabled = True
            self._servers[server_id] = server_info

            tools = session.exec(
                select(ProxyTool).where(ProxyTool.server_id == server_id)
            ).all()
            count = 0
            for tool in tools:
                schema = json.loads(tool.input_schema) if tool.input_schema else {}
                desc = tool.custom_desc or tool.description
                raw_name = tool.raw_name
                local_name = self._make_local_name(server.name, raw_name)
                # 若已注册（可能已有），先移除再重注册
                if local_name in self._proxy_tool_to_server:
                    try:
                        self.mcp.remove_tool(local_name)
                    except Exception as e:
                        app_logger.debug(f"移除已注册工具 {local_name} 失败: {e}")
                    self.module_manager._tool_to_module.pop(local_name, None)
                    self._proxy_tool_to_server.pop(local_name, None)
                self._register_proxy_tool_in_fastmcp(
                    server_info, raw_name, local_name, desc, schema, bool(tool.enabled)
                )
                count += 1

            # 实际挂载 FastMCPProxy
            name = server.name
            if name not in self._mounted_proxies:
                # 延迟导入避免循环依赖
                from my_mcp_middleware import ToolEnabledCheckerMiddleware, ToolDescriptionCheckerMiddleware, RequestMCPMiddleware

                def make_factory(target_url):
                    return lambda: ProxyClient(target_url)
                proxy_server = FastMCPProxy(
                    client_factory=make_factory(server_info.url),
                )

                # 增加工具启用检查中间件
                self.mcp.add_middleware(ToolEnabledCheckerMiddleware())

                # 增加工具描述变化检查中间件
                self.mcp.add_middleware(ToolDescriptionCheckerMiddleware())

                # 增加请求的日志
                self.mcp.add_middleware(RequestMCPMiddleware(self.module_manager))

                self.mcp.mount(proxy_server)
                self._mounted_proxies[name] = proxy_server

            server.enabled = 1
            session.add(server)
            session.commit()
            return {"success": True, "message": f"服务器已启用，注册了 {count} 个工具"}

    def disable_server(self, server_id: int) -> dict:
        with self._get_session() as session:
            self._unregister_server_tools(server_id)

            # 实际卸载 FastMCPProxy
            server = self._servers.get(server_id)
            if server:
                name = server.name
                if name in self._mounted_proxies:
                    proxy_server = self._mounted_proxies[name]
                    for ms in list(self.mcp._mounted_servers):
                        if ms.server is proxy_server:
                            self.mcp._mounted_servers.remove(ms)
                            break
                    del self._mounted_proxies[name]

            db_server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if db_server:
                db_server.enabled = 0
                session.add(db_server)
                session.commit()

            self._servers.pop(server_id, None)
            return {"success": True, "message": "服务器已禁用"}

    # ================================================================
    #  工具启用 / 禁用 / 描述更新
    # ================================================================

    def enable_tool(self, tool_id: int) -> dict:
        with self._get_session() as session:
            tool = session.exec(
                select(ProxyTool).where(ProxyTool.id == tool_id)
            ).first()
            if not tool:
                return {"success": False, "message": "工具不存在"}

            # 获取服务器状态
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == tool.server_id)
            ).first()

            tool.enabled = 1
            session.add(tool)
            session.commit()

            raw_name = tool.raw_name
            server_info = self._servers.get(tool.server_id)
            local_name = self._make_local_name(server_info.name, raw_name) if server_info else None

            if server and server.enabled and local_name:
                tool_obj = self.mcp._tool_manager._tools.get(local_name)
                if tool_obj:
                    tool_obj.enabled = True
                elif server_info:
                    # 工具不在 FastMCP 中，重新注册
                    schema = json.loads(tool.input_schema) if tool.input_schema else {}
                    desc = tool.custom_desc or tool.description
                    self._register_proxy_tool_in_fastmcp(
                        server_info, raw_name, local_name, desc, schema, True
                    )
            return {"success": True, "message": "工具已启用"}

    def disable_tool(self, tool_id: int) -> dict:
        with self._get_session() as session:
            tool = session.exec(
                select(ProxyTool).where(ProxyTool.id == tool_id)
            ).first()
            if not tool:
                return {"success": False, "message": "工具不存在"}

            raw_name = tool.raw_name
            server_info = self._servers.get(tool.server_id)
            local_name = self._make_local_name(server_info.name, raw_name) if server_info else None
            if local_name:
                tool_obj = self.mcp._tool_manager._tools.get(local_name)
                if tool_obj:
                    tool_obj.enabled = False

            tool.enabled = 0
            session.add(tool)
            session.commit()
            return {"success": True, "message": "工具已禁用"}

    def update_tool_description(self, tool_id: int, description: str) -> dict:
        with self._get_session() as session:
            tool = session.exec(
                select(ProxyTool).where(ProxyTool.id == tool_id)
            ).first()
            if not tool:
                return {"success": False, "message": "工具不存在"}

            tool.custom_desc = description
            session.add(tool)
            session.commit()

            # 同步更新 FastMCP 工具描述
            raw_name = tool.raw_name
            server_info = self._servers.get(tool.server_id)
            local_name = self._make_local_name(server_info.name, raw_name) if server_info else None
            if local_name:
                tool_obj = self.mcp._tool_manager._tools.get(local_name)
                if tool_obj:
                    tool_obj.description = description

            return {"success": True, "message": "工具描述已更新"}