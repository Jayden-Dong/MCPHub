import time

from config_py.config import settings
from mcp_service import mcp
from utils import com_utils

sleep_str = "sleep"
@mcp.tool(name=f'{settings.MCP_TOOL_NAME_PREFIX}{sleep_str}',
          enabled=com_utils.get_tool_enable(sleep_str))
def sleep(space: float):
    """
        等待指定时长。可以实现间隔轮询、等待等任务。

        Args:
            space:  等待的时长，小于 60，单位：秒。 

    """

    if space > 60:
        raise ValueError("space must be less than 60")

    time.sleep(space)
