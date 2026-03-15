<template>
  <div class="detail-page">
    <!-- 面包屑 -->
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ path: '/modules' }">{{ t('page_breadcrumb_modules') }}</el-breadcrumb-item>
      <el-breadcrumb-item>{{ moduleInfo?.display_name || moduleName }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div v-loading="loading">
      <!-- 模块信息卡片 -->
      <el-card class="info-card" shadow="never" v-if="moduleInfo">
        <div class="info-header">
          <div>
            <h2>{{ moduleInfo.display_name || moduleInfo.module_name }}</h2>
            <div class="info-meta">
              <el-tag :type="moduleInfo.loaded ? 'success' : 'info'" size="small">
                {{ moduleInfo.loaded ? t('tag_loaded') : t('tag_unloaded') }}
              </el-tag>
              <el-tag v-if="moduleInfo.is_external" type="warning" size="small">{{ t('tag_external_module') }}</el-tag>
              <span class="meta-text">{{ moduleInfo.module_name }}</span>
              <span class="meta-text" v-if="moduleInfo.version">v{{ moduleInfo.version }}</span>
              <span class="meta-text" v-if="moduleInfo.install_time">{{ t('col_install_time') }}: {{ moduleInfo.install_time }}</span>
            </div>
            <p class="info-desc" v-if="moduleInfo.description">{{ moduleInfo.description }}</p>
          </div>
          <div class="info-actions">
            <el-button @click="handleExport" :loading="exporting" v-if="moduleInfo?.is_external">
              <el-icon><Download /></el-icon> {{ t('btn_export_module') }}
            </el-button>
            <el-button @click="handleReload" :loading="reloading" :disabled="!moduleInfo.loaded">
              <el-icon><RefreshRight /></el-icon> {{ t('btn_reload_module') }}
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 工具列表 -->
      <el-card shadow="never" class="tools-card" v-if="moduleInfo">
        <template #header>
          <div class="tools-header">
            <span>{{ t('tools_list') }} ({{ tools.length }})</span>
            <span v-if="!moduleInfo.loaded" class="tools-unloaded-tip">{{ t('tools_unloaded_tip') }}</span>
          </div>
        </template>

        <el-empty v-if="!moduleInfo.loaded" :description="t('tools_empty_unloaded')" :image-size="80" />
        <ToolsTable
          v-else
          :tools="tools"
          :primary-label="t('col_tool_name')"
          :primary-width="280"
          primary-field="name"
          schema-field="parameters"
          row-key-field="name"
          :show-edit-desc="moduleInfo?.is_external"
          hide-secondary
          @toggle-tool="handleToggleTool"
          @edit-desc="handleEditDesc"
        />
      </el-card>

      <!-- 编辑工具描述对话框 -->
      <EditToolDescDialog
        v-model:visible="editDescDialog"
        v-model="editDescValue"
        :tool-name="editDescTool?.name"
        :saving="editDescSaving"
        @save="handleSaveDesc"
      />

      <!-- 模块配置 -->
      <el-card shadow="never" class="config-card" v-if="moduleInfo?.config && Object.keys(moduleInfo.config).length > 0">
        <template #header>
          <div class="config-header">
            <span>{{ t('module_config') }}</span>
            <el-button type="primary" size="small" @click="handleEditConfig">
              <el-icon><Edit /></el-icon> {{ t('btn_edit_config') }}
            </el-button>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <template v-for="(value, key) in flattenConfig(moduleInfo.config)" :key="key">
            <el-descriptions-item :label="key">
              <template v-if="isPasswordField(key)">
                <div class="password-field">
                  <code v-if="visiblePasswords.has(key)">{{ typeof value === 'object' ? JSON.stringify(value) : value }}</code>
                  <code v-else>{{ maskPassword(value) }}</code>
                  <el-icon class="password-toggle" @click="togglePasswordVisibility(key)">
                    <View v-if="!visiblePasswords.has(key)" />
                    <Hide v-else />
                  </el-icon>
                </div>
              </template>
              <template v-else>
                <code>{{ typeof value === 'object' ? JSON.stringify(value) : value }}</code>
              </template>
            </el-descriptions-item>
          </template>
        </el-descriptions>
      </el-card>

      <!-- 编辑配置对话框 -->
      <el-dialog
        v-model="editConfigDialog"
        :title="t('dlg_edit_config_title')"
        width="640px"
        :close-on-click-modal="false"
        class="edit-config-dialog"
      >
        <div class="edit-config-content">
          <el-form label-width="160px" label-position="left">
            <template v-for="item in editConfigFields" :key="item.key">
              <el-form-item :label="item.key">
                <!-- 密码字段使用密码输入框 -->
                <el-input
                  v-if="item.isPassword"
                  v-model="item.value"
                  type="password"
                  show-password
                  :placeholder="item.key"
                />
                <!-- 数字类型 -->
                <el-input-number
                  v-else-if="item.isNumber"
                  v-model="item.value"
                  style="width: 100%"
                />
                <!-- 普通文本 -->
                <el-input
                  v-else
                  v-model="item.value"
                  :placeholder="item.key"
                />
              </el-form-item>
            </template>
          </el-form>
        </div>

        <template #footer>
          <div class="dialog-footer">
            <el-button class="cancel-btn" @click="editConfigDialog = false">
              {{ t('btn_cancel') }}
            </el-button>
            <el-button type="primary" class="save-btn" :loading="editConfigSaving" @click="handleSaveConfig">
              {{ t('btn_save_config') }}
            </el-button>
          </div>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getModuleDetail, enableTool, disableTool, reloadModule, updateToolDescription, updateModuleConfig, exportModule } from '../api/index.js'
