"""
FastAPI 认证依赖项
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from utils.auth import verify_token
from config_py.config import settings
from config_py.config import settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    获取当前登录用户

    从请求头中获取 Bearer Token 并验证，返回用户信息
    如果 AUTH_ENABLED 为 False，则跳过鉴权返回匿名用户

    Raises:
        HTTPException: Token 无效或用户不存在
    """
    # 如果未启用鉴权，返回默认匿名用户
    if not settings.AUTH_ENABLED:
        return {"sub": "anonymous", "role": "user", "user_id": 0}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    可选的用户认证（不强制要求登录）

    Returns:
        用户信息字典，如果未登录返回 None
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = verify_token(token)
    return payload


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    要求管理员权限

    如果 AUTH_ENABLED 为 False，则跳过权限检查
    Raises:
        HTTPException: 用户不是管理员
    """
    # 如果未启用鉴权，跳过管理员检查
    if not settings.AUTH_ENABLED:
        return {"sub": "anonymous", "role": "admin", "user_id": 0}

    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user