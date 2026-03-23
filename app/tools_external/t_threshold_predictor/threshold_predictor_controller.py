import logging
from typing import Optional

from schemas.base import ApiResponse
from tools_external.t_threshold_predictor.threshold_predictor_tool import (
    predict_udb,
    predict_atoplex,
    predict_degenerate
)
from fastapi import APIRouter, Form, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threshold_predictor")


@router.post("/v1/predict_udb")
async def api_predict_udb(
    seq: str = Form(..., description="碱基序列（5'→3'，仅含 A/T/G/C）"),
    obs_threshold: float = Form(..., description="当前已知的收集阈值（uV）"),
    obs_purity: float = Form(..., description="在该阈值下测得的 QC 纯度（%）"),
    obs_volume: int = Form(..., description="在该阈值下的馏分体积（0 或 1）"),
    desired_purity: float = Form(..., description="要求达到的目标纯度（%）")):
    """
    UDB 预测接口 - 根据观测数据 (阈值、纯度、体积、目标纯度) 预测收集阈值
    """
    try:
        result = predict_udb(
            seq=seq,
            obs_threshold=obs_threshold,
            obs_purity=obs_purity,
            obs_volume=obs_volume,
            desired_purity=desired_purity
        )

        if result['success']:
            return ApiResponse.success(
                description="UDB 预测成功",
                data={
                    "raw_prediction": result['raw_prediction'],
                    "rounded_prediction": result['rounded_prediction'],
                    "unit": result['unit']
                }
            )

        return ApiResponse.error(description=f"UDB 预测失败，原因：{result.get('error', '未知错误')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"UDB 预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/predict_atoplex")
async def api_predict_atoplex(
    sequence: str = Form(..., description="碱基序列"),
    purification_method: str = Form(..., description="纯化方法（序号/别名/简称/完整名称），支持：1/普通/v0.1=短链纯化 -12min-1cm-V0.1, 2/兼并 1/v0.1-兼并=短链纯化 -19min-1cm-V0.1-兼并，3/兼并 2/v0.2-兼并=短链纯化 -19min-1cm-V0.2-兼并")):
    """
    AtoPlex 预测接口 - 根据碱基序列和纯化方法预测收集阈值
    """
    try:
        result = predict_atoplex(
            sequence=sequence,
            purification_method=purification_method
        )

        if result['success']:
            return ApiResponse.success(
                description="AtoPlex 预测成功",
                data={
                    "prediction": result['prediction'],
                    "unit": result['unit']
                }
            )

        return ApiResponse.error(description=f"AtoPlex 预测失败，原因：{result.get('error', '未知错误')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"AtoPlex 预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/predict_degenerate")
async def api_predict_degenerate(
    sequence: str = Form(..., description="碱基序列"),
    purification_method: str = Form(..., description="纯化方法（数字或名称），支持：1=短链纯化 -16min-1cm-V0.1, 2=短链纯化 -16min-1cm-V0.2"),
    injection_volume: Optional[float] = Form(None, description="进样体积（可选，默认 260）")):
    """
    Degenerate 预测接口 - 根据碱基序列、纯化方法、进样体积预测收集阈值
    """
    try:
        result = predict_degenerate(
            sequence=sequence,
            purification_method=purification_method,
            injection_volume=injection_volume
        )

        if result['success']:
            return ApiResponse.success(
                description="Degenerate 预测成功",
                data={
                    "prediction": result['prediction'],
                    "unit": result['unit']
                }
            )

        return ApiResponse.error(description=f"Degenerate 预测失败，原因：{result.get('error', '未知错误')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Degenerate 预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))