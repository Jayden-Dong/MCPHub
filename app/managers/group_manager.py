"""
分组管理器
负责分组的 CRUD 和成员管理
"""
import uuid
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from db.database import engine
from db.models.group import Group, ModuleGroupLink, ProxyGroupLink
from db.models.module import Module
from db.models.proxy import ProxyServer

logger = logging.getLogger(__name__)


class GroupManager:
    """分组管理器"""

    def __init__(self):
        pass

    def _get_session(self) -> Session:
        return Session(engine)

    # ================================================================
    #  辅助方法
    # ================================================================

    def _get_default_group_id(self) -> Optional[str]:
        """获取默认分组的 ID"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.is_default == 1)
            ).first()
            return group.id if group else None

    # ================================================================
    #  自动归组（供 ModuleManager / ProxyManager 调用）
    # ================================================================

    def add_module_to_default_group(self, module_name: str):
        """将模块加入默认分组"""
        default_id = self._get_default_group_id()
        if not default_id:
            return
        with self._get_session() as session:
            existing = session.exec(
                select(ModuleGroupLink).where(
                    ModuleGroupLink.module_name == module_name,
                    ModuleGroupLink.group_id == default_id,
                )
            ).first()
            if not existing:
                session.add(ModuleGroupLink(module_name=module_name, group_id=default_id))
                session.commit()

    def add_proxy_to_default_group(self, server_id: int):
        """将代理服务器加入默认分组"""
        default_id = self._get_default_group_id()
        if not default_id:
            return
        with self._get_session() as session:
            existing = session.exec(
                select(ProxyGroupLink).where(
                    ProxyGroupLink.server_id == server_id,
                    ProxyGroupLink.group_id == default_id,
                )
            ).first()
            if not existing:
                session.add(ProxyGroupLink(server_id=server_id, group_id=default_id))
                session.commit()

    # ================================================================
    #  分组 CRUD
    # ================================================================

    def get_all_groups(self) -> list[dict]:
        """获取所有分组列表（含成员数量统计）"""
        with self._get_session() as session:
            groups = session.exec(select(Group).order_by(Group.created_time)).all()
            result = []
            for g in groups:
                module_count = len(session.exec(
                    select(ModuleGroupLink).where(ModuleGroupLink.group_id == g.id)
                ).all())
                proxy_count = len(session.exec(
                    select(ProxyGroupLink).where(ProxyGroupLink.group_id == g.id)
                ).all())
                d = g.to_dict()
                d["module_count"] = module_count
                d["proxy_count"] = proxy_count
                result.append(d)
            return result

    def get_group_detail(self, group_id: str) -> Optional[dict]:
        """获取单个分组详情"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return None
            return group.to_dict()

    def create_group(self, name: str, description: str = "") -> dict:
        """创建分组"""
        with self._get_session() as session:
            existing = session.exec(
                select(Group).where(Group.name == name)
            ).first()
            if existing:
                return {"success": False, "message": f"分组名称 '{name}' 已存在"}
            group = Group(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                is_default=0,
                created_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            session.add(group)
            session.commit()
            return {"success": True, "message": "分组创建成功", "group": group.to_dict()}

    def update_group(self, group_id: str, name: str = None, description: str = None) -> dict:
        """更新分组信息"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return {"success": False, "message": "分组不存在"}
            if name is not None:
                # 检查名称唯一性
                dup = session.exec(
                    select(Group).where(Group.name == name, Group.id != group_id)
                ).first()
                if dup:
                    return {"success": False, "message": f"分组名称 '{name}' 已存在"}
                group.name = name
            if description is not None:
                group.description = description
            session.add(group)
            session.commit()
            return {"success": True, "message": "分组更新成功", "group": group.to_dict()}

    def delete_group(self, group_id: str) -> dict:
        """删除分组（默认组不可删）"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return {"success": False, "message": "分组不存在"}
            if group.is_default:
                return {"success": False, "message": "默认分组不可删除"}
            # 删除关联关系
            for link in session.exec(
                select(ModuleGroupLink).where(ModuleGroupLink.group_id == group_id)
            ).all():
                session.delete(link)
            for link in session.exec(
                select(ProxyGroupLink).where(ProxyGroupLink.group_id == group_id)
            ).all():
                session.delete(link)
            session.delete(group)
            session.commit()
            return {"success": True, "message": "分组已删除"}

    # ================================================================
    #  成员管理
    # ================================================================

    def get_group_members(self, group_id: str) -> Optional[dict]:
        """获取组内所有成员（模块 + 代理服务器）"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return None

            # 获取模块成员
            module_links = session.exec(
                select(ModuleGroupLink).where(ModuleGroupLink.group_id == group_id)
            ).all()
            modules = []
            for link in module_links:
                m = session.exec(
                    select(Module).where(Module.module_name == link.module_name)
                ).first()
                if m:
                    modules.append({
                        "module_name": m.module_name,
                        "display_name": m.display_name,
                        "description": m.description,
                        "loaded": bool(m.loaded),
                    })

            # 获取代理成员
            proxy_links = session.exec(
                select(ProxyGroupLink).where(ProxyGroupLink.group_id == group_id)
            ).all()
            proxies = []
            for link in proxy_links:
                s = session.exec(
                    select(ProxyServer).where(ProxyServer.id == link.server_id)
                ).first()
                if s:
                    proxies.append({
                        "id": s.id,
                        "name": s.name,
                        "description": s.description,
                        "enabled": bool(s.enabled),
                    })

            return {
                "group": group.to_dict(),
                "modules": modules,
                "proxies": proxies,
            }

    def add_module_to_group(self, group_id: str, module_name: str) -> dict:
        """将模块加入分组"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return {"success": False, "message": "分组不存在"}
            # 检查模块是否存在
            module = session.exec(
                select(Module).where(Module.module_name == module_name)
            ).first()
            if not module:
                return {"success": False, "message": f"模块 '{module_name}' 不存在"}
            existing = session.exec(
                select(ModuleGroupLink).where(
                    ModuleGroupLink.module_name == module_name,
                    ModuleGroupLink.group_id == group_id,
                )
            ).first()
            if existing:
                return {"success": False, "message": "模块已在该分组中"}
            session.add(ModuleGroupLink(module_name=module_name, group_id=group_id))
            session.commit()
            return {"success": True, "message": "模块已加入分组"}

    def remove_module_from_group(self, group_id: str, module_name: str) -> dict:
        """从分组中移除模块"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return {"success": False, "message": "分组不存在"}
            if group.is_default:
                return {"success": False, "message": "不能从默认分组中移除成员"}
            link = session.exec(
                select(ModuleGroupLink).where(
                    ModuleGroupLink.module_name == module_name,
                    ModuleGroupLink.group_id == group_id,
                )
            ).first()
            if not link:
                return {"success": False, "message": "模块不在该分组中"}
            session.delete(link)
            session.commit()
            return {"success": True, "message": "模块已从分组移除"}

    def add_proxy_to_group(self, group_id: str, server_id: int) -> dict:
        """将代理服务器加入分组"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return {"success": False, "message": "分组不存在"}
            server = session.exec(
                select(ProxyServer).where(ProxyServer.id == server_id)
            ).first()
            if not server:
                return {"success": False, "message": f"代理服务器 {server_id} 不存在"}
            existing = session.exec(
                select(ProxyGroupLink).where(
                    ProxyGroupLink.server_id == server_id,
                    ProxyGroupLink.group_id == group_id,
                )
            ).first()
            if existing:
                return {"success": False, "message": "代理服务器已在该分组中"}
            session.add(ProxyGroupLink(server_id=server_id, group_id=group_id))
            session.commit()
            return {"success": True, "message": "代理服务器已加入分组"}

    def remove_proxy_from_group(self, group_id: str, server_id: int) -> dict:
        """从分组中移除代理服务器"""
        with self._get_session() as session:
            group = session.exec(
                select(Group).where(Group.id == group_id)
            ).first()
            if not group:
                return {"success": False, "message": "分组不存在"}
            if group.is_default:
                return {"success": False, "message": "不能从默认分组中移除成员"}
            link = session.exec(
                select(ProxyGroupLink).where(
                    ProxyGroupLink.server_id == server_id,
                    ProxyGroupLink.group_id == group_id,
                )
            ).first()
            if not link:
                return {"success": False, "message": "代理服务器不在该分组中"}
            session.delete(link)
            session.commit()
            return {"success": True, "message": "代理服务器已从分组移除"}

    # ================================================================
    #  反向查询：查看某模块/代理所属的所有分组
    # ================================================================

    def get_module_groups(self, module_name: str) -> list[dict]:
        """查询模块所属的所有分组"""
        with self._get_session() as session:
            links = session.exec(
                select(ModuleGroupLink).where(ModuleGroupLink.module_name == module_name)
            ).all()
            groups = []
            for link in links:
                g = session.exec(
                    select(Group).where(Group.id == link.group_id)
                ).first()
                if g:
                    groups.append(g.to_dict())
            return groups

    def get_proxy_groups(self, server_id: int) -> list[dict]:
        """查询代理服务器所属的所有分组"""
        with self._get_session() as session:
            links = session.exec(
                select(ProxyGroupLink).where(ProxyGroupLink.server_id == server_id)
            ).all()
            groups = []
            for link in links:
                g = session.exec(
                    select(Group).where(Group.id == link.group_id)
                ).first()
                if g:
                    groups.append(g.to_dict())
            return groups
