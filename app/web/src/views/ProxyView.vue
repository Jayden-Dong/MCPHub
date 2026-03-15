<template>
  <div class="proxy-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">{{ t('page_title_proxy') }}</h2>
        <span class="server-count-badge">{{ servers.length }}</span>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openAddDialog">
          <el-icon><Plus /></el-icon> {{ t('btn_add_server') }}
        </el-button>
        <el-button @click="fetchServers" :loading="loading" circle>
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(64,158,255,0.1); color: #409EFF;">
          <el-icon :size="20"><Share /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #409EFF;">{{ servers.length }}</div>
          <div class="stat-label">{{ t('stat_proxy_servers') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(103,194,58,0.1); color: #67C23A;">
          <el-icon :size="20"><CircleCheckFilled /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #67C23A;">{{ enabledCount }}</div>
          <div class="stat-label">{{ t('stat_proxy_enabled') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(0,210,255,0.1); color: #00afc8;">
          <el-icon :size="20"><Tools /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #00afc8;">{{ totalTools }}</div>
          <div class="stat-label">{{ t('stat_proxy_tools') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(230,162,60,0.1); color: #E6A23C;">
          <el-icon :size="20"><Star /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #E6A23C;">{{ enabledTools }}</div>
          <div class="stat-label">{{ t('stat_enabled_tools') }}</div>
        </div>
      </div>
    </div>

    <!-- 服务器列表 -->
    <div v-loading="loading" class="server-list">
      <el-empty v-if="!loading && servers.length === 0"
                description="暂无代理服务器，点击「添加服务器」开始接入"
                :image-size="100" />

      <el-table v-else :data="servers" stripe class="server-table" @row-dblclick="goDetail">
        <!-- 启用开关 -->
        <el-table-column :label="t('col_status')" width="90">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              :active-value="1"
              :inactive-value="0"
              size="small"
              :disabled="!row.last_sync"
              :title="!row.last_sync ? t('proxy_not_synced_tip') : ''"
              @change="(val) => handleToggleServer(row, val === 1)"
            />
          </template>
        </el-table-column>

        <!-- 服务器名称 -->
        <el-table-column :label="t('col_server_name')" width="180">
          <template #default="{ row }">
            <div class="server-name-cell">
              <span class="server-name">{{ row.name }}</span>
              <el-tag v-if="row.enabled" type="success" size="small">{{ t('tag_enabled') }}</el-tag>
              <el-tag v-else type="info" size="small">{{ t('tag_disabled') }}</el-tag>
            </div>
          </template>
        </el-table-column>

        <!-- 地址 -->
        <el-table-column :label="t('col_server_url')" width="160">
          <template #default="{ row }">
            <el-tooltip :content="row.url" placement="top" :show-after="400">
              <code class="url-text url-truncated">{{ row.url }}</code>
            </el-tooltip>
          </template>
        </el-table-column>

        <!-- 描述 -->
        <el-table-column :label="t('col_description')" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="server-desc-text">{{ row.description || '' }}</span>
          </template>
        </el-table-column>

        <!-- 传输类型 -->
        <el-table-column :label="t('col_transport')" width="160">
          <template #default="{ row }">
            <el-tag :type="row.transport === 'streamable-http' ? 'primary' : 'warning'" size="small">
              {{ row.transport === 'streamable-http' ? t('transport_streamable') : t('transport_sse') }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 工具数 -->
        <el-table-column label="工具" width="120">
          <template #default="{ row }">
            <span v-if="row.last_sync">
              {{ row.enabled_tool_count }} / {{ row.tool_count }}
            </span>
            <el-tag v-else type="warning" size="small">{{ t('tag_not_synced') }}</el-tag>
          </template>
        </el-table-column>

        <!-- 最近同步 -->
        <el-table-column label="最近同步" width="170">
          <template #default="{ row }">
            <span class="sync-time">{{ row.last_sync || t('label_never_synced') }}</span>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('col_actions')" width="100" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-tooltip content="编辑配置" placement="top">
                <el-button size="small" circle @click="handleCommand('edit', row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button size="small" circle type="danger" plain @click="handleDelete(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加 / 编辑服务器对话框 -->
    <el-dialog
      v-model="showServerDialog"
      :title="editingServer ? t('dlg_edit_server_title') : t('dlg_add_server_title')"
      width="500px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="serverForm" label-position="top" class="server-form">
        <div class="form-row">
          <el-form-item :label="t('label_server_name')" class="form-item-flex">
            <el-input v-model="serverForm.name" :placeholder="t('placeholder_server_name')"
                      :disabled="!!editingServer" />
          </el-form-item>
          <el-form-item :label="t('label_transport')" class="form-item-transport">
            <el-select v-model="serverForm.transport" style="width: 100%;">
              <el-option value="streamable-http" :label="t('transport_streamable')" />
              <el-option value="sse" :label="t('transport_sse')" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item :label="t('label_server_url')">
          <el-input v-model="serverForm.url" :placeholder="t('placeholder_server_url')" />
        </el-form-item>
        <el-form-item :label="t('label_description')">
          <el-input v-model="serverForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('label_headers')">
          <el-input v-model="serverForm.headersRaw" type="textarea" :rows="3"
                    :placeholder="t('placeholder_headers')" class="mono-input" />
        </el-form-item>
        <el-form-item :label="t('label_timeout')">
          <el-input-number v-model="serverForm.timeout" :min="5" :max="600" :step="5"
                           controls-position="right" style="width: 160px;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showServerDialog = false">{{ t('btn_cancel') }}</el-button>
        <el-button type="primary" :loading="serverSaving" @click="handleSaveServer">
          {{ editingServer ? t('btn_save_config') : t('btn_add_server') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getProxyServers, addProxyServer, updateProxyServer, deleteProxyServer,
  syncProxyServer, enableProxyServer, disableProxyServer
} from '../api/index.js'
import { useI18n } from '../i18n.js'

const { t } = useI18n()
const router = useRouter()

const servers = ref([])
const loading = ref(false)
const syncingId = ref(null)
const showServerDialog = ref(false)
const editingServer = ref(null)
const serverSaving = ref(false)

const serverForm = ref({
  name: '',
  url: '',
  transport: 'streamable-http',
  timeout: 60,
  description: '',
  headersRaw: '{}',
})

const enabledCount = computed(() => servers.value.filter(s => s.enabled).length)
const totalTools = computed(() => servers.value.reduce((sum, s) => sum + (s.tool_count || 0), 0))
const enabledTools = computed(() => servers.value.reduce((sum, s) => sum + (s.enabled_tool_count || 0), 0))

async function fetchServers() {
  loading.value = true
  try {
    const res = await getProxyServers()
    if (res.Code === 12) {
      servers.value = res.Data || []
    } else {
      ElMessage.error(res.Message?.Description || '获取列表失败')
    }
  } catch {
    ElMessage.error('获取列表失败')
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  editingServer.value = null
  serverForm.value = { name: '', url: '', transport: 'streamable-http', timeout: 60, description: '', headersRaw: '{}' }
  showServerDialog.value = true
}

function handleCommand(cmd, row) {
  if (cmd === 'edit') {
    editingServer.value = row
    serverForm.value = {
      name: row.name,
      url: row.url,
      transport: row.transport,
      timeout: row.timeout || 60,
      description: row.description || '',
      headersRaw: JSON.stringify(row.headers || {}, null, 2),
    }
    showServerDialog.value = true
  } else if (cmd === 'delete') {
    handleDelete(row)
  }
}

async function handleSaveServer() {
  if (!serverForm.value.name || !serverForm.value.url) {
    ElMessage.warning('名称和地址不能为空')
    return
  }
  let headers = {}
  try {
    headers = JSON.parse(serverForm.value.headersRaw || '{}')
  } catch {
    ElMessage.error(t('msg_invalid_headers_json'))
    return
  }
  serverSaving.value = true
  try {
    const payload = {
      name: serverForm.value.name,
      url: serverForm.value.url,
      transport: serverForm.value.transport,
      timeout: serverForm.value.timeout,
      description: serverForm.value.description,
      headers,
    }
    let res
    if (editingServer.value) {
      res = await updateProxyServer(editingServer.value.id, payload)
    } else {
      res = await addProxyServer(payload)
    }
    if (res.Code === 12) {
      ElMessage.success(editingServer.value ? t('msg_update_server_success') : t('msg_add_server_success'))
      showServerDialog.value = false
      await fetchServers()
    } else {
      ElMessage.error(res.Message?.Description || (editingServer.value ? t('msg_update_server_fail') : t('msg_add_server_fail')))
    }
  } catch {
    ElMessage.error(editingServer.value ? t('msg_update_server_fail') : t('msg_add_server_fail'))
  } finally {
    serverSaving.value = false
  }
}

async function handleSync(row) {
  syncingId.value = row.id
  try {
    const res = await syncProxyServer(row.id)
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || t('msg_sync_success'))
      await fetchServers()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_sync_fail'))
    }
  } catch {
    ElMessage.error(t('msg_sync_fail'))
  } finally {
    syncingId.value = null
  }
}

async function handleToggleServer(row, val) {
  try {
    const res = val ? await enableProxyServer(row.id) : await disableProxyServer(row.id)
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || (val ? t('msg_enable_server_success') : t('msg_disable_server_success')))
      row.enabled = val ? 1 : 0
    } else {
      ElMessage.error(res.Message?.Description || t('msg_op_fail'))
    }
  } catch {
    ElMessage.error(t('msg_op_fail'))
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      t('msg_delete_server_confirm', { name: row.name }),
      t('msg_delete_server_title'),
      { type: 'warning', confirmButtonText: t('btn_delete'), cancelButtonText: t('btn_cancel') }
    )
    const res = await deleteProxyServer(row.id)
    if (res.Code === 12) {
      ElMessage.success(t('msg_delete_server_success'))
      await fetchServers()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_delete_server_fail'))
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('msg_delete_server_fail'))
  }
}

function goDetail(row) {
  router.push(`/proxy/${row.id}`)
}

onMounted(fetchServers)
</script>

<style scoped>
.proxy-page {
  width: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  color: var(--el-text-color-primary);
}

.server-count-badge {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 13px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-default);
  transition: box-shadow 0.2s, background-color 0.3s;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.server-list {
  background: var(--el-bg-color);
  border-radius: 10px;
  border: 1px solid var(--el-border-color);
  overflow: hidden;
}

.server-table {
  width: 100%;
}

.server-name-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.server-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.url-text {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.url-truncated {
  display: block;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.server-desc-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.sync-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.action-btns {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.server-form {
  padding: 0 4px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-item-flex {
  flex: 1;
  min-width: 0;
}

.form-item-transport {
  width: 190px;
  flex-shrink: 0;
}


.mono-input :deep(textarea) {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
}
</style>
