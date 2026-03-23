"""
用户认证 REST API
提供登录、登出、用户管理等接口
使用 SQLModel ORM 操作数据库
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends

from config_py.logger import app_logger
from schemas.base import ApiResponse
from models.user import UserLogin, UserCreate, UserResponse, Token, PasswordChange
from utils.auth import verify_password, get_password_hash, create_access_token
from utils.dependencies import get_current_user, require_admin
from db.database import get_db
from db.models.user import User
from sqlmodel import select

router = APIRouter(prefix="/api/auth", tags=["认证管理"])



@router.get("/config")
async def get_auth_config():
    """获取鉴权配置（公开接口，无需登录）"""
    return {"enabled": settings.AUTH_ENABLED}

@router.get("/config")
async def get_auth_config():
    """获取鉴权配置（公开接口，无需登录）"""
    from config_py.config import settings
    return {"enabled": settings.AUTH_ENABLED}


def _init_user_table():
    """初始化用户表和默认管理员"""
    from db.database import init_db, engine
    from sqlmodel import Session, text

    # 初始化所有表
    init_db()

    # 检查是否存在默认管理员账户
    with Session(engine) as session:
        result = session.exec(
            select(User).where(User.role == "admin")
        ).all()
        if len(result) == 0:
            # 创建默认管理员账户
            default_password = "admin123"  # 默认密码，首次登录后应修改
            password_hash = get_password_hash(default_password)
            admin = User(
                username="admin",
                password_hash=password_hash,
                role="admin",
                is_active=1,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(admin)
            session.commit()
            app_logger.info("已创建默认管理员账户: admin / admin123")


# 应用启动时初始化用户表
_init_user_table()


def _user_to_response(user: User) -> UserResponse:
    """将 User ORM 对象转换为响应模型"""
    created_at = user.created_at
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    last_login = user.last_login
    if last_login and isinstance(last_login, str):
        last_login = datetime.fromisoformat(last_login)

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=bool(user.is_active),
        created_at=created_at,
        last_login=last_login
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    用户登录

    验证用户名密码，返回 JWT Token
    """
    with get_db() as session:
        user = session.exec(
            select(User).where(User.username == credentials.username)
        ).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被禁用"
            )

        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        # 更新最后登录时间
        user.last_login = datetime.utcnow().isoformat()
        session.add(user)
        session.commit()

        # 生成 Token
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role, "user_id": user.id}
        )

        app_logger.info(f"用户登录成功: {user.username}")

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=_user_to_response(user)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    with get_db() as session:
        user = session.exec(
            select(User).where(User.username == current_user["sub"])
        ).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )

        return _user_to_response(user)


@router.post("/password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    with get_db() as session:
        user = session.exec(
            select(User).where(User.username == current_user["sub"])
        ).first()

        if user is None:
            return ApiResponse.error(description="用户不存在")

        if not verify_password(password_data.old_password, user.password_hash):
            return ApiResponse.error(description="原密码错误")

        user.password_hash = get_password_hash(password_data.new_password)
        session.add(user)
        session.commit()

        app_logger.info(f"用户修改密码: {user.username}")
        return ApiResponse.success(description="密码修改成功")


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    用户登出

    注：JWT 是无状态的，服务端不记录 Token 状态
    客户端需要自行删除 Token
    """
    app_logger.info(f"用户登出: {current_user['sub']}")
    return ApiResponse.success(description="登出成功")


# ============== 管理员接口 ==============

@router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    """获取所有用户列表（管理员）"""
    with get_db() as session:
        users = session.exec(select(User).order_by(User.id)).all()

        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at,
                "last_login": user.last_login
            })

        return ApiResponse.success(data=user_list, description="获取用户列表成功")


@router.post("/register")
async def register_user(
    user_data: UserCreate,
    admin: dict = Depends(require_admin)
):
    """注册新用户（管理员）"""
    with get_db() as session:
        # 检查用户名是否已存在
        existing = session.exec(
            select(User).where(User.username == user_data.username)
        ).first()
        if existing is not None:
            return ApiResponse.error(description="用户名已存在")

        # 创建用户
        password_hash = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            password_hash=password_hash,
            role="user",
            is_active=1,
            created_at=datetime.utcnow().isoformat()
        )
        session.add(new_user)
        session.commit()

        app_logger.info(f"管理员创建新用户: {user_data.username}")
        return ApiResponse.success(description="用户创建成功")


@router.put("/users/{user_id}/status")
async def toggle_user_status(
    user_id: int,
    is_active: bool,
    admin: dict = Depends(require_admin)
):
    """启用/禁用用户（管理员）"""
    with get_db() as session:
        user = session.exec(
            select(User).where(User.id == user_id)
        ).first()
        if user is None:
            return ApiResponse.error(description="用户不存在")

        user.is_active = 1 if is_active else 0
        session.add(user)
        session.commit()

        status_text = "启用" if is_active else "禁用"
        app_logger.info(f"管理员{status_text}用户: {user.username}")
        return ApiResponse.success(description=f"用户已{status_text}")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: dict = Depends(require_admin)
):
    """删除用户（管理员）"""
    with get_db() as session:
        user = session.exec(
            select(User).where(User.id == user_id)
        ).first()
        if user is None:
            return ApiResponse.error(description="用户不存在")

        if user.role == "admin":
            return ApiResponse.error(description="不能删除管理员账户")

        session.delete(user)
        session.commit()

        app_logger.info(f"管理员删除用户: {user.username}")
        return ApiResponse.success(description="用户已删除")


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: int,
    new_password: str,
    admin: dict = Depends(require_admin)
):
    """重置用户密码（管理员）"""
    with get_db() as session:
        user = session.exec(
            select(User).where(User.id == user_id)
        ).first()
        if user is None:
            return ApiResponse.error(description="用户不存在")

        user.password_hash = get_password_hash(new_password)
        session.add(user)
        session.commit()

        app_logger.info(f"管理员重置用户密码: {user.username}")
        return ApiResponse.success(description="密码已重置")