"""
用户相关的 Pydantic 模型（用于 API 请求/响应）
数据库模型请使用 db.models.user.User
"""
from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import Optional


class UserCreate(SQLModel):
    """用户创建模型"""
    username: str = Field(max_length=50)
    password: str = Field(max_length=100)


class UserLogin(SQLModel):
    """用户登录模型"""
    username: str
    password: str


class UserResponse(SQLModel):
    """用户响应模型"""
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class Token(SQLModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordChange(SQLModel):
    """修改密码模型"""
    old_password: str
    new_password: str