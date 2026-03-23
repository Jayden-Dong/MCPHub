"""
数据库连接管理
提供 SQLModel/SQLAlchemy 引擎和会话管理
"""
import logging
from contextlib import contextmanager
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    """获取数据库路径"""
    # 延迟导入避免循环依赖
    from config_py.config import settings
    return str(Path(settings.DB_PATH).resolve())


def _create_db_engine():
    """创建数据库引擎"""
    db_path = _get_db_path()
    # 确保数据库目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    sqlite_url = f"sqlite:///{db_path}"
    engine = create_engine(
        sqlite_url,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    return engine


# 创建全局引擎
engine = _create_db_engine()


def get_session() -> Session:
    """获取数据库会话"""
    return Session(engine)


@contextmanager
def get_db():
    """
    获取数据库会话上下文管理器
    自动处理事务提交和回滚

    用法:
        with get_db() as session:
            session.add(obj)
            # 自动 commit 或 rollback
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """
    初始化数据库
    创建所有表（如果不存在）
    """
    # 导入所有模型以注册到 SQLModel.metadata
    from db.models import (
        User, Module, Tool, ProxyServer, ProxyTool, ToolCall,
        Group, ModuleGroupLink, ProxyGroupLink,
    )

    SQLModel.metadata.create_all(engine)
    logger.info("数据库表初始化完成")

    # 确保默认分组存在
    _ensure_default_group()


def _ensure_default_group():
    """确保默认分组存在，不存在则创建"""
    import uuid
    from datetime import datetime
    from db.models.group import Group

    with Session(engine) as session:
        from sqlmodel import select
        existing = session.exec(
            select(Group).where(Group.is_default == 1)
        ).first()
        if not existing:
            default_group = Group(
                id=str(uuid.uuid4()),
                name="全部",
                description="默认分组，包含所有模块和代理服务器",
                is_default=1,
                created_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            session.add(default_group)
            session.commit()
            logger.info(f"默认分组已创建: {default_group.id}")