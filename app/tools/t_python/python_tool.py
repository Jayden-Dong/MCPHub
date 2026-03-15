"""
Python工具模块
提供Python脚本相关操作功能
"""
import os
import uuid
import threading
from typing import Dict
import time

import utils.com_utils
from config_py.config import settings
from config_py.logger import app_logger
import subprocess
import sys

def _read_stream_to_dict(stream, storage_dict: dict, key: str) -> None:
    """
    在后台线程中持续读取流内容，防止管道缓冲区满导致子进程阻塞。
    当子进程输出超过管道缓冲（约64KB）时，若不持续读取，子进程会阻塞在write上，
    导致 poll() 一直返回 None，状态错误地显示为 running。
    """
    try:
        if stream:
            content = stream.read()
            storage_dict[key] = content
    except Exception as e:
        app_logger.debug(f"读取流内容失败 (key={key}): {e}")
    finally:
        if stream:
            try:
                stream.close()
            except Exception as e:
                app_logger.debug(f"关闭流失败 (key={key}): {e}")


class PythonTool:
    """Python工具类"""
    
    def __init__(self):
        """初始化Python工具"""
        # 存储正在执行的脚本状态信息
        self._running_scripts = {}

        config = utils.com_utils.get_module_config("python_mcp")
        self.python_script_dir = config['python_script_dir']

    def save_python_script(self, file_name:str, script_content: str) -> Dict[str, any]:
        """
        以UTF-8编码保存Python脚本内容
        
        Args:
            file_name: 保存文件的名称，不包含路径
            script_content: Python脚本内容
        
        Returns:
            包含保存结果信息的字典：
                - success: 是否保存成功
                - path: 保存成功的脚本绝对路径（使用/分隔符）
                - error: 错误信息（成功时为None）
        """
        # 参数验证
        file_path = f'{self.python_script_dir}/{file_name}'
        if not isinstance(file_path, str) or not file_path.strip():
            error_msg = "文件路径必须是非空字符串"
            app_logger.error(error_msg)
            return {
                "success": False,
                "path": None,
                "error": error_msg
            }
        
        if not isinstance(script_content, str):
            error_msg = "脚本内容必须是字符串类型"
            app_logger.error(error_msg)
            return {
                "success": False,
                "path": None,
                "error": error_msg
            }
        
        try:
            # 确保父目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 以UTF-8编码写入文件
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(script_content)
            
            # 获取绝对路径并将\替换为/
            abs_path = os.path.abspath(file_path).replace('\\', '/')
            
            app_logger.info(f"成功保存Python脚本到: {abs_path}")
            return {
                "success": True,
                "path": abs_path,
                "error": None
            }
        except PermissionError:
            error_msg = f"没有权限写入文件: {file_path}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "path": None,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"保存Python脚本时出错: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "path": None,
                "error": error_msg
            }

    def run_python_script(self, file_path:str) -> Dict[str, any]:
        """
        运行指定的Python脚本
        
        Args:
            file_path: 要运行的Python脚本路径
        
        Returns:
            包含运行结果信息的字典：
                - success: 是否运行成功
                - output: 脚本输出（成功时为None）
                - error: 错误信息（成功时为None）
        """
        # 参数验证
        if not isinstance(file_path, str) or not file_path.strip():
            error_msg = "文件路径必须是非空字符串"
            app_logger.error(error_msg)
            return {
                "success": False,
                "output": None,
                "error": error_msg
            }
        
        if not os.path.exists(file_path):
            error_msg = f"文件不存在: {file_path}"
            app_logger.error(error_msg)
            return {
                "success": False,
                "output": None,
                "error": error_msg
            }
        
        try:
            # 执行脚本（-u 参数禁用输出缓冲，确保能实时捕获 print 输出）
            result = subprocess.run(
                [sys.executable, "-u", file_path],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            
            app_logger.info(f"成功运行Python脚本: {file_path}")
            return {
                "success": True,
                "output": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            error_msg = f"运行Python脚本时出错: {str(e)}\n输出: {e.stdout}\n错误: {e.stderr}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "output": e.stdout,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"运行Python脚本时出错: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "output": None,
                "error": error_msg
            }

    def install_package(self, package_name: str) -> Dict[str, str]:
        """
        通过 pip 安装指定的 Python 包

        Args:
            package_name: 要安装的包名，可附带版本号，如 "requests" 或 "numpy==1.21.0"

        Returns:
            包含安装结果信息的字典：
                - success: 是否安装成功
                - message: 安装过程的输出或错误信息
        """
        if not isinstance(package_name, str) or not package_name.strip():
            error_msg = "包名必须是非空字符串"
            app_logger.error(error_msg)
            return {"success": False, "message": error_msg}

        try:
            app_logger.info(f"开始通过 pip 安装包: {package_name}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            message = result.stdout
            app_logger.info(f"成功安装包: {package_name}")
            return {"success": True, "message": message}
        except subprocess.CalledProcessError as e:
            message = e.stderr or e.stdout
            error_msg = f"安装包 {package_name} 失败: {message}"
            app_logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"安装包 {package_name} 时发生异常: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg}

    def run_python_script_async(self, file_path: str) -> Dict[str, any]:
        """
        异步运行指定的Python脚本
        
        Args:
            file_path: 要运行的Python脚本路径
        
        Returns:
            包含运行结果信息的字典：
                - success: 是否启动成功
                - sessionId: 脚本执行会话ID
                - error: 错误信息（成功时为None）
        """
        # 参数验证
        if not isinstance(file_path, str) or not file_path.strip():
            error_msg = "文件路径必须是非空字符串"
            app_logger.error(error_msg)
            return {
                "success": False,
                "sessionId": None,
                "error": error_msg
            }
        
        if not os.path.exists(file_path):
            error_msg = f"文件不存在: {file_path}"
            app_logger.error(error_msg)
            return {
                "success": False,
                "sessionId": None,
                "error": error_msg
            }
        
        try:
            # 生成唯一的sessionId
            session_id = f"python_session_{uuid.uuid4()}"
            
            # 异步执行脚本（-u 参数禁用输出缓冲，确保能实时捕获 print 输出）
            process = subprocess.Popen(
                [sys.executable, "-u", file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace'
            )
            
            # 使用可变容器供后台线程写入，避免管道缓冲满导致子进程阻塞
            output_container = {"stdout": "", "stderr": ""}
            
            # 启动后台线程持续读取 stdout/stderr，防止管道填满时子进程阻塞在 write 上
            stdout_thread = threading.Thread(
                target=_read_stream_to_dict,
                args=(process.stdout, output_container, "stdout"),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=_read_stream_to_dict,
                args=(process.stderr, output_container, "stderr"),
                daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()
            
            # 存储脚本执行状态信息
            self._running_scripts[session_id] = {
                "process": process,
                "status": "running",
                "stdout": "",
                "stderr": "",
                "output_container": output_container,
                "stdout_thread": stdout_thread,
                "stderr_thread": stderr_thread,
                "start_time": time.time()
            }
            
            app_logger.info(f"成功启动异步Python脚本: {file_path}, sessionId: {session_id}")
            return {
                "success": True,
                "sessionId": session_id,
                "error": None
            }
        except Exception as e:
            error_msg = f"启动Python脚本时出错: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "sessionId": None,
                "error": error_msg
            }

    def get_script_status(self, session_id: str) -> Dict[str, any]:
        """
        根据sessionId查询脚本执行状态
        
        Args:
            session_id: 脚本执行会话ID
        
        Returns:
            包含执行状态信息的字典：
                - status: 执行状态（running, success, failed）
                - output: 脚本输出（仅当执行完成时）
                - error: 错误信息（仅当执行失败时）
        """
        # 参数验证
        if not isinstance(session_id, str) or not session_id.strip():
            error_msg = "sessionId必须是非空字符串"
            app_logger.error(error_msg)
            return {
                "status": "failed",
                "output": None,
                "error": error_msg
            }
        
        # 检查sessionId是否存在
        if session_id not in self._running_scripts:
            error_msg = f"sessionId不存在: {session_id}"
            app_logger.error(error_msg)
            return {
                "status": "failed",
                "output": None,
                "error": error_msg
            }
        
        try:
            script_info = self._running_scripts[session_id]
            process = script_info["process"]
            
            # 检查进程是否还在运行
            poll_result = process.poll()
            
            if poll_result is None:
                # 进程还在运行中
                return {
                    "status": "running",
                    "output": None,
                    "error": None
                }
            else:
                # 进程已结束，等待后台读取线程完成以确保拿到完整输出
                output_container = script_info.get("output_container")
                if output_container is not None:
                    stdout_thread = script_info.get("stdout_thread")
                    stderr_thread = script_info.get("stderr_thread")
                    if stdout_thread and stdout_thread.is_alive():
                        stdout_thread.join(timeout=2.0)
                    if stderr_thread and stderr_thread.is_alive():
                        stderr_thread.join(timeout=2.0)
                    script_info["stdout"] = output_container.get("stdout", "")
                    script_info["stderr"] = output_container.get("stderr", "")
                else:
                    # 兼容旧格式：无 output_container 时使用 communicate()
                    try:
                        stdout, stderr = process.communicate(timeout=2.0)
                        script_info["stdout"] = stdout or ""
                        script_info["stderr"] = stderr or ""
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                        script_info["stdout"] = script_info.get("stdout", "")
                        script_info["stderr"] = script_info.get("stderr", "communicate 超时")
                
                if poll_result == 0:
                    # 执行成功
                    script_info["status"] = "success"
                    return {
                        "status": "success",
                        "output": script_info["stdout"],
                        "error": None
                    }
                else:
                    # 执行失败
                    script_info["status"] = "failed"
                    error_msg = f"脚本执行失败，退出码: {poll_result}\n错误: {script_info['stderr']}"
                    return {
                        "status": "failed",
                        "output": script_info["stdout"],
                        "error": error_msg
                    }
        except Exception as e:
            error_msg = f"查询脚本状态时出错: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "status": "failed",
                "output": None,
                "error": error_msg
            }

python_tool = PythonTool()