[English](README.md) | [中文](README_ZH.md)

# MCPHub

<h3 align="center">🚀 一个 MCP 工具服务平台 - 让 AI Agent 只需一个连接，拥有无限能力</h3>

<p align="center">
  <a href="#-核心亮点">核心亮点</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-功能详解">功能详解</a> •
  <a href="#-api-文档">API 文档</a> •
  <a href="#-开发指南">开发指南</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastMCP-2.14+-green.svg" alt="FastMCP">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

---

## 📸 系统截图

### 登录界面
![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/login.png)


> 初始账号：admin，初始密码：admin123

### 模块管理界面

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/modules.png)


> 管理所有 MCP 模块，支持加载、卸载、重载操作

### 工具详情与控制

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/tool%20detail.png)


> 单独启用/禁用每个工具，实时编辑工具描述

### 代理服务器管理

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/extended%20mcp.png)


> 代理现有 MCP Server，无需改造即可接入

### 使用统计看板

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/statistics.png)


> 可视化展示工具调用次数、成功率、响应时间

### AI 代码生成

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/ai%20coding.png)


> 通过自然语言对话生成 MCP 插件代码

---

## 🎯 这是什么？

**MCPHub** 是一个基于 MCP (Model Context Protocol) 协议的**工具服务平台**。它解决了当前 AI Agent 系统的一个痛点：

> 每个 MCP Server 都需要在客户端单独配置，当工具数量增多时，配置管理变得混乱。

**MCPHub 的解决方案：**

```
┌─────────────────────────────────────────────────────────────────┐
│                    之前：分散配置                                
│  Claude/Cursor 需要配置数十个 MCP Server 地址                    
│  - mcp-server-filesystem                                        
│  - mcp-server-github                                            
│  - mcp-server-postgres                                          
│  - mcp-server-python                                            
│  - ... (配置爆炸)                                                
└─────────────────────────────────────────────────────────────────┘
                              ⬇️
┌─────────────────────────────────────────────────────────────────────────┐
│                    之后：统一入口                                
│  Claude/Cursor 只需配置一个地址                                 
│  { "mcpServers": { "mcp-hub": { "url": "http://host:6081/mcp" } } } 
│                                                                 
│  MCP Hub 自动聚合所有工具，实现：                                
│  ✅ 集中式工具管理                                               
│  ✅ 热插拔启用/禁用                                              
│  ✅ 统一监控统计                                                 
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ 核心亮点

### 1️⃣ 一个地址，无限工具

AI Agent 客户端只需配置**一个 MCP Server 地址**，即可访问平台上所有工具。无论是内置工具、自定义插件，还是代理的第三方 MCP Server，都对客户端透明。

### 2️⃣ 热插拔工具管理

- **模块级管理**：加载、卸载、重载模块，无需重启服务
- **工具级控制**：单个工具可独立启用/禁用
- **配置热更新**：工具描述修改后立即生效，无需重启

### 3️⃣ 代理现有 MCP Server

已有 MCP Server？无需改造，直接配置代理即可接入：

```json
{
  "name": "my-existing-server",
  "url": "http://existing-server:8080/mcp",
  "transport": "streamable-http"
}
```

平台会自动发现并透明代理该服务器的所有工具。

### 4️⃣ AI 自动生成 MCP 插件

内置 AI 代码生成功能，通过自然语言对话即可生成符合规范的 MCP 模块代码：

```
用户: 帮我创建一个天气查询工具
AI: 已生成 t_weather 模块，包含 get_current_weather 和 get_forecast 两个工具...
```

**人人都能成为 MCP 工具开发者！**

### 5️⃣ 插件生态：安装与分享

- **一键安装**：上传 ZIP 包即可安装第三方插件
- **一键导出**：将自定义插件打包为 ZIP，分享给其他用户
- **模块化隔离**：内置工具 (`tools/`) 与外部插件 (`tools_external/`) 分离管理

### 6️⃣ 全方位使用统计

直观查看每个工具的使用情况：

- 调用次数统计
- 成功率追踪
- 响应时间分析
- 24 小时趋势图

---

## 🛠️ 内置工具

平台预置了核心工具模块，开箱即用：

| 类别 | 模块 | 工具 | 说明 |
|------|------|------|------|
| **🖥️ CLI 执行** | `t_cli` | `run_cli_command`, `list_directory`, `get_system_info`, `get_disk_usage`, `get_running_processes`, `find_files`... | 执行系统命令、查看进程、磁盘监控、网络信息 |
| **🐍 Python 执行** | `t_python` | `run_python_script`, `install_package`, `run_python_script_async`, `get_script_status` | 安全执行 Python 脚本、安装依赖包、异步执行 |
| **🤖 GUI 自动化** | `t_autogui` | `autogui_start_task`, `autogui_get_status`, `autogui_get_history`, `autogui_stop_task` | AI 驱动的桌面自动化，自动操作鼠标键盘 |
| **📓 笔记本** | `t_notebook` | `add_note`, `read_note` | 笔记创建与查询，持久化存储 |

### 特色功能：AI 驱动 GUI 自动化

`t_autogui` 模块实现了 **AI 驱动的桌面自动化**：

```
用户: 帮我打开浏览器并访问 GitHub
Agent: [调用 autogui_start_task] → AI 规划任务步骤 → 执行鼠标键盘操作
```

这是本平台的**杀手级功能**：AI 可以像人类一样操作电脑桌面，完成复杂的 GUI 交互任务。

---

## 📦 扩展工具

除了内置工具，平台还支持安装扩展插件。以下是一些可用的扩展工具示例：

| 类别 | 模块 | 工具 | 说明 |
|------|------|------|------|
| **📁 文件操作** | `t_file` | `read_file_utf8`, `write_file_utf8`, `unzip` | 本地文件读写、解压缩 |
| **🌐 FTP 传输** | `t_ftp` | `ftp_upload_file`, `ftp_download_file`, `ftp_create_directory` | FTP 文件传输和管理 |
| **🧬 PDB 数据库** | `t_pdb` | `download_structure`, `convert_cif_to_pdb` | 蛋白质结构数据库查询和格式转换 |
| **🔬 Foldseek** | `t_foldseek` | `foldseek_sort_by_evalue`, `foldseek_sort_by_fident` | 蛋白质结构相似性搜索结果处理 |
| **📊 AlphaBio** | `t_alphabio` | `get_project_info`, `get_enzyme_activity` | AlphaBio 数据库集成 |
| **🧪 DNA 预测** | `t_dna_predict` | `predict_collection_threshold` | DNA 碱基序列收集阈值预测 |
| **🗃️ 项目数据库** | `t_project_db` | `query_project_db`, `get_project_db_schema` | PostgreSQL 项目管理数据库查询 |

> 这些扩展工具位于 `tools_external/` 目录，可通过 Web 界面或 API 按需加载。你也可以开发自己的扩展工具并安装到平台。

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- (可选) Node.js 18+ - 用于构建前端

### 安装

```bash
# 克隆项目
git clone https://github.com/Jayden-Dong/MCPHub.git
cd MCPHub

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 启动服务