import { useI18n } from '../i18n.js'
import ToolParamsExpand from '../components/ToolParamsExpand.vue'
import EditToolDescDialog from '../components/EditToolDescDialog.vue'
import ToolsTable from '../components/ToolsTable.vue'

const { t } = useI18n()

const props = defineProps({
  moduleName: String
})

// 密码可见性状态
const visiblePasswords = reactive(new Set())

const editDescDialog = ref(false)
const editDescTool = ref(null)
const editDescValue = ref('')
const editDescSaving = ref(false)

// 配置编辑相关
const editConfigDialog = ref(false)
const editConfigFields = ref([])
const editConfigSaving = ref(false)

const route = useRoute()
const moduleInfo = ref(null)
const loading = ref(false)
const reloading = ref(false)
const exporting = ref(false)

const tools = computed(() => moduleInfo.value?.tools || [])

async function fetchDetail() {
  loading.value = true
  try {
    const name = props.moduleName || route.params.moduleName
    const res = await getModuleDetail(name)
    if (res.Code === 12) {
      moduleInfo.value = res.Data
    } else {
      ElMessage.error(res.Message?.Description || t('msg_fetch_module_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_fetch_module_fail'))
  } finally {
    loading.value = false
  }
}

async function handleToggleTool(tool, enabled) {
  try {
    const res = enabled ? await enableTool(tool.name) : await disableTool(tool.name)
    if (res.Code === 12) {
      tool.enabled = enabled ? 1 : 0
      ElMessage.success(res.Message?.Description)
    } else {
      ElMessage.error(res.Message?.Description || t('msg_op_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_op_fail'))
  }
}

async function handleReload() {
  reloading.value = true
  try {
    const name = props.moduleName || route.params.moduleName
    const res = await reloadModule(name)
    if (res.Code === 12) {
      ElMessage.success(t('msg_reload_success'))
      await fetchDetail()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_reload_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_reload_fail'))
  } finally {
    reloading.value = false
  }
}

async function handleExport() {
  if (!moduleInfo.value) return
  exporting.value = true
  try {
    const name = props.moduleName || route.params.moduleName
    const res = await exportModule(name)

    // 创建下载链接
    // 注意：由于 axios 拦截器返回 response.data，res 已经是 blob 对象
    const blob = res instanceof Blob ? res : new Blob([res], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${name.split('.')[0]}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success(t('msg_export_success'))
  } catch (e) {
    ElMessage.error(t('msg_export_fail'))
  } finally {
    exporting.value = false
  }
}

function handleEditDesc(row) {
  editDescTool.value = row
  editDescValue.value = row.custom_desc || row.description || ''
  editDescDialog.value = true
}

async function handleSaveDesc() {
  if (!editDescTool.value) return
  editDescSaving.value = true
  try {
    const res = await updateToolDescription(editDescTool.value.name, editDescValue.value)
    if (res.Code === 12) {
      editDescTool.value.description = editDescValue.value
      ElMessage.success(t('msg_update_desc_success'))
      editDescDialog.value = false
    } else {
      ElMessage.error(res.Message?.Description || t('msg_update_desc_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_update_desc_fail'))
  } finally {
    editDescSaving.value = false
  }
}

function flattenConfig(config, prefix = '') {
  const result = {}
  for (const [key, value] of Object.entries(config)) {
    const fullKey = prefix ? `${prefix}.${key}` : key
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      Object.assign(result, flattenConfig(value, fullKey))
    } else {
      result[fullKey] = value
    }
  }
  return result
}

// 判断是否为密码字段
function isPasswordField(key) {
  const lowerKey = key.toLowerCase()
  return lowerKey.includes('password') || lowerKey.includes('pwd') || lowerKey.includes('secret') || lowerKey.includes('token') || lowerKey.includes('key')
}

// 判断是否为数字字段
function isNumberField(value) {
  return typeof value === 'number'
}

// 密码脱敏显示
function maskPassword(value) {
  if (!value) return ''
  const str = String(value)
  if (str.length <= 2) return '******'
  return '******'
}

// 切换密码可见性
function togglePasswordVisibility(key) {
  if (visiblePasswords.has(key)) {
    visiblePasswords.delete(key)
  } else {
    visiblePasswords.add(key)
  }
}

// 打开配置编辑对话框
function handleEditConfig() {
  if (!moduleInfo.value?.config) return

  const flatConfig = flattenConfig(moduleInfo.value.config)
  editConfigFields.value = Object.entries(flatConfig).map(([key, value]) => ({
    key,
    value: value,
    originalValue: value,
    isPassword: isPasswordField(key),
    isNumber: isNumberField(value)
  }))

  editConfigDialog.value = true
}

// 将扁平化的配置还原为嵌套结构
function unflattenConfig(fields) {
  const result = {}

  for (const field of fields) {
    const keys = field.key.split('.')
    let current = result

    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i]
      if (!(k in current)) {
        current[k] = {}
      }
      current = current[k]
    }

    const lastKey = keys[keys.length - 1]
    // 处理数字类型
    if (field.isNumber && typeof field.value === 'string') {
      current[lastKey] = parseFloat(field.value) || 0
    } else {
      current[lastKey] = field.value
    }
  }

  return result
}

// 保存配置
async function handleSaveConfig() {
  if (!moduleInfo.value) return

  editConfigSaving.value = true
  try {
    const newConfig = unflattenConfig(editConfigFields.value)
    const name = props.moduleName || route.params.moduleName
    const res = await updateModuleConfig(name, newConfig)

    if (res.Code === 12) {
      moduleInfo.value.config = newConfig
      ElMessage.success(t('msg_update_config_success'))
      editConfigDialog.value = false
    } else {
      ElMessage.error(res.Message?.Description || t('msg_update_config_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_update_config_fail'))
  } finally {
    editConfigSaving.value = false
  }
}

onMounted(fetchDetail)

watch(() => route.params.moduleName, () => {
  if (route.params.moduleName) fetchDetail()
})
</script>

<style scoped>
.detail-page {
  width: 100%;
}

.breadcrumb {
  margin-bottom: 20px;
  font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 13px;
}

.info-card {
  margin-bottom: 20px;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.info-header h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif;
  letter-spacing: 0.02em;
}

.info-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.meta-text {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
}

.info-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.tools-card {
  margin-bottom: 20px;
}

.tools-header {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.tools-unloaded-tip {
  font-weight: 400;
  font-size: 12px;
  color: var(--text-muted);
}

.config-card {
  margin-bottom: 20px;
}

.config-card code {
  font-size: 12px;
  word-break: break-all;
}

/* 密码字段样式 */
.password-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.password-field code {
  flex: 1;
}

.password-toggle {
  cursor: pointer;
  color: #909399;
  transition: color 0.2s;
  flex-shrink: 0;
}

.password-toggle:hover {
  color: #409EFF;
}

/* 配置卡片头部 */
.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 编辑配置对话框样式 */
.edit-config-dialog :deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

.edit-config-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 16px 20px;
  margin: 0;
  border-bottom: 1px solid rgba(0, 210, 255, 0.15);
}

.edit-config-dialog :deep(.el-dialog__title) {
  color: rgba(255, 255, 255, 0.9);
  font-size: 16px;
  font-weight: 600;
}

.edit-config-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: rgba(255, 255, 255, 0.5);
}

.edit-config-dialog :deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: #00d2ff;
}

.edit-config-dialog :deep(.el-dialog__body) {
  padding: 20px;
  background: var(--bg-secondary);
  max-height: 60vh;
  overflow-y: auto;
}

.edit-config-dialog :deep(.el-dialog__footer) {
  padding: 16px 20px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-light);
}

.edit-config-content :deep(.el-form-item) {
  margin-bottom: 16px;
}

.edit-config-content :deep(.el-form-item__label) {
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.edit-config-content :deep(.el-input__wrapper),
.edit-config-content :deep(.el-input-number) {
  border-radius: 6px;
}
</style>
