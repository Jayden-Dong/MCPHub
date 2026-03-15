<template>
  <div class="detail-page">
    <!-- 面包屑 -->
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ path: '/proxy' }">{{ t('page_breadcrumb_proxy') }}</el-breadcrumb-item>
      <el-breadcrumb-item>{{ serverInfo?.name || serverId }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div v-loading="loading">
      <!-- 服务器信息卡片 -->
      <el-card class="info-card" shadow="never" v-if="serverInfo">
        <div class="info-header">
          <div>
            <h2>{{ serverInfo.name }}</h2>
            <div class="info-meta">
              <el-tag :type="serverInfo.enabled ? 'success' : 'info'" size="small">
                {{ serverInfo.enabled ? t('tag_enabled') : t('tag_disabled') }}
              </el-tag>
              <el-tag :type="serverInfo.transport === 'streamable-http' ? 'primary' : 'warning'" size="small">
                {{ serverInfo.transport === 'streamable-http' ? t('transport_streamable') : t('transport_sse') }}
              </el-tag>
              <code class="meta-url">{{ serverInfo.url }}</code>
            </div>
            <div class="info-meta" v-if="serverInfo.last_sync">
              <span class="meta-text">{{ t('label_last_sync') }}: {{ serverInfo.last_sync }}</span>
            </div>
            <p class="info-desc" v-if="serverInfo.description">{{ serverInfo.description }}</p>
          </div>
          <div class="info-actions">
            <el-button @click="handleSync" :loading="syncing">
              <el-icon><Refresh /></el-icon> {{ t('btn_sync_tools') }}
            </el-button>
            <el-button @click="handleForceSync" :loading="forceSyncing" type="warning" plain>
              <el-icon><RefreshRight /></el-icon> {{ t('btn_force_sync_tools') }}
            </el-button>
            <el-button v-if="!serverInfo.enabled" type="primary"
                       @click="handleToggleServer(true)" :loading="toggling"
                       :disabled="!serverInfo.last_sync">
              {{ t('btn_enable_server') }}
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 工具列表 -->
      <el-card shadow="never" class="tools-card" v-if="serverInfo">
        <template #header>
          <div class="tools-header">
            <span>{{ t('proxy_tools_list') }} ({{ tools.length }})</span>
            <span v-if="!serverInfo.last_sync" class="tools-tip">{{ t('proxy_not_synced_tip') }}</span>
          </div>
        </template>

        <el-empty v-if="!serverInfo.last_sync"
                  :description="t('proxy_not_synced_empty')" :image-size="80" />

        <ToolsTable
          v-else
          :tools="tools"
          :primary-label="t('col_raw_name')"
          :primary-width="260"
          primary-field="raw_name"
          schema-field="input_schema"
          row-key-field="id"
          :disable-switch="!serverInfo.enabled"
          hide-secondary
          @toggle-tool="handleToggleTool"
          @edit-desc="handleEditDesc"
        />
      </el-card>

      <!-- 编辑工具描述对话框 -->
      <EditToolDescDialog
        v-model:visible="editDescDialog"
        v-model="editDescValue"
        :tool-name="editDescTool?.raw_name"
        :saving="editDescSaving"
        @save="handleSaveDesc"
      />

      <!-- 请求头展示 -->
      <el-card shadow="never" class="headers-card"
               v-if="serverInfo && serverInfo.headers && Object.keys(serverInfo.headers).length > 0">
        <template #header>请求头配置</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item v-for="(val, key) in serverInfo.headers" :key="key" :label="key">
            <code class="header-val">{{ maskHeaderValue(key, val) }}</code>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getProxyServerDetail, syncProxyServer, forceSyncProxyServer,
  enableProxyServer, disableProxyServer,
  enableProxyTool, disableProxyTool, updateProxyToolDescription
} from '../api/index.js'
import { useI18n } from '../i18n.js'
import EditToolDescDialog from '../components/EditToolDescDialog.vue'
import ToolsTable from '../components/ToolsTable.vue'

const { t } = useI18n()

