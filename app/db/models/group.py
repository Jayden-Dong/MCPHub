"""
分组模型
支持模块和代理服务器的多对多分组
"""
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class Group(SQLModel, table=True):
    """分组表"""
    __tablename__ = "groups"

    id: str = Field(primary_key=True)  # UUID
    name: str = Field(unique=True)
    description: str = Field(default="")
    is_default: int = Field(default=0)  # 1=默认组（不可删除）
    created_time: str = Field(default="")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_default": bool(self.is_default),
            "created_time": self.created_time,
        }


class ModuleGroupLink(SQLModel, table=True):
    """模块-分组关联表（多对多）"""
    __tablename__ = "module_group_links"
    __table_args__ = (
        UniqueConstraint("module_name", "group_id", name="uq_module_group"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    module_name: str = Field(foreign_key="modules.module_name")
    group_id: str = Field(foreign_key="groups.id")


class ProxyGroupLink(SQLModel, table=True):
    """代理服务器-分组关联表（多对多）"""
    __tablename__ = "proxy_group_links"
    __table_args__ = (
        UniqueConstraint("server_id", "group_id", name="uq_proxy_group"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    server_id: int = Field(foreign_key="proxy_servers.id")
    group_id: str = Field(foreign_key="groups.id")
