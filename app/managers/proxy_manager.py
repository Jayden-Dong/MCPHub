"""
第三方 MCP Server 代理管理器
支持接入 HTTP Streamable 和 HTTP SSE 类型的第三方 MCP 服务器，
将远端工具透明代理到本地 FastMCP 实例。
"""
import asyncio
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from config_py.logger import app_logger
from config_py.config import settings
from fastmcp.server.proxy import FastMCPProxy, ProxyClient



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

    DB_PATH = Path(settings.DB_PATH)

    def __init__(self, mcp_instance, module_manager):
        self.mcp = mcp_instance
        self.module_manager = module_manager

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

    def _get_conn(self) -> sqlite3.Connection:
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS proxy_servers (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL UNIQUE,
                    url           TEXT NOT NULL,
                    transport     TEXT DEFAULT 'streamable-http',
                    enabled       INTEGER DEFAULT 0,
                    description   TEXT DEFAULT '',
                    headers       TEXT DEFAULT '{}',
                    created_time  TEXT DEFAULT '',
                    last_sync     TEXT DEFAULT '',
                    timeout       INTEGER DEFAULT 60
                );

                CREATE TABLE IF NOT EXISTS proxy_tools (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id    INTEGER NOT NULL,
                    raw_name     TEXT NOT NULL,
                    description  TEXT DEFAULT '',
                    custom_desc  TEXT DEFAULT '',
                    input_schema TEXT DEFAULT '{}',
                    enabled      INTEGER DEFAULT 1,
                    FOREIGN KEY (server_id) REFERENCES proxy_servers(id) ON DELETE CASCADE,
                    UNIQUE(server_id, raw_name)
                );
            """)
            conn.commit()

            # 兼容旧数据库：若 timeout 列不存在则补加
            try:
                conn.execute("ALTER TABLE proxy_servers ADD COLUMN timeout INTEGER DEFAULT 60")
                conn.commit()
            except Exception as e:
                # 列已存在，忽略
                app_logger.debug(f"添加 timeout 列失败（可能已存在）: {e}")
        finally:
            conn.close()

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
        conn = self._get_conn()
        try:
            servers = conn.execute(
                "SELECT * FROM proxy_servers WHERE enabled = 1"
            ).fetchall()
            for row in servers:
                server = ProxyServerInfo(**dict(row))
                # 调用 enable_server 完成完整的启用流程：
                # 注册工具、挂载 FastMCPProxy、添加中间件
                self.enable_server(server.id)
        finally:
            conn.close()

    # ================================================================
    #  服务器 CRUD
    # ================================================================

    def get_all_servers(self) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM proxy_servers ORDER BY id").fetchall()
            result = []
            for row in rows:
                s = dict(row)
                s['headers'] = json.loads(s['headers']) if s['headers'] else {}
                counts = conn.execute(
                    "SELECT COUNT(*) as total, SUM(enabled) as ena "
                    "FROM proxy_tools WHERE server_id = ?",
                    (s['id'],)
                ).fetchone()
                s['tool_count'] = counts['total'] or 0
                s['enabled_tool_count'] = counts['ena'] or 0
                result.append(s)
            return result
        finally:
            conn.close()

    def get_server_detail(self, server_id: int) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_servers WHERE id = ?", (server_id,)
            ).fetchone()
            if not row:
                return None
            s = dict(row)
            s['headers'] = json.loads(s['headers']) if s['headers'] else {}

            tools = conn.execute(
                "SELECT * FROM proxy_tools WHERE server_id = ? ORDER BY raw_name",
                (server_id,)
            ).fetchall()
            s['tools'] = []
            for t in tools:
                td = dict(t)
                td['input_schema'] = json.loads(td['input_schema']) if td['input_schema'] else {}
                s['tools'].append(td)
            return s
        finally:
            conn.close()

    def add_server(self, name: str, url: str, transport: str = 'streamable-http',
                   description: str = '', headers: dict = None, timeout: int = 60) -> dict:
        conn = self._get_conn()
        try:
            created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT INTO proxy_servers (name, url, transport, enabled, description, headers, created_time, timeout)
                VALUES (?, ?, ?, 0, ?, ?, ?, ?)
            """, (name, url, transport, description,
                  json.dumps(headers or {}, ensure_ascii=False), created_time, timeout))
            conn.commit()
            server_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return {"success": True, "message": f"服务器 {name} 添加成功", "server_id": server_id}
        except Exception as e:
            return {"success": False, "message": f"添加失败: {str(e)}"}
        finally:
            conn.close()

    def update_server(self, server_id: int, name: str = None, url: str = None,
                      transport: str = None, description: str = None,
                      headers: dict = None, timeout: int = None) -> dict:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_servers WHERE id = ?", (server_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "服务器不存在"}

            new_name = name if name is not None else row['name']
            new_url = url if url is not None else row['url']
            new_transport = transport if transport is not None else row['transport']
            new_desc = description if description is not None else row['description']
            new_headers = (json.dumps(headers, ensure_ascii=False)
                           if headers is not None else row['headers'])
            new_timeout = timeout if timeout is not None else (row['timeout'] or 60)

            conn.execute("""
                UPDATE proxy_servers
                SET name=?, url=?, transport=?, description=?, headers=?, timeout=?
                WHERE id=?
            """, (new_name, new_url, new_transport, new_desc, new_headers, new_timeout, server_id))
            conn.commit()

            # 同步更新内存
            if server_id in self._servers:
                s = self._servers[server_id]
                s.name = new_name
                s.url = new_url
                s.transport = new_transport
                s.description = new_desc
                s.headers = json.loads(new_headers) if isinstance(new_headers, str) else (new_headers or {})
                s.timeout = new_timeout

            return {"success": True, "message": "服务器配置已更新"}
        except Exception as e:
            return {"success": False, "message": f"更新失败: {str(e)}"}
        finally:
            conn.close()

    def delete_server(self, server_id: int) -> dict:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_servers WHERE id = ?", (server_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "服务器不存在"}

            self._unregister_server_tools(server_id)
            conn.execute("DELETE FROM proxy_servers WHERE id = ?", (server_id,))
            conn.commit()
            self._servers.pop(server_id, None)
            return {"success": True, "message": "服务器已删除"}
        except Exception as e:
            return {"success": False, "message": f"删除失败: {str(e)}"}
        finally:
            conn.close()

    # ================================================================
    #  同步工具列表（异步）
    # ================================================================

    async def sync_server(self, server_id: int) -> dict:
        """连接远端服务器并同步工具列表到数据库（不自动启用）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_servers WHERE id = ?", (server_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "服务器不存在"}
            url = row['url']
            transport = row['transport']
            headers = json.loads(row['headers']) if row['headers'] else {}
            server_name = row['name']
            timeout = row['timeout'] or 60
        finally:
            conn.close()

        try:
            tools = await self._discover_tools(url, transport, headers, timeout)
        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}

        conn = self._get_conn()
        try:
            sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            existing_raw = {
                r['raw_name'] for r in conn.execute(
                    "SELECT raw_name FROM proxy_tools WHERE server_id = ?", (server_id,)
                ).fetchall()
            }

            new_count = 0
            for tool in tools:
                raw_name = tool['name']
                description = tool['description']
                input_schema = json.dumps(tool['inputSchema'], ensure_ascii=False)

                if raw_name not in existing_raw:
                    conn.execute("""
                        INSERT INTO proxy_tools
                            (server_id, raw_name, description, input_schema, enabled)
                        VALUES (?, ?, ?, ?, 1)
                    """, (server_id, raw_name, description, input_schema))
                    new_count += 1
                else:
                    # 仅更新描述和 schema，保留用户设置的 enabled 和 custom_desc
                    conn.execute("""
                        UPDATE proxy_tools SET description=?, input_schema=?
                        WHERE server_id=? AND raw_name=?
                    """, (description, input_schema, server_id, raw_name))

            conn.execute(
                "UPDATE proxy_servers SET last_sync=? WHERE id=?", (sync_time, server_id)
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "success": True,
            "message": f"同步成功，共 {len(tools)} 个工具（新增 {new_count} 个）",
            "tool_count": len(tools),
            "new_count": new_count,
        }

    async def force_sync_server(self, server_id: int) -> dict:
        """覆盖同步：删除该服务器所有已有工具，重新从远端拉取并写入（不保留用户配置）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_servers WHERE id = ?", (server_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "服务器不存在"}
            url = row['url']
            transport = row['transport']
            headers = json.loads(row['headers']) if row['headers'] else {}
            server_name = row['name']
            timeout = row['timeout'] or 60
        finally:
            conn.close()

        try:
            tools = await self._discover_tools(url, transport, headers, timeout)
        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}

        conn = self._get_conn()
        try:
            # 删除该服务器所有已有工具
            conn.execute("DELETE FROM proxy_tools WHERE server_id = ?", (server_id,))

            sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for tool in tools:
                raw_name = tool['name']
                description = tool['description']
                input_schema = json.dumps(tool['inputSchema'], ensure_ascii=False)
                conn.execute("""
                    INSERT INTO proxy_tools
                        (server_id, raw_name, description, input_schema, enabled)
                    VALUES (?, ?, ?, ?, 1)
                """, (server_id, raw_name, description, input_schema))

            conn.execute(
                "UPDATE proxy_servers SET last_sync=? WHERE id=?", (sync_time, server_id)
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "success": True,
            "message": f"覆盖同步成功，共 {len(tools)} 个工具",
            "tool_count": len(tools),
        }

    # ================================================================
    #  服务器启用 / 禁用
    # ================================================================

    def enable_server(self, server_id: int) -> dict:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_servers WHERE id = ?", (server_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "服务器不存在"}

            server = ProxyServerInfo(**dict(row))
            server.enabled = True
            self._servers[server_id] = server

            tools = conn.execute(
                "SELECT * FROM proxy_tools WHERE server_id = ?", (server_id,)
            ).fetchall()
            count = 0
            for tool in tools:
                schema = json.loads(tool['input_schema']) if tool['input_schema'] else {}
                desc = tool['custom_desc'] or tool['description']
                raw_name = tool['raw_name']
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
                    server, raw_name, local_name, desc, schema, bool(tool['enabled'])
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
                    client_factory=make_factory(server.url),
                )

                # 增加工具启用检查中间件
                self.mcp.add_middleware(ToolEnabledCheckerMiddleware())

                # 增加工具描述变化检查中间件
                self.mcp.add_middleware(ToolDescriptionCheckerMiddleware())

                # 增加请求的日志
                self.mcp.add_middleware(RequestMCPMiddleware(self.module_manager))

                self.mcp.mount(proxy_server)
                self._mounted_proxies[name] = proxy_server

            conn.execute("UPDATE proxy_servers SET enabled=1 WHERE id=?", (server_id,))
            conn.commit()
            return {"success": True, "message": f"服务器已启用，注册了 {count} 个工具"}
        finally:
            conn.close()

    def disable_server(self, server_id: int) -> dict:
        conn = self._get_conn()
        try:
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

            conn.execute("UPDATE proxy_servers SET enabled=0 WHERE id=?", (server_id,))
            conn.commit()
            self._servers.pop(server_id, None)
            return {"success": True, "message": "服务器已禁用"}
        finally:
            conn.close()

    # ================================================================
    #  工具启用 / 禁用 / 描述更新
    # ================================================================

    def enable_tool(self, tool_id: int) -> dict:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT pt.*, ps.enabled as server_enabled "
                "FROM proxy_tools pt JOIN proxy_servers ps ON pt.server_id = ps.id "
                "WHERE pt.id = ?", (tool_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "工具不存在"}

            conn.execute("UPDATE proxy_tools SET enabled=1 WHERE id=?", (tool_id,))
            conn.commit()

            raw_name = row['raw_name']
            server = self._servers.get(row['server_id'])
            local_name = self._make_local_name(server.name, raw_name) if server else None
            if row['server_enabled'] and local_name:
                tool_obj = self.mcp._tool_manager._tools.get(local_name)
                if tool_obj:
                    tool_obj.enabled = True
                elif server:
                    # 工具不在 FastMCP 中，重新注册
                    schema = json.loads(row['input_schema']) if row['input_schema'] else {}
                    desc = row['custom_desc'] or row['description']
                    self._register_proxy_tool_in_fastmcp(
                        server, raw_name, local_name, desc, schema, True
                    )
            return {"success": True, "message": "工具已启用"}
        finally:
            conn.close()

    def disable_tool(self, tool_id: int) -> dict:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_tools WHERE id=?", (tool_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "工具不存在"}

            raw_name = row['raw_name']
            server = self._servers.get(row['server_id'])
            local_name = self._make_local_name(server.name, raw_name) if server else None
            if local_name:
                tool_obj = self.mcp._tool_manager._tools.get(local_name)
                if tool_obj:
                    tool_obj.enabled = False

            conn.execute("UPDATE proxy_tools SET enabled=0 WHERE id=?", (tool_id,))
            conn.commit()
            return {"success": True, "message": "工具已禁用"}
        finally:
            conn.close()

    def update_tool_description(self, tool_id: int, description: str) -> dict:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM proxy_tools WHERE id=?", (tool_id,)
            ).fetchone()
            if not row:
                return {"success": False, "message": "工具不存在"}

            conn.execute(
                "UPDATE proxy_tools SET custom_desc=? WHERE id=?", (description, tool_id)
            )
            conn.commit()

            # 同步更新 FastMCP 工具描述
            raw_name = row['raw_name']
            server = self._servers.get(row['server_id'])
            local_name = self._make_local_name(server.name, raw_name) if server else None
            if local_name:
                tool_obj = self.mcp._tool_manager._tools.get(local_name)
                if tool_obj:
                    tool_obj.description = description

            return {"success": True, "message": "工具描述已更新"}
        finally:
            conn.close()
