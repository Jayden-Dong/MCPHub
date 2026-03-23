import asyncio
import logging
from typing import Optional

from schemas.base import ApiResponse

from tools_external.t_liquid_chromatograph.liquid_chromatograph_tool import liquid_chromatograph_tool
from fastapi import APIRouter, Form, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/liquid_chromatograph")


@router.post("/v1/set_threshold")
async def api_set_threshold(
    protocol_name: str = Form(..., description="脚本名称"),
    threshold: float = Form(..., description="收集阈值")):
    """
    设置收集阈值接口
    """
    try:
        success, message, data = await asyncio.to_thread(liquid_chromatograph_tool.set_threshold, protocol_name, threshold)

        if success:
            return ApiResponse.success(
                description="阈值设置成功",
                data={"protocol_name": protocol_name, "threshold": threshold}
            )

        return ApiResponse.error(description=f"阈值设置失败，原因：{message}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"设置阈值失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/start_collect_protocol")
async def api_start_collect_protocol(
    protocol_name: str = Form(..., description="脚本名称"),
    result_file: str = Form(..., description="结果文件路径")):
    """
    启动收集馏分脚本接口
    """
    try:
        success, message, data = await asyncio.to_thread(liquid_chromatograph_tool.start_collect_protocol, protocol_name, result_file)

        if success:
            return ApiResponse.success(
                description="收集脚本启动成功",
                data={"protocol_name": protocol_name, "result_file": result_file}
            )

        return ApiResponse.error(description=f"收集脚本启动失败，原因：{message}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"启动收集脚本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/start_analyse_protocol")
async def api_start_analyse_protocol(
    protocol_name: str = Form(..., description="脚本名称"),
    result_file: str = Form(..., description="结果文件路径")):
    """
    启动分析馏分脚本接口
    """
    try:
        success, message, data = await asyncio.to_thread(liquid_chromatograph_tool.start_analyse_protocol, protocol_name, result_file)

        if success:
            return ApiResponse.success(
                description="分析脚本启动成功",
                data={"protocol_name": protocol_name, "result_file": result_file}
            )

        return ApiResponse.error(description=f"分析脚本启动失败，原因：{message}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"启动分析脚本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/get_protocol_status")
async def api_get_protocol_status():
    """
    获取脚本执行状态接口
    """
    try:
        status, message, data = await asyncio.to_thread(liquid_chromatograph_tool.get_protocol_status)

        return ApiResponse.success(
            description="获取状态成功",
            data={
                "status": "finished" if status is True else ("failed" if status is False else "running"),
                "message": message,
                "data": data
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/get_purity")
async def api_get_purity(
    result_file: str = Form(..., description="结果文件路径")):
    """
    获取纯度接口
    """
    try:
        success, message, data = await asyncio.to_thread(liquid_chromatograph_tool.get_purity, result_file)

        if success:
            return ApiResponse.success(
                description="获取纯度成功",
                data={"purity": data['user_data']["purity"]}
            )

        return ApiResponse.error(description=f"获取纯度失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取纯度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))