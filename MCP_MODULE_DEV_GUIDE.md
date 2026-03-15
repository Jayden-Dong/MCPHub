# MCP 模块插件开发指南

本文档面向第三方开发者，介绍如何为 **GeneralMCPTool** 平台开发自定义 MCP 模块插件，并将其安装到平台上使用。

---

## 目录

1. [前置知识](#1-前置知识)
2. [模块目录结构](#2-模块目录结构)
3. [模块元信息（MODULE_INFO）](#3-模块元信息module_info)
4. [工具注册（*_mcp.py）](#4-工具注册_mcppy)
5. [业务逻辑（*_tool.py）](#5-业务逻辑_toolpy)
6. [读取模块配置](#6-读取模块配置)
7. [工具描述管理（prompt.yaml）](#7-工具描述管理promptyaml)
8. [工具返回值规范](#8-工具返回值规范)
9. [WebAPI 热加载](#9-webapi-热加载)
10. [打包与安装](#10-打包与安装)
11. [在 config.json 中配置模块](#11-在-configjson-中配置模块)
12. [完整示例：天气查询模块](#12-完整示例天气查询模块)
13. [常见问题](#13-常见问题)

---

## 1. 前置知识

- **Python 3.10+** 基础
- 了解 [MCP 协议](https://modelcontextprotocol.io/) 的基本概念（Tool、Resource）
- 了解 **fastmcp** 的 `@mcp.tool` 装饰器用法

平台使用 `fastmcp` 管理 MCP 工具注册，开发者无需关心 MCP 底层通信，只需按规范编写工具函数并注册即可。

---

## 2. 模块目录结构

每个模块是一个 **Python 包**（含 `__init__.py` 的目录）。最简结构：

```
my_module/
├── __init__.py          # 必须，可为空
├── my_module_mcp.py     # 工具注册文件（核心）
└── my_module_tool.py    # 业务逻辑实现（推荐分离）
```

推荐完整结构：

```
my_module/
├── __init__.py
├── MODULE_INFO          # 模块元信息文件
├── my_module_mcp.py     # 工具注册（@mcp.tool 装饰器）
├── my_module_tool.py    # 业务逻辑
└── requirements.txt     # 模块专属依赖（可选）
```

> **命名约定**：模块目录名即为模块的唯一标识（如 `my_module`）。外部模块安装后，其 Python 导入路径为 `my_module.my_module_mcp`。

---

## 3. 模块元信息（MODULE_INFO）

在模块目录下创建名为 `MODULE_INFO` 的文本文件（无扩展名），内容为 JSON 格式：

```json
{
  "display_name": "天气查询模块",
  "version": "1.0.0",
  "description": "通过公开 API 查询全球城市的实时天气数据。",
  "author": "Your Name"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `display_name` | string | 推荐 | 在 Web 管理界面显示的名称 |
| `version` | string | 推荐 | 语义化版本号（如 `1.2.0`） |
| `description` | string | 推荐 | 模块功能描述 |
| `author` | string | 可选 | 作者名称 |

若不提供 `MODULE_INFO`，平台将使用模块目录名作为 `display_name`，版本默认为 `1.0.0`。

---

## 4. 工具注册（*_mcp.py）

工具注册文件是模块的**核心**。使用 `@mcp.tool` 装饰器将函数注册为 MCP 工具。

### 4.1 基本写法

```python
# my_module/my_module_mcp.py

from mcp_service import mcp                        # 获取全局 FastMCP 实例
from config_py.config import settings              # 获取全局配置（含工具名前缀）
from config_py.prompt import prompt_manager        # 工具描述管理器
from utils import com_utils                        # 工具启用状态检查
from utils.com_utils import get_mcp_exposed_url    # 获取 MCP 服务暴露 URL

from my_module.my_module_tool import my_tool       # 引入业务逻辑

# 工具的原始名称（不含前缀）
TOOL_NAME = "get_weather"

@mcp.tool(
    name=f'{settings.MCP_TOOL_NAME_PREFIX}{TOOL_NAME}',
    description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(TOOL_NAME)}',
    enabled=com_utils.get_tool_enable(TOOL_NAME),
)
def get_weather(city: str, unit: str = "celsius") -> dict:
    """
    查询指定城市的实时天气。

    参数:
        city: 城市名称，支持中英文（如 "北京" 或 "Beijing"）
        unit: 温度单位，"celsius"（摄氏）或 "fahrenheit"（华氏），默认 celsius

    返回:
        包含天气信息的字典
    """
    return my_tool.get_weather(city, unit)
```

### 4.2 关键说明

**工具名称**

工具名称必须以平台前缀开头：

```python
name=f'{settings.MCP_TOOL_NAME_PREFIX}{TOOL_NAME}'
```

`settings.MCP_TOOL_NAME_PREFIX` 由 `config.json` 中的 `tool_name_prefix` 字段设置（如 `"ComputerA_"`），用于区分多台机器。开发者**不应硬编码**前缀，始终使用 `settings.MCP_TOOL_NAME_PREFIX`。

**工具描述**

```python
description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(TOOL_NAME)}'
```

- 固定格式：先附上 MCP 服务 URL（便于 AI 客户端识别服务位置），再附上工具说明
- `prompt_manager.get(TOOL_NAME)` 从 `prompt.yaml` 热加载描述，返回 `str`
- 若 `prompt.yaml` 中无该条目，会返回空字符串，此时 `description` 仅含 URL

**工具启用状态**

```python
enabled=com_utils.get_tool_enable(TOOL_NAME)
```

`get_tool_enable` 检查 `config.json` 的 `disable_tool` 列表，若工具名在其中则返回 `False`（禁用）。这允许管理员在配置文件中禁用指定工具，无需修改代码。

**函数签名**

- 参数类型注解（`str`、`int`、`float`、`bool`、`list`、`dict`）会被 MCP 客户端用于生成调用界面，请务必添加
- 有默认值的参数为可选参数
- 函数 docstring 作为工具的补充说明（会与 `description` 合并）

### 4.3 注册多个工具

在同一个 `*_mcp.py` 文件中可以注册任意数量的工具：

```python
TOOL_FORECAST = "get_forecast"

@mcp.tool(
    name=f'{settings.MCP_TOOL_NAME_PREFIX}{TOOL_FORECAST}',
    description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(TOOL_FORECAST)}',
    enabled=com_utils.get_tool_enable(TOOL_FORECAST),
)
def get_forecast(city: str, days: int = 7) -> dict:
    """查询未来天气预报。"""
    return my_tool.get_forecast(city, days)
```

---

## 5. 业务逻辑（*_tool.py）

推荐将业务逻辑与工具注册分离，便于测试和维护。

```python
# my_module/my_module_tool.py

import requests
from config_py.logger import app_logger
from config_py.config import settings


class MyTool:
    """天气查询工具业务逻辑"""

    def __init__(self):
        # 从平台配置中读取模块专属配置
        cfg = settings.get_module_config("my_module.my_module_mcp")
        self.api_key = cfg.get("api_key", "")
        self.base_url = cfg.get("base_url", "https://api.example.com")

    def get_weather(self, city: str, unit: str = "celsius") -> dict:
        try:
            resp = requests.get(
                f"{self.base_url}/current",
                params={"city": city, "unit": unit, "key": self.api_key},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "data": data}
        except Exception as e:
            app_logger.error(f"查询天气失败: {e}")
            return {"success": False, "error": str(e)}

    def get_forecast(self, city: str, days: int = 7) -> dict:
        # ... 实现逻辑
        pass


# 单例，供 *_mcp.py 调用
my_tool = MyTool()
```

---

## 6. 读取模块配置

平台通过 `config.json` 向每个模块注入配置。在业务代码中读取方式：

### 方法一：通过 `settings.get_module_config()`

```python
from config_py.config import settings

# 传入模块的完整 Python 路径
cfg = settings.get_module_config("my_module.my_module_mcp")
api_key = cfg.get("api_key", "default_value")
```

### 方法二：直接访问 `settings`（适用于全局配置）

```python
from config_py.config import settings

# 全局服务配置
host = settings.HOST
port = settings.PORT
```

### 在 config.json 中定义模块配置

```json
{
  "mcp": {
    "module_enable": [
      {
        "enable": true,
        "module_name": "my_module.my_module_mcp",
        "disable_tool": [],
        "config": {
          "api_key": "your-api-key-here",
          "base_url": "https://api.weatherservice.com"
        }
      }
    ]
  }
}
```

> **重要**：`config` 节点下的所有字段由你自由定义，平台不做任何约束，原样传递给模块。

---

## 7. 工具描述管理（prompt.yaml）

工具描述存储在平台的 `app/config/prompt.yaml` 文件中，支持**热更新**（修改后无需重启）。

在 `prompt.yaml` 中添加条目：

```yaml
# 以工具原始名（不含前缀）为 key
get_weather: |
  查询指定城市的实时天气数据。

  参数说明：
  - city：城市名称，支持中英文，如"北京"或"Beijing"
  - unit：温度单位，"celsius"（摄氏，默认）或"fahrenheit"（华氏）

  返回说明：
  - success：是否成功（bool）
  - data.temperature：当前温度
  - data.humidity：湿度百分比
  - data.description：天气描述

get_forecast: |
  查询指定城市未来 N 天的天气预报。

  参数说明：
  - city：城市名称
  - days：预报天数，1-14，默认7
```

**建议**：在工具描述中详细说明参数格式、返回值结构，这将直接影响 AI 客户端调用工具的准确率。

---

## 8. 工具返回值规范

工具函数应始终返回 `dict`，推荐以下格式：

### 成功响应

```python
{
    "success": True,
    "data": {
        # 具体数据...
    },
    "message": "操作成功"   # 可选
}
```

### 失败响应

```python
{
    "success": False,
    "error": "错误原因描述",
    "data": None
}
```

**原则**：

- 返回 `dict` 而非抛出异常（异常会被 MCP 框架捕获并返回错误，但不如结构化响应清晰）
- `success` 字段帮助 AI 客户端快速判断是否需要重试或报错
- 错误信息应对用户友好，便于 AI 向用户描述问题

---

## 9. WebAPI 热加载

除了 MCP 工具，模块还可以提供 REST API 接口（WebAPI），这些接口可以在模块加载/卸载时自动注册/注销，实现热加载。

### 9.1 基本用法

在模块目录中创建 `webapi.py` 文件，定义一个 FastAPI 子应用 `webapi_app`：

```
my_module/
├── __init__.py          # 导入 webapi_app
├── webapi.py            # WebAPI 定义（新增）
├── my_module_mcp.py     # MCP 工具注册
└── my_module_tool.py    # 业务逻辑
```

### 9.2 webapi.py 示例

```python
# my_module/webapi.py
from fastapi import FastAPI
from pydantic import BaseModel

# 创建模块的独立子应用
# 注意：变量名必须是 webapi_app
webapi_app = FastAPI(
    docs_url=None,   # 禁用独立的 /docs
    redoc_url=None   # 禁用独立的 /redoc
)


class CalcRequest(BaseModel):
    a: float
    b: float


@webapi_app.get("/hello")
def hello():
    """健康检查"""
    return {"msg": "hello from my_module webapi"}


@webapi_app.post("/calculate")
def calculate(req: CalcRequest):
    """计算接口"""
    return {"result": req.a + req.b}
```

### 9.3 在 __init__.py 中导入

确保 `webapi_app` 可以从模块根目录导入：

```python
# my_module/__init__.py
from .webapi import webapi_app

# MODULE_INFO 等其他内容...
MODULE_INFO = {
    "display_name": "我的模块",
    "version": "1.0.0",
    "description": "示例模块"
}
```

### 9.4 API 挂载路径

模块加载后，WebAPI 会自动挂载到：

```
http://host:port/api/{模块目录名}/{路由路径}
```

例如，`my_module` 模块的 `/hello` 接口将挂载到：

```
http://localhost:6080/api/my_module/hello
http://localhost:6080/api/my_module/calculate
```

### 9.5 热加载生命周期

| 操作 | WebAPI 行为 |
|------|------------|
| 模块加载 | 自动挂载 `webapi_app` 到 `/api/{模块名}/` |
| 模块卸载 | 自动移除挂载的 WebAPI 路由 |
| 模块重载 | 先卸载旧的，再加载新的 |

### 9.6 完整示例

参考 `tools_external/t_calculator` 模块：

```
tools_external/t_calculator/
├── __init__.py           # 导入 webapi_app
├── webapi.py             # WebAPI 子应用
├── calculator_tool.py    # 业务逻辑
└── MODULE_INFO           # 模块信息
```

`webapi.py`:
```python
from fastapi import FastAPI
from pydantic import BaseModel

webapi_app = FastAPI(docs_url=None, redoc_url=None)


class CalcRequest(BaseModel):
    a: float
    b: float


@webapi_app.get("/hello")
def hello():
    return {"msg": "hello from calculator webapi"}


@webapi_app.post("/add")
def add(req: CalcRequest):
    return {"result": req.a + req.b, "operation": "add"}
```

`__init__.py`:
```python
from .webapi import webapi_app

MODULE_INFO = {
    "display_name": "计算器",
    "version": "1.0.1",
    "description": "提供基本数学运算功能"
}

def register(mcp_instance):
    # MCP 工具注册逻辑...
    pass
```

加载模块后，可通过以下 URL 访问：
- `GET /api/t_calculator/hello`
- `POST /api/t_calculator/add`

### 9.7 注意事项

1. **变量名必须是 `webapi_app`**：平台通过查找该变量名来识别 WebAPI
2. **使用子应用而非 APIRouter**：子应用通过 `mount()` 挂载，支持完整的隔离和卸载
3. **禁用独立文档**：建议设置 `docs_url=None, redoc_url=None`，避免与主应用文档冲突
4. **业务逻辑复用**：WebAPI 可以调用 `*_tool.py` 中的业务逻辑，与 MCP 工具共享代码

---

## 10. 打包与安装

### 打包为 ZIP

将模块目录打包为 ZIP 文件：

```bash
# 目录结构：
# my_module/
#   __init__.py
#   MODULE_INFO
#   my_module_mcp.py
#   my_module_tool.py

# 打包（ZIP 内顶层就是模块目录）
zip -r my_module.zip my_module/
```

**注意**：ZIP 包内**顶层**必须是模块目录（`my_module/`），不要多套一层目录，也不要把模块文件直接放在 ZIP 根目录。

### 通过 Web 界面安装

1. 打开管理界面 `http://localhost:6080`
2. 进入「模块管理」页面
3. 点击「安装模块」，上传 ZIP 文件
4. 安装成功后，在模块列表中找到新模块，点击「加载」

### 通过 API 安装

```bash
curl -X POST http://localhost:6080/api/modules/install \
  -F "file=@my_module.zip"
```

响应示例：

```json
{
  "Code": 12,
  "Message": {"Description": "模块安装成功"},
  "Data": {"module_name": "my_module.my_module_mcp"}
}
```

### 加载模块（安装后需手动加载）

```bash
curl -X POST http://localhost:6080/api/modules/load \
  -H "Content-Type: application/json" \
  -d '{"module_name": "my_module.my_module_mcp", "config": {"api_key": "xxx"}}'
```

---

## 11. 在 config.json 中配置模块

如果希望服务**启动时自动加载**模块，将其加入 `config.json` 的 `module_enable` 列表：

```json
{
  "mcp": {
    "module_enable": [
      {
        "enable": true,
        "module_name": "my_module.my_module_mcp",
        "disable_tool": [],
        "config": {
          "api_key": "your-api-key",
          "base_url": "https://api.example.com"
        }
      }
    ]
  }
}
```

| 字段 | 说明 |
|------|------|
| `enable` | `true` 启用，`false` 跳过加载 |
| `module_name` | Python 导入路径，格式为 `{包名}.{mcp文件名}` |
| `disable_tool` | 工具原始名列表（不含前缀），列表中的工具将被禁用 |
| `config` | 传递给模块的配置字典，模块通过 `settings.get_module_config()` 读取 |

---

## 12. 完整示例：天气查询模块

以下是一个完整的可运行示例。

### 目录结构

```
t_weather/
├── __init__.py
├── MODULE_INFO
├── weather_mcp.py
└── weather_tool.py
```

### `__init__.py`

```python
# 空文件，标记为 Python 包
```

### `MODULE_INFO`

```json
{
  "display_name": "天气查询",
  "version": "1.0.0",
  "description": "查询全球城市实时天气和未来预报（使用 OpenWeatherMap API）",
  "author": "Your Name"
}
```

### `weather_tool.py`

```python
import requests
from config_py.config import settings
from config_py.logger import app_logger


class WeatherTool:

    def __init__(self):
        cfg = settings.get_module_config("t_weather.weather_mcp")
        self.api_key = cfg.get("api_key", "")
        self.base_url = "https://api.openweathermap.org/data/2.5"

    def get_current_weather(self, city: str, unit: str = "metric") -> dict:
        """查询当前天气"""
        if not self.api_key:
            return {"success": False, "error": "未配置 API Key，请在 config.json 中设置 api_key"}
        try:
            resp = requests.get(
                f"{self.base_url}/weather",
                params={"q": city, "units": unit, "appid": self.api_key},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "data": {
                    "city": data["name"],
                    "country": data["sys"]["country"],
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"],
                    "wind_speed": data["wind"]["speed"],
                }
            }
        except requests.HTTPError as e:
            return {"success": False, "error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            app_logger.error(f"天气查询失败: {e}")
            return {"success": False, "error": str(e)}

    def get_forecast(self, city: str, days: int = 5) -> dict:
        """查询未来天气预报"""
        if not self.api_key:
            return {"success": False, "error": "未配置 API Key"}
        try:
            resp = requests.get(
                f"{self.base_url}/forecast",
                params={"q": city, "cnt": days * 8, "appid": self.api_key},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            # 简化：每天取第一条记录
            forecasts = []
            seen_dates = set()
            for item in data["list"]:
                date = item["dt_txt"].split(" ")[0]
                if date not in seen_dates:
                    seen_dates.add(date)
                    forecasts.append({
                        "date": date,
                        "temperature": item["main"]["temp"],
                        "description": item["weather"][0]["description"],
                    })
            return {"success": True, "data": {"city": data["city"]["name"], "forecasts": forecasts}}
        except Exception as e:
            app_logger.error(f"天气预报查询失败: {e}")
            return {"success": False, "error": str(e)}


# 单例
weather_tool = WeatherTool()
```

### `weather_mcp.py`

```python
"""
天气查询 MCP 工具定义
提供城市实时天气查询和未来天气预报功能
"""
from mcp_service import mcp
from config_py.config import settings
from config_py.prompt import prompt_manager
from utils import com_utils
from utils.com_utils import get_mcp_exposed_url

from t_weather.weather_tool import weather_tool

# ---- 当前天气 ----
CURRENT_WEATHER = "get_current_weather"

@mcp.tool(
    name=f'{settings.MCP_TOOL_NAME_PREFIX}{CURRENT_WEATHER}',
    description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(CURRENT_WEATHER)}',
    enabled=com_utils.get_tool_enable(CURRENT_WEATHER),
)
def get_current_weather(city: str, unit: str = "metric") -> dict:
    """
    查询指定城市的实时天气。

    参数:
        city: 城市名称，支持英文（如 "Beijing"）
        unit: 单位制，"metric"（摄氏，默认）或 "imperial"（华氏）

    返回:
        包含温度、湿度、天气描述等信息的字典
    """
    return weather_tool.get_current_weather(city, unit)


# ---- 天气预报 ----
FORECAST = "get_forecast"

@mcp.tool(
    name=f'{settings.MCP_TOOL_NAME_PREFIX}{FORECAST}',
    description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(FORECAST)}',
    enabled=com_utils.get_tool_enable(FORECAST),
)
def get_forecast(city: str, days: int = 5) -> dict:
    """
    查询指定城市未来天气预报。

    参数:
        city: 城市名称（英文）
        days: 预报天数，1-5，默认5

    返回:
        包含每日预报列表的字典
    """
    return weather_tool.get_forecast(city, days)
```

### 添加工具描述到 prompt.yaml

在平台的 `app/config/prompt.yaml` 中追加：

```yaml
get_current_weather: |
  查询指定城市的实时天气数据（使用 OpenWeatherMap API）。

  参数：
  - city（必填）：城市名，英文，如 "Beijing"、"Shanghai"
  - unit（可选）：温度单位，"metric"=摄氏（默认），"imperial"=华氏

  返回字段：
  - success：是否成功
  - data.temperature：当前温度
  - data.humidity：湿度（%）
  - data.description：天气描述（如 "clear sky"）
  - data.wind_speed：风速（m/s）

get_forecast: |
  查询城市未来最多5天的天气预报。

  参数：
  - city（必填）：城市名，英文
  - days（可选）：天数，1-5，默认5

  返回字段：
  - success：是否成功
  - data.forecasts：预报列表，每项含 date、temperature、description
```

### 在 config.json 中启用模块

```json
{
  "mcp": {
    "module_enable": [
      {
        "enable": true,
        "module_name": "t_weather.weather_mcp",
        "disable_tool": [],
        "config": {
          "api_key": "your-openweathermap-api-key"
        }
      }
    ]
  }
}
```

### 打包安装

```bash
# 项目目录下执行
zip -r t_weather.zip t_weather/

# 上传安装
curl -X POST http://localhost:6080/api/modules/install \
  -F "file=@t_weather.zip"
```

---

## 13. 常见问题

### Q: 模块安装后找不到工具？

检查以下几点：
1. 确认 ZIP 包结构正确，顶层是模块目录
2. 确认 `*_mcp.py` 文件中 `@mcp.tool` 装饰器的 `name` 已包含 `settings.MCP_TOOL_NAME_PREFIX`
3. 安装后需要手动「加载」模块，或重启服务（若已在 `config.json` 中配置）
4. 查看 `logs/log.log` 日志确认是否有报错

### Q: 如何调试模块？

1. 查看 `logs/log.log` 了解模块加载过程
2. 查看 `logs/mcp.log` 了解工具调用的入参和返回值
3. 通过 Swagger UI（`http://localhost:6080/docs`）测试相关 REST API

### Q: 模块的 Python 依赖如何安装？

外部模块如果有额外依赖（如 `requests`），需要在部署环境中提前安装：

```bash
pip install requests
```

或者在模块目录中提供 `requirements.txt`，提醒平台管理员手动安装：

```
# my_module/requirements.txt
requests>=2.28.0
```

> 注：平台目前不会自动安装模块的依赖，需手动执行 `pip install`。

### Q: 工具描述修改后不生效？

工具描述从 `app/config/prompt.yaml` 热加载，只在 MCP 客户端调用 `list_tools` 时更新。修改 YAML 后，让 MCP 客户端重新获取工具列表即可（如在 Claude Desktop 中刷新连接）。

### Q: 如何禁用某个工具而不删除模块？

两种方式：
1. **Web 界面**：进入模块详情，点击工具旁的开关
2. **config.json**：在对应模块的 `disable_tool` 列表中加入工具原始名（不含前缀）

```json
{
  "module_name": "my_module.my_module_mcp",
  "disable_tool": ["get_forecast"]
}
```

### Q: 如何让模块在服务重启后自动加载？

将模块配置加入 `app/config/config.json` 的 `mcp.module_enable` 列表，并设置 `"enable": true`。

### Q: 工具名称有什么限制？

工具原始名（不含前缀）建议：
- 使用小写字母、数字和下划线
- 全局唯一（不同模块之间的工具名不要重复）
- 长度适中，便于 AI 理解含义

最终注册到 MCP 的工具名格式为：`{前缀}{工具名}`，例如 `ComputerA_get_weather`。

---

## 附录：平台可用的辅助函数

在 `*_mcp.py` 和 `*_tool.py` 中可以使用以下平台提供的工具：

```python
# 全局 FastMCP 实例（用于注册工具）
from mcp_service import mcp

# 全局配置对象
from config_py.config import settings
settings.MCP_TOOL_NAME_PREFIX   # 工具名前缀（str）
settings.HOST                   # API 服务 Host
settings.PORT                   # API 服务 Port
settings.get_module_config(module_name)  # 获取模块配置 dict

# 工具描述管理器（热加载 prompt.yaml）
from config_py.prompt import prompt_manager
prompt_manager.get("tool_name")  # 返回工具描述 str

# 日志
from config_py.logger import app_logger
app_logger.info("...")
app_logger.error("...")

# 工具启用状态检查（根据 config.json 的 disable_tool）
from utils import com_utils
com_utils.get_tool_enable("tool_name")  # 返回 bool

# 获取 MCP 服务暴露的 URL
from utils.com_utils import get_mcp_exposed_url
get_mcp_exposed_url()  # 返回如 "http://localhost:6081/mcp"
```
