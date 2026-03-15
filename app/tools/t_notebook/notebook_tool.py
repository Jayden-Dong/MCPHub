"""
笔记工具模块
提供笔记的添加、读取等操作功能
"""
import os
import time
import threading
from typing import Dict

import utils.com_utils
from config_py.config import settings
from config_py.logger import app_logger


class NotebookTool:
    """笔记工具类"""
    
    def __init__(self):
        """初始化笔记工具"""
        # 创建全局锁用于保护文件写入操作
        self.note_file_lock = threading.Lock()

        config = utils.com_utils.get_module_config("notebook_mcp")
        self.note_dir = config["note_dir"]
    
    def add_note(self, note: str, note_file_name: str) -> Dict:
        """
        将笔记添加到指定文件中。

        Args:
            note: 要添加的笔记内容。
            note_file_name: 笔记文件名称。

        Returns:
            包含添加结果信息的字典
        """
        try:
            # 确保笔记目录存在
            os.makedirs(self.note_dir, exist_ok=True)
            note_file = os.path.join(self.note_dir, note_file_name)

            # 使用锁保护文件写入操作，确保线程安全
            with self.note_file_lock:
                with open(note_file, "a", encoding="utf-8") as f:
                    f.write(f"--------\n记录时间：{time.strftime('%Y-%m-%d %H:%M:%S')}: \n{note}\n\n")
            
            app_logger.info(f"成功添加笔记到文件: {note_file_name}")
            return {
                "success": True,
                "err_msg": ""
            }
        except Exception as e:
            error_msg = f"添加笔记失败: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "err_msg": str(e)
            }
    
    def read_note(self, note_file_name: str) -> Dict:
        """
        读取指定文件中的笔记。

        Args:
            note_file_name: 笔记文件名称。

        Returns:
            包含读取结果信息的字典
        """
        try:
            note_file = os.path.join(self.note_dir, note_file_name)
            
            # 使用锁保护文件读取操作，确保获取完整一致的数据
            with self.note_file_lock:
                with open(note_file, "r", encoding="utf-8") as f:
                    notes = f.read()
            
            app_logger.info(f"成功读取笔记文件: {note_file_name}")
            return {
                "success": True,
                "note_content": notes,
                "err_msg": ""
            }
        except FileNotFoundError:
            app_logger.info(f"笔记文件不存在: {note_file_name}")
            return {
                "success": True, # 不代表错误，只代表笔记是空的
                "note_content": "",
                "err_msg": ""
            }
        except Exception as e:
            error_msg = f"读取笔记失败: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "note_content": "",
                "err_msg": str(e)
            }


# 创建单例实例
notebook_tool = NotebookTool()