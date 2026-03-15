"""AutoGUI 配置模块
从 MCP 模块配置中直接读取配置，与 t_ftp 模块保持一致的配置获取方式。
"""
import logging
from pathlib import Path

import utils.com_utils
from config_py.config import settings

# 从 MCP 模块配置中获取 autogui_mcp 的配置
_config = utils.com_utils.get_module_config("autogui_mcp")

# API settings
DASHSCOPE_API_KEY: str = _config.get("llm_api_key", "")
DASHSCOPE_BASE_URL: str = _config.get("llm_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME: str = _config.get("model_name", "qwen3.5-plus")

# Agent settings
MAX_STEPS: int = int(_config.get("max_steps", 20))
SCREENSHOT_DELAY: float = float(_config.get("screenshot_delay", 1.0))
LLM_TEMPERATURE: float = float(_config.get("llm_temperature", 0.1))
LLM_MAX_TOKENS: int = int(_config.get("llm_max_tokens", 1024))

# Logging
LOG_LEVEL: str = settings.LOG_LEVEL

# 截图存储目录：复用 app 级别的 logs 目录
LOG_DIR = Path(settings.LOG_FILE).parent
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(name: str = "gui_agent") -> logging.Logger:
    """返回指定名称的 logger。
    文件输出由 app 级别根 logger（config_py/logger.py）统一处理，
    日志通过 propagation 自动写入 GeneralMCPTool/logs/。
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(console_handler)

    return logger
