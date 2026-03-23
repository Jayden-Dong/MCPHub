"""
用户模型
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """用户表"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="user")
    is_active: int = Field(default=1)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_login: Optional[str] = Field(default=None)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "is_active": bool(self.is_active),
            "created_at": self.created_at,
            "last_login": self.last_login
        }