"""
跨平台命令映射表
根据当前操作系统自动选择对应的系统命令
"""
import platform

# 当前平台标识：Windows / Darwin / Linux
PLATFORM = platform.system()

# 命令映射表
# key -> {平台: 命令模板}
# 模板中使用 {变量名} 作为占位符，由 get_cmd() 替换
CMD_MAP = {
    # 列出目录内容
    "list_dir": {
        "Windows": 'dir "{path}"',
        "Darwin":  'ls -la "{path}"',
        "Linux":   'ls -la "{path}"',
    },

    # 系统信息
    "system_info": {
        "Windows": "systeminfo",
        "Darwin":  "sw_vers && echo '---' && uname -a",
        "Linux":   "uname -a && echo '---' && (cat /etc/os-release 2>/dev/null || cat /etc/issue 2>/dev/null)",
    },

    # 磁盘使用情况
    "disk_usage": {
        "Windows": "wmic logicaldisk get Caption,FreeSpace,Size,VolumeName",
        "Darwin":  "df -h",
        "Linux":   "df -h",
    },

    # 所有进程
    "processes": {
        "Windows": "tasklist",
        "Darwin":  "ps aux",
        "Linux":   "ps aux",
    },

    # 按名称过滤进程
    "processes_filter": {
        "Windows": 'tasklist /FI "IMAGENAME eq {filter_name}*"',
        "Darwin":  "ps aux | grep '{filter_name}' | grep -v grep",
        "Linux":   "ps aux | grep '{filter_name}' | grep -v grep",
    },

    # 网络配置信息
    "network_info": {
        "Windows": "ipconfig /all",
        "Darwin":  "ifconfig",
        "Linux":   "ip addr show 2>/dev/null || ifconfig 2>/dev/null",
    },

    # 搜索文件
    "find_files": {
        "Windows": 'dir /s /b "{search_dir}\\{pattern}" 2>nul',
        "Darwin":  'find "{search_dir}" -name "{pattern}"',
        "Linux":   'find "{search_dir}" -name "{pattern}"',
    },

    # 终止进程
    "kill_process": {
        "Windows": "taskkill /F /PID {pid}",
        "Darwin":  "kill -9 {pid}",
        "Linux":   "kill -9 {pid}",
    },

    # 环境变量
    "env_vars": {
        "Windows": "set",
        "Darwin":  "env",
        "Linux":   "env",
    },
}


def get_cmd(cmd_key: str, **kwargs) -> str:
    """
    根据当前平台获取命令，并替换占位符。

    Args:
        cmd_key: CMD_MAP 中的命令键
        **kwargs: 占位符替换参数

    Returns:
        替换后的命令字符串；平台或键不存在时返回空字符串
    """
    platform_cmds = CMD_MAP.get(cmd_key, {})
    cmd_template = platform_cmds.get(PLATFORM, "")
    if not cmd_template:
        return ""
    if kwargs:
        try:
            return cmd_template.format(**kwargs)
        except KeyError:
            return cmd_template
    return cmd_template
