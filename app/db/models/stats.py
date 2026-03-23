"""
统计数据模型
"""
from typing import Optional
from sqlmodel import SQLModel, Field


class ToolCall(SQLModel, table=True):
    """工具调用记录表"""
    __tablename__ = "tool_calls"

    id: Optional[int] = Field(default=None, primary_key=True)
    tool_name: str = Field(index=True)
    module_name: str = Field(index=True)
    timestamp: float = Field(index=True)
    success: int = Field(default=1)
    duration_ms: float = Field(default=0)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "module_name": self.module_name,
            "timestamp": self.timestamp,
            "success": bool(self.success),
            "duration_ms": self.duration_ms
        }