"""
AI代码生成 REST API
提供与LLM对话生成FastMCP模块代码的接口
"""
import asyncio
import json
import os
import uuid
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, File, Form, UploadFile, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config_py.config import settings
from config_py.logger import app_logger
from schemas.base import ApiResponse
from utils.dependencies import get_current_user

router = APIRouter(prefix="/api/codegen", tags=["AI代码生成"], dependencies=[Depends(get_current_user)])

# 生成任务缓存
_codegen_tasks: dict[str, dict] = {}

# 可读取的文本文件扩展名
_TEXT_EXTENSIONS = {
    '.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.cfg',
    '.ini', '.sh', '.js', '.ts', '.html', '.css', '.xml', '.csv',
    '.rst', '.env', '.conf', '.log', '.sql', '.r', '.ipynb'
}

# MCP模块代码生成的系统提示词
SYSTEM_PROMPT = '''你是一个专业的MCP工具模块代码生成器。用户会描述他们需要的工具功能，或上传已有代码让你重构为MCP模块规范，你需要生成基于FastMCP的Python模块代码。

## 模块规范

生成的模块必须遵循以下目录结构：
```
t_<module_name>/
├── __init__.py           # 仅含MODULE_INFO和委托调用_mcp.py的register/unregister
├── <module_name>_mcp.py  # 工具注册逻辑（register_tools/unregister_tools）
├── <module_name>_tool.py # 业务逻辑实现
└── requirements.txt      # 额外依赖（如有）
```

**重要**：`__init__.py` 只负责声明模块元信息并委托给 `_mcp.py`，不要在 `__init__.py` 中重复写工具注册代码。所有 `Tool.from_function` 和 `mcp_instance.add_tool` 调用只写在 `_mcp.py` 中。

## __init__.py 模板

```python
MODULE_INFO = {
    "display_name": "模块显示名称",
    "version": "1.0.0",
    "description": "模块功能描述",
    "author": "作者",
    # 可选：声明模块的默认配置项，用户可在管理界面查看和修改
    # "default_config": {
    #     "api_key": "",
    #     "server_url": "http://localhost:8080",
    #     "timeout": 30
    # }
}

# 运行时配置（由平台注入，勿手动修改）
_config: dict = {}

def init_config(config: dict):
    """平台加载模块时注入初始配置"""
    global _config
    _config = config.copy()

def update_config(config: dict):
    """用户在管理界面修改配置后平台回调此函数（热更新）"""
    global _config
    _config = config.copy()

def register(mcp_instance):
    """注册本模块的所有工具到MCP"""
    from .<module_name>_mcp import register_tools
    return register_tools(mcp_instance)

def unregister(mcp_instance):
    """从MCP移除本模块的所有工具"""
    from .<module_name>_mcp import unregister_tools
    unregister_tools(mcp_instance)
```

**说明**：如果模块需要配置项（如 API Key、服务地址等），请在 `MODULE_INFO` 中填写 `default_config`，平台会自动在详情页展示配置面板供用户编辑。模块内部通过模块级变量 `_config` 读取配置，`init_config` 在加载时调用，`update_config` 在用户修改后热更新。

## <module_name>_mcp.py 模板

```python
from fastmcp.tools.tool import Tool
from . import <module_name>_tool


def register_tools(mcp_instance):
    """注册所有工具到MCP实例"""
    tools = []

    # description 填写工具的整体用途说明；参数描述已在 _tool.py 中通过 Annotated+Field 定义
    # 重构已有代码时，务必保留原 @mcp.tool(description="...") 中的描述或函数文档字符串
    tool = Tool.from_function(
        <module_name>_tool.some_function,
        name="tool_name",
        description="工具的整体功能描述"
    )
    mcp_instance.add_tool(tool)
    tools.append("tool_name")

    return tools  # 返回注册的工具名列表


def unregister_tools(mcp_instance):
    """从MCP移除所有工具"""
    tool_names = ["tool_name"]  # 与register_tools中一致
    for name in tool_names:
        try:
            mcp_instance.remove_tool(name)
        except Exception:
            pass
```

**重构示例**：若原代码为：
```python
@mcp.tool(description="计算两个数的和，返回相加结果")
def add(a: int, b: int) -> int:
    return a + b
```
则生成的 `_mcp.py` 应为：
```python
tool = Tool.from_function(
    xxx_tool.add,
    name="add",
    description="计算两个数的和，返回相加结果"  # 保留原有的description
)
```

若原代码未显式指定 description 但函数有文档字符串：
```python
@mcp.tool()
def add(a: int, b: int) -> int:
    """计算两个数的和，返回相加结果"""
    return a + b
```
则应提取文档字符串作为 description：
```python
tool = Tool.from_function(
    xxx_tool.add,
    name="add",
    description="计算两个数的和，返回相加结果"  # 从函数文档字符串提取
)
```

## <module_name>_tool.py 参数规范

工具函数的每个参数**必须**使用 `Annotated[类型, Field(description="...")]` 注解，这样平台才能在工具详情页自动展示参数说明。示例：

```python
from typing import Annotated, Dict, Any
from pydantic import Field

def some_function(
    param1: Annotated[str, Field(description="参数1的含义，例如：用户输入的查询词")],
    param2: Annotated[float, Field(description="参数2的含义，例如：置信度阈值，取值范围0~1")],
    param3: Annotated[int, Field(description="参数3的含义，例如：返回结果数量上限")] = 10,
) -> Dict[str, Any]:
    """函数的整体描述（作为工具description使用）"""
    ...
```

## 工具实现规范

1. 工具函数应返回dict类型，包含 success 字段
2. 需要妥善处理异常，不要让异常直接抛出
3. 工具描述要清晰，**每个参数都必须用 `Annotated[类型, Field(description="...")]` 注解**，不允许使用裸类型注解（如 `param: str`）

## 重构已有代码的最小改动原则

当用户上传了已有代码并要求封装为MCP模块时，必须遵循**最小改动原则**：

1. **辅助文件/子目录保持不变**：对于原代码中的辅助模块、数据库模型、子目录（如 `db_models/`、`utils/` 等），直接将其内容原样包含在输出中，不做任何修改。只有在这些文件存在明显错误或与MCP规范强冲突时，才允许最小范围修改，并在注释中说明改动原因。

2. **_tool.py 只做参数注解补充**：保留原有的全部业务逻辑、类结构、方法实现不变。仅在缺少 `Annotated[类型, Field(description="...")]` 注解的工具函数参数上补充注解。不改变函数签名、不重构类、不调整导入结构。

3. **_mcp.py 重点调整**：将原有的 `@mcp.tool()` 装饰器模式替换为 `register_tools/unregister_tools` + `Tool.from_function` 规范模式。导入路径使用相对导入（`from . import xxx_tool`）。

   **重要：保留原有工具描述**。当原代码中的工具使用 `@mcp.tool(description="...")` 或函数文档字符串定义了工具描述时，必须在 `Tool.from_function()` 的 `description` 参数中保留该描述，确保用户原有的工具使用说明不会丢失。优先级：`@mcp.tool(description="...")` 中的显式 description > 函数文档字符串。

4. **新增 __init__.py**：按模板生成规范的 `MODULE_INFO`、`_config`、`init_config`、`update_config`、`register`、`unregister`，如原代码有配置项需求，在 `default_config` 中声明。

5. **输出所有文件**：输出的 files 数组必须包含模块目录下的全部文件（含未修改的辅助文件），确保安装后模块可完整运行。未修改的文件内容与上传时保持完全一致。

## 输出格式

请以JSON格式输出，包含files数组，每个元素有path和content：
```json
{
    "module_name": "t_xxx",
    "files": [
        {"path": "t_xxx/__init__.py", "content": "..."},
        {"path": "t_xxx/xxx_mcp.py", "content": "..."},
        {"path": "t_xxx/xxx_tool.py", "content": "..."},
        {"path": "t_xxx/requirements.txt", "content": "..."}
    ]
}
```

只输出JSON，不要输出其他内容。
'''


