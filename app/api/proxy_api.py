"""
第三方 MCP Server 代理管理 REST API
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from schemas.base import ApiResponse
from utils.dependencies import get_current_user

app_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proxy", tags=["代理服务器管理"], dependencies=[Depends(get_current_user)])


def _get_proxy_manager():
    from mcp_service import proxy_manager
    return proxy_manager


# ======================== Request Models ========================

class AddServerRequest(BaseModel):
    name: str
    url: str
    transport: str = "streamable-http"
    description: str = ""
    headers: Optional[dict] = None
    timeout: int = 60


class UpdateServerRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    transport: Optional[str] = None
    description: Optional[str] = None
    headers: Optional[dict] = None
    timeout: Optional[int] = None


class ToolDescriptionRequest(BaseModel):
    description: str


# ======================== Server CRUD ========================

@router.get("/servers")
async def list_servers():
    """获取所有代理服务器列表"""
    pm = _get_proxy_manager()
    data = pm.get_all_servers()
    return ApiResponse.success(data=data, description="获取代理服务器列表成功")


@router.get("/servers/{server_id}")
async def get_server_detail(server_id: int):
    """获取单个代理服务器详情（含工具列表）"""
    pm = _get_proxy_manager()
    data = pm.get_server_detail(server_id)
    if data is None:
        return ApiResponse.error(description=f"服务器 {server_id} 不存在")
    return ApiResponse.success(data=data, description="获取成功")


@router.post("/servers")
async def add_server(req: AddServerRequest):
    """添加代理服务器"""
    pm = _get_proxy_manager()
    result = pm.add_server(
        name=req.name, url=req.url, transport=req.transport,
        description=req.description, headers=req.headers, timeout=req.timeout
    )
    if result["success"]:
        return ApiResponse.success(
            data={"server_id": result.get("server_id")},
            description=result["message"]
        )
    return ApiResponse.error(description=result["message"])


@router.put("/servers/{server_id}")
async def update_server(server_id: int, req: UpdateServerRequest):
    """更新代理服务器配置"""
    pm = _get_proxy_manager()
    result = pm.update_server(
        server_id=server_id, name=req.name, url=req.url,
        transport=req.transport, description=req.description,
        headers=req.headers, timeout=req.timeout
    )
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.delete("/servers/{server_id}")
async def delete_server(server_id: int):
    """删除代理服务器"""
    pm = _get_proxy_manager()
    result = pm.delete_server(server_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.get("/servers/{server_id}/groups")
async def get_proxy_groups(server_id: int):
    """查看代理服务器所属的所有分组"""
    from mcp_service import group_manager
    data = group_manager.get_proxy_groups(server_id)
    return ApiResponse.success(data=data, description="获取成功")


# ======================== Sync & Enable/Disable ========================

@router.post("/servers/{server_id}/sync")
async def sync_server(server_id: int):
    """连接远端服务器并同步工具列表"""
    pm = _get_proxy_manager()
    result = await pm.sync_server(server_id)
    if result["success"]:
        return ApiResponse.success(
            data={"tool_count": result.get("tool_count"), "new_count": result.get("new_count")},
            description=result["message"]
        )
    return ApiResponse.error(description=result["message"])


@router.post("/servers/{server_id}/force-sync")
async def force_sync_server(server_id: int):
    """覆盖同步：删除所有已有工具后重新从远端拉取（不保留用户配置）"""
    pm = _get_proxy_manager()
    result = await pm.force_sync_server(server_id)
    if result["success"]:
        return ApiResponse.success(
            data={"tool_count": result.get("tool_count")},
            description=result["message"]
        )
    return ApiResponse.error(description=result["message"])


@router.post("/servers/{server_id}/enable")
async def enable_server(server_id: int):
    """启用代理服务器（将其工具注册到 FastMCP）"""
    pm = _get_proxy_manager()
    result = pm.enable_server(server_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/servers/{server_id}/disable")
async def disable_server(server_id: int):
    """禁用代理服务器（从 FastMCP 注销其工具）"""
    pm = _get_proxy_manager()
    result = pm.disable_server(server_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


# ======================== Tool Operations ========================

@router.post("/tools/{tool_id}/enable")
async def enable_tool(tool_id: int):
    """启用单个代理工具"""
    pm = _get_proxy_manager()
    result = pm.enable_tool(tool_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/tools/{tool_id}/disable")
async def disable_tool(tool_id: int):
    """禁用单个代理工具"""
    pm = _get_proxy_manager()
    result = pm.disable_tool(tool_id)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])


@router.post("/tools/{tool_id}/description")
async def update_tool_description(tool_id: int, req: ToolDescriptionRequest):
    """更新代理工具描述"""
    pm = _get_proxy_manager()
    result = pm.update_tool_description(tool_id, req.description)
    if result["success"]:
        return ApiResponse.success(description=result["message"])
    return ApiResponse.error(description=result["message"])