```bash
cd app
python main.py
```

启动后访问：
- 🌐 **Web 管理界面**：`http://localhost:6080`
- 📚 **API 文档**：`http://localhost:6080/docs`
- 🔌 **MCP 服务端点**：`http://localhost:6081/mcp`

### 配置 MCP 客户端

在 Claude Desktop / Cursor/Cherry Studio 等 MCP 客户端中添加：

```json
{
  "mcpServers": {
    "general-tools": {
      "url": "http://localhost:6081/mcp"
    }
  }
}
```

🎉 完成！现在您的 AI Agent 可以使用平台上所有已启用的工具。

---

## 📖 功能详解

### 模块管理

通过 Web 界面或 API 管理模块：

```
┌─────────────────────────────────────────────────────────┐
│  模块列表                    [扫描新模块] [安装模块]      
├─────────────────────────────────────────────────────────┤
│  ✅ t_cli        已加载    [详情] [重载] [卸载]          
│  ✅ t_python     已加载    [详情] [重载] [卸载]          
│  ⏸️ t_autogui    已暂停    [详情] [加载]                
│  📦 t_weather    未加载    [详情] [加载]    [导出] [删除]
└─────────────────────────────────────────────────────────┘
```

### 工具级控制

进入模块详情，可单独启用/禁用每个工具：

```
┌─────────────────────────────────────────────────────────┐
│  t_cli 模块详情                                          
├─────────────────────────────────────────────────────────┤
│  🔧 run_cli_command      [✅ 启用]                      
│  🔧 list_directory       [✅ 启用]                      
│  🔧 get_system_info      [❌ 禁用]                      
│  🔧 kill_process         [❌ 禁用]  ⚠️ 危险操作         
└─────────────────────────────────────────────────────────┘
```

