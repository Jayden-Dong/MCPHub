"""
分组管理 REST API
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from schemas.base import ApiResponse
from utils.dependencies import get_current_user

app_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/groups", tags=["分组管理"], dependencies=[Depends(get_current_user)])


def _get_group_manager():
    from mcp_service import group_manager
    return group_manager


# ======================== Request Models ========================

class CreateGroupRequest(BaseModel):
    name: str
    description: str = ""


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AddModuleRequest(BaseModel):
    module_name: str


class AddProxyRequest(BaseModel):
    server_id: int


# ======================== 分组 CRUD ========================

@router.get("")
async def list_groups():
    """获取所有分组列表"""
    gm = _get_group_manager()
    data = gm.get_all_groups()
    return ApiResponse.success(data=data, description="获取分组列表成功")


# ======================== 反向查询（必须在 /{group_id} 之前注册） ========================

@router.get("/by-module/{module_name:path}")
async def get_module_groups(module_name: str):
    """查看模块所属的所有分组"""
    gm = _get_group_manager()
    data = gm.get_module_groups(module_name)
    return ApiResponse.success(data=data, description="获取成功")


@router.get("/by-proxy/{server_id}")
async def get_proxy_groups(server_id: int):
    """查看代理服务器所属的所有分组"""
    gm = _get_group_manager()
    data = gm.get_proxy_groups(server_id)
    return ApiResponse.success(data=data, description="获取成功")


@router.get("/{group_id}")
async def get_group_detail(group_id: str):
    """获取单个分组详情"""
    gm = _get_group_manager()
    data = gm.get_group_detail(group_id)
    if data is None:
        return ApiResponse.error(description="分组不存在")
    return ApiResponse.success(data=data, description="获取成功")


@router.post("")
async def create_group(req: CreateGroupRequest):
    """创建分组"""
    gm = _get_group_manager()
    result = gm.create_group(name=req.name, description=req.description)
    if result["success"]:
        return ApiResponse.success(data=result.get("group"), description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.put("/{group_id}")
async def update_group(group_id: str, req: UpdateGroupRequest):
    """更新分组信息"""
    gm = _get_group_manager()
    result = gm.update_group(group_id=group_id, name=req.name, description=req.description)
    if result["success"]:
        return ApiResponse.success(data=result.get("group"), description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.delete("/{group_id}")
async def delete_group(group_id: str):
    """删除分组（默认组不可删）"""
    gm = _get_group_manager()
    result = gm.delete_group(group_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


# ======================== 成员管理 ========================

@router.get("/{group_id}/members")
async def get_group_members(group_id: str):
    """获取组内所有成员（模块 + 代理服务器）"""
    gm = _get_group_manager()
    data = gm.get_group_members(group_id)
    if data is None:
        return ApiResponse.error(description="分组不存在")
    return ApiResponse.success(data=data, description="获取成功")


@router.post("/{group_id}/modules")
async def add_module_to_group(group_id: str, req: AddModuleRequest):
    """将模块加入分组"""
    gm = _get_group_manager()
    result = gm.add_module_to_group(group_id, req.module_name)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.delete("/{group_id}/modules/{module_name:path}")
async def remove_module_from_group(group_id: str, module_name: str):
    """从分组中移除模块"""
    gm = _get_group_manager()
    result = gm.remove_module_from_group(group_id, module_name)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/{group_id}/proxies")
async def add_proxy_to_group(group_id: str, req: AddProxyRequest):
    """将代理服务器加入分组"""
    gm = _get_group_manager()
    result = gm.add_proxy_to_group(group_id, req.server_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.delete("/{group_id}/proxies/{server_id}")
async def remove_proxy_from_group(group_id: str, server_id: int):
    """从分组中移除代理服务器"""
    gm = _get_group_manager()
    result = gm.remove_proxy_from_group(group_id, server_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])