class ChatRequest(BaseModel):
    message: str
    task_id: Optional[str] = None  # 如果有则继续对话
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = 8192  # 默认8192，避免代码生成被截断


class GenerateRequest(BaseModel):
    task_id: str


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    与LLM对话，生成MCP模块代码
    支持流式返回和多轮对话
    """
    try:
        from openai import OpenAI
    except ImportError:
        return ApiResponse.error(description="请先安装openai包: pip install openai")

    # 获取或创建任务
    task_id = req.task_id or str(uuid.uuid4())
    if task_id not in _codegen_tasks:
        _codegen_tasks[task_id] = {
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "generated_code": None,
            "file_context": None,
            "file_context_injected": False,
        }

    task = _codegen_tasks[task_id]

    # 若有未注入的文件上下文，附加到本次用户消息前
    user_content = req.message
    if task.get("file_context") and not task.get("file_context_injected"):
        user_content = (
            "[以下是用户上传的已有代码文件，请将其重构为MCP模块规范。"
            "遵循最小改动原则：辅助文件/子目录内容原样保留，"
            "重点调整 _mcp.py（改为 register_tools/unregister_tools 模式，**保留原有工具的description**）、"
            "_tool.py（工具函数参数补充 Annotated+Field 注解）、"
            "以及新增规范的 __init__.py。输出的 files 数组需包含所有文件。]\n\n"
            + task["file_context"]
            + "\n\n[用户请求]\n"
            + req.message
        )
        task["file_context_injected"] = True

    task["messages"].append({"role": "user", "content": user_content})

    # 获取LLM配置
    api_key = req.api_key
    base_url = req.base_url
    model = req.model

    if not api_key:
        return ApiResponse.error(description="未配置LLM API Key，请在请求中提供或在config.json中配置")

    max_tokens = req.max_tokens or 8192
    app_logger.info(f"[codegen chat] 开始 task_id={task_id} model={model} max_tokens={max_tokens}")
    try:
        import httpx
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=None, pool=None),
        )

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=task["messages"],
            temperature=0.3,
            max_tokens=max_tokens
        )

        choice = response.choices[0]
        assistant_message = choice.message.content
        finish_reason = choice.finish_reason
        app_logger.info(
            f"[codegen chat] 完成 task_id={task_id} chars={len(assistant_message or '')} finish_reason={finish_reason}"
        )
        if finish_reason == "length":
            app_logger.warning(
                f"[codegen chat] 输出被截断(max_tokens={max_tokens}) task_id={task_id}，请增大 max_tokens"
            )

        task["messages"].append({"role": "assistant", "content": assistant_message})

        # 尝试解析JSON代码
        try:
            code_data = _extract_json(assistant_message)
            if code_data and "files" in code_data:
                task["generated_code"] = code_data
        except Exception as e:
            app_logger.debug(f"解析生成代码JSON失败: {e}")

        result: dict = {
            "task_id": task_id,
            "reply": assistant_message,
            "has_code": task["generated_code"] is not None
        }
        if finish_reason == "length":
            result["warning"] = f"输出已被截断(max_tokens={max_tokens})，代码可能不完整，请增大 max_tokens 后重试"
        return ApiResponse.success(data=result, description="对话成功")

    except Exception as e:
        app_logger.exception(f"[codegen chat] 异常 task_id={task_id} error={e}")
        return ApiResponse.error(description=f"LLM对话失败: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    与LLM对话，流式返回
    """
    try:
        from openai import OpenAI
    except ImportError:
        return ApiResponse.error(description="请先安装openai包: pip install openai")

    task_id = req.task_id or str(uuid.uuid4())
    if task_id not in _codegen_tasks:
        _codegen_tasks[task_id] = {
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "generated_code": None,
            "file_context": None,
            "file_context_injected": False,
        }

    task = _codegen_tasks[task_id]

    # 若有未注入的文件上下文，附加到本次用户消息前
    user_content = req.message
    if task.get("file_context") and not task.get("file_context_injected"):
        user_content = (
            "[以下是用户上传的已有代码文件，请将其重构为MCP模块规范。"
            "遵循最小改动原则：辅助文件/子目录内容原样保留，"
            "重点调整 _mcp.py（改为 register_tools/unregister_tools 模式，**保留原有工具的description**）、"
            "_tool.py（工具函数参数补充 Annotated+Field 注解）、"
            "以及新增规范的 __init__.py。输出的 files 数组需包含所有文件。]\n\n"
            + task["file_context"]
            + "\n\n[用户请求]\n"
            + req.message
        )
        task["file_context_injected"] = True

    task["messages"].append({"role": "user", "content": user_content})

    api_key = req.api_key
    base_url = req.base_url
    model = req.model

    if not api_key:
        return ApiResponse.error(description="未配置LLM API Key")

    import httpx
    import traceback
    max_tokens = req.max_tokens or 8192
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=httpx.Timeout(connect=10.0, read=None, write=None, pool=None),
    )

    queue: asyncio.Queue = asyncio.Queue()

    async def producer():
        full_content = ""
        chunk_count = 0
        finish_reason = None
        app_logger.info(f"[codegen stream] 开始 task_id={task_id} model={model} max_tokens={max_tokens}")
        try:
            stream = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=task["messages"],
                temperature=0.3,
                max_tokens=max_tokens,
                stream=True
            )

            _sentinel = object()

            def _next_chunk():
                try:
                    return next(stream)
                except StopIteration:
                    return _sentinel

            while True:
                chunk = await asyncio.to_thread(_next_chunk)
                if chunk is _sentinel:
                    break
                if chunk.choices:
                    choice = chunk.choices[0]
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                    if choice.delta.content:
                        content = choice.delta.content
                        full_content += content
                        chunk_count += 1
                        await queue.put(f"data: {json.dumps({'content': content, 'task_id': task_id}, ensure_ascii=False)}\n\n")

            app_logger.info(
                f"[codegen stream] 完成 task_id={task_id} chunks={chunk_count} "
                f"chars={len(full_content)} finish_reason={finish_reason}"
            )
            if finish_reason == "length":
                app_logger.warning(
                    f"[codegen stream] 输出被截断(max_tokens={max_tokens}) task_id={task_id}，"
                    f"已输出 {len(full_content)} 字符，请增大 max_tokens"
                )

            # 完成后保存消息
            task["messages"].append({"role": "assistant", "content": full_content})

            # 尝试解析代码
            try:
                code_data = _extract_json(full_content)
                if code_data and "files" in code_data:
                    task["generated_code"] = code_data
            except Exception as e:
                app_logger.debug(f"解析生成代码JSON失败: {e}")

            done_payload: dict = {'done': True, 'task_id': task_id, 'has_code': task['generated_code'] is not None}
            if finish_reason == "length":
                done_payload['warning'] = f"输出已被截断(max_tokens={max_tokens})，代码可能不完整，请增大 max_tokens 后重试"
            await queue.put(f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n")

        except Exception as e:
            app_logger.error(
                f"[codegen stream] 异常 task_id={task_id} chunks={chunk_count} "
                f"chars={len(full_content)} error={e}\n{traceback.format_exc()}"
            )
            await queue.put(f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n")
        finally:
            await queue.put(None)  # 结束信号

    async def generate():
        asyncio.create_task(producer())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/preview/{task_id}")
async def preview_code(task_id: str):
    """预览生成的模块代码"""
    if task_id not in _codegen_tasks:
        return ApiResponse.error(description="任务不存在")

    task = _codegen_tasks[task_id]
    if not task["generated_code"]:
        return ApiResponse.error(description="尚未生成代码，请继续与AI对话")

    return ApiResponse.success(
        data=task["generated_code"],
        description="获取代码预览成功"
    )


@router.post("/download/{task_id}")
async def download_code(task_id: str):
    """将生成的代码打包为zip下载"""
    if task_id not in _codegen_tasks:
        return ApiResponse.error(description="任务不存在")

    task = _codegen_tasks[task_id]
    if not task["generated_code"]:
        return ApiResponse.error(description="尚未生成代码")

    code_data = task["generated_code"]
    module_name = code_data.get("module_name", "t_custom_module")

    # 创建zip文件
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, f"{module_name}.zip")

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in code_data["files"]:
                zf.writestr(file_info["path"], file_info["content"])

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{module_name}.zip"
        )
    except Exception as e:
        return ApiResponse.error(description=f"打包失败: {str(e)}")


