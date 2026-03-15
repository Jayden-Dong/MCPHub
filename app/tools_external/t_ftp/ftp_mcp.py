from fastmcp.tools.tool import Tool
from . import ftp_tool


def register_tools(mcp_instance):
    """注册所有工具到 MCP 实例"""
    tools = []

    # 上传文件工具
    tool = Tool.from_function(
        ftp_tool.upload_file,
        name="ftp_upload_file",
        description="通过 FTP 上传文件或目录到服务器。支持单文件和整个目录的上传，自动为用户创建专属存储目录。上传成功后返回文件路径、大小等详细信息。"
    )
    mcp_instance.add_tool(tool)
    tools.append("ftp_upload_file")

    # 下载文件工具
    tool = Tool.from_function(
        ftp_tool.download_file,
        name="ftp_download_file",
        description="从 FTP 服务器下载文件或目录到本地。下载单个文件直接保存，下载目录时自动打包为 zip 或 tar 格式。支持绝对路径和相对路径。"
    )
    mcp_instance.add_tool(tool)
    tools.append("ftp_download_file")

    # 创建目录工具
    tool = Tool.from_function(
        ftp_tool.create_directory,
        name="ftp_create_directory",
        description="在 FTP 服务器上创建目录。支持创建多级目录（父目录不存在时自动创建），支持绝对路径和相对于基础目录的相对路径。"
    )
    mcp_instance.add_tool(tool)
    tools.append("ftp_create_directory")

    # 移动文件工具
    tool = Tool.from_function(
        ftp_tool.move_file,
        name="ftp_move_file",
        description="在 FTP 服务器上移动文件到目标目录。支持绝对路径和相对路径，自动处理目标目录的创建。移动后验证文件是否存在于目标位置。"
    )
    mcp_instance.add_tool(tool)
    tools.append("ftp_move_file")

    return tools


def unregister_tools(mcp_instance):
    """从 MCP 移除所有工具"""
    tool_names = ["ftp_upload_file", "ftp_download_file", "ftp_create_directory", "ftp_move_file"]
    for name in tool_names:
        try:
            mcp_instance.remove_tool(name)
        except Exception:
            pass
