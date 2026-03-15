# Prompt management module with hot reload support
import os
import logging
from pathlib import Path
import yaml
from config_py.config import settings

# 使用延迟导入避免循环依赖
def _get_logger():
    return logging.getLogger(__name__)


class PromptManager:
    def __init__(self, prompt_file: str = "./config/prompt.yaml"):
        """初始化提示管理器，支持热重载功能

        Args:
            prompt_file: 提示文件路径
        """
        self.prompt_file = prompt_file
        self.prompt_path = Path(prompt_file)
        self._prompts = {}
        self._last_modified = 0
        self._load_prompts()

    def _load_prompts(self) -> dict:
        """从 YAML 提示文件加载提示内容，支持热重载

        Args:
            force_reload: 是否强制重新加载，不检查文件修改时间

        Returns:
            提示内容字典
        """
        logger = _get_logger()

        # 检查文件是否存在
        if not self.prompt_path.exists():
            logger.warning(f"提示文件 {self.prompt_file} 不存在，使用空提示")
            return {}

        # 检查文件是否被修改（如果不是强制重载）
        if not self.prompts_is_changed():
            return self._prompts

        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if not isinstance(data, dict):
                    logger.warning(f"提示文件 {self.prompt_file} 格式应为字典，已返回空提示")
                    return {}

                # 更新修改时间和提示内容
                self._last_modified = os.path.getmtime(self.prompt_path)
                self._prompts = data
                return data
        except yaml.YAMLError as e:
            logger.error(f"提示文件 {self.prompt_file} YAML 格式错误: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"无法读取提示文件 {self.prompt_file}: {e}", exc_info=True)
            return {}

    def prompts_is_changed(self) -> bool:
        """获取prompt是否被修改了
        :return:
        """
        current_modified = os.path.getmtime(self.prompt_path)
        if current_modified <= self._last_modified:
            return False

        return True

    def get(self, key: str) -> str:
        """
        获取特定键的提示内容，支持热重载

        """

        self._load_prompts()

        return self._prompts.get(key, "")


# 创建全局实例，便于其他模块导入使用
prompt_manager = PromptManager(settings.MCP_PROMPT_FILE)