@router.post("/install/{task_id}")
async def install_code(task_id: str, force: bool = False):
    """将生成的代码直接安装到平台"""
    if task_id not in _codegen_tasks:
        return ApiResponse.error(description="任务不存在")

    task = _codegen_tasks[task_id]
    if not task["generated_code"]:
        return ApiResponse.error(description="尚未生成代码")

    code_data = task["generated_code"]

    try:
        from mcp_service import module_manager

        module_name_dir = code_data.get("module_name", "")
        if not module_name_dir:
            return ApiResponse.error(description="无法确定模块名称")

        # 安装前检查是否已存在同名模块
        existing_module_name = module_manager._find_existing_module(module_name_dir)
        if existing_module_name and not force:
            return ApiResponse.error(
                description=f"模块 {existing_module_name} 已存在",
                data={"exists": True, "module_name": existing_module_name}
            )

        # force=True 时先删除旧模块
        if existing_module_name and force:
            module_manager.delete_module(existing_module_name)

        # 将代码文件写入外部模块目录
        for file_info in code_data["files"]:
            file_path = module_manager.EXTERNAL_TOOLS_DIR / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info["content"], encoding='utf-8')

        # 查找MCP文件确定module_name
        module_dir = module_manager.EXTERNAL_TOOLS_DIR / module_name_dir
        mcp_files = list(module_dir.glob('*_mcp.py'))
        if not mcp_files:
            return ApiResponse.error(description="模块中未找到 *_mcp.py 文件")

        module_import_name = f"{module_name_dir}.{mcp_files[0].stem}"

        # 安装依赖
        req_file = module_dir / "requirements.txt"
        if req_file.exists():
            import subprocess, sys
            await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                capture_output=True, text=True, timeout=120
            )

        # 自动加载模块，工具默认启用（但模块默认不启用，需要用户手动启用模块）
        result = module_manager.load_module(module_import_name, is_external=True, default_tools_enabled=True)

        # 安装后立即将模块标记为未加载（loaded=False），用户需手动启用
        if module_import_name in module_manager._modules:
            module_manager._modules[module_import_name].loaded = False
            module_manager._db_update_module_loaded(module_import_name, False)
            for tool in module_manager._modules[module_import_name].tools:
                tool_obj = module_manager.mcp._tool_manager._tools.get(tool['name'])
                if tool_obj:
                    tool_obj.enabled = False

        return ApiResponse.success(
            data=result.get("module_info"),
            description=result["message"]
        )

    except Exception as e:
        app_logger.exception("安装生成的模块失败")
        return ApiResponse.error(description=f"安装失败: {str(e)}")


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """删除对话任务"""
    if task_id in _codegen_tasks:
        del _codegen_tasks[task_id]
    return ApiResponse.success(description="任务已删除")


