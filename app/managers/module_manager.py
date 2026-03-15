"""
MCP模块管理器
负责模块的生命周期管理：扫描、加载、卸载、启用/禁用工具
使用SQLite持久化模块和工具的启停状态，重启后自动恢复
"""
import importlib
import json
import os
import sqlite3
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from config_py.logger import app_logger
from config_py.config import settings


@dataclass
class ToolInfo:
    """工具信息"""
    name: str  # 工具名称（带前缀）
    description: str = ""
    enabled: bool = True


@dataclass
class ModuleInfo:
    """模块信息"""
    module_name: str  # Python模块路径，如 tools.t_ftp.ftp_mcp
    display_name: str = ""  # 显示名称
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    loaded: bool = False
    is_external: bool = False  # 是否为外部安装的模块
    install_time: str = ""  # 安装时间，格式：YYYY-MM-DD HH:MM:SS
    config: dict = field(default_factory=dict)
    tools: list = field(default_factory=list)  # List[ToolInfo] serialized


class ModuleManager:
    """MCP模块生命周期管理器"""

    # 内置模块目录
    BUILTIN_TOOLS_DIR = Path("./tools")
    # 外部模块目录
    EXTERNAL_TOOLS_DIR = Path("./tools_external")
    # SQLite数据库路径
    DB_PATH = Path(settings.DB_PATH)

    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        self._modules: dict[str, ModuleInfo] = {}  # module_name -> ModuleInfo
        self._tool_to_module: dict[str, str] = {}  # tool_name -> module_name

        # 确保外部模块目录存在
        self.EXTERNAL_TOOLS_DIR.mkdir(parents=True, exist_ok=True)

        # 将外部模块目录加入sys.path
        ext_path = str(self.EXTERNAL_TOOLS_DIR.resolve())
        if ext_path not in sys.path:
            sys.path.insert(0, ext_path)

        # 初始化数据库
        self._init_db()

    # ================================================================
    #  SQLite 持久化层
    # ================================================================

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS modules (
                    module_name   TEXT PRIMARY KEY,
                    display_name  TEXT DEFAULT '',
                    version       TEXT DEFAULT '1.0.0',
                    description   TEXT DEFAULT '',
                    author        TEXT DEFAULT '',
                    loaded        INTEGER DEFAULT 1,
                    is_external   INTEGER DEFAULT 0,
                    install_time  TEXT DEFAULT '',
                    config        TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS tools (
                    tool_name    TEXT PRIMARY KEY,
                    module_name  TEXT NOT NULL,
                    enabled      INTEGER DEFAULT 1,
                    FOREIGN KEY (module_name) REFERENCES modules(module_name)
                        ON DELETE CASCADE
                );
            """)
            conn.commit()

            # 检查并添加 install_time 字段（兼容已有数据库）
            cursor = conn.execute("PRAGMA table_info(modules)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'install_time' not in columns:
                conn.execute("ALTER TABLE modules ADD COLUMN install_time TEXT DEFAULT ''")
                conn.commit()
        finally:
            conn.close()

    def _db_save_module(self, module_info: ModuleInfo):
        """保存/更新模块状态到数据库"""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO modules
                    (module_name, display_name, version, description, author,
                     loaded, is_external, install_time, config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                module_info.module_name,
                module_info.display_name,
                module_info.version,
                module_info.description,
                module_info.author,
                1 if module_info.loaded else 0,
                1 if module_info.is_external else 0,
                module_info.install_time,
                json.dumps(module_info.config, ensure_ascii=False),
            ))
            conn.commit()
        finally:
            conn.close()

    def _db_save_tool(self, tool_name: str, module_name: str, enabled: bool):
        """保存工具到数据库（仅新增，不覆盖已有记录的enabled状态）"""
        conn = self._get_conn()
        try:
            # 使用 INSERT OR IGNORE：如果工具已存在则保留旧记录（保留用户设置的enabled状态）
            conn.execute("""
                INSERT OR IGNORE INTO tools
                    (tool_name, module_name, enabled)
                VALUES (?, ?, ?)
            """, (tool_name, module_name, 1 if enabled else 0))
            conn.commit()
        finally:
            conn.close()

    def _db_update_tool_enabled(self, tool_name: str, enabled: bool):
        """仅更新工具的启用状态"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE tools SET enabled = ? WHERE tool_name = ?",
                (1 if enabled else 0, tool_name)
            )
            conn.commit()
        finally:
            conn.close()

    def _db_update_module_loaded(self, module_name: str, loaded: bool):
        """仅更新模块的加载状态"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE modules SET loaded = ? WHERE module_name = ?",
                (1 if loaded else 0, module_name)
            )
            conn.commit()
        finally:
            conn.close()

    def _db_update_module_config(self, module_name: str, config: dict):
        """更新模块的配置"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE modules SET config = ? WHERE module_name = ?",
                (json.dumps(config, ensure_ascii=False), module_name)
            )
            conn.commit()
        finally:
            conn.close()

    def _db_delete_module(self, module_name: str):
        """从数据库中删除模块及其工具"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM tools WHERE module_name = ?", (module_name,))
            conn.execute("DELETE FROM modules WHERE module_name = ?", (module_name,))
            conn.commit()
        finally:
            conn.close()

    def _db_delete_tools_by_module(self, module_name: str):
        """删除某模块下所有工具记录"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM tools WHERE module_name = ?", (module_name,))
            conn.commit()
        finally:
            conn.close()

    def _db_get_tool_enabled(self, tool_name: str) -> Optional[bool]:
        """从数据库查询工具的启用状态，不存在返回None"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT enabled FROM tools WHERE tool_name = ?",
                (tool_name,)
            ).fetchone()
            if row is not None:
                return bool(row["enabled"])
            return None
        finally:
            conn.close()

    def _db_get_all_external_modules(self) -> list[dict]:
        """获取数据库中所有外部模块（重启恢复用）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM modules WHERE is_external = 1"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _db_get_module_loaded(self, module_name: str) -> Optional[bool]:
        """查询模块在DB中记录的loaded状态"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT loaded FROM modules WHERE module_name = ?",
                (module_name,)
            ).fetchone()
            if row is not None:
                return bool(row["loaded"])
            return None
        finally:
            conn.close()

    def _db_get_module_install_time(self, module_name: str) -> str:
        """查询模块在DB中记录的install_time"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT install_time FROM modules WHERE module_name = ?",
                (module_name,)
            ).fetchone()
            if row is not None:
                return row["install_time"] or ""
            return ""
        finally:
            conn.close()

    def _db_update_install_time(self, module_name: str, install_time: str):
        """更新模块的安装时间"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE modules SET install_time = ? WHERE module_name = ?",
                (install_time, module_name)
            )
            conn.commit()
        finally:
            conn.close()

    def _ensure_all_modules_install_time(self):
        """检查所有模块的安装时间，不存在则设置为当前时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_conn()
        try:
            # 查询所有没有安装时间的模块
            rows = conn.execute(
                "SELECT module_name FROM modules WHERE install_time = '' OR install_time IS NULL"
            ).fetchall()

            for row in rows:
                module_name = row["module_name"]
                conn.execute(
                    "UPDATE modules SET install_time = ? WHERE module_name = ?",
                    (current_time, module_name)
                )
                # 同时更新内存中的模块信息
                if module_name in self._modules:
                    self._modules[module_name].install_time = current_time
                app_logger.info(f"已为模块 {module_name} 补充安装时间: {current_time}")

            if rows:
                conn.commit()
        finally:
            conn.close()

    # ================================================================
    #  内部辅助方法
    # ================================================================

    def _get_tools_before(self) -> set:
        """获取当前已注册的工具名集合"""
        return set(self.mcp._tool_manager._tools.keys())

    def _get_tools_after(self, before: set) -> list[str]:
        """获取新增的工具名列表"""
        after = set(self.mcp._tool_manager._tools.keys())
        return list(after - before)

    def _find_existing_module(self, module_dir_name: str) -> Optional[str]:
        """查找已安装的同名外部模块，返回模块路径或None"""
        # 先从内存中查找
        for mn in self._modules:
            if mn.startswith(module_dir_name + '.') or mn == module_dir_name:
                return mn
        # 再检查文件系统
        target_dir = self.EXTERNAL_TOOLS_DIR / module_dir_name
        if target_dir.exists():
            mcp_files = list(target_dir.glob('*_mcp.py'))
            if mcp_files:
                return f"{module_dir_name}.{mcp_files[0].stem}"
            return module_dir_name
        return None

    def _get_tool_info(self, tool_name: str) -> Optional[ToolInfo]:
        """从MCP获取工具详细信息"""
        tool = self.mcp._tool_manager._tools.get(tool_name)
        if tool:
            return ToolInfo(
                name=tool_name,
                description=tool.description or "",
                enabled=getattr(tool, 'enabled', True) if hasattr(tool, 'enabled') else True
            )
        return None

    def _get_module_meta(self, module_obj) -> dict:
        """从模块对象中获取元信息"""
        meta = getattr(module_obj, 'MODULE_INFO', {})
        return {
            'display_name': meta.get('display_name', ''),
            'version': meta.get('version', '1.0.0'),
            'description': meta.get('description', ''),
            'author': meta.get('author', ''),
            'default_config': meta.get('default_config', {}),
        }

    def _apply_saved_tool_states(self, module_name: str):
        """加载模块后，从DB恢复工具的启禁状态（如果DB有记录的话）"""
        if module_name not in self._modules:
            return
        module_info = self._modules[module_name]
        for t in module_info.tools:
            tool_name = t['name']
            saved_enabled = self._db_get_tool_enabled(tool_name)
            if saved_enabled is not None:
                # DB中有记录，应用保存的状态
                t['enabled'] = 1 if saved_enabled else 0
                tool_obj = self.mcp._tool_manager._tools.get(tool_name)
                if tool_obj:
                    tool_obj.enabled = saved_enabled
                app_logger.debug(f"恢复工具状态: {tool_name} enabled={saved_enabled}")

    # ================================================================
    #  模块生命周期管理
    # ================================================================

    def load_module(self, module_name: str, config: dict = None,
                    is_external: bool = False, default_tools_enabled: bool = True) -> dict:
        """
        加载一个MCP模块

        Args:
            module_name: 模块路径，如 tools.t_ftp.ftp_mcp
            config: 模块配置
            is_external: 是否为外部模块

        Returns:
            dict with success, message, module_info
        """
        if module_name in self._modules and self._modules[module_name].loaded:
            return {"success": False, "message": f"模块 {module_name} 已经加载"}

        try:
            # 记录加载前的工具列表
            before = self._get_tools_before()

            # 刷新导入缓存，确保能发现新安装/更新的模块文件
            importlib.invalidate_caches()

            # 导入模块
            module_obj = importlib.import_module(module_name)

            # 查找 register 函数：优先在当前模块找，然后在父包中找
            register_target = None
            meta_target = module_obj

            if hasattr(module_obj, 'register'):
                register_target = module_obj
            else:
                # 检查父包是否有 register（外部模块的 register 通常在 __init__.py 中）
                parts = module_name.rsplit('.', 1)
                if len(parts) == 2:
                    try:
                        parent_pkg = importlib.import_module(parts[0])
                        if hasattr(parent_pkg, 'register'):
                            register_target = parent_pkg
                            meta_target = parent_pkg
                    except ImportError:
                        pass

            if register_target is not None:
                # 方案A：调用 register 函数
                registered_tools = register_target.register(self.mcp)
                if registered_tools is None:
                    registered_tools = []
                new_tools = registered_tools
            else:
                # 兼容模式：装饰器在import时自动注册，通过差异发现新工具
                new_tools = self._get_tools_after(before)

            # 获取模块元信息（优先从有 MODULE_INFO 的模块获取）
            meta = self._get_module_meta(meta_target)
            if not meta.get('display_name'):
                meta = self._get_module_meta(module_obj)

            # 如果调用方未传入 config，且模块声明了 default_config，则使用默认配置
            if not config and meta.get('default_config'):
                config = meta['default_config']

            # 调用模块的 init_config（如果存在），让外部插件获取初始配置
            if config:
                init_target = register_target or module_obj
                try:
                    if hasattr(init_target, 'init_config'):
                        init_target.init_config(config)
                except Exception as e:
                    app_logger.warning(f"调用模块 {module_name} 的 init_config 失败: {e}", exc_info=True)

            # 构建工具信息列表
            tool_infos = []
            for tool_name in new_tools:
                info = self._get_tool_info(tool_name)
                if info:
                    if not default_tools_enabled:
                        info.enabled = False
                    tool_infos.append(info)
                    self._tool_to_module[tool_name] = module_name

            # 创建模块信息
            # 如果是外部模块，尝试从数据库获取已有的install_time
            install_time = ""
            if is_external:
                install_time = self._db_get_module_install_time(module_name)

            module_info = ModuleInfo(
                module_name=module_name,
                display_name=meta.get('display_name') or module_name.split('.')[-1],
                version=meta.get('version', '1.0.0'),
                description=meta.get('description', ''),
                author=meta.get('author', ''),
                loaded=True,
                is_external=is_external,
                install_time=install_time,
                config=config or {},
                tools=[asdict(t) for t in tool_infos]
            )

            self._modules[module_name] = module_info

            # 持久化到数据库
            self._db_save_module(module_info)
            for ti in tool_infos:
                self._db_save_tool(ti.name, module_name, ti.enabled)

            # 从DB恢复工具启禁状态（覆盖默认值）
            self._apply_saved_tool_states(module_name)

            app_logger.info(f"模块加载成功: {module_name}, 工具数: {len(new_tools)}")
            return {
                "success": True,
                "message": f"模块 {module_name} 加载成功，注册了 {len(new_tools)} 个工具",
                "module_info": asdict(self._modules[module_name])
            }

        except Exception as e:
            app_logger.exception(f"模块加载失败: {module_name}")
            return {"success": False, "message": f"模块加载失败: {str(e)}"}

    def unload_module(self, module_name: str) -> dict:
        """
        卸载一个MCP模块

        Args:
            module_name: 模块路径

        Returns:
            dict with success, message
        """
        if module_name not in self._modules:
            return {"success": False, "message": f"模块 {module_name} 未找到"}

        module_info = self._modules[module_name]
        if not module_info.loaded:
            return {"success": False, "message": f"模块 {module_name} 未加载"}

        try:
            # 尝试调用 unregister 函数（当前模块或父包）
            unregister_called = False
            module_obj = sys.modules.get(module_name)
            if module_obj and hasattr(module_obj, 'unregister'):
                module_obj.unregister(self.mcp)
                unregister_called = True
            else:
                # 检查父包
                parts = module_name.rsplit('.', 1)
                if len(parts) == 2:
                    parent_obj = sys.modules.get(parts[0])
                    if parent_obj and hasattr(parent_obj, 'unregister'):
                        parent_obj.unregister(self.mcp)
                        unregister_called = True

            if not unregister_called:
                # 手动移除所有工具
                for tool_info in module_info.tools:
                    tool_name = tool_info['name']
                    try:
                        self.mcp.remove_tool(tool_name)
                        app_logger.info(f"移除工具: {tool_name}")
                    except Exception as e:
                        app_logger.warning(f"移除工具失败 {tool_name}: {e}", exc_info=True)

                    # 清理映射
                    self._tool_to_module.pop(tool_name, None)

            # 从sys.modules中彻底清除模块及其关联的所有缓存
            self._cleanup_sys_modules(module_name)

            # 更新内存状态
            module_info.loaded = False
            module_info.tools = []

            # 持久化：更新loaded状态（保留工具记录以便恢复）
            self._db_update_module_loaded(module_name, False)

            app_logger.info(f"模块卸载成功: {module_name}")
            return {"success": True, "message": f"模块 {module_name} 卸载成功"}

        except Exception as e:
            app_logger.exception(f"模块卸载失败: {module_name}")
            return {"success": False, "message": f"模块卸载失败: {str(e)}"}

    def reload_module(self, module_name: str) -> dict:
        """重新加载模块"""
        if module_name not in self._modules:
            return {"success": False, "message": f"模块 {module_name} 未找到"}

        module_info = self._modules[module_name]
        config = module_info.config
        is_external = module_info.is_external

        # 先卸载
        if module_info.loaded:
            result = self.unload_module(module_name)
            if not result["success"]:
                return result

        # 再加载
        return self.load_module(module_name, config, is_external)

    def update_module_config(self, module_name: str, config: dict) -> dict:
        """
        更新模块配置（热更新）

        Args:
            module_name: 模块路径
            config: 新的配置字典

        Returns:
            dict with success, message
        """
        if module_name not in self._modules:
            return {"success": False, "message": f"模块 {module_name} 未找到"}

        module_info = self._modules[module_name]

        # 更新内存中的配置
        module_info.config = config

        # 持久化到数据库
        self._db_update_module_config(module_name, config)

        # 如果是内部模块，同步更新 config.json 文件
        if not module_info.is_external:
            self._update_config_json(module_name, config)

        app_logger.info(f"模块 {module_name} 配置已更新")

        # 如果模块已加载，尝试调用模块的 update_config 方法（如果存在）
        if module_info.loaded:
            try:
                module_obj = sys.modules.get(module_name)
                if module_obj and hasattr(module_obj, 'update_config'):
                    module_obj.update_config(config)
                    app_logger.info(f"已调用模块 {module_name} 的 update_config 方法")
                else:
                    # 检查父包
                    parts = module_name.rsplit('.', 1)
                    if len(parts) == 2:
                        parent_obj = sys.modules.get(parts[0])
                        if parent_obj and hasattr(parent_obj, 'update_config'):
                            parent_obj.update_config(config)
                            app_logger.info(f"已调用父包 {parts[0]} 的 update_config 方法")
            except Exception as e:
                app_logger.warning(f"调用模块 {module_name} 的 update_config 失败: {e}", exc_info=True)

        return {"success": True, "message": f"模块 {module_name} 配置已更新"}

    def _update_config_json(self, module_name: str, config: dict):
        """更新 config.json 中指定模块的配置"""
        try:
            config_path = Path("./config/config.json")
            if not config_path.exists():
                app_logger.warning("config.json 文件不存在")
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 更新 mcp.module_enable 中对应模块的 config
            module_enable = config_data.get("mcp", {}).get("module_enable", [])
            updated = False
            for module in module_enable:
                if module.get("module_name") == module_name:
                    module["config"] = config
                    updated = True
                    break

            if updated:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                app_logger.info(f"已同步更新 config.json 中模块 {module_name} 的配置")
            else:
                app_logger.warning(f"在 config.json 中未找到模块 {module_name}")

        except Exception as e:
            app_logger.exception(f"更新 config.json 失败: {e}")

    def enable_tool(self, tool_name: str) -> dict:
        """启用某个工具"""
        tool = self.mcp._tool_manager._tools.get(tool_name)
        if not tool:
            return {"success": False, "message": f"工具 {tool_name} 未找到"}

        tool.enabled = True

        # 更新内存中的模块信息
        module_name = self._tool_to_module.get(tool_name)
        if module_name and module_name in self._modules:
            for t in self._modules[module_name].tools:
                if t['name'] == tool_name:
                    t['enabled'] = 1
                    break

        # 持久化到数据库
        self._db_update_tool_enabled(tool_name, True)

        return {"success": True, "message": f"工具 {tool_name} 已启用"}

    def disable_tool(self, tool_name: str) -> dict:
        """禁用某个工具"""
        tool = self.mcp._tool_manager._tools.get(tool_name)
        if not tool:
            return {"success": False, "message": f"工具 {tool_name} 未找到"}

        tool.enabled = False

        # 更新内存中的模块信息
        module_name = self._tool_to_module.get(tool_name)
        if module_name and module_name in self._modules:
            for t in self._modules[module_name].tools:
                if t['name'] == tool_name:
                    t['enabled'] = 0
                    break

        # 持久化到数据库
        self._db_update_tool_enabled(tool_name, False)

        return {"success": True, "message": f"工具 {tool_name} 已禁用"}

    def update_tool_description(self, tool_name: str, description: str) -> dict:
        """将工具描述写入源代码文件，并同步更新内存状态"""
        module_name = self._tool_to_module.get(tool_name)
        if not module_name:
            return {"success": False, "message": f"工具 {tool_name} 未找到"}

        module_info = self._modules.get(module_name)
        if not module_info or not module_info.is_external:
            return {"success": False, "message": "仅支持修改外部模块的工具描述"}

        # 获取 raw_name
        raw_name = tool_name
        prefix = settings.MCP_TOOL_NAME_PREFIX
        if prefix and tool_name.startswith(prefix):
            raw_name = tool_name[len(prefix):]

        # 获取模块目录
        module_dir = self._get_module_dir(module_name)
        if module_dir is None:
            return {"success": False, "message": f"未找到模块目录: {module_name}"}

        # 在目录下所有 .py 文件中搜索并替换描述
        if not self._replace_description_in_module(module_dir, tool_name, raw_name, description):
            return {"success": False, "message": "未能在源文件中定位到该工具的描述，请检查工具定义格式"}

        # 同步更新内存中的 MCP tool 对象
        tool = self.mcp._tool_manager._tools.get(tool_name)
        if tool:
            tool.description = description

        # 同步更新内存中的模块信息
        for t in module_info.tools:
            if t['name'] == tool_name:
                t['description'] = description
                break

        app_logger.info(f"已将工具 {tool_name} 的描述写入源文件（目录: {module_dir}）")
        return {"success": True, "message": f"工具 {tool_name} 描述已更新到源文件"}

    def _get_module_dir(self, module_name: str) -> Optional[Path]:
        """根据模块名获取模块所在目录"""
        parts = module_name.split('.')
        if module_name.startswith('tools.') and len(parts) >= 2:
            module_dir = self.BUILTIN_TOOLS_DIR / parts[1]
        else:
            module_dir = self.EXTERNAL_TOOLS_DIR / parts[0]
        return module_dir if module_dir.exists() else None

    def _replace_description_in_module(self, module_dir: Path, tool_name: str,
                                        raw_name: str, new_description: str) -> bool:
        """
        在模块目录的所有 .py 文件中搜索工具描述并替换。
        支持两种模式：
          1. Tool.from_function(..., name="xxx", description="...") 风格
          2. @mcp.tool(description="...") 装饰器 + def raw_name(...) 风格
        tool_name 和 raw_name 都会尝试匹配（处理有/无前缀的情况）。
        """
        # __init__.py 优先搜索（AI 生成的外部模块描述通常在这里）
        py_files = sorted(module_dir.glob('*.py'),
                          key=lambda p: (0 if p.name == '__init__.py' else 1, p.name))

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8')
            except Exception as e:
                app_logger.debug(f"读取文件 {py_file} 失败: {e}")
                continue

            # 策略1：通过 name="xxx" 定位（Tool.from_function 风格）
            # tool_name 和 raw_name 都尝试
            names_to_try = list(dict.fromkeys([raw_name, tool_name]))  # 去重保序
            for name_val in names_to_try:
                new_content = self._replace_by_name_kwarg(content, name_val, new_description)
                if new_content is not None:
                    py_file.write_text(new_content, encoding='utf-8')
                    return True

            # 策略2：通过 def raw_name( 前的 @mcp.tool 装饰器定位
            new_content = self._replace_by_decorator(content, raw_name, new_description)
            if new_content is not None:
                py_file.write_text(new_content, encoding='utf-8')
                return True

        return False

    def _replace_by_name_kwarg(self, content: str, name_value: str,
                                new_description: str) -> Optional[str]:
        """
        策略1：找到 name="name_value" 所在的函数调用括号块，替换其中的 description=。
        适用于 Tool.from_function(func, name="...", description="...") 风格。
        """
        import re

        name_pat = re.compile(
            r'name\s*=\s*(?:"' + re.escape(name_value) + r'"|'
            + "'" + re.escape(name_value) + r"')"
        )
        m = name_pat.search(content)
        if not m:
            return None

        name_pos = m.start()

        # 向左扫描，找包含此 name= 的最近一个开括号
        depth = 0
        open_paren = None
        for i in range(name_pos, -1, -1):
            c = content[i]
            if c == ')':
                depth += 1
            elif c == '(':
                if depth == 0:
                    open_paren = i
                    break
                depth -= 1

        if open_paren is None:
            return None

        # 向右扫描，找对应的闭括号
        depth = 1
        close_paren = None
        for i in range(open_paren + 1, len(content)):
            c = content[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    close_paren = i
                    break

        if close_paren is None:
            return None

        # 在括号块内替换 description=
        block = content[open_paren: close_paren + 1]
        new_block = self._replace_description_param(block, new_description)
        if new_block is None:
            return None

        return content[:open_paren] + new_block + content[close_paren + 1:]

    def _replace_by_decorator(self, content: str, raw_name: str,
                               new_description: str) -> Optional[str]:
        """
        策略2：找到 def raw_name( 前的 @mcp.tool 装饰器，替换其中的 description=。
        适用于 @mcp.tool(description="...") 装饰器风格。
        """
        import re

        func_pat = re.compile(
            r'^[ \t]*def\s+' + re.escape(raw_name) + r'\s*\(',
            re.MULTILINE
        )
        func_match = func_pat.search(content)
        if not func_match:
            return None

        func_pos = func_match.start()
        search_start = max(0, func_pos - 3000)
        pre_region = content[search_start:func_pos]

        deco_matches = list(re.finditer(r'@\S*tool\b', pre_region, re.IGNORECASE))
        if not deco_matches:
            return None

        deco_abs_start = search_start + deco_matches[-1].start()
        decorator_block = content[deco_abs_start:func_pos]

        new_block = self._replace_description_param(decorator_block, new_description)
        if new_block is None:
            return None

        return content[:deco_abs_start] + new_block + content[func_pos:]

    @staticmethod
    def _replace_description_param(block: str, new_description: str) -> Optional[str]:
        """
        在代码块中替换 description= 的字符串值。
        支持：单/双引号单行、三引号多行、f-string（替换后变为普通字符串）。
        """
        import re

        # 按优先级匹配（三引号必须先于单引号，避免误截断）
        patterns = [
            (re.compile(r'description\s*=\s*f?""".*?"""', re.DOTALL), '"""'),
            (re.compile(r"description\s*=\s*f?'''.*?'''", re.DOTALL), "'''"),
            (re.compile(r'description\s*=\s*f?"(?:[^"\\]|\\.)*"'), '"'),
            (re.compile(r"description\s*=\s*f?'(?:[^'\\]|\\.)*'"), "'"),
        ]

        for pattern, quote in patterns:
            m = pattern.search(block)
            if not m:
                continue

            if len(quote) == 3:
                safe = new_description.replace(quote, quote[0] * 2) \
                    if quote in new_description else new_description
                replacement = f'description={quote}{safe}{quote}'
            else:
                escaped = new_description.replace('\\', '\\\\').replace(quote, '\\' + quote)
                replacement = f'description={quote}{escaped}{quote}'

            return block[:m.start()] + replacement + block[m.end():]

        return None

    # ================================================================
    #  查询接口
    # ================================================================

    def get_all_modules(self) -> list[dict]:
        """获取所有模块状态"""
        result = []
        for module_name, info in self._modules.items():
            module_dict = asdict(info)
            # 如果模块已加载，从MCP实例刷新工具的实时状态
            if info.loaded:
                refreshed_tools = []
                for t in info.tools:
                    tool_obj = self.mcp._tool_manager._tools.get(t['name'])
                    if tool_obj:
                        t['enabled'] = 1 if getattr(tool_obj, 'enabled', True) else 0
                        t['description'] = tool_obj.description or t.get('description', '')
                    refreshed_tools.append(t)
                module_dict['tools'] = refreshed_tools
            result.append(module_dict)
        return result

    def get_module(self, module_name: str) -> Optional[dict]:
        """获取单个模块信息（支持已加载和未加载的模块）"""
        # 先从内存中查找
        if module_name in self._modules:
            info = self._modules[module_name]
            module_dict = asdict(info)
            if info.loaded:
                for t in module_dict['tools']:
                    tool_obj = self.mcp._tool_manager._tools.get(t['name'])
                    if tool_obj:
                        t['description'] = tool_obj.description or t.get('description', '')
                        t['enabled'] = 1 if getattr(tool_obj, 'enabled', True) else 0
                        t['parameters'] = getattr(tool_obj, 'parameters', {})
            return module_dict

        # 如果内存中没有，尝试从数据库获取（未加载但已安装的模块）
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM modules WHERE module_name = ?",
                (module_name,)
            ).fetchone()
            if row:
                # 从数据库构建 ModuleInfo
                module_info = ModuleInfo(
                    module_name=row["module_name"],
                    display_name=row["display_name"] or "",
                    version=row["version"] or "1.0.0",
                    description=row["description"] or "",
                    author=row["author"] or "",
                    loaded=bool(row["loaded"]),
                    is_external=bool(row["is_external"]),
                    install_time=row["install_time"] or "",
                    config=json.loads(row["config"] or "{}"),
                    tools=[]  # 未加载模块工具列表为空
                )
                # 缓存到内存
                self._modules[module_name] = module_info
                return asdict(module_info)
        finally:
            conn.close()

        return None

    def scan_available_modules(self) -> list[dict]:
        """扫描所有可用但未加载的模块（包括内置和外部）"""
        available = []

        # 扫描内置模块目录
        for item in self.BUILTIN_TOOLS_DIR.iterdir():
            if item.is_dir() and item.name.startswith('t_'):
                mcp_files = list(item.glob('*_mcp.py'))
                for mcp_file in mcp_files:
                    module_name = f"tools.{item.name}.{mcp_file.stem}"
                    if module_name not in self._modules or not self._modules[module_name].loaded:
                        available.append({
                            "module_name": module_name,
                            "display_name": item.name,
                            "is_external": False,
                            "path": str(item),
                            "loaded": False
                        })

        # 扫描外部模块目录
        if self.EXTERNAL_TOOLS_DIR.exists():
            for item in self.EXTERNAL_TOOLS_DIR.iterdir():
                if item.is_dir() and item.name.startswith('t_'):
                    mcp_files = list(item.glob('*_mcp.py'))
                    for mcp_file in mcp_files:
                        module_name = f"{item.name}.{mcp_file.stem}"
                        if module_name not in self._modules or not self._modules[module_name].loaded:
                            meta = self._read_module_meta_from_file(item)
                            available.append({
                                "module_name": module_name,
                                "display_name": meta.get('display_name', item.name),
                                "description": meta.get('description', ''),
                                "version": meta.get('version', '1.0.0'),
                                "is_external": True,
                                "path": str(item),
                                "loaded": False
                            })

        return available

    def _read_module_meta_from_file(self, module_dir: Path) -> dict:
        """从模块目录的__init__.py中读取MODULE_INFO（不导入）"""
        init_file = module_dir / "__init__.py"
        if not init_file.exists():
            return {}
        try:
            content = init_file.read_text(encoding='utf-8')
            if 'MODULE_INFO' in content:
                namespace = {}
                exec(content, namespace)
                return namespace.get('MODULE_INFO', {})
        except Exception as e:
            app_logger.debug(f"读取模块 {module_dir} 的 MODULE_INFO 失败: {e}")
        return {}

    # ================================================================
    #  模块安装与删除
    # ================================================================

    def install_module(self, zip_path: str, force: bool = False) -> dict:
        """从zip包安装新模块到外部模块目录"""
        import zipfile

        if not os.path.exists(zip_path):
            return {"success": False, "message": f"文件不存在: {zip_path}"}

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                names = zf.namelist()
                top_dirs = set()
                for name in names:
                    parts = name.split('/')
                    if len(parts) > 1 and parts[0]:
                        top_dirs.add(parts[0])

                if len(top_dirs) != 1:
                    return {"success": False, "message": "zip包应包含且仅包含一个顶层模块目录"}

                module_dir_name = top_dirs.pop()
                if not module_dir_name.startswith('t_'):
                    return {"success": False,
                            "message": f"模块目录名必须以 t_ 开头，当前为: {module_dir_name}"}

                target_dir = self.EXTERNAL_TOOLS_DIR / module_dir_name

                # 检查是否已存在同名模块
                existing_module_name = self._find_existing_module(module_dir_name)
                if existing_module_name and not force:
                    return {
                        "success": False,
                        "exists": True,
                        "message": f"模块 {existing_module_name} 已存在",
                        "module_name": existing_module_name,
                    }

                # force=True 时先删除旧模块（文件 + 数据库 + 内存）
                if existing_module_name and force:
                    self.delete_module(existing_module_name)
                elif target_dir.exists():
                    shutil.rmtree(target_dir)

                zf.extractall(self.EXTERNAL_TOOLS_DIR)

            # 安装依赖
            req_file = target_dir / "requirements.txt"
            if req_file.exists():
                app_logger.info(f"安装模块依赖: {req_file}")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    capture_output=True, text=True, timeout=120
                )

            mcp_files = list(target_dir.glob('*_mcp.py'))
            if not mcp_files:
                return {"success": False, "message": "模块中未找到 *_mcp.py 文件"}

            module_name = f"{module_dir_name}.{mcp_files[0].stem}"

            app_logger.info(f"模块安装成功: {module_name}，开始自动加载")

            # 安装后自动加载，工具默认启用（但模块默认不启用，需要用户手动启用模块）
            load_result = self.load_module(module_name, is_external=True, default_tools_enabled=True)

            # 安装后立即将模块标记为未加载（loaded=False），用户需手动启用
            if module_name in self._modules:
                # 记录安装时间
                install_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._modules[module_name].loaded = False
                self._modules[module_name].install_time = install_time
                self._db_update_module_loaded(module_name, False)
                # 更新数据库中的安装时间
                conn = self._get_conn()
                try:
                    conn.execute(
                        "UPDATE modules SET install_time = ? WHERE module_name = ?",
                        (install_time, module_name)
                    )
                    conn.commit()
                finally:
                    conn.close()
                # 同时从内存中移除工具注册
                for tool in self._modules[module_name].tools:
                    tool_obj = self.mcp._tool_manager._tools.get(tool['name'])
                    if tool_obj:
                        tool_obj.enabled = False
                # 清除sys.modules中的缓存，防止后续重装时加载到旧代码
                self._cleanup_sys_modules(module_name)

            return {
                "success": True,
                "message": f"模块 {module_name} 安装成功",
                "module_name": module_name,
                "module_info": load_result.get("module_info"),
            }

        except Exception as e:
            app_logger.exception("模块安装失败")
            return {"success": False, "message": f"安装失败: {str(e)}"}

    def _cleanup_sys_modules(self, module_name: str):
        """从sys.modules中彻底清除模块及其关联的所有子模块和父包"""
        modules_to_remove = [
            key for key in sys.modules
            if key == module_name or key.startswith(module_name + '.')
        ]
        # 也清除父包及其下所有子模块
        parts = module_name.rsplit('.', 1)
        if len(parts) == 2:
            parent_pkg = parts[0]
            modules_to_remove.extend([
                key for key in sys.modules
                if (key == parent_pkg or key.startswith(parent_pkg + '.'))
                and key not in modules_to_remove
            ])

        for mod_key in modules_to_remove:
            del sys.modules[mod_key]
            app_logger.debug(f"从sys.modules移除: {mod_key}")

    def delete_module(self, module_name: str) -> dict:
        """删除已安装的外部模块"""
        if module_name in self._modules:
            info = self._modules[module_name]
            if not info.is_external:
                return {"success": False, "message": "不能删除内置模块"}
            if info.loaded:
                self.unload_module(module_name)

        # 无论loaded状态如何，都确保从sys.modules中清除（防止缓存旧代码）
        self._cleanup_sys_modules(module_name)

        # 根据module_name推断目录
        parts = module_name.split('.')
        dir_name = parts[0] if len(parts) >= 1 else module_name
        target_dir = self.EXTERNAL_TOOLS_DIR / dir_name

        file_deleted = True
        try:
            if target_dir.exists():
                shutil.rmtree(target_dir)
        except Exception as e:
            file_deleted = False
            app_logger.warning(f"删除模块目录失败: {target_dir}, 错误: {e}", exc_info=True)
        finally:
            # 无论文件是否删除成功，始终清理内存和数据库
            self._modules.pop(module_name, None)
            self._db_delete_module(module_name)

        if not file_deleted:
            return {"success": True, "message": f"模块 {module_name} 已从系统中移除（目录删除失败，请手动清理 {target_dir}）"}
        return {"success": True, "message": f"模块 {module_name} 已删除"}

    # ================================================================
    #  启动加载
    # ================================================================

    def load_from_config(self):
        """
        服务启动时调用：
        1. 从config.json加载内置模块
        2. 从数据库恢复外部模块
        3. 应用数据库中保存的工具启禁状态
        4. 检查并补充所有模块的安装时间
        """
        # ---------- 步骤1：加载config.json中的内置模块 ----------
        for mcp_module in settings.MCP_ENABLE_MODULE:
            module_name = mcp_module.get("module_name", "")
            if not module_name:
                continue

            # 检查内置模块目录是否实际存在，不存在则跳过（前端也不展示）
            module_dir = self._get_module_dir(module_name)
            if module_dir is None:
                app_logger.warning(f"内置模块 {module_name} 的目录不存在，已跳过")
                continue

            enable = mcp_module.get("enable", True)
            config = mcp_module.get("config", {})

            # 检查DB中是否有该模块的保存状态
            db_loaded = self._db_get_module_loaded(module_name)
            # DB中有明确的loaded=False记录（用户手动卸载过），则不加载
            if db_loaded is False:
                app_logger.info(f"模块 {module_name} 在数据库中标记为未加载，跳过")
                self._modules[module_name] = ModuleInfo(
                    module_name=module_name,
                    display_name=module_name.split('.')[-1],
                    loaded=False,
                    config=config
                )
                continue

            if enable:
                self.load_module(module_name, config, is_external=False)
            else:
                self._modules[module_name] = ModuleInfo(
                    module_name=module_name,
                    display_name=module_name.split('.')[-1],
                    loaded=False,
                    config=config
                )

        # ---------- 步骤2：从数据库恢复外部模块 ----------
        external_modules = self._db_get_all_external_modules()
        for row in external_modules:
            module_name = row["module_name"]
            if module_name in self._modules:
                continue  # 已经处理过

            if not row["loaded"]:
                # 记录但不加载
                self._modules[module_name] = ModuleInfo(
                    module_name=module_name,
                    display_name=row.get("display_name", ""),
                    version=row.get("version", "1.0.0"),
                    description=row.get("description", ""),
                    loaded=False,
                    is_external=True,
                    install_time=row.get("install_time", ""),
                    config=json.loads(row.get("config", "{}"))
                )
                app_logger.info(f"外部模块 {module_name} 已记录但不加载（DB标记为未加载）")
                continue

            # 加载外部模块
            config = json.loads(row.get("config", "{}"))
            app_logger.info(f"从数据库恢复外部模块: {module_name}")
            self.load_module(module_name, config, is_external=True)

        # ---------- 步骤3：检查并补充所有模块的安装时间 ----------
        self._ensure_all_modules_install_time()