### 代理 MCP Server

将现有的 MCP Server 接入平台：

**通过 Web 界面：**
1. 进入「代理管理」页面
2. 点击「添加服务器」
3. 填写服务器名称、URL、传输类型
4. 点击「同步工具」→ 工具自动出现在平台中

**通过 API：**
```bash
curl -X POST http://localhost:6080/api/proxy/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem-server",
    "url": "http://localhost:3000/mcp",
    "transport": "streamable-http"
  }'
```

### AI 代码生成

通过对话生成 MCP 插件：

```bash
# 开始对话
curl -X POST http://localhost:6080/api/codegen/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我创建一个股票查询工具，支持查询实时价格和历史走势"}'

# 预览生成的代码
curl http://localhost:6080/api/codegen/preview/{task_id}

# 直接安装到平台
curl -X POST http://localhost:6080/api/codegen/install/{task_id}
```

### 使用统计

查看工具调用情况：

```bash
# 整体概览
curl http://localhost:6080/api/stats/overview

# 按工具统计
curl http://localhost:6080/api/stats/tools

# 最近调用记录
curl http://localhost:6080/api/stats/recent?limit=100
```

响应示例：
```json
{
  "total_calls": 1523,
  "success_rate": 0.98,
  "top_tools": [
    {"name": "run_python_script", "calls": 456, "avg_duration_ms": 1234},
    {"name": "run_cli_command", "calls": 312, "avg_duration_ms": 567}
  ]
}
```

---

## 🔌 API 文档

### 模块管理 `/api/modules`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/modules` | 获取所有模块列表 |
| GET | `/api/modules/scan` | 扫描未加载的模块 |
| POST | `/api/modules/load` | 加载模块 |
| POST | `/api/modules/{name}/unload` | 卸载模块 |
| POST | `/api/modules/{name}/reload` | 重载模块 |
| POST | `/api/modules/tool/enable` | 启用工具 |
| POST | `/api/modules/tool/disable` | 禁用工具 |
| POST | `/api/modules/install` | 安装 ZIP 插件 |
| GET | `/api/modules/{name}/export` | 导出模块为 ZIP |
| DELETE | `/api/modules/{name}` | 删除外部模块 |

### 代理管理 `/api/proxy`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/proxy/servers` | 获取代理服务器列表 |
| POST | `/api/proxy/servers` | 添加代理服务器 |
| PUT | `/api/proxy/servers/{id}` | 更新配置 |
| DELETE | `/api/proxy/servers/{id}` | 删除服务器 |
| POST | `/api/proxy/servers/{id}/sync` | 同步工具列表 |
| POST | `/api/proxy/servers/{id}/enable` | 启用服务器 |
| POST | `/api/proxy/servers/{id}/disable` | 禁用服务器 |

### 统计查询 `/api/stats`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats/overview` | 整体统计概览 |
| GET | `/api/stats/modules` | 按模块统计 |
| GET | `/api/stats/tools` | 按工具统计 |
| GET | `/api/stats/recent` | 最近调用记录 |

### AI 代码生成 `/api/codegen`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/codegen/chat` | 对话生成代码 |
| POST | `/api/codegen/chat/stream` | 流式对话 |
| GET | `/api/codegen/preview/{task_id}` | 预览生成代码 |
| POST | `/api/codegen/install/{task_id}` | 安装到平台 |
| POST | `/api/codegen/download/{task_id}` | 下载 ZIP |

---

## 🧩 开发指南

### 创建自定义模块

详细的模块开发规范请参阅 [MCP_MODULE_DEV_GUIDE.md](./MCP_MODULE_DEV_GUIDE.md)。

快速开始：

```
my_module/
├── __init__.py          # 包标记
├── MODULE_INFO          # 模块元信息
├── my_module_mcp.py     # MCP 工具注册
├── my_module_tool.py    # 业务逻辑
└── requirements.txt     # 可选依赖
```

**MODULE_INFO:**
```json
{
  "display_name": "我的工具",
  "version": "1.0.0",
  "description": "工具描述",
  "author": "Your Name"
}
```

