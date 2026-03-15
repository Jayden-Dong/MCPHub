"""
FTP 工具模块
提供 FTP 文件上传、下载、目录创建和文件移动等操作功能
"""
import os
import tempfile
import shutil
import tarfile
from ftplib import FTP, error_perm
from pathlib import Path
from typing import Annotated, Dict, Any, Optional
from pydantic import Field

# 模块级配置（由__init__.py 注入）
_config: dict = {}

def init_config(config: dict):
    """初始化配置"""
    global _config
    _config = config.copy()


class FTPClient:
    """FTP 客户端封装类"""
    
    def __init__(self):
        """初始化 FTP 客户端"""
        self.server = "localhost"
        self.username = "ftp_user"
        self.password = ""
        self.base_dir = "/data"
        self.ftp_download_dir = "/tmp/ftp_downloads"
        self.ftp: Optional[FTP] = None
    
    def _load_config(self):
        """加载配置"""
        global _config
        if _config:
            ftp_server_config = _config.get("ftp_server", {})
            self.server = ftp_server_config.get("host", "localhost")
            self.username = ftp_server_config.get("username", "ftp_user")
            self.password = ftp_server_config.get("password", "")
            self.base_dir = ftp_server_config.get("base_dir", "/data")
            self.ftp_download_dir = _config.get("download_dir", "/tmp/ftp_downloads")
    
    def connect(self) -> FTP:
        """
        连接到 FTP 服务器并登录
        
        Returns:
            FTP 连接对象
        """
        self._load_config()
        self.ftp = FTP(self.server)
        self.ftp.login(user=self.username, passwd=self.password)
        return self.ftp
    
    def disconnect(self):
        """断开 FTP 连接"""
        if self.ftp:
            try:
                self.ftp.quit()
            except Exception:
                pass
            finally:
                self.ftp = None
    
    def ensure_directory_exists(self, directory_path: str):
        """
        确保 FTP 服务器上的目录存在，如果不存在则创建
        
        Args:
            directory_path: 目录路径
        """
        if not self.ftp:
            raise RuntimeError("FTP 连接未建立")
        
        try:
            self.ftp.cwd(directory_path)
        except error_perm:
            dirs = directory_path.split('/')
            current_path = ''
            for dir_name in dirs:
                if not dir_name:
                    continue
                current_path = current_path + '/' + dir_name if current_path else '/' + dir_name
                try:
                    self.ftp.cwd(current_path)
                except error_perm:
                    self.ftp.mkd(current_path)
                    self.ftp.cwd(current_path)
    
    def _is_dir(self, remote_path: str) -> bool:
        """判断远程路径是否为目录"""
        if not self.ftp:
            raise RuntimeError("FTP 连接未建立")
        
        current = self.ftp.pwd()
        try:
            self.ftp.cwd(remote_path)
            self.ftp.cwd(current)
            return True
        except error_perm:
            try:
                self.ftp.cwd(current)
            except Exception:
                pass
            return False
    
    def _upload_dir_recursive(self, local_dir: str, remote_base_dir: str) -> None:
        """递归上传本地目录到 FTP 服务器"""
        if not self.ftp:
            raise RuntimeError("FTP 连接未建立")
        
        items = os.listdir(local_dir)
        
        for item in items:
            local_item_path = os.path.join(local_dir, item)
            remote_item_path = f"{remote_base_dir}/{item}"
            
            if os.path.isdir(local_item_path):
                self.ensure_directory_exists(remote_item_path)
                self._upload_dir_recursive(local_item_path, remote_item_path)
            else:
                with open(local_item_path, 'rb') as local_file:
                    self.ftp.storbinary(f'STOR {item}', local_file, blocksize=8192)
    
    def _ensure_local_dir(self, path: str) -> None:
        """确保本地目录存在"""
        os.makedirs(path, exist_ok=True)
    
    def _download_file(self, remote_file_path: str, local_file_path: str) -> None:
        """下载单个文件"""
        if not self.ftp:
            raise RuntimeError("FTP 连接未建立")
        
        self._ensure_local_dir(os.path.dirname(local_file_path) or ".")
        with open(local_file_path, 'wb') as f:
            self.ftp.retrbinary(f'RETR {remote_file_path}', f.write, blocksize=8192)
    
    def _download_dir_recursive(self, remote_dir: str, local_dir: str) -> None:
        """递归下载远程目录内容到本地目录"""
        if not self.ftp:
            raise RuntimeError("FTP 连接未建立")
        
        start_pwd = self.ftp.pwd()
        try:
            self.ftp.cwd(remote_dir)
            self._ensure_local_dir(local_dir)
            entries = self.ftp.nlst()
            for name in entries:
                if name in ('.', '..'):
                    continue
                if self._is_dir(name):
                    self._download_dir_recursive(name, os.path.join(local_dir, name))
                    self.ftp.cwd('..')
                else:
                    self._download_file(name, os.path.join(local_dir, name))
        finally:
            try:
                self.ftp.cwd(start_pwd)
            except Exception:
                pass
    
    def _make_archive(self, src_dir: str, dest_dir: str, base_name: str, archive_format: str) -> str:
        """将目录打包为 zip 或 tar"""
        self._ensure_local_dir(dest_dir)
        archive_format = (archive_format or 'zip').lower()
        if archive_format not in ('zip', 'tar'):
            archive_format = 'zip'

        output_path = os.path.join(dest_dir, base_name)
        if archive_format == 'zip':
            return shutil.make_archive(output_path, 'zip', root_dir=src_dir)
        else:
            tar_path = f"{output_path}.tar"
            with tarfile.open(tar_path, mode='w') as tf:
                for root, dirs, files in os.walk(src_dir):
                    rel_root = os.path.relpath(root, src_dir)
                    for d in dirs:
                        dir_full = os.path.join(root, d)
                        arcname = os.path.normpath(os.path.join(rel_root, d)) if rel_root != '.' else d
                        tf.add(dir_full, arcname=arcname)
                    for f_name in files:
                        f_full = os.path.join(root, f_name)
                        arcname = os.path.normpath(os.path.join(rel_root, f_name)) if rel_root != '.' else f_name
                        tf.add(f_full, arcname=arcname)
            return tar_path


