"""
代理服务器和代理工具模型
"""
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ProxyServer(SQLModel, table=True):
    """代理服务器表"""
    __tablename__ = "proxy_servers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    url: str
    transport: str = Field(default="streamable-http")
    enabled: int = Field(default=0)
    description: str = Field(default="")
    headers: str = Field(default="{}")
    created_time: str = Field(default="")
    last_sync: str = Field(default="")
    timeout: int = Field(default=60)

    # 关系：一个服务器有多个代理工具
    tools: List["ProxyTool"] = Relationship(back_populates="server", cascade_delete=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "transport": self.transport,
            "enabled": bool(self.enabled),
            "description": self.description,
            "headers": self.headers,
            "created_time": self.created_time,
            "last_sync": self.last_sync,
            "timeout": self.timeout
        }


class ProxyTool(SQLModel, table=True):
    """代理工具表"""
    __tablename__ = "proxy_tools"

    id: Optional[int] = Field(default=None, primary_key=True)
    server_id: int = Field(foreign_key="proxy_servers.id")
    raw_name: str
    description: str = Field(default="")
    custom_desc: str = Field(default="")
    input_schema: str = Field(default="{}")
    enabled: int = Field(default=1)

    # 关系：代理工具属于某个服务器
    server: Optional[ProxyServer] = Relationship(back_populates="tools")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "server_id": self.server_id,
            "raw_name": self.raw_name,
            "description": self.description,
            "custom_desc": self.custom_desc,
            "input_schema": self.input_schema,
            "enabled": bool(self.enabled)
        }