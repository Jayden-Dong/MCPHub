"""
CLI工具模块
提供跨平台命令行操作功能，自动适配 Windows / macOS / Linux
"""
import subprocess
from typing import Dict, Any

import utils.com_utils
from config_py.logger import app_logger
from tools.t_cli.platform_cmd import PLATFORM, get_cmd


class CLITool:
    """跨平台CLI工具类"""

    # 危险命令关键词黑名单（不区分大小写的子串匹配）
    _DEFAULT_BLACKLIST = [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf ~",
        "rm --no-preserve-root",
        "format c:",
        "format c:/",
        "del /s /q c:\\",
        "del /s /q c:/",
        ":(){ :|:& };:",
        "mkfs",
        "dd if=/dev/zero",
        "dd if=/dev/random",
        "> /dev/sda",
        "shutdown -h",
        "shutdown -r",
        "reboot",
        "halt",
        "poweroff",
        "reg delete hklm",
        "reg delete hkcu",
        "chmod -r 777 /",
        "chmod 777 /etc/passwd",
        "net user administrator",
        "net localgroup administrators",
    ]

    def __init__(self):
        config = utils.com_utils.get_module_config("cli_mcp")
        self.timeout_default = int(config.get("timeout_default", 30))
        self.enable_dangerous_check = bool(config.get("enable_dangerous_check", True))
        custom_blacklist = config.get("custom_blacklist", [])
        self._blacklist = self._DEFAULT_BLACKLIST + [c.lower() for c in custom_blacklist]

        # Windows 中文系统使用 GBK，其余使用 UTF-8
        self._encoding = "gbk" if PLATFORM == "Windows" else "utf-8"

        app_logger.info(
            f"CLITool 初始化，平台: {PLATFORM}, "
            f"编码: {self._encoding}, "
            f"默认超时: {self.timeout_default}s"
        )

    def _is_dangerous(self, command: str) -> bool:
        """检查命令是否命中黑名单"""
        cmd_lower = command.lower().strip()
        for pattern in self._blacklist:
            if pattern in cmd_lower:
                return True
        return False

    def _run(self, command: str, timeout: int = None, cwd: str = None) -> Dict[str, Any]:
        """
        底层命令执行，统一处理超时、编码、异常。

        Returns:
            {"success": bool, "stdout": str, "stderr": str, "returncode": int}
        """
        if timeout is None:
            timeout = self.timeout_default

        try:
            if PLATFORM == "Windows":
                # Windows：shell=True 才能执行 dir、set 等内置命令
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                )
            else:
                # macOS / Linux：通过 bash -c 执行，避免 shell=True 的安全风险
                proc = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                )

            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"命令执行超时（超过 {timeout}s）",
                    "returncode": -1,
                }

            stdout = stdout_bytes.decode(self._encoding, errors="replace")
            stderr = stderr_bytes.decode(self._encoding, errors="replace")

            return {
                "success": proc.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": proc.returncode,
            }

        except Exception as e:
            error_msg = f"执行命令时发生异常: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "stdout": "",
                "stderr": error_msg,
                "returncode": -1,
            }

    # ----------------------------------------------------------------
    #  公开工具方法
    # ----------------------------------------------------------------

    def run_command(self, command: str, timeout: int = None, work_dir: str = None) -> Dict[str, Any]:
        """执行任意命令行指令（带安全检查）"""
        if not isinstance(command, str) or not command.strip():
            return {"success": False, "stdout": "", "stderr": "命令不能为空", "returncode": -1}

        if self.enable_dangerous_check and self._is_dangerous(command):
            return {
                "success": False,
                "stdout": "",
                "stderr": f"命令被安全策略拒绝（包含危险操作）: {command}",
                "returncode": -1,
            }

        app_logger.info(f"执行CLI命令 [平台:{PLATFORM}]: {command}")
        return self._run(command, timeout=timeout, cwd=work_dir)

    def list_directory(self, path: str) -> Dict[str, Any]:
        """列出目录内容"""
        path = path.strip() if path and path.strip() else "."
        cmd = get_cmd("list_dir", path=path)
        app_logger.info(f"列出目录: {path}")
        return self._run(cmd)

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        cmd = get_cmd("system_info")
        app_logger.info("获取系统信息")
        return self._run(cmd)

    def get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        cmd = get_cmd("disk_usage")
        app_logger.info("获取磁盘使用情况")
        return self._run(cmd)

    def get_running_processes(self, filter_name: str = "") -> Dict[str, Any]:
        """获取运行中的进程列表"""
        if filter_name and filter_name.strip():
            cmd = get_cmd("processes_filter", filter_name=filter_name.strip())
        else:
            cmd = get_cmd("processes")
        app_logger.info(f"获取进程列表，过滤: {filter_name!r}")
        return self._run(cmd)

    def get_network_info(self) -> Dict[str, Any]:
        """获取网络配置信息"""
        cmd = get_cmd("network_info")
        app_logger.info("获取网络信息")
        return self._run(cmd)

    def find_files(self, search_dir: str, pattern: str) -> Dict[str, Any]:
        """在指定目录下递归搜索匹配文件"""
        search_dir = search_dir.strip() if search_dir and search_dir.strip() else "."
        pattern = pattern.strip() if pattern and pattern.strip() else "*"
        cmd = get_cmd("find_files", search_dir=search_dir, pattern=pattern)
        app_logger.info(f"搜索文件: dir={search_dir}, pattern={pattern}")
        return self._run(cmd)

    def kill_process(self, pid: int) -> Dict[str, Any]:
        """强制终止指定 PID 的进程"""
        if not isinstance(pid, int) or pid <= 0:
            return {"success": False, "stdout": "", "stderr": "PID 必须是正整数", "returncode": -1}
        cmd = get_cmd("kill_process", pid=pid)
        app_logger.info(f"终止进程 PID: {pid}")
        return self._run(cmd)

    def get_env_vars(self, filter_prefix: str = "") -> Dict[str, Any]:
        """获取环境变量，可按前缀过滤"""
        cmd = get_cmd("env_vars")
        result = self._run(cmd)
        if result["success"] and filter_prefix and filter_prefix.strip():
            prefix_upper = filter_prefix.strip().upper()
            lines = result["stdout"].splitlines()
            filtered = [line for line in lines if line.upper().startswith(prefix_upper)]
            result["stdout"] = "\n".join(filtered)
        return result


cli_tool = CLITool()
