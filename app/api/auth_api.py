"""
用户认证 REST API
提供登录、登出、用户管理等接口
"""
import sqlite3
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from pathlib import Path

from config_py.config import settings
from config_py.logger import app_logger
from schemas.base import ApiResponse
from models.user import UserLogin, UserCreate, UserResponse, Token, PasswordChange
from utils.auth import verify_password, get_password_hash, create_access_token
from utils.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["认证管理"])

# 数据库路径
DB_PATH = Path(settings.DB_PATH)


@router.get("/config")
async def get_auth_config():
    """获取鉴权配置（公开接口，无需登录）"""
    return {"enabled": settings.AUTH_ENABLED}


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_user_table():
    """初始化用户表"""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        """)
        conn.commit()

        # 检查是否存在默认管理员账户
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        if cursor.fetchone()[0] == 0:
            # 创建默认管理员账户
            default_password = "admin123"  # 默认密码，首次登录后应修改
            password_hash = get_password_hash(default_password)
            conn.execute("""
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, 'admin', 1, ?)
            """, ("admin", password_hash, datetime.utcnow().isoformat()))
            conn.commit()
            app_logger.info("已创建默认管理员账户: admin / admin123")
    finally:
        conn.close()


# 应用启动时初始化用户表
_init_user_table()


def _row_to_user(row: sqlite3.Row) -> dict:
    """将数据库行转换为用户字典"""
    return {
        "id": row["id"],
        "username": row["username"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "last_login": row["last_login"]
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    用户登录

    验证用户名密码，返回 JWT Token
    """
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (credentials.username,)
        )
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        user = _row_to_user(row)

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被禁用"
            )

        if not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        # 更新最后登录时间
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user["id"])
        )
        conn.commit()

        # 生成 Token
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"], "user_id": user["id"]}
        )

        app_logger.info(f"用户登录成功: {user['username']}")

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                role=user["role"],
                is_active=user["is_active"],
                created_at=datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"],
                last_login=datetime.fromisoformat(user["last_login"]) if user["last_login"] else None
            )
        )
    finally:
        conn.close()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (current_user["sub"],)
        )
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )

        user = _row_to_user(row)
        return UserResponse(
            id=user["id"],
            username=user["username"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"],
            last_login=datetime.fromisoformat(user["last_login"]) if user["last_login"] else None
        )
    finally:
        conn.close()


@router.post("/password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (current_user["sub"],)
        )
        row = cursor.fetchone()

        if row is None:
            return ApiResponse.error(description="用户不存在")

        user = _row_to_user(row)

        if not verify_password(password_data.old_password, user["password_hash"]):
            return ApiResponse.error(description="原密码错误")

        new_password_hash = get_password_hash(password_data.new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, user["id"])
        )
        conn.commit()

        app_logger.info(f"用户修改密码: {user['username']}")
        return ApiResponse.success(description="密码修改成功")
    finally:
        conn.close()


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
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT * FROM users ORDER BY id")
        rows = cursor.fetchall()

        users = []
        for row in rows:
            user = _row_to_user(row)
            users.append({
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "is_active": user["is_active"],
                "created_at": user["created_at"],
                "last_login": user["last_login"]
            })

        return ApiResponse.success(data=users, description="获取用户列表成功")
    finally:
        conn.close()


@router.post("/register")
async def register_user(
    user_data: UserCreate,
    admin: dict = Depends(require_admin)
):
    """注册新用户（管理员）"""
    conn = _get_conn()
    try:
        # 检查用户名是否已存在
        cursor = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (user_data.username,)
        )
        if cursor.fetchone() is not None:
            return ApiResponse.error(description="用户名已存在")

        # 创建用户
        password_hash = get_password_hash(user_data.password)
        conn.execute("""
            INSERT INTO users (username, password_hash, role, is_active, created_at)
            VALUES (?, ?, 'user', 1, ?)
        """, (user_data.username, password_hash, datetime.utcnow().isoformat()))
        conn.commit()

        app_logger.info(f"管理员创建新用户: {user_data.username}")
        return ApiResponse.success(description="用户创建成功")
    finally:
        conn.close()


@router.put("/users/{user_id}/status")
async def toggle_user_status(
    user_id: int,
    is_active: bool,
    admin: dict = Depends(require_admin)
):
    """启用/禁用用户（管理员）"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT username FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return ApiResponse.error(description="用户不存在")

        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, user_id)
        )
        conn.commit()

        status_text = "启用" if is_active else "禁用"
        app_logger.info(f"管理员{status_text}用户: {row['username']}")
        return ApiResponse.success(description=f"用户已{status_text}")
    finally:
        conn.close()


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: dict = Depends(require_admin)
):
    """删除用户（管理员）"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT username, role FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return ApiResponse.error(description="用户不存在")

        if row["role"] == "admin":
            return ApiResponse.error(description="不能删除管理员账户")

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

        app_logger.info(f"管理员删除用户: {row['username']}")
        return ApiResponse.success(description="用户已删除")
    finally:
        conn.close()


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: int,
    new_password: str,
    admin: dict = Depends(require_admin)
):
    """重置用户密码（管理员）"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT username FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return ApiResponse.error(description="用户不存在")

        password_hash = get_password_hash(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id)
        )
        conn.commit()

        app_logger.info(f"管理员重置用户密码: {row['username']}")
        return ApiResponse.success(description="密码已重置")
    finally:
        conn.close()