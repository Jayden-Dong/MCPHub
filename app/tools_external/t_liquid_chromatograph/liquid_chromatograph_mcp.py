from fastmcp.tools.tool import Tool
from tools_external.t_liquid_chromatograph.liquid_chromatograph_tool import liquid_chromatograph_tool


def register_tools(mcp_instance):
    """注册所有工具到 MCP 实例"""
    tools = []

    # 设置收集阈值工具
    tool = Tool.from_function(
        liquid_chromatograph_tool.set_threshold,
        name="set_threshold",
        description="设置色谱收集阈值 - 根据脚本名称设置收集阈值"
    )
    mcp_instance.add_tool(tool)
    tools.append("set_threshold")

    # 启动收集馏分脚本工具
    tool = Tool.from_function(
        liquid_chromatograph_tool.start_collect_protocol,
        name="start_collect_protocol",
        description="运行收集馏分的脚本 - 启动色谱收集程序"
    )
    mcp_instance.add_tool(tool)
    tools.append("start_collect_protocol")

    # 启动分析馏分脚本工具
    tool = Tool.from_function(
        liquid_chromatograph_tool.start_analyse_protocol,
        name="start_analyse_protocol",
        description="运行分析馏分的脚本 - 启动色谱分析程序"
    )
    mcp_instance.add_tool(tool)
    tools.append("start_analyse_protocol")

    # 获取脚本执行状态工具
    tool = Tool.from_function(
        liquid_chromatograph_tool.get_protocol_status,
        name="get_protocol_status",
        description="获取脚本执行状态 - 查询当前色谱程序的运行状态"
    )
    mcp_instance.add_tool(tool)
    tools.append("get_protocol_status")

    # 获取纯度工具
    tool = Tool.from_function(
        liquid_chromatograph_tool.get_purity,
        name="get_purity",
        description="获取纯度 - 从结果文件中读取纯度数据"
    )
    mcp_instance.add_tool(tool)
    tools.append("get_purity")

    return tools


def unregister_tools(mcp_instance):
    """从 MCP 移除所有工具"""
    tool_names = ["set_threshold", "start_collect_protocol", "start_analyse_protocol", "get_protocol_status", "get_purity"]
    for name in tool_names:
        try:
            mcp_instance.remove_tool(name)
        except Exception:
            pass