const props = defineProps({ serverId: [String, Number] })
const route = useRoute()

const serverInfo = ref(null)
const loading = ref(false)
const syncing = ref(false)
const forceSyncing = ref(false)
const toggling = ref(false)

const editDescDialog = ref(false)
const editDescTool = ref(null)
const editDescValue = ref('')
const editDescSaving = ref(false)

const tools = computed(() => serverInfo.value?.tools || [])

function getId() {
  return Number(props.serverId || route.params.serverId)
}

async function fetchDetail() {
  loading.value = true
  try {
    const res = await getProxyServerDetail(getId())
    if (res.Code === 12) {
      serverInfo.value = res.Data
    } else {
      ElMessage.error(res.Message?.Description || t('msg_fetch_proxy_fail'))
    }
  } catch {
    ElMessage.error(t('msg_fetch_proxy_fail'))
  } finally {
    loading.value = false
  }
}

async function handleSync() {
  syncing.value = true
  try {
    const res = await syncProxyServer(getId())
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || t('msg_sync_success'))
      await fetchDetail()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_sync_fail'))
    }
  } catch {
    ElMessage.error(t('msg_sync_fail'))
  } finally {
    syncing.value = false
  }
}

async function handleForceSync() {
  try {
    await ElMessageBox.confirm(
      t('msg_force_sync_confirm'),
      t('msg_force_sync_confirm_title'),
      { cancelButtonText: t('btn_cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  forceSyncing.value = true
  try {
    const res = await forceSyncProxyServer(getId())
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || t('msg_force_sync_success'))
      await fetchDetail()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_force_sync_fail'))
    }
  } catch {
    ElMessage.error(t('msg_force_sync_fail'))
  } finally {
    forceSyncing.value = false
  }
}

async function handleToggleServer(enable) {
  toggling.value = true
  try {
    const res = enable ? await enableProxyServer(getId()) : await disableProxyServer(getId())
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || (enable ? t('msg_enable_server_success') : t('msg_disable_server_success')))
      await fetchDetail()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_op_fail'))
    }
  } catch {
    ElMessage.error(t('msg_op_fail'))
  } finally {
    toggling.value = false
  }
}

async function handleToggleTool(tool, enabled) {
  try {
    const res = enabled ? await enableProxyTool(tool.id) : await disableProxyTool(tool.id)
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description)
      // 重新获取数据确保前端与数据库同步
      await fetchDetail()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_op_fail'))
      tool.enabled = !enabled
    }
  } catch {
    ElMessage.error(t('msg_op_fail'))
    tool.enabled = !enabled
  }
}

function handleEditDesc(tool) {
  editDescTool.value = tool
  editDescValue.value = tool.custom_desc || tool.description || ''
  editDescDialog.value = true
}

async function handleSaveDesc() {
  editDescSaving.value = true
  try {
    const res = await updateProxyToolDescription(editDescTool.value.id, editDescValue.value)
    if (res.Code === 12) {
      editDescTool.value.custom_desc = editDescValue.value
      ElMessage.success(t('msg_update_desc_success'))
      editDescDialog.value = false
    } else {
      ElMessage.error(res.Message?.Description || t('msg_update_desc_fail'))
    }
  } catch {
    ElMessage.error(t('msg_update_desc_fail'))
  } finally {
    editDescSaving.value = false
  }
}

// ---- 辅助函数 ----
function maskHeaderValue(key, val) {
  const lk = key.toLowerCase()
  if (lk.includes('auth') || lk.includes('token') || lk.includes('key') || lk.includes('secret')) {
    return String(val).substring(0, 4) + '****'
  }
  return val
}

onMounted(fetchDetail)
</script>

<style scoped>
.detail-page {
  width: 100%;
}

.breadcrumb {
  margin-bottom: 20px;
  font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacangSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
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

.meta-url {
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
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

.info-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
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

.tools-tip {
  font-size: 12px;
  color: var(--el-color-warning);
}

.headers-card {
  margin-bottom: 20px;
}

.header-val {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
}
</style>
