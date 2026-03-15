# 机器码工具函数
import platform
import subprocess
import hashlib
import uuid
import sys


def get_machine_code() -> str:
    """
    获取机器的唯一标识码

    在 Windows 系统上，通过组合以下信息生成机器码：
    1. MAC 地址
    2. CPU 序列号（如果可用）
    3. 主板序列号（如果可用）
    4. 系统信息

    Returns:
        32位十六进制字符串的机器码
    """
    try:
        machine_info = []

        # 1. 获取 MAC 地址
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                        for i in range(0, 8 * 6, 8)][::-1])
        machine_info.append(f"MAC:{mac}")

        # 2. 获取 Windows 平台特定信息
        if platform.system() == "Windows":
            # 尝试获取 CPU 序列号
            try:
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'ProcessorId'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                if result.returncode == 0 and result.stdout:
                    cpu_id = result.stdout.strip().split('\n')[-1].strip()
                    if cpu_id and cpu_id != "ProcessorId":
                        machine_info.append(f"CPU:{cpu_id}")
            except Exception:
                pass

            # 尝试获取主板序列号
            try:
                result = subprocess.run(
                    ['wmic', 'baseboard', 'get', 'SerialNumber'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                if result.returncode == 0 and result.stdout:
                    board_id = result.stdout.strip().split('\n')[-1].strip()
                    if board_id and board_id != "SerialNumber":
                        machine_info.append(f"Board:{board_id}")
            except Exception:
                pass

            # 获取计算机名和用户名
            machine_info.append(f"Computer:{platform.node()}")

        # 3. 添加系统信息
        machine_info.append(f"System:{platform.system()}")
        machine_info.append(f"Architecture:{platform.machine()}")

        # 4. 组合信息并生成哈希
        info_string = "|".join(machine_info)
        machine_hash = hashlib.md5(info_string.encode('utf-8')).hexdigest()

        return machine_hash

    except Exception as e:
        # 如果获取失败，使用 MAC 地址的哈希值作为后备方案
        try:
            mac_str = str(uuid.getnode())
            fallback_hash = hashlib.md5(mac_str.encode('utf-8')).hexdigest()
            return fallback_hash
        except Exception:
            # 最后的后备方案：使用随机但固定的 UUID
            return hashlib.md5(b"fallback_machine_code").hexdigest()


def get_machine_code_simple() -> str:
    """
    获取简化的机器码（仅使用 MAC 地址）

    这个方法更快更简单，但可能在不同虚拟机或容器中重复

    Returns:
        32位十六进制字符串的机器码
    """
    try:
        mac_node = uuid.getnode()
        mac_str = str(mac_node)
        return str(mac_str)

        machine_hash = hashlib.md5(mac_str.encode('utf-8')).hexdigest()
        return machine_hash
    except Exception:
        return hashlib.md5(b"fallback_machine_code").hexdigest()