@router.get("/system-prompt")
async def get_system_prompt():
    """获取代码生成的系统提示词"""
    return ApiResponse.success(
        data={"system_prompt": SYSTEM_PROMPT},
        description="获取系统提示词成功"
    )


@router.post("/upload")
async def upload_context(
    files: list[UploadFile] = File(...),
    task_id: Optional[str] = Form(None),
):
    """
    上传文件或文件夹（zip包）作为代码生成的参考上下文。
    支持：普通文本/代码文件、zip压缩包（文件夹）、Markdown文档。
    """
    task_id = task_id or str(uuid.uuid4())
    if task_id not in _codegen_tasks:
        _codegen_tasks[task_id] = {
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "generated_code": None,
            "file_context": None,
            "file_context_injected": False,
        }

    task = _codegen_tasks[task_id]
    file_sections = []
    file_summary = []

    for upload in files:
        filename = upload.filename or "unknown"
        raw = await upload.read()
        suffix = Path(filename).suffix.lower()

        if suffix == ".zip":
            # 解压 zip，读取其中的文本文件
            import io
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    for member in zf.infolist():
                        if member.is_dir():
                            continue
                        member_suffix = Path(member.filename).suffix.lower()
                        if member_suffix not in _TEXT_EXTENSIONS:
                            continue
                        try:
                            content = zf.read(member).decode("utf-8", errors="replace")
                            file_sections.append(f"### 文件：{member.filename}\n```\n{content}\n```")
                            file_summary.append(member.filename)
                        except Exception as e:
                            app_logger.debug(f"读取zip成员 {member.filename} 失败: {e}")
            except Exception as e:
                return ApiResponse.error(description=f"解压 zip 失败: {e}")
        elif suffix in _TEXT_EXTENSIONS:
            try:
                content = raw.decode("utf-8", errors="replace")
                file_sections.append(f"### 文件：{filename}\n```\n{content}\n```")
                file_summary.append(filename)
            except Exception as e:
                app_logger.debug(f"解码上传文件 {filename} 失败: {e}")
        else:
            # 不支持的文件类型，跳过
            file_summary.append(f"{filename}（已跳过，不支持的文件类型）")

    if not file_sections:
        return ApiResponse.error(description="未能读取到任何有效文本内容，请上传文本/代码文件或 zip 压缩包")

    task["file_context"] = "\n\n".join(file_sections)
    task["file_context_injected"] = False  # 重置，下次 chat 时注入

    return ApiResponse.success(
        data={"task_id": task_id, "files": file_summary},
        description=f"已上传 {len(file_sections)} 个文件，发送消息时将自动作为上下文",
    )


def _extract_json(text: str) -> Optional[dict]:
    """从文本中提取JSON对象"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从markdown代码块中提取
    import re
    json_match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试找到第一个 { 和最后一个 }
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None