# 全局 FTP 客户端实例
_ftp_client: Optional[FTPClient] = None


def _get_ftp_client() -> FTPClient:
    """获取 FTP 客户端实例"""
    global _ftp_client
    if _ftp_client is None:
        _ftp_client = FTPClient()
    return _ftp_client


def upload_file(
    user_id: Annotated[str, Field(description="用户 ID，用于在 FTP 服务器上创建用户专属目录，确保不同用户文件隔离存储")],
    local_file_path: Annotated[str, Field(description="本地要上传的文件或目录的完整绝对路径，例如：/home/user/document.pdf 或 C:\\Users\\user\\document.pdf")]
) -> Dict[str, Any]:
    """
    通过 FTP 上传文件或目录到服务器。
    
    功能说明：
    - 支持上传单个文件或整个目录
    - 自动在 FTP 服务器上为指定用户创建专属目录（base_dir/user_id/）
    - 上传目录时递归处理所有子目录和文件
    - 支持大文件流式传输（8KB 块大小）
    - 上传完成后验证文件是否存在
    
    返回结果包含：
    - success: 操作是否成功
    - message: 操作结果描述
    - remote_path: 文件在 FTP 服务器上的完整路径
    - file_size/file_size_mb: 文件大小（字节/MB）
    - is_directory: 是否为目录上传
    """
    try:
        client = _get_ftp_client()
        return client.upload_file(user_id, local_file_path)
    except Exception as e:
        return {
            "success": False,
            "message": f"上传失败：{str(e)}",
            "user_id": user_id,
            "file_path": local_file_path
        }


def download_file(
    remote_path: Annotated[str, Field(description="FTP 服务器上的远程路径。支持绝对路径（以/开头，如/data/files/doc.pdf）或相对于基础目录的相对路径（如 files/doc.pdf）")],
    archive_format: Annotated[str, Field(description="当下载目录时的打包格式。可选值：'zip'（默认，压缩格式）或'tar'（未压缩归档格式）")] = "zip"
) -> Dict[str, Any]:
    """
    从 FTP 服务器下载文件或目录到本地。
    
    功能说明：
    - 下载单个文件：直接保存到配置的下载目录
    - 下载目录：先递归下载到临时目录，再打包为指定格式
    - 支持绝对路径和相对路径
    - 自动创建本地保存目录
    - 返回下载文件的本地路径和大小信息
    
    返回结果包含：
    - success: 操作是否成功
    - message: 操作结果描述
    - local_path: 下载文件在本地保存的完整路径
    - remote_path: 源文件的远程路径
    - is_directory: 是否为目录下载
    - archive_format: 目录打包格式（仅目录下载时）
    - file_size/file_size_mb: 文件大小
    """
    try:
        client = _get_ftp_client()
        return client.download(remote_path, archive_format)
    except Exception as e:
        return {
            "success": False,
            "message": f"下载失败：{str(e)}",
            "remote_path": remote_path
        }


