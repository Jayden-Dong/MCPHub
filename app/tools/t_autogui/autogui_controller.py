"""
GUI自动化工具的HTTP Controller
提供GUI自动化任务的REST API接口
"""
import logging

from fastapi import APIRouter, Form, HTTPException

from schemas.base import ApiResponse
from tools.t_autogui.autogui_tool import autogui_tool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/autogui")


@router.post("/v1/start_task")
async def start_task(
        task: str = Form(..., description="自然语言描述的GUI自动化任务")):
    try:
        result = autogui_tool.start_task(task)

        if result['success']:
            return ApiResponse.success(description="任务已启动，在后台异步运行。")

        return ApiResponse.error(description=f'启动失败：{result["err_msg"]}')

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"启动GUI自动化任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/get_status")
async def get_status():
    try:
        result = autogui_tool.get_status()

        if result['success']:
            return ApiResponse.success(description="获取状态成功。", data=result['data'])

        return ApiResponse.error(description=f'获取状态失败：{result["err_msg"]}')

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取GUI任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/get_history")
async def get_history():
    try:
        result = autogui_tool.get_history()

        if result['success']:
            return ApiResponse.success(description="获取历史成功。", data=result['data'])

        return ApiResponse.error(description=f'获取历史失败：{result["err_msg"]}')

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取GUI任务历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/stop_task")
async def stop_task():
    try:
        result = autogui_tool.stop_task()

        if result['success']:
            return ApiResponse.success(description="任务已停止。")

        return ApiResponse.error(description=f'停止失败：{result["err_msg"]}')

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"停止GUI自动化任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
