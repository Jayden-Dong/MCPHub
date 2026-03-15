"""
配置管理模块
支持从配置文件读取配置信息
"""
import json
import logging
from pathlib import Path

# 使用延迟导入避免循环依赖，获取logger实例
def _get_logger():
    return logging.getLogger(__name__)


class Settings:
    def __init__(self, config_file):
        """初始化配置，从配置文件读取设置"""
        self.config_file = config_file
        self.config_data = self._load_config()

        # API Settings
        self.API_TITLE = self.config_data.get("api", {}).get("title", "Bio Tools Service")
        self.API_VERSION = self.config_data.get("api", {}).get("version", "1.0.0")
        self.API_DESCRIPTION = self.config_data.get("api", {}).get("description", "A service for anything")

        # Server Settings
        self.HOST = self.config_data.get("server", {}).get("host", "0.0.0.0")
        self.PORT = int(self.config_data.get("server", {}).get("port", 8000))
        self.SERVER_WHITE_LIST = self.config_data.get("server", {}).get("white_list", [])

        # MCP服务配置
        mcp_config = self.config_data.get("mcp", {})
        self.MCP_SERVICE_NAME: str = mcp_config.get('service_name', '')
        self.MCP_HOST = mcp_config.get("host", "0.0.0.0")
        self.MCP_PORT = int(mcp_config.get("port"))
        self.MCP_PATH = mcp_config.get("path", "/mcp")
        self.MCP_WHITE_LIST = mcp_config.get("white_list", [])
        self.MCP_PROMPT_FILE = mcp_config.get("prompt_file", "./config/prompt.yaml")
        self.MCP_TOOL_NAME_PREFIX = mcp_config.get("tool_name_prefix", "")
        self.MCP_ENABLE_MODULE = mcp_config.get("module_enable", [])

        # 日志配置
        self.LOG_LEVEL: str = self.config_data.get('log', {}).get('level', 'INFO')
        self.LOG_FORMAT: str = self.config_data.get('log', {}).get('format', '')
        # 日志文件前缀，如果配置文件中不存在则使用默认值
        self.LOG_FILE: str = self.config_data.get('log', {}).get('file', 'log')
        # 日志保留天数，如果配置文件中不存在则使用默认值
        self.LOG_BACKUP_COUNT: int = self.config_data.get('log', {}).get('backup_count', 30)

        # MCP Logging Settings
        self.MCP_LOG_LEVEL = self.config_data.get("mcp_log", {}).get("level", "INFO")
        self.MCP_LOG_FILE = self.config_data.get("mcp_log", {}).get("file", "mcp.log")
        self.MCP_LOG_BACKUP_COUNT = int(self.config_data.get("mcp_log", {}).get("backup_count", 30))

        # Database Settings
        self.DB_PATH = self.config_data.get("database", {}).get("db_path", "./config/mcp_hub.db")

        # Auth Settings
        auth_config = self.config_data.get("auth", {})
        self.AUTH_SECRET_KEY = auth_config.get("secret_key", "default-secret-key-please-change")
        self.AUTH_TOKEN_EXPIRE_HOURS = int(auth_config.get("token_expire_hours", 24))
        self.AUTH_ALGORITHM = auth_config.get("algorithm", "HS256")

        

    def _get_module_config(self, module_name_postfix: str) -> dict:
        """从 MCP_ENABLE_MODULE 中按模块名后缀查找 config 块"""
        for module in self.config_data.get("mcp", {}).get("module_enable", []):
            if module.get("module_name", "").endswith(module_name_postfix):
                return module.get("config", {})
        return {}

    def _load_config(self) -> dict:
        """从配置文件加载配置"""
        logger = _get_logger()
        config_path = Path(self.config_file)

        if not config_path.exists():
            logger.warning(f"配置文件 {self.config_file} 不存在，使用默认配置")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"配置文件 {self.config_file} JSON 格式错误: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"无法读取配置文件 {self.config_file}: {e}", exc_info=True)
            return {}

    def reload_config(self):
        """重新加载配置文件"""
        self.config_data = self._load_config()
        # 重新设置所有配置项
        self.__init__(self.config_file)


settings = Settings("./config/config.json")
