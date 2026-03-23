"""
通用工具MCP服务
提供各种类型的工具功能，包括FTP文件上传、下载等
"""

import argparse
import importlib
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config_py.config import settings
from config_py.logger import app_logger
from mcp_service import start_mcp_server


# 创建 FastAPI 应用
fastapi_app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# 添加CORS中间件，允许前端跨域访问
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def import_webapi_router():
    # 导入 api 目录下的固定路由
    from api import module_api, codegen_api, stats_api, proxy_api, auth_api, group_api
    fastapi_app.include_router(auth_api.router)  # 认证路由不需要保护
    fastapi_app.include_router(module_api.router)
    fastapi_app.include_router(codegen_api.router)
    fastapi_app.include_router(stats_api.router)
    fastapi_app.include_router(proxy_api.router)
    fastapi_app.include_router(group_api.router)

    # 动态扫描 tools 和 tools_external 目录下 t_* 子目录中的 *_controller.py
    base_dir = Path(__file__).parent
    scan_dirs = [
        (base_dir / "tools", "tools"),
        (base_dir / "tools_external", "tools_external"),
    ]
    for scan_path, package_prefix in scan_dirs:
        if not scan_path.exists():
            continue
        for tool_dir in sorted(scan_path.iterdir()):
            if not tool_dir.is_dir() or not tool_dir.name.startswith("t_"):
                continue
            for controller_file in tool_dir.glob("*_controller.py"):
                module_name = f"{package_prefix}.{tool_dir.name}.{controller_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, "router"):
                        fastapi_app.include_router(module.router)
                        app_logger.info(f"已加载路由: {module_name}")
                except Exception as e:
                    app_logger.warning(f"加载路由失败 {module_name}: {e}")


def mount_static_files():
    """挂载Vue3前端静态文件"""
    static_dir = Path("./web/dist")
    if static_dir.exists():
        fastapi_app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="web")
        app_logger.info(f"前端静态文件已挂载: {static_dir.resolve()}")
    else:
        app_logger.warning(f"前端目录不存在: {static_dir.resolve()}，跳过静态文件挂载")


@fastapi_app.get("/api/ping")
async def ping():
    return {"status": "ok"}


@fastapi_app.on_event("startup")
async def _start_mcp():
    start_mcp_server(host=settings.MCP_HOST, port=settings.MCP_PORT, path=settings.MCP_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="General Tools Service")
    parser.add_argument("--web-port", type=int, default=None, help=f"Web服务端口 (默认: {settings.PORT})")
    parser.add_argument("--mcp-port", type=int, default=None, help=f"MCP服务端口 (默认: {settings.MCP_PORT})")
    args = parser.parse_args()

    if args.web_port is not None:
        settings.PORT = args.web_port
    if args.mcp_port is not None:
        settings.MCP_PORT = args.mcp_port

    app_logger.info("=" * 50)
    app_logger.info("启动 general tools Service")
    app_logger.info(f"服务地址: http://{settings.HOST}:{settings.PORT}")
    app_logger.info(f"API 文档: http://{settings.HOST}:{settings.PORT}/docs")
    app_logger.info(f"MCP 服务: http://{settings.MCP_HOST}:{settings.MCP_PORT}{settings.MCP_PATH}")
    app_logger.info("=" * 50)

    import_webapi_router()

    # 静态文件挂载必须放在最后（因为使用了 "/" 路径）
    mount_static_files()

    uvicorn.run(fastapi_app, host=settings.HOST, port=settings.PORT)
