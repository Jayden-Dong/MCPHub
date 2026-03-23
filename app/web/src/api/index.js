import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 请求拦截器：自动添加 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 401 错误：Token 无效或过期，跳转到登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 避免在登录页重复跳转
      if (window.location.hash !== '#/login') {
        window.location.href = '#/login'
      }
    }
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// ========== 模块管理 API ==========

export function getModules() {
  return api.get('/modules')
}

export function scanModules() {
  return api.get('/modules/scan')
}

export function getModuleDetail(moduleName) {
  return api.get(`/modules/${moduleName}/detail`)
}

export function loadModule(moduleName, config = null, isExternal = false) {
  return api.post('/modules/load', {
    module_name: moduleName,
    config: config,
    is_external: isExternal,
  })
}

export function unloadModule(moduleName) {
  return api.post(`/modules/${moduleName}/unload`)
}

export function reloadModule(moduleName) {
  return api.post(`/modules/${moduleName}/reload`)
}

export function enableTool(toolName) {
  return api.post('/modules/tool/enable', { tool_name: toolName })
}

export function disableTool(toolName) {
  return api.post('/modules/tool/disable', { tool_name: toolName })
}

export function updateToolDescription(toolName, description) {
  return api.post('/modules/tool/description', { tool_name: toolName, description })
}

export function updateModuleConfig(moduleName, config) {
  return api.post(`/modules/${moduleName}/config`, { config })
}

export function installModule(file, force = false) {
  const formData = new FormData()
  formData.append('file', file)
  const forceValue = force === true || force === 'true'
  return api.post(`/modules/install?force=${forceValue}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function deleteModule(moduleName) {
  return api.delete(`/modules/${moduleName}`)
}

export function exportModule(moduleName) {
  return api.get(`/modules/${moduleName}/export`, {
    responseType: 'blob',
  })
}

// ========== AI代码生成 API ==========

export function codegenChat(message, taskId = null, config = {}) {
  return api.post('/codegen/chat', {
    message,
    task_id: taskId,
    ...config,
  })
}

export function codegenChatStream(message, taskId = null, config = {}, onChunk, onDone, onError) {
  const token = localStorage.getItem('token')
  const headers = { 'Content-Type': 'application/json' }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  fetch('/api/codegen/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, task_id: taskId, ...config }),
  }).then(async (response) => {
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('text/event-stream')) {
      try {
        const data = await response.json()
        onError?.(data.Message?.Description || data.Msg || data.message || '请求失败')
      } catch {
        onError?.('请求失败')
      }
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.error) onError?.(data.error)
          else if (data.done) onDone?.(data)
          else if (data.content) onChunk?.(data)
        } catch {}
      }
    }
  }).catch((err) => onError?.(err.message))
}

export function codegenPreview(taskId) {
  return api.get(`/codegen/preview/${taskId}`)
}

export function codegenDownload(taskId) {
  return api.post(`/codegen/download/${taskId}`, null, {
    responseType: 'blob',
  })
}

export function codegenInstall(taskId, force = false) {
  const forceValue = force === true || force === 'true'
  return api.post(`/codegen/install/${taskId}?force=${forceValue}`)
}

export function codegenDeleteTask(taskId) {
  return api.delete(`/codegen/task/${taskId}`)
}

export function codegenUpload(files, taskId = null) {
  const form = new FormData()
  files.forEach(f => form.append('files', f.raw || f))
  if (taskId) form.append('task_id', taskId)
  return api.post('/codegen/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function codegenGetSystemPrompt() {
  return api.get('/codegen/system-prompt')
}

// ========== 第三方 MCP 代理 API ==========

export function getProxyServers() {
  return api.get('/proxy/servers')
}

export function getProxyServerDetail(serverId) {
  return api.get(`/proxy/servers/${serverId}`)
}

export function addProxyServer(data) {
  return api.post('/proxy/servers', data)
}

export function updateProxyServer(serverId, data) {
  return api.put(`/proxy/servers/${serverId}`, data)
}

export function deleteProxyServer(serverId) {
  return api.delete(`/proxy/servers/${serverId}`)
}

export function syncProxyServer(serverId) {
  return api.post(`/proxy/servers/${serverId}/sync`)
}

export function forceSyncProxyServer(serverId) {
  return api.post(`/proxy/servers/${serverId}/force-sync`)
}

export function enableProxyServer(serverId) {
  return api.post(`/proxy/servers/${serverId}/enable`)
}

export function disableProxyServer(serverId) {
  return api.post(`/proxy/servers/${serverId}/disable`)
}

export function enableProxyTool(toolId) {
  return api.post(`/proxy/tools/${toolId}/enable`)
}

export function disableProxyTool(toolId) {
  return api.post(`/proxy/tools/${toolId}/disable`)
}

export function updateProxyToolDescription(toolId, description) {
  return api.post(`/proxy/tools/${toolId}/description`, { description })
}

// ========== 分组管理 API ==========

export function getGroups() {
  return api.get('/groups')
}

export function getGroupDetail(groupId) {
  return api.get(`/groups/${groupId}`)
}

export function createGroup(name, description = '') {
  return api.post('/groups', { name, description })
}

export function updateGroup(groupId, data) {
  return api.put(`/groups/${groupId}`, data)
}

export function deleteGroup(groupId) {
  return api.delete(`/groups/${groupId}`)
}

export function getGroupMembers(groupId) {
  return api.get(`/groups/${groupId}/members`)
}

export function addModuleToGroup(groupId, moduleName) {
  return api.post(`/groups/${groupId}/modules`, { module_name: moduleName })
}

export function removeModuleFromGroup(groupId, moduleName) {
  return api.delete(`/groups/${groupId}/modules/${moduleName}`)
}

export function addProxyToGroup(groupId, serverId) {
  return api.post(`/groups/${groupId}/proxies`, { server_id: serverId })
}

export function removeProxyFromGroup(groupId, serverId) {
  return api.delete(`/groups/${groupId}/proxies/${serverId}`)
}

// ========== 统计数据 API ==========

export function getStatsOverview(hours = 24) {
  return api.get(`/stats/overview?hours=${hours}`)
}

export function getStatsModules(hours = 24) {
  return api.get(`/stats/modules?hours=${hours}`)
}

export function getStatsTools(hours = 24, limit = 50) {
  return api.get(`/stats/tools?hours=${hours}&limit=${limit}`)
}

export function getStatsRecent(limit = 100) {
  return api.get(`/stats/recent?limit=${limit}`)
}
