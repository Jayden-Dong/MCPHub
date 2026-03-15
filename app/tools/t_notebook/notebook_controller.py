import logging
from typing import Optional

from schemas.base import ApiResponse
from tools.t_notebook.notebook_tool import notebook_tool
from fastapi import APIRouter, Form, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notebook")

@router.post("/v1/add_note")
async def add_note(
    notebook_name: str = Form(..., description="笔记本名称"),
    note_content: Optional[str] = Form(None, description="笔记内容")):
    try:

        result = notebook_tool.add_note(note_content, notebook_name)

        if result['success']:
            return ApiResponse.success(description="添加笔记成功.")

        return ApiResponse.error(description=f'添加笔记失败，原因：{result["err_msg"]}')

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"添加笔记失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/read_note")
async def read_note(
    notebook_name: str = Form(..., description="笔记本名称")):
    try:

        result = notebook_tool.read_note(notebook_name)

        if result['success']:
            return ApiResponse.success(description="读取笔记成功.", data=result['note_content'])

        return ApiResponse.error(description=f'读取笔记失败，原因：{result["err_msg"]}')

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"读取笔记失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))