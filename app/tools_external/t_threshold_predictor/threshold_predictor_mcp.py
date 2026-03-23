from fastmcp.tools.tool import Tool
from . import threshold_predictor_tool


def register_tools(mcp_instance):
    """注册所有工具到 MCP 实例"""
    tools = []

    # UDB 预测工具
    tool = Tool.from_function(
        threshold_predictor_tool.predict_udb,
        name="predict_udb",
        description="UDB 预测便捷函数 - 根据观测数据 (阈值、纯度、体积、目标纯度) 预测收集阈值"
    )
    mcp_instance.add_tool(tool)
    tools.append("predict_udb")

    # AtoPlex 预测工具
    tool = Tool.from_function(
        threshold_predictor_tool.predict_atoplex,
        name="predict_atoplex",
        description="AtoPlex 预测便捷函数 - 根据碱基序列和纯化方法预测收集阈值"
    )
    mcp_instance.add_tool(tool)
    tools.append("predict_atoplex")

    # Degenerate 预测工具
    tool = Tool.from_function(
        threshold_predictor_tool.predict_degenerate,
        name="predict_degenerate",
        description="Degenerate 预测便捷函数 - 根据碱基序列、纯化方法、进样体积预测收集阈值"
    )
    mcp_instance.add_tool(tool)
    tools.append("predict_degenerate")

    return tools


def unregister_tools(mcp_instance):
    """从 MCP 移除所有工具"""
    tool_names = ["predict_udb", "predict_atoplex", "predict_degenerate"]
    for name in tool_names:
        try:
            mcp_instance.remove_tool(name)
        except Exception:
            pass