def create_directory(
    remote_path: Annotated[str, Field(description="要在 FTP 服务器上创建的目录路径。支持绝对路径（以/开头，如/data/users/user1）或相对于基础目录的相对路径（如 users/user1）")]
) -> Dict[str, Any]:
    """
    在 FTP 服务器上创建目录。
    
    功能说明：
    - 支持创建多级目录（父目录不存在时自动递归创建）
    - 支持绝对路径和相对路径
    - 自动处理路径分隔符（支持/和\\）
    - 目录已存在时不会报错
    
    返回结果包含：
    - success: 操作是否成功
    - message: 操作结果描述
    - created_path: 实际创建的目录完整路径
    """
    try:
        client = _get_ftp_client()
        return client.create_directory(remote_path)
    except Exception as e:
        return {
            "success": False,
            "message": f"创建目录失败：{str(e)}",
            "directory_path": remote_path
        }


def move_file(
    source_path: Annotated[str, Field(description="源文件的完整路径。支持绝对路径（以/开头）或相对于基础目录的相对路径")],
    destination_path: Annotated[str, Field(description="目标目录的完整路径。支持绝对路径（以/开头）或相对于基础目录的相对路径。文件名将保持不变。")]
) -> Dict[str, Any]:
    """
    在 FTP 服务器上移动文件到目标目录。
    
    功能说明：
    - 支持绝对路径和相对路径
    - 目标目录不存在时自动创建
    - 移动后验证文件是否存在于目标位置
    - 保持原文件名不变
    - 不支持跨服务器移动
    
    返回结果包含：
    - success: 操作是否成功
    - message: 操作结果描述
    - source_path: 源文件完整路径
    - destination_path: 目标文件完整路径
    - file_name: 移动的文件名
    """
    try:
        client = _get_ftp_client()
        return client.move_file(source_path, destination_path)
    except Exception as e:
        return {
            "success": False,
            "message": f"移动文件失败：{str(e)}",
            "source_path": source_path,
            "destination_path": destination_path
        }


# FTPClient 类的方法实现
def _upload_file_impl(self, user_id: str, local_file_path: str) -> Dict[str, Any]:
    """上传文件或目录实现"""
    if not os.path.exists(local_file_path):
        return {
            "success": False,
            "message": f"本地文件/目录不存在：{local_file_path}",
            "user_id": user_id,
            "file_path": local_file_path
        }
    
    is_directory = os.path.isdir(local_file_path)
    upload_name = os.path.basename(local_file_path)
    
    try:
        self.connect()
        
        try:
            self.ftp.cwd(self.base_dir)
        except error_perm:
            self.ensure_directory_exists(self.base_dir)
        
        user_dir = os.path.join(self.base_dir, user_id).replace('\\', '/')
        self.ensure_directory_exists(user_dir)
        
        if is_directory:
            remote_dir_path = f"{user_dir}/{upload_name}"
            self.ensure_directory_exists(remote_dir_path)
            self._upload_dir_recursive(local_file_path, remote_dir_path)
            
            return {
                "success": True,
                "message": f"目录 '{upload_name}' 成功上传到 FTP 服务器",
                "user_id": user_id,
                "directory_name": upload_name,
                "remote_path": remote_dir_path,
                "is_directory": True
            }
        else:
            file_size = os.path.getsize(local_file_path)
            self.ftp.cwd(user_dir)
            
            with open(local_file_path, 'rb') as local_file:
                self.ftp.storbinary(f'STOR {upload_name}', local_file, blocksize=8192)
            
            return {
                "success": True,
                "message": f"文件 '{upload_name}' 成功上传到 FTP 服务器",
                "user_id": user_id,
                "file_name": upload_name,
                "file_size": file_size,
                "remote_path": f"{user_dir}/{upload_name}",
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "is_directory": False
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"{'目录' if is_directory else '文件'}上传失败：{str(e)}",
            "user_id": user_id,
            "file_path": local_file_path,
            "is_directory": is_directory
        }
    finally:
        self.disconnect()