**my_module_mcp.py:**
```python
from mcp_service import mcp
from config_py.config import settings
from config_py.prompt import prompt_manager
from utils import com_utils
from utils.com_utils import get_mcp_exposed_url

TOOL_NAME = "my_tool"

@mcp.tool(
    name=f'{settings.MCP_TOOL_NAME_PREFIX}{TOOL_NAME}',
    description=f'MCP Server URL：{get_mcp_exposed_url()}。{prompt_manager.get(TOOL_NAME)}',
    enabled=com_utils.get_tool_enable(TOOL_NAME),
)
def my_tool(param: str) -> dict:
    """工具说明"""
    return {"success": True, "data": "result"}
```

### 打包与分享

```bash
# 打包
zip -r my_module.zip my_module/

# 安装
curl -X POST http://localhost:6080/api/modules/install \
  -F "file=@my_module.zip"
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP 客户端 (Claude / Cursor)                  
└───────────────────────────────┬─────────────────────────────────┘
                                │ MCP Protocol (HTTP Streamable)
                                ▼ :6081
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Service (FastMCP)                        
│  ┌───────────────────────────────────────────────────────────┐  
│  │  中间件层                                                   
│  │  • RequestMCPMiddleware (日志记录/统计)                    
│  │  • ToolDescriptionCheckerMiddleware (描述热更新)           
│  │  • ToolEnabledCheckerMiddleware (工具过滤)                 
│  └───────────────────────────────────────────────────────────┘ 
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             
│  │  内置工具    │  │  外部插件    │  │  代理工具    │             
│  │  tools/     │  │  external/  │  │  proxy/     │             
│  └─────────────┘  └─────────────┘  └─────────────┘             
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    REST API (FastAPI) :6080                     
│  /api/modules  /api/stats  /api/proxy  /api/codegen  /api/auth 
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    Web 前端 (Vue 3)                            
│  模块管理 | 工具控制 | 代理配置 | 统计看板 | AI 生成             
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    数据层 (SQLite)                              
│  模块状态 | 工具配置 | 调用统计 | 代理配置 | 用户认证            
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
MCPHub/
├── requirements.txt              # Python 依赖
├── README.md                     # 本文件
├── MCP_MODULE_DEV_GUIDE.md       # 模块开发指南
├── config/
│   ├── config.json               # 主配置文件
│   └── mcp_hub.db               # SQLite 数据库
└── app/
    ├── main.py                   # FastAPI 入口
    ├── mcp_service.py            # MCP 服务初始化
    ├── my_mcp_middleware.py      # MCP 中间件
    ├── config_py/                # 配置管理
    ├── managers/                 # 核心管理器
    │   ├── module_manager.py     # 模块生命周期
    │   ├── proxy_manager.py      # 代理服务器
    │   └── stats_manager.py      # 统计管理
    ├── api/                      # REST API
    ├── tools/                    # 内置模块
    │   ├── t_autogui/            # GUI 自动化
    │   ├── t_cli/                # CLI 命令
    │   ├── t_python/             # Python 执行
    │   └── ...
    ├── tools_external/           # 外部插件
    ├── toolsmcp/                 # MCP 工具封装
    └── web/                      # Vue 3 前端
```

---

## ⚙️ 配置说明

主配置文件：`config/config.json`

```json
{
  "api": {
    "title": "MCPHub Service",
    "version": "1.0.0"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 6080
  },
  "mcp": {
    "service_name": "mcphub",
    "host": "0.0.0.0",
    "port": 6081,
    "path": "/mcp",
    "tool_name_prefix": "",
    "module_enable": [
      {
        "enable": true,
        "module_name": "tools.t_cli.cli_mcp",
        "disable_tool": [],
        "config": {}
      }
    ]
  },
  "database": {
    "db_path": "./config/mcp_hub.db"
  },
  "auth": {
    "secret_key": "your-secret-key",
    "token_expire_hours": 24
  }
}
```

| 配置项 | 说明 |
|--------|------|
| `mcp.tool_name_prefix` | 工具名前缀，用于多实例部署时区分 |
| `mcp.module_enable` | 启动时自动加载的模块列表 |
| `module_enable[].disable_tool` | 该模块中禁用的工具名列表 |
| `module_enable[].config` | 传递给模块的自定义配置 |

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 License

本项目采用 MIT License 开源协议。

---

## 🙏 致谢

- [FastMCP](https://github.com/anthropics/fastmcp) - 快速构建 MCP Server 的框架
- [MCP Protocol](https://modelcontextprotocol.io/) - Model Context Protocol 规范
- [FastAPI](https://fastapi.tiangolo.com/) - 现代高性能 Python Web 框架

---

<p align="center">
  <strong>让 AI Agent 拥有无限可能 🚀</strong>
</p>
