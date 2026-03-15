"""
统计数据 REST API
提供MCP工具调用统计查询接口
"""
import logging
from fastapi import APIRouter, Query, Depends
from schemas.base import ApiResponse
from utils.dependencies import get_current_user

app_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["统计数据"], dependencies=[Depends(get_current_user)])


def _get_stats_manager():
    """延迟获取stats_manager实例"""
    from managers.stats_manager import stats_manager
    return stats_manager


def _get_module_manager():
    """延迟获取module_manager实例"""
    from mcp_service import module_manager
    return module_manager


@router.get("/overview")
async def get_overview(hours: int = Query(default=24, ge=1, le=168)):
    """获取概览统计数据"""
    try:
        stats = _get_stats_manager()
        data = stats.get_overview_stats(hours)

        # 补充模块总数信息
        mm = _get_module_manager()
        modules = mm.get_all_modules()
        data["total_modules"] = len(modules)
        data["loaded_modules"] = sum(1 for m in modules if m.get("loaded"))

        return ApiResponse.success(data=data, description="获取概览统计成功")
    except Exception as e:
        app_logger.exception("获取概览统计失败")
        return ApiResponse.error(description=f"获取概览统计失败: {str(e)}")


@router.get("/modules")
async def get_module_stats(hours: int = Query(default=24, ge=1, le=168)):
    """获取模块调用排行榜"""
    try:
        stats = _get_stats_manager()
        data = stats.get_module_stats(hours)
        return ApiResponse.success(data=data, description="获取模块统计成功")
    except Exception as e:
        app_logger.exception("获取模块统计失败")
        return ApiResponse.error(description=f"获取模块统计失败: {str(e)}")


@router.get("/tools")
async def get_tool_stats(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200)
):
    """获取工具调用排行榜"""
    try:
        stats = _get_stats_manager()
        data = stats.get_tool_stats(hours, limit)
        return ApiResponse.success(data=data, description="获取工具统计成功")
    except Exception as e:
        app_logger.exception("获取工具统计失败")
        return ApiResponse.error(description=f"获取工具统计失败: {str(e)}")


@router.get("/recent")
async def get_recent_calls(limit: int = Query(default=100, ge=1, le=500)):
    """获取最近的调用记录"""
    try:
        stats = _get_stats_manager()
        data = stats.get_recent_calls(limit)
        return ApiResponse.success(data=data, description="获取最近调用记录成功")
    except Exception as e:
        app_logger.exception("获取最近调用记录失败")
        return ApiResponse.error(description=f"获取最近调用记录失败: {str(e)}")