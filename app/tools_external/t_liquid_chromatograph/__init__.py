MODULE_INFO = {
    "display_name": "液相色谱控制模块",
    "version": "1.0.0",
    "description": "液相色谱自动化控制：设置收集阈值、启动收集/分析脚本、获取执行状态、获取纯度",
    "author": "系统",
    "default_config": {
        "autogui_base_url": ""
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
    from .liquid_chromatograph_mcp import register_tools
    return register_tools(mcp_instance)

def unregister(mcp_instance):
    """从 MCP 移除本模块的所有工具"""
    from .liquid_chromatograph_mcp import unregister_tools
    unregister_tools(mcp_instance)