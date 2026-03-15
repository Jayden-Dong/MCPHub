<template>
  <div class="codegen-page">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">{{ t('page_title_codegen') }}</h2>
      </div>
      <div class="header-actions">
        <el-button @click="handleViewPrompt">
          <el-icon><Document /></el-icon> {{ t('btn_view_prompt') }}
        </el-button>
        <el-button @click="handleNewChat" :disabled="!taskId">
          <el-icon><Plus /></el-icon> {{ t('btn_new_chat') }}
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" class="main-content">
      <!-- 左侧：聊天区域 -->
      <el-col :span="14">
        <el-card shadow="never" class="chat-card">
          <template #header>
            <div class="chat-header">
              <div class="chat-header-left">
                <span class="chat-header-title">{{ t('chat_header_title') }}</span>
                <el-tag v-if="taskId" size="small" type="info" style="margin-left: 8px;">{{ taskId.substring(0, 8) }}...</el-tag>
              </div>
            </div>
          </template>

          <!-- 聊天消息列表 -->
          <div class="chat-messages" ref="messagesRef">
            <div class="welcome-msg" v-if="messages.length === 0">
              <div class="welcome-icon-wrap">
                <el-icon :size="36" color="#00d2ff"><ChatDotRound /></el-icon>
              </div>
              <h3>{{ t('welcome_title') }}</h3>
              <p>{{ t('welcome_example') }}</p>
            </div>

            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="message"
              :class="[msg.role, { 'message--error': msg.isError }]"
            >
              <div class="message-avatar">
                <el-icon v-if="msg.role === 'user'" :size="16"><User /></el-icon>
                <el-icon v-else-if="msg.isError" :size="16"><Warning /></el-icon>
                <el-icon v-else :size="16"><Monitor /></el-icon>
              </div>
              <div class="message-content">
                <div v-if="msg.isError" class="error-label">{{ t('msg_error_label') }}</div>
                <div v-if="msg.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
                <div v-else>{{ msg.content }}</div>
              </div>
            </div>

            <div v-if="streaming" class="message assistant">
              <div class="message-avatar">
                <el-icon :size="16"><Monitor /></el-icon>
              </div>
              <div class="message-content">
                <div class="markdown-body" v-html="renderMarkdown(streamContent)"></div>
                <span class="typing-cursor">|</span>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="chat-input">
            <!-- LLM 配置 -->
            <div class="llm-config-bar">
              <div class="llm-config-title">
                <el-icon><Setting /></el-icon>
                <span>{{ t('llm_config') }}</span>
              </div>
              <div class="llm-config-fields">
                <div class="llm-config-row">
                  <div class="llm-field">
                    <label class="llm-field-label">API Key</label>
                    <el-input v-model="llmConfig.api_key" :placeholder="t('placeholder_api_key')" show-password size="small" class="llm-input" />
                  </div>
                  <div class="llm-field llm-field--model">
                    <label class="llm-field-label">{{ t('label_model') }}</label>
                    <el-input v-model="llmConfig.model" :placeholder="t('placeholder_model')" size="small" class="llm-input" />
                  </div>
                </div>
                <div class="llm-field">
                  <label class="llm-field-label">Base URL</label>
                  <el-input v-model="llmConfig.base_url" placeholder="https://..." size="small" class="llm-input" />
                </div>
              </div>
            </div>

            <!-- Gemini 风格输入框容器 -->
            <div class="input-box" :class="{ 'input-box--focused': inputFocused, 'input-box--disabled': sending }">
              <!-- 已上传文件 chips -->
              <div v-if="uploadedFiles.length > 0" class="file-chips">
                <div v-for="(f, i) in uploadedFiles" :key="i" class="file-chip">
                  <el-icon class="file-chip-icon"><Document /></el-icon>
                  <span class="file-chip-name">{{ f.name }}</span>
                  <span v-if="f.size" class="file-chip-size">{{ formatFileSize(f.size) }}</span>
                  <span class="file-chip-close" @click="removeUploadedFile(i)">
                    <el-icon><Close /></el-icon>
                  </span>
                </div>
              </div>

              <!-- textarea -->
              <textarea
                v-model="inputMessage"
                class="input-textarea"
                :placeholder="t('placeholder_input')"
                rows="1"
                @keydown.ctrl.enter="handleSend"
                @focus="inputFocused = true"
                @blur="inputFocused = false"
                @input="autoResize"
                ref="textareaRef"
                :disabled="sending"
              ></textarea>

              <!-- 底部操作栏 -->
              <div class="input-actions">
                <!-- 左侧：附件 -->
                <div class="input-actions-left">
                  <el-upload
                    :show-file-list="false"
                    :auto-upload="false"
                    multiple
                    :on-change="handleFileChange"
                    accept=".py,.md,.txt,.json,.yaml,.yml,.toml,.cfg,.ini,.sh,.js,.ts,.html,.css,.xml,.csv,.rst,.zip"
                  >
                    <button class="icon-btn" :class="{ 'icon-btn--loading': uploading }" type="button" :title="t('upload_file_title')">
                      <svg v-if="!uploading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                      </svg>
                      <svg v-else viewBox="0 0 24 24" class="spin">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2.5" fill="none" stroke-dasharray="31.4" stroke-dashoffset="10"/>
                      </svg>
                    </button>
                  </el-upload>
                </div>

                <!-- 右侧：提示 + 发送 -->
                <div class="input-actions-right">
                  <span class="input-shortcut">Ctrl+Enter</span>
                  <button
                    class="send-circle-btn"
                    :class="{ 'send-circle-btn--active': inputMessage.trim() && !sending }"
                    type="button"
                    @click="handleSend"
                    :disabled="!inputMessage.trim() || sending"
                  >
                    <svg v-if="!sending" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" class="spin">
                      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" fill="none" stroke-dasharray="28" stroke-dashoffset="8"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：代码预览和操作 -->
      <el-col :span="10">
        <el-card shadow="never" class="preview-card">
          <template #header>
            <div class="preview-header">
              <span class="chat-header-title">{{ t('preview_title') }}</span>
              <div class="preview-actions" v-if="generatedCode">
                <el-button size="small" type="success" @click="handleDownload" :loading="downloading">
                  <el-icon><Download /></el-icon> {{ t('btn_download') }}
                </el-button>
                <el-button size="small" type="primary" @click="handleInstall" :loading="installLoading">
                  <el-icon><Upload /></el-icon> {{ t('btn_install_platform') }}
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="!generatedCode" class="empty-preview">
            <el-empty :description="t('empty_preview')" :image-size="80" />
          </div>

          <div v-else class="code-preview">
            <div class="module-name-tag">
              <el-tag type="success">{{ generatedCode.module_name }}</el-tag>
            </div>

            <el-tabs v-model="activeTab">
              <el-tab-pane
                v-for="file in generatedCode.files"
                :key="file.path"
                :label="getFileName(file.path)"
                :name="file.path"
              >
                <div class="code-block">
                  <pre><code>{{ file.content }}</code></pre>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统提示词弹窗 -->
    <el-dialog
      v-model="promptDialogVisible"
      :title="t('dlg_prompt_title')"
      width="700px"
      top="5vh"
    >
      <div class="prompt-content">
        <pre>{{ systemPrompt }}</pre>
      </div>
      <template #footer>
        <el-button @click="promptDialogVisible = false">{{ t('btn_cancel') }}</el-button>
        <el-button type="primary" @click="handleDownloadPrompt">
          <el-icon><Download /></el-icon> {{ t('btn_download_prompt') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { codegenChatStream, codegenPreview, codegenDownload, codegenInstall, codegenDeleteTask, codegenUpload, codegenGetSystemPrompt } from '../api/index.js'
import { useI18n } from '../i18n.js'

const { t } = useI18n()

const messages = ref([])
const inputMessage = ref('')
const taskId = ref(null)
const sending = ref(false)
const streaming = ref(false)
const streamContent = ref('')
const generatedCode = ref(null)
const activeTab = ref('')
const downloading = ref(false)
const installLoading = ref(false)
const messagesRef = ref(null)
const inputFocused = ref(false)
const textareaRef = ref(null)

const uploadedFiles = ref([])
const uploading = ref(false)

const promptDialogVisible = ref(false)
const systemPrompt = ref('')

const llmConfig = ref({
  api_key: '',
  base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  model: 'qwen3.5-plus'
})

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block-inner"><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function getFileName(path) {
  return path.split('/').pop()
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}

function handleSend() {
  const msg = inputMessage.value.trim()
  if (!msg || sending.value) return

  messages.value.push({ role: 'user', content: msg })
  inputMessage.value = ''
  nextTick(() => { if (textareaRef.value) textareaRef.value.style.height = 'auto' })
  sending.value = true
  streaming.value = true
  streamContent.value = ''
  scrollToBottom()

  const config = {}
  if (llmConfig.value.api_key) config.api_key = llmConfig.value.api_key
  if (llmConfig.value.base_url) config.base_url = llmConfig.value.base_url
  if (llmConfig.value.model) config.model = llmConfig.value.model

  codegenChatStream(
    msg,
    taskId.value,
    config,
    (data) => {
      streamContent.value += data.content
      scrollToBottom()
    },
    async (data) => {
      taskId.value = data.task_id
      messages.value.push({ role: 'assistant', content: streamContent.value })
      streaming.value = false
      streamContent.value = ''
      sending.value = false
      scrollToBottom()
      if (data.has_code) {
        await fetchPreview()
      }
    },
    (err) => {
      streaming.value = false
      streamContent.value = ''
      sending.value = false
      messages.value.push({ role: 'assistant', content: err || t('msg_unknown_error'), isError: true })
      scrollToBottom()
    }
  )
}

async function fetchPreview() {
  if (!taskId.value) return
  try {
    const res = await codegenPreview(taskId.value)
    if (res.Code === 12 && res.Data) {
      generatedCode.value = res.Data
      if (res.Data.files?.length > 0) {
        activeTab.value = res.Data.files[0].path
      }
    }
  } catch (e) {
    ElMessage.error(t('msg_request_fail') + ': ' + (e.message || t('msg_unknown_error')))
  }
}

async function handleDownload() {
  if (!taskId.value) return
  downloading.value = true
  try {
    const res = await codegenDownload(taskId.value)
    const blob = new Blob([res], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${generatedCode.value?.module_name || 'module'}.zip`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success(t('msg_download_success'))
  } catch (e) {
    ElMessage.error(t('msg_download_fail'))
  } finally {
    downloading.value = false
  }
}

async function handleInstall(force = false) {
  if (!taskId.value) return
  installLoading.value = true
  try {
    const res = await codegenInstall(taskId.value, force)
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || t('msg_install_success'))
    } else if (res.Data?.exists) {
      installLoading.value = false
      try {
        await ElMessageBox.confirm(
          t('msg_overwrite_content', { name: res.Data.module_name }),
          t('msg_overwrite_title'),
          { type: 'warning', confirmButtonText: t('btn_overwrite'), cancelButtonText: t('btn_cancel') }
        )
        await handleInstall(true)
      } catch {
        // cancelled
      }
    } else {
      ElMessage.error(res.Message?.Description || t('msg_install_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_install_fail'))
  } finally {
    installLoading.value = false
  }
}

function handleNewChat() {
  if (taskId.value) {
    codegenDeleteTask(taskId.value).catch(() => {})
  }
  messages.value = []
  taskId.value = null
  generatedCode.value = null
  streamContent.value = ''
  uploadedFiles.value = []
}

async function handleFileChange(file, fileList) {
  uploading.value = true
  try {
    const res = await codegenUpload([file], taskId.value)
    if (res.Code === 12) {
      const data = res.Data
      taskId.value = data.task_id
      data.files.forEach(name => {
        uploadedFiles.value.push({ name, size: file.size })
      })
      ElMessage.success(t('msg_upload_success', { n: data.files.length }))
    } else {
      ElMessage.error(res.Message?.Description || t('msg_upload_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_upload_fail') + ': ' + (e.message || t('msg_unknown_error')))
  } finally {
    uploading.value = false
  }
}

function removeUploadedFile(index) {
  uploadedFiles.value.splice(index, 1)
}

function formatFileSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

async function handleViewPrompt() {
  if (!systemPrompt.value) {
    try {
      const res = await codegenGetSystemPrompt()
      if (res.Code === 12 && res.Data?.system_prompt) {
        systemPrompt.value = res.Data.system_prompt
      } else {
        ElMessage.error(t('msg_prompt_load_fail'))
        return
      }
    } catch (e) {
      ElMessage.error(t('msg_prompt_load_fail'))
      return
    }
  }
  promptDialogVisible.value = true
}

function handleDownloadPrompt() {
  if (!systemPrompt.value) return
  const blob = new Blob([systemPrompt.value], { type: 'text/plain;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'mcp_system_prompt.txt'
  a.click()
  window.URL.revokeObjectURL(url)
}
</script>

<style scoped>
.codegen-page {
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.main-content {
  height: calc(100vh - 155px);
}

/* ---- 聊天卡片 ---- */
.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 10px !important;
}

.chat-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header-left {
  display: flex;
  align-items: center;
}

.chat-header-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ---- 消息列表 ---- */
.chat-messages {
  flex: 1 1 0;
  overflow-y: auto;
  padding: 20px 16px;
  min-height: 0;
}

.welcome-msg {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.welcome-icon-wrap {
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: rgba(0, 210, 255, 0.08);
  border: 1px solid rgba(0, 210, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-msg h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
}

.welcome-msg p {
  font-size: 13px;
  color: var(--text-subtle);
  line-height: 1.6;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message.user .message-avatar {
  background: linear-gradient(135deg, #409EFF, #0077e6);
  color: #fff;
}

.message.assistant .message-avatar {
  background: linear-gradient(135deg, #00c7a8, #00afc8);
  color: #fff;
}

.message-content {
  flex: 1;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-regular);
  padding: 10px 14px;
  border-radius: 8px;
  overflow-x: auto;
}

.message.user .message-content {
  background: rgba(64, 158, 255, 0.08);
  border: 1px solid rgba(64, 158, 255, 0.12);
}

.message.assistant .message-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
}

.message--error .message-avatar {
  background: linear-gradient(135deg, #f56c6c, #c0392b) !important;
}

.message--error .message-content {
  background: rgba(245, 108, 108, 0.06) !important;
  border-color: rgba(245, 108, 108, 0.3) !important;
}

.error-label {
  font-size: 11px;
  font-weight: 600;
  color: #f56c6c;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.typing-cursor {
  animation: blink 0.8s infinite;
  color: #00afc8;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ---- 输入区域 ---- */
.chat-input {
  border-top: 1px solid var(--border-light);
  padding: 12px 16px 14px;
  background: var(--bg-card);
}

/* ---- LLM 配置 ---- */
.llm-config-bar {
  background: var(--bg-secondary);
  border: 1px solid var(--border-input);
  border-radius: 12px;
  padding: 10px 14px 12px;
  margin-bottom: 10px;
}

.llm-config-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.4px;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.llm-config-title .el-icon {
  font-size: 12px;
}

.llm-config-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.llm-config-row {
  display: flex;
  gap: 8px;
  min-width: 0;
}

.llm-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.llm-field--model {
  flex: 0.7;
}

.llm-field-label {
  font-size: 10.5px;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.3px;
  padding-left: 2px;
}

.llm-input {
  width: 100%;
}

.llm-input :deep(.el-input__wrapper) {
  background: var(--bg-input);
  border-radius: 7px;
  box-shadow: 0 0 0 1px var(--border-input) !important;
  padding: 0 8px;
  transition: box-shadow 0.15s;
}

.llm-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-control) !important;
}

.llm-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.25) !important;
}

.llm-input :deep(.el-input__inner) {
  font-size: 12.5px;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
  color: var(--text-regular);
  height: 26px;
  line-height: 26px;
}

.llm-input :deep(.el-input__inner::placeholder) {
  color: #c2c8d8;
  font-size: 12px;
}

/* ---- Gemini 风格输入框 ---- */
.input-box {
  background: var(--bg-input);
  border: 1.5px solid var(--border-input);
  border-radius: 16px;
  padding: 10px 12px 8px 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.input-box--focused {
  border-color: var(--border-control);
  box-shadow: 0 2px 10px rgba(60, 80, 140, 0.08);
}

.input-box--disabled {
  opacity: 0.7;
  pointer-events: none;
}

/* 已上传文件 chips */
.file-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-input);
  border-radius: 8px;
  padding: 3px 8px 3px 6px;
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 260px;
  cursor: default;
}

.file-chip-icon {
  font-size: 13px;
  color: #7a8ba8;
  flex-shrink: 0;
}

.file-chip-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-chip-size {
  color: #adb5bd;
  font-size: 11px;
  white-space: nowrap;
}

.file-chip-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  cursor: pointer;
  color: #909399;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}

.file-chip-close:hover {
  background: #dde2ee;
  color: #4a5568;
}

/* 原生 textarea */
.input-textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-regular);
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
  letter-spacing: 0.2px;
  min-height: 26px;
  max-height: 180px;
  overflow-y: auto;
  display: block;
  box-sizing: border-box;
  padding: 2px 0;
}

.input-textarea::placeholder {
  color: var(--text-subtle);
  font-size: 13.5px;
}

/* 底部操作栏 */
.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.input-actions-left,
.input-actions-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 图标按钮（附件） */
.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s;
  padding: 0;
}

.icon-btn svg {
  width: 18px;
  height: 18px;
}

.icon-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.icon-btn--loading {
  cursor: default;
  color: #409eff;
}

/* Ctrl+Enter 提示 */
.input-shortcut {
  font-size: 11px;
  color: #c8cdd8;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.3px;
}

/* 发送圆形按钮 */
.send-circle-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  background: #dde2ee;
  cursor: default;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: background 0.2s, transform 0.15s;
  padding: 0;
  flex-shrink: 0;
}

.send-circle-btn svg {
  width: 17px;
  height: 17px;
}

.send-circle-btn--active {
  background: #1a73e8;
  cursor: pointer;
}

.send-circle-btn--active:hover {
  background: #1558c0;
  transform: scale(1.06);
}

.send-circle-btn:disabled {
  cursor: default;
}

/* 旋转动画 */
.spin {
  animation: spin-anim 0.8s linear infinite;
}

@keyframes spin-anim {
  to { transform: rotate(360deg); }
}

/* ---- 预览卡片 ---- */
.preview-card {
  height: 100%;
  border-radius: 10px !important;
}

.preview-card :deep(.el-card__body) {
  overflow: auto;
  max-height: calc(100vh - 250px);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.empty-preview {
  padding: 40px 0;
}

.module-name-tag {
  margin-bottom: 12px;
}

.code-block {
  background: #1a1e2e;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.code-block pre {
  margin: 0;
}

.code-block code {
  color: #cdd6f4;
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre;
}

.markdown-body :deep(.code-block-inner) {
  background: #1a1e2e;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 8px 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.markdown-body :deep(.code-block-inner code) {
  color: #cdd6f4;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
  white-space: pre;
}

.markdown-body :deep(.inline-code) {
  background: rgba(0, 210, 255, 0.08);
  border: 1px solid rgba(0, 210, 255, 0.15);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #00afc8;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

/* ---- 系统提示词弹窗 ---- */
.prompt-content {
  max-height: 60vh;
  overflow-y: auto;
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
}

.prompt-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-regular);
}
</style>
