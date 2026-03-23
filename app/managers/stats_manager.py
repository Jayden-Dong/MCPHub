"""
统计数据管理器
记录MCP工具调用次数、成功率、响应时间等统计信息
使用 SQLModel ORM 操作数据库
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, and_
from sqlmodel import Session, select

from config_py.logger import app_logger
from db.database import engine
from db.models.stats import ToolCall


class ToolCallRecord:
    """工具调用记录"""
    def __init__(self, tool_name: str, module_name: str,
                 timestamp: float, success: bool, duration_ms: float):
        self.tool_name = tool_name
        self.module_name = module_name
        self.timestamp = timestamp
        self.success = success
        self.duration_ms = duration_ms


class StatsManager:
    """统计数据管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return Session(engine)

    def _init_db(self):
        """初始化统计表"""
        from db.database import init_db
        init_db()

    def record_call(self, tool_name: str, module_name: str,
                   success: bool = True, duration_ms: float = 0):
        """记录一次工具调用"""
        try:
            with self._get_session() as session:
                call = ToolCall(
                    tool_name=tool_name,
                    module_name=module_name,
                    timestamp=time.time(),
                    success=1 if success else 0,
                    duration_ms=duration_ms
                )
                session.add(call)
                session.commit()
        except Exception as e:
            app_logger.warning(f"记录工具调用统计失败: {e}")

    def get_module_stats(self, hours: int = 24) -> list[dict]:
        """获取模块调用统计（排行榜）"""
        with self._get_session() as session:
            cutoff = time.time() - hours * 3600

            # 使用原生 SQL 进行聚合查询（更高效）
            result = session.exec(
                select(
                    ToolCall.module_name,
                    func.count(ToolCall.id).label("call_count"),
                    func.sum(ToolCall.success).label("success_count"),
                    func.avg(ToolCall.duration_ms).label("avg_duration_ms")
                )
                .where(ToolCall.timestamp >= cutoff)
                .group_by(ToolCall.module_name)
                .order_by(func.count(ToolCall.id).desc())
            ).all()

            return [
                {
                    "module_name": row.module_name,
                    "call_count": row.call_count,
                    "success_count": row.success_count,
                    "avg_duration_ms": row.avg_duration_ms
                }
                for row in result
            ]

    def get_tool_stats(self, hours: int = 24, limit: int = 50) -> list[dict]:
        """获取工具调用统计（排行榜）"""
        with self._get_session() as session:
            cutoff = time.time() - hours * 3600

            result = session.exec(
                select(
                    ToolCall.tool_name,
                    ToolCall.module_name,
                    func.count(ToolCall.id).label("call_count"),
                    func.sum(ToolCall.success).label("success_count"),
                    func.avg(ToolCall.duration_ms).label("avg_duration_ms"),
                    func.max(ToolCall.duration_ms).label("max_duration_ms"),
                    func.min(ToolCall.duration_ms).label("min_duration_ms")
                )
                .where(ToolCall.timestamp >= cutoff)
                .group_by(ToolCall.tool_name)
                .order_by(func.count(ToolCall.id).desc())
                .limit(limit)
            ).all()

            return [
                {
                    "tool_name": row.tool_name,
                    "module_name": row.module_name,
                    "call_count": row.call_count,
                    "success_count": row.success_count,
                    "avg_duration_ms": row.avg_duration_ms,
                    "max_duration_ms": row.max_duration_ms,
                    "min_duration_ms": row.min_duration_ms
                }
                for row in result
            ]

    def get_overview_stats(self, hours: int = 24) -> dict:
        """获取概览统计"""
        with self._get_session() as session:
            cutoff = time.time() - hours * 3600

            # 总调用次数
            total_calls = session.exec(
                select(func.count(ToolCall.id))
                .where(ToolCall.timestamp >= cutoff)
            ).one()

            # 成功次数
            success_calls = session.exec(
                select(func.count(ToolCall.id))
                .where(and_(ToolCall.timestamp >= cutoff, ToolCall.success == 1))
            ).one()

            # 平均响应时间
            avg_duration = session.exec(
                select(func.avg(ToolCall.duration_ms))
                .where(ToolCall.timestamp >= cutoff)
            ).one() or 0

            # 活跃工具数
            active_tools = session.exec(
                select(func.count(func.distinct(ToolCall.tool_name)))
                .where(ToolCall.timestamp >= cutoff)
            ).one()

            # 活跃模块数
            active_modules = session.exec(
                select(func.count(func.distinct(ToolCall.module_name)))
                .where(ToolCall.timestamp >= cutoff)
            ).one()

            # 按小时统计（最近24小时）
            hourly_stats = []
            now = datetime.now()
            for i in range(24):
                hour_start = now - timedelta(hours=23-i)
                hour_start_ts = hour_start.replace(minute=0, second=0, microsecond=0).timestamp()
                hour_end_ts = hour_start_ts + 3600

                count = session.exec(
                    select(func.count(ToolCall.id))
                    .where(and_(
                        ToolCall.timestamp >= hour_start_ts,
                        ToolCall.timestamp < hour_end_ts
                    ))
                ).one()

                hourly_stats.append({
                    "hour": hour_start.strftime("%H:00"),
                    "count": count
                })

            # 今日统计
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            today_calls = session.exec(
                select(func.count(ToolCall.id))
                .where(ToolCall.timestamp >= today_start)
            ).one()

            return {
                "total_calls": total_calls,
                "success_calls": success_calls,
                "success_rate": round(success_calls / total_calls * 100, 2) if total_calls > 0 else 0,
                "avg_duration_ms": round(avg_duration, 2),
                "active_tools": active_tools,
                "active_modules": active_modules,
                "today_calls": today_calls,
                "hourly_stats": hourly_stats,
                "time_range_hours": hours
            }

    def get_recent_calls(self, limit: int = 100) -> list[dict]:
        """获取最近的调用记录"""
        with self._get_session() as session:
            calls = session.exec(
                select(ToolCall)
                .order_by(ToolCall.timestamp.desc())
                .limit(limit)
            ).all()

            result = []
            for call in calls:
                result.append({
                    "tool_name": call.tool_name,
                    "module_name": call.module_name,
                    "timestamp": call.timestamp,
                    "success": call.success,
                    "duration_ms": call.duration_ms,
                    "timestamp_str": datetime.fromtimestamp(call.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                })
            return result

    def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        with self._get_session() as session:
            cutoff = time.time() - days * 24 * 3600
            # 使用原生 SQL 删除（更高效）
            session.exec(
                ToolCall.__table__.delete().where(ToolCall.timestamp < cutoff)
            )
            session.commit()


# 全局单例
stats_manager = StatsManager()