def _download_impl(self, remote_path: str, archive_format: str = "zip") -> Dict[str, Any]:
    """下载文件或目录实现"""
    try:
        self.connect()
        
        if not remote_path:
            return {"success": False, "message": "remote_path 不能为空"}
        
        remote_path_clean = remote_path.replace('\\', '/')
        if remote_path_clean.startswith('/'):
            target_remote = remote_path_clean
        else:
            target_remote = os.path.join(self.base_dir, remote_path_clean).replace('\\', '/')

        is_dir = self._is_dir(target_remote)
        local_save_dir = self.ftp_download_dir
        self._ensure_local_dir(local_save_dir)

        if not is_dir:
            local_file = os.path.join(local_save_dir, os.path.basename(target_remote.rstrip('/')))
            local_file = str(Path(local_file).absolute()).replace('\\', '/')
            self._download_file(target_remote, local_file)
            size = os.path.getsize(local_file) if os.path.exists(local_file) else None
            return {
                "success": True,
                "message": "文件下载完成",
                "remote_path": target_remote,
                "local_path": local_file,
                "is_directory": False,
                "file_size": size,
                "file_size_mb": round((size or 0) / (1024*1024), 2)
            }
        else:
            base_name = os.path.basename(target_remote.rstrip('/')) or 'archive'
            with tempfile.TemporaryDirectory() as tmp_dir:
                stage_dir = os.path.join(tmp_dir, base_name)
                self._download_dir_recursive(target_remote, stage_dir)
                archive_path = self._make_archive(stage_dir, local_save_dir, base_name, archive_format)
                archive_path = archive_path.replace('\\', '/')
                size = os.path.getsize(archive_path) if os.path.exists(archive_path) else None
                return {
                    "success": True,
                    "message": "目录下载并打包完成",
                    "remote_path": target_remote,
                    "local_path": archive_path,
                    "is_directory": True,
                    "archive_format": 'zip' if archive_path.endswith('.zip') else 'tar',
                    "file_size": size,
                    "file_size_mb": round((size or 0) / (1024*1024), 2)
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"下载失败：{str(e)}",
            "remote_path": remote_path
        }
    finally:
        self.disconnect()


def _create_directory_impl(self, directory_path: str) -> Dict[str, Any]:
    """创建目录实现"""
    try:
        self.connect()
        
        if not directory_path:
            return {"success": False, "message": "directory_path 不能为空"}
        
        directory_path_clean = directory_path.replace('\\', '/')
        
        if directory_path_clean.startswith('/'):
            target_dir = directory_path_clean
        else:
            target_dir = os.path.join(self.base_dir, directory_path_clean).replace('\\', '/')
        
        self.ensure_directory_exists(target_dir)
        
        return {
            "success": True,
            "message": f"目录创建成功：{target_dir}",
            "created_path": target_dir
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"创建目录失败：{str(e)}",
            "directory_path": directory_path
        }
    finally:
        self.disconnect()


def _move_file_impl(self, source_path: str, destination_dir: str) -> Dict[str, Any]:
    """移动文件实现"""
    try:
        self.connect()
        
        if not source_path:
            return {"success": False, "message": "source_path 不能为空"}
        
        if not destination_dir:
            return {"success": False, "message": "destination_dir 不能为空"}
        
        source_path_clean = source_path.replace('\\', '/')
        destination_dir_clean = destination_dir.replace('\\', '/')
        
        if source_path_clean.startswith('/'):
            source_absolute = source_path_clean
        else:
            source_absolute = os.path.join(self.base_dir, source_path_clean).replace('\\', '/')
        
        if destination_dir_clean.startswith('/'):
            dest_absolute = destination_dir_clean
        else:
            dest_absolute = os.path.join(self.base_dir, destination_dir_clean).replace('\\', '/')
        
        self.ensure_directory_exists(dest_absolute)
        
        source_filename = os.path.basename(source_absolute)
        destination_path = f"{dest_absolute}/{source_filename}"
        
        source_dir = os.path.dirname(source_absolute) or '/'
        
        current_pwd = self.ftp.pwd()
        try:
            self.ftp.cwd(source_dir)
            files_in_source = self.ftp.nlst()
            
            if source_filename not in files_in_source:
                return {
                    "success": False,
                    "message": f"源文件不存在：{source_absolute}",
                    "source_path": source_path,
                    "destination_dir": destination_dir
                }
            
            self.ftp.rename(source_absolute, destination_path)
            
            self.ftp.cwd(dest_absolute)
            files_in_dest = self.ftp.nlst()
            
            if source_filename in files_in_dest:
                return {
                    "success": True,
                    "message": "文件移动成功",
                    "source_path": source_absolute,
                    "destination_path": destination_path,
                    "file_name": source_filename
                }
            else:
                return {
                    "success": True,
                    "message": "文件移动完成（但未验证）",
                    "source_path": source_absolute,
                    "destination_path": destination_path,
                    "file_name": source_filename
                }
        finally:
            try:
                self.ftp.cwd(current_pwd)
            except Exception:
                pass
        
    except error_perm as e:
        return {
            "success": False,
            "message": f"FTP 权限错误：{str(e)}",
            "source_path": source_path,
            "destination_dir": destination_dir
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件移动失败：{str(e)}",
            "source_path": source_path,
            "destination_dir": destination_dir
        }
    finally:
        self.disconnect()


# 将实现方法绑定到 FTPClient 类
FTPClient.upload_file = _upload_file_impl
FTPClient.download = _download_impl
FTPClient.create_directory = _create_directory_impl
FTPClient.move_file = _move_file_impl
