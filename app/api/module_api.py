"""
模块管理 REST API
提供MCP模块的热加载、卸载、启用/禁用等管理接口
"""
import os
import shutil
import tempfile
import logging
import zipfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from schemas.base import ApiResponse
from utils.dependencies import get_current_user

app_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules", tags=["模块管理"], dependencies=[Depends(get_current_user)])


def _get_manager():
    """延迟获取module_manager实例，避免循环导入"""
    from mcp_service import module_manager
    return module_manager


class ModuleLoadRequest(BaseModel):
    module_name: str
    config: Optional[dict] = None
    is_external: bool = False


class ToolToggleRequest(BaseModel):
    tool_name: str


class ToolDescriptionRequest(BaseModel):
    tool_name: str
    description: str


class ModuleConfigRequest(BaseModel):
    config: dict


@router.get("")
async def list_modules():
    """获取所有已注册模块的列表及状态"""
    manager = _get_manager()
    modules = manager.get_all_modules()
    return ApiResponse.success(data=modules, description="获取模块列表成功")


@router.get("/scan")
async def scan_modules():
    """扫描可用但未加载的模块"""
    manager = _get_manager()
    available = manager.scan_available_modules()
    return ApiResponse.success(data=available, description="扫描完成")


@router.get("/{module_name:path}/detail")
async def get_module_detail(module_name: str):
    """获取单个模块的详细信息"""
    manager = _get_manager()
    info = manager.get_module(module_name)
    if info is None:
        return ApiResponse.error(description=f"模块 {module_name} 未找到")
    return ApiResponse.success(data=info, description="获取模块信息成功")


@router.post("/load")
async def load_module(req: ModuleLoadRequest):
    """加载一个模块"""
    manager = _get_manager()
    result = manager.load_module(req.module_name, req.config, req.is_external)
    if result["success"]:
        return ApiResponse.success(
            data=result.get("module_info"),
            description=result["message"]
        )
    return ApiResponse.error(description=result["message"])


@router.post("/{module_name:path}/unload")
async def unload_module(module_name: str):
    """卸载一个模块"""
    manager = _get_manager()
    result = manager.unload_module(module_name)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/{module_name:path}/reload")
async def reload_module(module_name: str):
    """重新加载一个模块"""
    manager = _get_manager()
    result = manager.reload_module(module_name)
    if result["success"]:
        return ApiResponse.success(
            data=result.get("module_info"),
            description=result["message"]
        )
    return ApiResponse.error(description=result["message"])


@router.post("/tool/enable")
async def enable_tool(req: ToolToggleRequest):
    """启用某个工具"""
    manager = _get_manager()
    result = manager.enable_tool(req.tool_name)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/tool/disable")
async def disable_tool(req: ToolToggleRequest):
    """禁用某个工具"""
    manager = _get_manager()
    result = manager.disable_tool(req.tool_name)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/tool/description")
async def update_tool_description(req: ToolDescriptionRequest):
    """更新工具描述"""
    manager = _get_manager()
    result = manager.update_tool_description(req.tool_name, req.description)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/{module_name:path}/config")
async def update_module_config(module_name: str, req: ModuleConfigRequest):
    """更新模块配置"""
    manager = _get_manager()
    result = manager.update_module_config(module_name, req.config)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/install")
async def install_module(file: UploadFile = File(...), force: bool = False):
    """上传zip包安装新模块"""
    manager = _get_manager()

    if not file.filename.endswith('.zip'):
        return ApiResponse.error(description="仅支持zip格式的模块包")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        result = manager.install_module(tmp_path, force=force)

        if result.get("exists"):
            return ApiResponse.error(
                description=result["message"],
                data={"exists": True, "module_name": result["module_name"]}
            )

        if result["success"]:
            return ApiResponse.success(
                data={"module_name": result.get("module_name"), "module_info": result.get("module_info")},
                description=result["message"]
            )
        return ApiResponse.error(description=result["message"])

    except Exception as e:
        app_logger.exception("模块安装接口异常")
        return ApiResponse.error(description=f"安装失败: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.delete("/{module_name:path}")
async def delete_module(module_name: str):
    """删除已安装的外部模块"""
    manager = _get_manager()
    result = manager.delete_module(module_name)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.get("/{module_name:path}/groups")
async def get_module_groups(module_name: str):
    """查看模块所属的所有分组"""
    from mcp_service import group_manager
    data = group_manager.get_module_groups(module_name)
    return ApiResponse.success(data=data, description="获取成功")


@router.get("/{module_name:path}/export")
async def export_module(module_name: str):
    """导出模块为zip包"""
    manager = _get_manager()

    # 获取模块信息
    module_info = manager.get_module(module_name)
    if module_info is None:
        return ApiResponse.error(description=f"模块 {module_name} 未找到")

    # 获取模块目录
    module_dir = manager._get_module_dir(module_name)
    if module_dir is None or not module_dir.exists():
        return ApiResponse.error(description=f"未找到模块目录: {module_name}")

    # 创建临时zip文件
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, f"{module_name.split('.')[0]}.zip")

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 遍历模块目录下的所有文件
            for root, dirs, files in os.walk(module_dir):
                # 排除 __pycache__ 目录
                dirs[:] = [d for d in dirs if d != '__pycache__']

                for file in files:
                    # 排除 .pyc 文件
                    if file.endswith('.pyc'):
                        continue

                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, module_dir.parent)
                    zf.write(file_path, arcname)

        # 返回文件下载响应
        return FileResponse(
            zip_path,
            media_type='application/zip',
            filename=f"{module_name.split('.')[0]}.zip"
        )
    except Exception as e:
        app_logger.exception("创建zip文件失败")
        # 清理临时文件
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        return ApiResponse.error(description=f"创建zip文件失败: {str(e)}")
