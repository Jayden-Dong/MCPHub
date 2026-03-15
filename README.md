[English](README.md) | [中文](README_ZH.md)

# MCPHub

<h3 align="center">🚀 An MCP Tool Service Platform - One Connection, Infinite Possibilities for AI Agents</h3>

<p align="center">
  <a href="#-key-features">Key Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-feature-details">Feature Details</a> •
  <a href="#-api-documentation">API Documentation</a> •
  <a href="#-development-guide">Development Guide</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastMCP-2.14+-green.svg" alt="FastMCP">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

---

## 📸 System Screenshots

### Login Interface

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/login.png)


> Default credentials: username `admin`, password `admin123`

### Module Management Interface

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/modules.png)


> Manage all MCP modules with support for loading, unloading, and reloading operations

### Tool Details & Control

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/tool%20detail.png)


> Enable/disable each tool individually, edit tool descriptions in real-time

### Proxy Server Management

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/extended%20mcp.png)


> Proxy existing MCP Servers without modification

### Usage Statistics Dashboard

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/statistics.png)


> Visualize tool call counts, success rates, and response times

### AI Code Generation

![Image text](https://github.com/Jayden-Dong/MCPHub/blob/213b5ea070cae4fdf584b6f441f1aed7525a95db/img/ai%20coding.png)


> Generate MCP plugin code through natural language conversation

---

## 🎯 What is This?

**MCPHub** is a **tool service platform** based on the MCP (Model Context Protocol). It addresses a pain point in current AI Agent systems:

> Each MCP Server needs to be configured separately on the client side. As the number of tools increases, configuration management becomes chaotic.

**MCPHub's Solution:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Before: Scattered Configuration              │
│  Claude/Cursor needs to configure dozens of MCP Server addresses│
│  - mcp-server-filesystem                                        │
│  - mcp-server-github                                            │
│  - mcp-server-postgres                                          │
│  - mcp-server-python                                            │
│  - ... (configuration explosion)                                │
└─────────────────────────────────────────────────────────────────┘
                              ⬇️
┌─────────────────────────────────────────────────────────────────────┐
│                    After: Unified Entry Point                       
│  Claude/Cursor only needs to configure one address                  
│  { "mcpServers": { "mcp-hub": { "url": "http://host:9000/mcp" } } } 
│                                                                     
│  MCP Hub automatically aggregates all tools, providing:             
│  ✅ Centralized tool management                                     
│  ✅ Hot-pluggable enable/disable                                    
│  ✅ Unified monitoring and statistics                               
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 1️⃣ One Address, Infinite Tools

AI Agent clients only need to configure **one MCP Server address** to access all tools on the platform. Whether built-in tools, custom plugins, or proxied third-party MCP Servers, they are all transparent to clients.

### 2️⃣ Hot-Pluggable Tool Management

- **Module-level Management**: Load, unload, and reload modules without restarting the service
- **Tool-level Control**: Individual tools can be enabled/disabled independently
- **Hot Configuration Updates**: Tool description changes take effect immediately without restart

### 3️⃣ Proxy Existing MCP Servers

Already have MCP Servers? No modification needed - just configure a proxy to integrate:

```json
{
  "name": "my-existing-server",
  "url": "http://existing-server:8080/mcp",
  "transport": "streamable-http"
}
```

The platform automatically discovers and transparently proxies all tools from that server.

### 4️⃣ AI-Powered MCP Plugin Generation

Built-in AI code generation feature - generate compliant MCP module code through natural language conversation:

```
User: Help me create a weather query tool
AI: Generated t_weather module with get_current_weather and get_forecast tools...
```

**Everyone can become an MCP tool developer!**

### 5️⃣ Plugin Ecosystem: Install & Share

- **One-click Install**: Upload a ZIP package to install third-party plugins
- **One-click Export**: Package custom plugins as ZIP to share with other users
- **Modular Isolation**: Separate management of built-in tools (`tools/`) and external plugins (`tools_external/`)

### 6️⃣ Comprehensive Usage Statistics

Intuitively view usage for each tool:

- Call count statistics
- Success rate tracking
- Response time analysis
- 24-hour trend charts

---

## 🛠️ Built-in Tools

The platform comes with core tool modules ready to use:

| Category | Module | Tools | Description |
|----------|--------|-------|-------------|
| **🖥️ CLI Execution** | `t_cli` | `run_cli_command`, `list_directory`, `get_system_info`, `get_disk_usage`, `get_running_processes`, `find_files`... | Execute system commands, view processes, disk monitoring, network info |
| **🐍 Python Execution** | `t_python` | `run_python_script`, `installPackage`, `run_python_script_async`, `get_script_status` | Safely execute Python scripts, install dependencies, async execution |
| **🤖 GUI Automation** | `t_autogui` | `autogui_start_task`, `autogui_get_status`, `autogui_get_history`, `autogui_stop_task` | AI-driven desktop automation, automatic mouse and keyboard operations |
| **📓 Notebook** | `t_notebook` | `add_note`, `read_note` | Note creation and querying, persistent storage |

### Featured: AI-Driven GUI Automation

The `t_autogui` module implements **AI-driven desktop automation**:

```
User: Help me open the browser and visit GitHub
Agent: [Calls autogui_start_task] → AI plans task steps → Executes mouse and keyboard operations
```

This is a **killer feature** of this platform: AI can operate the computer desktop like a human, completing complex GUI interaction tasks.

---

## 📦 Extension Tools

Beyond built-in tools, the platform supports installing extension plugins. Here are some available extension tool examples:

| Category | Module | Tools | Description |
|----------|--------|-------|-------------|
| **📁 File Operations** | `t_file` | `read_file_utf8`, `write_file_utf8`, `unzip` | Local file read/write, unzip |
| **🌐 FTP Transfer** | `t_ftp` | `ftp_upload_file`, `ftp_download_file`, `ftp_create_directory` | FTP file transfer and management |
| **🧬 PDB Database** | `t_pdb` | `download_structure`, `convert_cif_to_pdb` | Protein structure database query and format conversion |
| **🔬 Foldseek** | `t_foldseek` | `foldseek_sort_by_evalue`, `foldseek_sort_by_fident` | Protein structure similarity search result processing |
| **📊 AlphaBio** | `t_alphabio` | `get_project_info`, `get_enzyme_activity` | AlphaBio database integration |
| **🧪 DNA Prediction** | `t_dna_predict` | `predict_collection_threshold` | DNA base sequence collection threshold prediction |
| **🗃️ Project Database** | `t_project_db` | `query_project_db`, `get_project_db_schema` | PostgreSQL project management database query |

> These extension tools are located in the `tools_external/` directory and can be loaded on demand through the Web interface or API. You can also develop your own extension tools and install them on the platform.

---

## 🚀 Quick Start

### Requirements

- Python 3.10+
- (Optional) Node.js 18+ - for building the frontend

### Installation

```bash
# Clone the project
git clone https://github.com/Jayden-Dong/MCPHub.git
cd MCPHub

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Start the Service

```bash
cd app
python main.py
```

After starting, access:
- 🌐 **Web Management Interface**: `http://localhost:6080`
- 📚 **API Documentation**: `http://localhost:6080/docs`
- 🔌 **MCP Endpoint**: `http://localhost:6081/mcp`

### Configure MCP Client

Add the following in Claude Desktop / Cursor/Cherry Studio or other MCP clients:

```json
{
  "mcpServers": {
    "general-tools": {
      "url": "http://localhost:6081/mcp"
    }
  }
}
```

🎉 Done! Your AI Agent can now use all enabled tools on the platform.

---

## 📖 Feature Details

### Module Management

Manage modules through the Web interface or API:

```
┌───────────────────────────────────────────────────────────┐
│  Module List              [Scan New Modules] [Install]    
├───────────────────────────────────────────────────────────┤
│  ✅ t_cli        Loaded      [Details] [Reload] [Unload]  
│  ✅ t_python     Loaded      [Details] [Reload] [Unload]  
│  ⏸️ t_autogui    Paused      [Details] [Load]             
│  📦 t_weather    Not Loaded  [Details] [Load]    [Export] 
└───────────────────────────────────────────────────────────┘
```

### Tool-level Control

Enter module details to enable/disable each tool individually:

```
┌─────────────────────────────────────────────────────────┐
│  t_cli Module Details                                   
├─────────────────────────────────────────────────────────┤
│  🔧 run_cli_command      [✅ Enabled]                   
│  🔧 list_directory       [✅ Enabled]                   
│  🔧 get_system_info      [❌ Disabled]                  
│  🔧 kill_process         [❌ Disabled]  ⚠️ Dangerous      
└─────────────────────────────────────────────────────────┘
```

### Proxy MCP Server

Connect existing MCP Servers to the platform:

**Via Web Interface:**
1. Navigate to the "Proxy Management" page
2. Click "Add Server"
3. Fill in server name, URL, and transport type
4. Click "Sync Tools" → Tools automatically appear in the platform

**Via API:**
```bash
curl -X POST http://localhost:8000/api/proxy/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem-server",
    "url": "http://localhost:3000/mcp",
    "transport": "streamable-http"
  }'
```

### AI Code Generation

Generate MCP plugins through conversation:

```bash
# Start conversation
curl -X POST http://localhost:8000/api/codegen/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Help me create a stock query tool that supports real-time prices and historical trends"}'

# Preview generated code
curl http://localhost:8000/api/codegen/preview/{task_id}

# Install directly to platform
curl -X POST http://localhost:8000/api/codegen/install/{task_id}
```

### Usage Statistics

View tool call information:

```bash
# Overall overview
curl http://localhost:8000/api/stats/overview

# Statistics by tool
curl http://localhost:8000/api/stats/tools

# Recent call records
curl http://localhost:8000/api/stats/recent?limit=100
```

Response example:
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

## 🔌 API Documentation

### Module Management `/api/modules`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/modules` | Get all module list |
| GET | `/api/modules/scan` | Scan unloaded modules |
| POST | `/api/modules/load` | Load module |
| POST | `/api/modules/{name}/unload` | Unload module |
| POST | `/api/modules/{name}/reload` | Reload module |
| POST | `/api/modules/tool/enable` | Enable tool |
| POST | `/api/modules/tool/disable` | Disable tool |
| POST | `/api/modules/install` | Install ZIP plugin |
| GET | `/api/modules/{name}/export` | Export module as ZIP |
| DELETE | `/api/modules/{name}` | Delete external module |

### Proxy Management `/api/proxy`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/proxy/servers` | Get proxy server list |
| POST | `/api/proxy/servers` | Add proxy server |
| PUT | `/api/proxy/servers/{id}` | Update configuration |
| DELETE | `/api/proxy/servers/{id}` | Delete server |
| POST | `/api/proxy/servers/{id}/sync` | Sync tool list |
| POST | `/api/proxy/servers/{id}/enable` | Enable server |
| POST | `/api/proxy/servers/{id}/disable` | Disable server |

### Statistics Query `/api/stats`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stats/overview` | Overall statistics overview |
| GET | `/api/stats/modules` | Statistics by module |
| GET | `/api/stats/tools` | Statistics by tool |
| GET | `/api/stats/recent` | Recent call records |

### AI Code Generation `/api/codegen`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/codegen/chat` | Conversational code generation |
| POST | `/api/codegen/chat/stream` | Streaming conversation |
| GET | `/api/codegen/preview/{task_id}` | Preview generated code |
| POST | `/api/codegen/install/{task_id}` | Install to platform |
| POST | `/api/codegen/download/{task_id}` | Download ZIP |

---

## 🧩 Development Guide

### Creating Custom Modules

For detailed module development specifications, please refer to [MCP_MODULE_DEV_GUIDE.md](./MCP_MODULE_DEV_GUIDE.md).

Quick Start:

```
my_module/
├── __init__.py          # Package marker
├── MODULE_INFO          # Module metadata
├── my_module_mcp.py     # MCP tool registration
├── my_module_tool.py    # Business logic
└── requirements.txt     # Optional dependencies
```

**MODULE_INFO:**
```json
{
  "display_name": "My Tool",
  "version": "1.0.0",
  "description": "Tool description",
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
    description=f'MCP Server URL: {get_mcp_exposed_url()}. {prompt_manager.get(TOOL_NAME)}',
    enabled=com_utils.get_tool_enable(TOOL_NAME),
)
def my_tool(param: str) -> dict:
    """Tool description"""
    return {"success": True, "data": "result"}
```

### Package & Share

```bash
# Package
zip -r my_module.zip my_module/

# Install
curl -X POST http://localhost:8000/api/modules/install \
  -F "file=@my_module.zip"
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Client (Claude / Cursor)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │ MCP Protocol (HTTP Streamable)
                                ▼ :9000
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Service (FastMCP)                        
│  ┌───────────────────────────────────────────────────────────┐ 
│  │  Middleware Layer                                          
│  │  • RequestMCPMiddleware (logging/statistics)               
│  │  • ToolDescriptionCheckerMiddleware (description hot update)
│  │  • ToolEnabledCheckerMiddleware (tool filtering)          
│  └───────────────────────────────────────────────────────────┘  
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              
│  │  Built-in   │  │  External   │  │  Proxy      │              
│  │  Tools      │  │  Plugins    │  │  Tools      │              
│  │  tools/     │  │  external/  │  │  proxy/     │              
│  └─────────────┘  └─────────────┘  └─────────────┘              
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    REST API (FastAPI) :8000                     │
│  /api/modules  /api/stats  /api/proxy  /api/codegen  /api/auth  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    Web Frontend (Vue 3)                         │
│  Module Management | Tool Control | Proxy Config | Statistics   │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer (SQLite)                          │
│  Module Status | Tool Config | Call Statistics | Proxy Config   │
│  User Authentication                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
MCPHub/
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── MCP_MODULE_DEV_GUIDE.md       # Module development guide
├── config/
│   ├── config.json               # Main configuration file
│   └── mcp_hub.db               # SQLite database
└── app/
    ├── main.py                   # FastAPI entry point
    ├── mcp_service.py            # MCP service initialization
    ├── my_mcp_middleware.py      # MCP middleware
    ├── config_py/                # Configuration management
    ├── managers/                 # Core managers
    │   ├── module_manager.py     # Module lifecycle
    │   ├── proxy_manager.py      # Proxy servers
    │   └── stats_manager.py      # Statistics management
    ├── api/                      # REST API
    ├── tools/                    # Built-in modules
    │   ├── t_autogui/            # GUI automation
    │   ├── t_cli/                # CLI commands
    │   ├── t_python/             # Python execution
    │   └── ...
    ├── tools_external/           # External plugins
    ├── toolsmcp/                 # MCP tool wrappers
    └── web/                      # Vue 3 frontend
```

---

## ⚙️ Configuration

Main configuration file: `config/config.json`

```json
{
  "api": {
    "title": "MCPHub Service",
    "version": "1.0.0"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "mcp": {
    "service_name": "mcphub",
    "host": "0.0.0.0",
    "port": 9000,
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

| Configuration | Description |
|---------------|-------------|
| `mcp.tool_name_prefix` | Tool name prefix for distinguishing multi-instance deployments |
| `mcp.module_enable` | List of modules to auto-load on startup |
| `module_enable[].disable_tool` | List of disabled tool names in the module |
| `module_enable[].config` | Custom configuration passed to the module |

---

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome!

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- [FastMCP](https://github.com/anthropics/fastmcp) - Framework for quickly building MCP Servers
- [MCP Protocol](https://modelcontextprotocol.io/) - Model Context Protocol specification
- [FastAPI](https://fastapi.tiangolo.com/) - Modern high-performance Python web framework

---

<p align="center">
  <strong>Empower AI Agents with Infinite Possibilities 🚀</strong>
</p>