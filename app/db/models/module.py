"""
模块和工具模型
"""
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Module(SQLModel, table=True):
    """模块表"""
    __tablename__ = "modules"

    module_name: str = Field(primary_key=True)
    display_name: str = Field(default="")
    version: str = Field(default="1.0.0")
    description: str = Field(default="")
    author: str = Field(default="")
    loaded: int = Field(default=1)
    is_external: int = Field(default=0)
    install_time: str = Field(default="")
    config: str = Field(default="{}")

    # 关系：一个模块有多个工具
    tools: List["Tool"] = Relationship(back_populates="module", cascade_delete=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "module_name": self.module_name,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "loaded": bool(self.loaded),
            "is_external": bool(self.is_external),
            "install_time": self.install_time,
            "config": self.config,
            "tools": [t.to_dict() for t in self.tools] if self.tools else []
        }


class Tool(SQLModel, table=True):
    """工具表"""
    __tablename__ = "tools"

    tool_name: str = Field(primary_key=True)
    module_name: str = Field(foreign_key="modules.module_name")
    enabled: int = Field(default=1)

    # 关系：工具属于某个模块
    module: Optional[Module] = Relationship(back_populates="tools")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "module_name": self.module_name,
            "enabled": bool(self.enabled)
        }