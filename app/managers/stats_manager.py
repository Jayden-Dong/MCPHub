"""
统计数据管理器
记录MCP工具调用次数、成功率、响应时间等统计信息
"""
import sqlite3
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional
from dataclasses import dataclass, asdict

from config_py.logger import app_logger
from config_py.config import settings


@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_name: str
    module_name: str
    timestamp: float
    success: bool
    duration_ms: float


class StatsManager:
    """统计数据管理器"""

    DB_PATH = Path(settings.DB_PATH)
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

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """初始化统计表"""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    module_name TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    success INTEGER DEFAULT 1,
                    duration_ms REAL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls(tool_name);
                CREATE INDEX IF NOT EXISTS idx_tool_calls_module_name ON tool_calls(module_name);
                CREATE INDEX IF NOT EXISTS idx_tool_calls_timestamp ON tool_calls(timestamp);
            """)
            conn.commit()
        finally:
            conn.close()

    def record_call(self, tool_name: str, module_name: str,
                   success: bool = True, duration_ms: float = 0):
        """记录一次工具调用"""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO tool_calls (tool_name, module_name, timestamp, success, duration_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (tool_name, module_name, time.time(), 1 if success else 0, duration_ms))
            conn.commit()
        except Exception as e:
            app_logger.warning(f"记录工具调用统计失败: {e}")
        finally:
            conn.close()

    def get_module_stats(self, hours: int = 24) -> list[dict]:
        """获取模块调用统计（排行榜）"""
        conn = self._get_conn()
        try:
            cutoff = time.time() - hours * 3600
            rows = conn.execute("""
                SELECT
                    module_name,
                    COUNT(*) as call_count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(duration_ms) as avg_duration_ms
                FROM tool_calls
                WHERE timestamp >= ?
                GROUP BY module_name
                ORDER BY call_count DESC
            """, (cutoff,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_tool_stats(self, hours: int = 24, limit: int = 50) -> list[dict]:
        """获取工具调用统计（排行榜）"""
        conn = self._get_conn()
        try:
            cutoff = time.time() - hours * 3600
            rows = conn.execute("""
                SELECT
                    tool_name,
                    module_name,
                    COUNT(*) as call_count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(duration_ms) as avg_duration_ms,
                    MAX(duration_ms) as max_duration_ms,
                    MIN(duration_ms) as min_duration_ms
                FROM tool_calls
                WHERE timestamp >= ?
                GROUP BY tool_name
                ORDER BY call_count DESC
                LIMIT ?
            """, (cutoff, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_overview_stats(self, hours: int = 24) -> dict:
        """获取概览统计"""
        conn = self._get_conn()
        try:
            cutoff = time.time() - hours * 3600

            # 总调用次数
            total_calls = conn.execute(
                "SELECT COUNT(*) as cnt FROM tool_calls WHERE timestamp >= ?",
                (cutoff,)
            ).fetchone()["cnt"]

            # 成功次数
            success_calls = conn.execute(
                "SELECT COUNT(*) as cnt FROM tool_calls WHERE timestamp >= ? AND success = 1",
                (cutoff,)
            ).fetchone()["cnt"]

            # 平均响应时间
            avg_duration = conn.execute(
                "SELECT AVG(duration_ms) as avg FROM tool_calls WHERE timestamp >= ?",
                (cutoff,)
            ).fetchone()["avg"] or 0

            # 活跃工具数
            active_tools = conn.execute(
                "SELECT COUNT(DISTINCT tool_name) as cnt FROM tool_calls WHERE timestamp >= ?",
                (cutoff,)
            ).fetchone()["cnt"]

            # 活跃模块数
            active_modules = conn.execute(
                "SELECT COUNT(DISTINCT module_name) as cnt FROM tool_calls WHERE timestamp >= ?",
                (cutoff,)
            ).fetchone()["cnt"]

            # 按小时统计（最近24小时）
            hourly_stats = []
            now = datetime.now()
            for i in range(24):
                hour_start = now - timedelta(hours=23-i)
                hour_start_ts = hour_start.replace(minute=0, second=0, microsecond=0).timestamp()
                hour_end_ts = hour_start_ts + 3600

                row = conn.execute("""
                    SELECT COUNT(*) as cnt FROM tool_calls
                    WHERE timestamp >= ? AND timestamp < ?
                """, (hour_start_ts, hour_end_ts)).fetchone()
                hourly_stats.append({
                    "hour": hour_start.strftime("%H:00"),
                    "count": row["cnt"]
                })

            # 今日统计
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            today_calls = conn.execute(
                "SELECT COUNT(*) as cnt FROM tool_calls WHERE timestamp >= ?",
                (today_start,)
            ).fetchone()["cnt"]

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
        finally:
            conn.close()

    def get_recent_calls(self, limit: int = 100) -> list[dict]:
        """获取最近的调用记录"""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT
                    tool_name,
                    module_name,
                    timestamp,
                    success,
                    duration_ms
                FROM tool_calls
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["timestamp_str"] = datetime.fromtimestamp(d["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                result.append(d)
            return result
        finally:
            conn.close()

    def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        conn = self._get_conn()
        try:
            cutoff = time.time() - days * 24 * 3600
            conn.execute("DELETE FROM tool_calls WHERE timestamp < ?", (cutoff,))
            conn.commit()
        finally:
            conn.close()


# 全局单例
stats_manager = StatsManager()