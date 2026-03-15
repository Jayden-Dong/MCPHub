MODULE_INFO = {
    "display_name": "FTP 文件管理工具",
    "version": "1.0.0",
    "description": "提供 FTP 文件上传、下载、目录创建和文件移动等功能，支持用户隔离存储",
    "author": "系统管理员",
    "default_config": {
        "ftp_server": {
            "host": "localhost",
            "username": "ftp_user",
            "password": "",
            "base_dir": "/data"
        },
        "download_dir": "/tmp/ftp_downloads"
    }
}

# 运行时配置（由平台注入，勿手动修改）
_config: dict = {}

def init_config(config: dict):
    """平台加载模块时注入初始配置"""
    global _config
    _config = config.copy()

def update_config(config: dict):
    """用户在管理界面修改配置后平台回调此函数（热更新）"""
    global _config
    _config = config.copy()

def register(mcp_instance):
    """注册本模块的所有工具到 MCP"""
    from .ftp_mcp import register_tools
    return register_tools(mcp_instance)

def unregister(mcp_instance):
    """从 MCP 移除本模块的所有工具"""
    from .ftp_mcp import unregister_tools
    unregister_tools(mcp_instance)
