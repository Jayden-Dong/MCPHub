"""
用户数据库模型
"""
from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import Optional


class User(SQLModel, table=True):
    """用户表"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True, nullable=False)
    password_hash: str = Field(max_length=255, nullable=False)
    role: str = Field(default="user", max_length=20)  # admin / user
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)


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