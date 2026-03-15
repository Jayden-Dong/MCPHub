# Base schemas for the application
from pydantic import BaseModel
from typing import Optional, Any, Union

class TaskStatus(BaseModel):
    """任务状态模型"""
    status: str  # Pending, Running, Finished, Failed, Error
    result: Optional[str] = None

class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    status: str
    message: str

class StatusQuery(BaseModel):
    """状态查询模型"""
    task_id: str

class TaskQuery(BaseModel):
    """任务查询模型"""
    task_id: str

class ApiMessage(BaseModel):
    """API消息模型"""
    Source: str = ""  # 工具报错的原始提示信息
    Description: str = ""  # 对错误的描述
    Data: Optional[Any] = None  # 内部数据

class ApiResponse(BaseModel):
    """统一API响应模型"""
    Code: int  # 12表示成功，11表示失败
    Message: ApiMessage
    Data: Optional[Any] = None  # 最外层数据

    @classmethod
    def success(cls, data: Any = None, description: str = "操作成功"):
        """创建成功响应"""
        return cls(
            Code=12,
            Message=ApiMessage(Description=description),
            Data=data
        )

    @classmethod
    def error(cls, source: str = "", description: str = "操作失败", data: Any = None):
        """创建失败响应"""
        return cls(
            Code=11,
            Message=ApiMessage(Source=source, Description=description),
            Data=data
        )

class CommandTask(BaseModel):
    """通用命令任务模型"""
    command: str              # 要执行的完整命令字符串
    user_id: Optional[str] = None  # 可选的用户ID，用于按用户隔离任务目录