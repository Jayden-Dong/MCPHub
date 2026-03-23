<template>
  <div class="modules-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">{{ t('page_title_modules') }}</h2>
        <span class="module-count-badge">{{ modules.length }}</span>
      </div>
      <div class="header-actions">
        <!-- 搜索框 -->
        <div class="search-box">
          <el-input
            v-model="searchKeyword"
            :placeholder="t('search_placeholder')"
            clearable
            :prefix-icon="Search"
            style="width: 200px;"
          />
        </div>
        <!-- 视图切换 -->
        <div class="view-toggle-group">
          <button
            :class="['view-btn', viewMode === 'grid' ? 'active' : '']"
            @click="viewMode = 'grid'"
            :title="t('title_card_view')"
          >
            <el-icon><Grid /></el-icon>
          </button>
          <button
            :class="['view-btn', viewMode === 'list' ? 'active' : '']"
            @click="viewMode = 'list'"
            :title="t('title_list_view')"
          >
            <el-icon><List /></el-icon>
          </button>
        </div>
        <el-button @click="handleScan" :loading="scanning">
          <el-icon><Search /></el-icon> {{ t('btn_scan') }}
        </el-button>
        <el-button type="primary" @click="showInstallDialog = true">
          <el-icon><Upload /></el-icon> {{ t('btn_install') }}
        </el-button>
        <el-button @click="fetchModules" :loading="loading" circle>
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 分组筛选栏 -->
    <div class="group-filter-bar">
      <div class="group-tabs">
        <button
          :class="['group-tab', !selectedGroupId ? 'active' : '']"
          @click="selectedGroupId = null"
          @contextmenu.prevent="openGroupContextMenu($event, defaultGroup)"
        >{{ t('group_all') }}<span class="group-tab-count">{{ modules.length }}</span></button>
        <button
          v-for="g in groups"
          :key="g.id"
          :class="['group-tab', selectedGroupId === g.id ? 'active' : '']"
          @click="selectedGroupId = g.id"
          @contextmenu.prevent="openGroupContextMenu($event, g)"
        >
          {{ g.name }}
          <span class="group-tab-count">{{ (g.module_count || 0) + (g.proxy_count || 0) }}</span>
        </button>
        <button class="group-tab group-tab-add" @click="openCreateGroupDialog" :title="t('btn_create_group')">
          <el-icon :size="14"><Plus /></el-icon>
        </button>
      </div>
    </div>

    <!-- 分组右键菜单 -->
    <teleport to="body">
      <div
        v-if="groupContextMenu.visible"
        class="group-context-menu"
        :style="{ left: groupContextMenu.x + 'px', top: groupContextMenu.y + 'px' }"
        @click="groupContextMenu.visible = false"
      >
        <div class="context-menu-item" @click="copyGroupId(groupContextMenu.group)">
          <el-icon><CopyDocument /></el-icon> {{ t('menu_copy_group_id') }}
        </div>
        <template v-if="groupContextMenu.group">
          <div class="context-menu-divider"></div>
          <div class="context-menu-item" @click="openEditGroupDialog(groupContextMenu.group)">
            <el-icon><Edit /></el-icon> {{ t('dlg_edit_group_title') }}
          </div>
          <div class="context-menu-item context-menu-danger" @click="handleDeleteGroup(groupContextMenu.group)">
            <el-icon><Delete /></el-icon> {{ t('btn_delete') }}
          </div>
        </template>
      </div>
    </teleport>

    <!-- 统计信息 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(64,158,255,0.1); color: #409EFF;">
          <el-icon :size="20"><Box /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #409EFF;">{{ modules.length }}</div>
          <div class="stat-label">{{ t('stat_total') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(103,194,58,0.1); color: #67C23A;">
          <el-icon :size="20"><CircleCheckFilled /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #67C23A;">{{ loadedCount }}</div>
          <div class="stat-label">{{ t('stat_loaded') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(144,147,153,0.1); color: #909399;">
          <el-icon :size="20"><CircleCloseFilled /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #909399;">{{ modules.length - loadedCount }}</div>
          <div class="stat-label">{{ t('stat_unloaded') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap" style="background: rgba(0,210,255,0.1); color: #00afc8;">
          <el-icon :size="20"><SetUp /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value" style="color: #00afc8;">{{ totalTools }}</div>
          <div class="stat-label">{{ t('stat_tools') }}</div>
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

    <!-- 卡片视图 -->
    <div v-if="viewMode === 'grid'" class="modules-grid" v-loading="loading">
      <el-card
        v-for="mod in filteredModules"
        :key="mod.module_name"
        class="module-card"
        :class="{ 'module-loaded': mod.loaded, 'module-external': mod.is_external, 'module-proxy': mod.is_proxy }"
        shadow="hover"
        @dblclick="handleCardDblClick(mod)"
      >
        <div class="module-card-header">
          <div class="module-title-row">
            <span :class="['status-dot-sm', mod.loaded ? 'dot-online' : 'dot-offline']"></span>
            <span class="module-name">{{ mod.display_name || mod.module_name }}</span>
            <el-tag v-if="mod.is_proxy" size="small" type="primary">{{ t('tag_proxy') }}</el-tag>
            <el-tag v-else-if="mod.is_external" size="small" type="warning">{{ t('tag_external') }}</el-tag>
          </div>
          <el-switch
            :key="'switch-' + mod.module_name"
            v-model="mod.loaded"
            :loading="mod._switching"
            @change="(val) => handleToggleModule(mod, val)"
          />
        </div>

        <div class="module-meta">
          <template v-if="mod.is_proxy">
            <el-tag size="small" :type="mod._proxy_transport === 'streamable-http' ? 'primary' : 'warning'" style="font-size: 10px;">
              {{ mod._proxy_transport === 'streamable-http' ? t('transport_streamable') : t('transport_sse') }}
            </el-tag>
          </template>
          <template v-else>
            <span class="module-path">{{ mod.module_name }}</span>
            <span v-if="mod.version" class="module-version">v{{ mod.version }}</span>
          </template>
        </div>

        <p class="module-desc" v-if="mod.description">{{ mod.description }}</p>

        <div class="module-tools-summary" v-if="mod.is_proxy && mod._proxy_tool_count > 0">
          <el-icon><SetUp /></el-icon>
          <span>{{ t('tools_count', { n: mod._proxy_tool_count }) }}</span>
          <span class="tools-enabled">{{ t('tools_enabled', { n: mod._proxy_enabled_tool_count }) }}</span>
        </div>
        <div class="module-tools-summary" v-else-if="!mod.is_proxy && mod.loaded && mod.tools">
          <el-icon><SetUp /></el-icon>
          <span>{{ t('tools_count', { n: mod.tools.length }) }}</span>
          <span class="tools-enabled">{{ t('tools_enabled', { n: enabledToolCount(mod) }) }}</span>
        </div>

        <!-- 占位区域，确保操作按钮对齐到底部 -->
        <div class="module-spacer"></div>

        <div class="module-actions">
          <el-button
            size="small"
            @click="handleGoDetail(mod)"
          >
            <el-icon><View /></el-icon> {{ t('btn_detail') }}
          </el-button>
          <el-popover
            trigger="click"
            :width="240"
            placement="bottom-start"
            popper-class="group-assign-popper"
            @show="loadModuleGroupState(mod)"
          >
            <template #reference>
              <el-button size="small" :class="hasAnyGroup(mod) ? 'btn-grouped' : ''">
                <el-icon><Folder /></el-icon> {{ t('btn_group') }}
              </el-button>
            </template>
            <div class="gap-panel">
              <div class="gap-header">
                <el-icon :size="13" style="color:#409EFF;flex-shrink:0"><Folder /></el-icon>
                <span class="gap-header-title">{{ t('btn_group') }}</span>
                <span class="gap-header-name">{{ mod.display_name || mod.module_name }}</span>
              </div>
              <div class="gap-divider"></div>
              <div class="gap-list" v-if="groups.length > 0">
                <div
                  v-for="g in groups"
                  :key="g.id"
                  class="gap-item"
                  :class="{ 'gap-item-checked': modGroupChecked[g.id] }"
                  @click="handleToggleModGroup(mod, g.id, !modGroupChecked[g.id])"
                >
                  <span class="gap-item-dot" :style="{ background: groupColor(g.id) }"></span>
                  <span class="gap-item-label">{{ g.name }}</span>
                  <el-icon v-if="modGroupChecked[g.id]" class="gap-item-check" :size="14"><Check /></el-icon>
                </div>
              </div>
              <div v-else class="gap-empty">
                <el-icon :size="28" style="color:var(--text-subtle)"><FolderOpened /></el-icon>
                <span>{{ t('group_none_hint') }}</span>
              </div>
              <div class="gap-divider"></div>
              <div class="gap-footer" @click="openCreateGroupDialog">
                <el-icon :size="13"><Plus /></el-icon>
                <span>{{ t('btn_create_group') }}</span>
              </div>
            </div>
          </el-popover>
          <el-button
            size="small"
            @click="handleReload(mod)"
            :disabled="!mod.is_proxy && !mod.loaded"
            :loading="mod._reloading"
          >
            <el-icon><RefreshRight /></el-icon> {{ t('btn_reload') }}
          </el-button>
          <el-button
            v-if="!mod.is_proxy && mod.is_external"
            size="small"
            @click="handleExport(mod)"
            :loading="mod._exporting"
          >
            <el-icon><Download /></el-icon> {{ t('btn_export') }}
          </el-button>
          <el-button
            v-if="mod.is_proxy || mod.is_external"
            size="small"
            type="danger"
            @click="handleDelete(mod)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 列表视图 -->
    <div v-else class="modules-table-wrap" v-loading="loading">
      <el-table :data="filteredModules" stripe class="modules-table" row-key="module_name" @row-dblclick="handleRowDblClick">
        <el-table-column :label="t('col_status')" width="70" align="center">
          <template #default="{ row }">
            <span :class="['status-dot-sm', row.loaded ? 'dot-online' : 'dot-offline']"></span>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_module_name')" min-width="130">
          <template #default="{ row }">
            <div class="list-name-cell">
              <span class="module-name">{{ row.display_name || row.module_name }}</span>
              <el-tag v-if="row.is_proxy" size="small" type="primary" style="margin-left: 6px;">{{ t('tag_proxy') }}</el-tag>
              <el-tag v-else-if="row.is_external" size="small" type="warning" style="margin-left: 6px;">{{ t('tag_external') }}</el-tag>
            </div>
            <div v-if="!row.is_proxy" class="module-path" style="margin-top: 2px;">{{ row.module_name }}</div>
            <div v-else class="module-path" style="margin-top: 2px;">
              <el-tag size="small" :type="row._proxy_transport === 'streamable-http' ? 'primary' : 'warning'" style="font-size: 10px;">
                {{ row._proxy_transport === 'streamable-http' ? t('transport_streamable') : t('transport_sse') }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_version')" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.version" class="module-version">v{{ row.version }}</span>
            <span v-else style="color: #C0C4CC;">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_description')" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: #606266; font-size: 13px;">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_tools')" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.is_proxy && row._proxy_tool_count > 0" style="color: #00afc8; font-weight: 600;">
              {{ row._proxy_enabled_tool_count }}/{{ row._proxy_tool_count }}
            </span>
            <span v-else-if="!row.is_proxy && row.loaded && row.tools" style="color: #00afc8; font-weight: 600;">{{ row.tools.length }}</span>
            <span v-else style="color: #C0C4CC;">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_install_time')" width="160" align="center">
          <template #default="{ row }">
            <span v-if="row.install_time" style="color: #606266; font-size: 12px;">{{ row.install_time }}</span>
            <span v-else style="color: #C0C4CC;">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_toggle')" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              :key="'switch-' + row.module_name"
              v-model="row.loaded"
              :loading="row._switching"
              @change="(val) => handleToggleModule(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column :label="t('col_actions')" width="320" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button
                size="small"
                @click="handleGoDetail(row)"
              >{{ t('btn_detail') }}</el-button>
              <el-popover
                trigger="click"
                :width="240"
                placement="bottom-start"
                popper-class="group-assign-popper"
                @show="loadModuleGroupState(row)"
              >
                <template #reference>
                  <el-button size="small" :class="hasAnyGroup(row) ? 'btn-grouped' : ''" :title="t('btn_group')">
                    <el-icon><Folder /></el-icon>
                  </el-button>
                </template>
                <div class="gap-panel">
                  <div class="gap-header">
                    <el-icon :size="13" style="color:#409EFF;flex-shrink:0"><Folder /></el-icon>
                    <span class="gap-header-title">{{ t('btn_group') }}</span>
                    <span class="gap-header-name">{{ row.display_name || row.module_name }}</span>
                  </div>
                  <div class="gap-divider"></div>
                  <div class="gap-list" v-if="groups.length > 0">
                    <div
                      v-for="g in groups"
                      :key="g.id"
                      class="gap-item"
                      :class="{ 'gap-item-checked': modGroupChecked[g.id] }"
                      @click="handleToggleModGroup(row, g.id, !modGroupChecked[g.id])"
                    >
                      <span class="gap-item-dot" :style="{ background: groupColor(g.id) }"></span>
                      <span class="gap-item-label">{{ g.name }}</span>
                      <el-icon v-if="modGroupChecked[g.id]" class="gap-item-check" :size="14"><Check /></el-icon>
                    </div>
                  </div>
                  <div v-else class="gap-empty">
                    <el-icon :size="28" style="color:var(--text-subtle)"><FolderOpened /></el-icon>
                    <span>{{ t('group_none_hint') }}</span>
                  </div>
                  <div class="gap-divider"></div>
                  <div class="gap-footer" @click="openCreateGroupDialog">
                    <el-icon :size="13"><Plus /></el-icon>
                    <span>{{ t('btn_create_group') }}</span>
                  </div>
                </div>
              </el-popover>
              <el-button
                size="small"
                @click="handleReload(row)"
                :disabled="!row.is_proxy && !row.loaded"
                :loading="row._reloading"
              >{{ t('btn_reload') }}</el-button>
              <el-button
                v-if="!row.is_proxy && row.is_external"
                size="small"
                @click="handleExport(row)"
                :loading="row._exporting"
              >{{ t('btn_export') }}</el-button>
              <el-button
                v-if="row.is_proxy || row.is_external"
                size="small"
                type="danger"
                @click="handleDelete(row)"
              >{{ t('btn_delete') }}</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 安装模块对话框 -->
    <el-dialog v-model="showInstallDialog" :title="t('dlg_install_title')" width="480px">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        accept=".zip"
        :limit="1"
        :on-exceed="() => ElMessage.warning(t('upload_only_one'))"
        v-model:file-list="uploadFiles"
      >
        <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
        <div class="el-upload__text">{{ t('upload_drag_text') }} <em>{{ t('upload_click_select') }}</em></div>
        <template #tip>
          <div class="el-upload__tip">{{ t('upload_tip') }}</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showInstallDialog = false">{{ t('btn_cancel') }}</el-button>
        <el-button type="primary" @click="handleInstall" :loading="installing">{{ t('btn_install_confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫描结果对话框 -->
    <el-dialog v-model="showScanDialog" :title="t('dlg_scan_title')" width="600px">
      <el-table :data="scanResults" stripe>
        <el-table-column prop="display_name" :label="t('col_module_name')" width="150" />
        <el-table-column prop="module_name" :label="t('col_module_path')" />
        <el-table-column prop="is_external" :label="t('col_type')" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_external ? 'warning' : 'info'" size="small">
              {{ row.is_external ? t('tag_external') : t('tag_builtin') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_action')" width="100">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleLoadScanned(row)">
              {{ t('btn_load') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="scanResults.length === 0" :description="t('no_unloaded')" />
    </el-dialog>

    <!-- 创建/编辑分组对话框 -->
    <el-dialog
      v-model="showGroupFormDialog"
      :show-close="false"
      width="520px"
      class="group-form-dialog"
    >
      <template #header>
        <div class="group-dlg-header">
          <div class="group-dlg-icon" :class="editingGroup ? 'icon-edit' : 'icon-create'">
            <el-icon :size="22"><CollectionTag v-if="!editingGroup" /><Edit v-else /></el-icon>
          </div>
          <div>
            <div class="group-dlg-title">{{ editingGroup ? t('dlg_edit_group_title') : t('dlg_create_group_title') }}</div>
            <div class="group-dlg-sub">{{ editingGroup ? t('group_dlg_sub_edit') : t('group_dlg_sub_create') }}</div>
          </div>
        </div>
      </template>

      <div class="group-dlg-body">
        <div class="group-field">
          <label class="group-field-label">{{ t('label_group_name') }}<span class="required-mark">*</span></label>
          <el-input
            v-model="groupForm.name"
            :placeholder="t('placeholder_group_name')"
            size="large"
            clearable
            @keyup.enter="handleSaveGroup"
          />
        </div>
        <div class="group-field">
          <label class="group-field-label">{{ t('label_group_desc') }}</label>
          <el-input
            v-model="groupForm.description"
            type="textarea"
            :rows="3"
            :placeholder="t('placeholder_group_desc')"
            resize="none"
          />
        </div>
      </div>

      <template #footer>
        <div class="group-dlg-footer">
          <el-button size="large" @click="showGroupFormDialog = false">{{ t('btn_cancel') }}</el-button>
          <el-button
            type="primary"
            size="large"
            :disabled="!groupForm.name.trim()"
            @click="handleSaveGroup"
          >
            <el-icon><Check /></el-icon>
            {{ editingGroup ? t('btn_save_desc') : t('btn_create_group') }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getModules, scanModules, loadModule, unloadModule, reloadModule, installModule, deleteModule, exportModule,
  getProxyServers, enableProxyServer, disableProxyServer, syncProxyServer, deleteProxyServer,
  getGroups, createGroup, updateGroup, deleteGroup as deleteGroupApi, getGroupMembers,
  addModuleToGroup, removeModuleFromGroup, addProxyToGroup, removeProxyFromGroup
} from '../api/index.js'
import { useI18n } from '../i18n.js'

const { t } = useI18n()
const router = useRouter()

const modules = ref([])
const loading = ref(false)
const scanning = ref(false)
const installing = ref(false)
const showInstallDialog = ref(false)
const showScanDialog = ref(false)
const scanResults = ref([])
const uploadFiles = ref([])
const uploadRef = ref()
const viewMode = ref('grid')
const searchKeyword = ref('')

// ---- 分组相关 ----
const groups = ref([])
const defaultGroup = ref(null)
const selectedGroupId = ref(null)
const groupMemberModuleNames = ref(new Set())
const groupMemberProxyIds = ref(new Set())
const showGroupFormDialog = ref(false)
const editingGroup = ref(null)
const groupForm = ref({ name: '', description: '' })
const modGroupChecked = ref({})  // { groupId: boolean } — 当前 popover 打开的模块的分组状态
const groupContextMenu = ref({ visible: false, x: 0, y: 0, group: null })

const loadedCount = computed(() => modules.value.filter(m => m.loaded).length)
const totalTools = computed(() =>
  modules.value.reduce((sum, m) => {
    if (m.is_proxy) return sum + (m._proxy_tool_count || 0)
    return sum + (m.tools ? m.tools.length : 0)
  }, 0)
)
const enabledTools = computed(() =>
  modules.value.reduce((sum, m) => {
    if (m.is_proxy) return sum + (m._proxy_enabled_tool_count || 0)
    return sum + (m.tools ? m.tools.filter(t => t.enabled).length : 0)
  }, 0)
)

// 过滤后的模块列表（分组 + 搜索）
const filteredModules = computed(() => {
  let list = modules.value

  // 按分组筛选
  if (selectedGroupId.value) {
    list = list.filter(m => {
      if (m.is_proxy) {
        return groupMemberProxyIds.value.has(m._proxy_id)
      }
      return groupMemberModuleNames.value.has(m.module_name)
    })
  }

  // 按关键字搜索
  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.toLowerCase().trim()
    list = list.filter(m => {
      const name = (m.module_name || '').toLowerCase()
      const displayName = (m.display_name || '').toLowerCase()
      const desc = (m.description || '').toLowerCase()
      return name.includes(keyword) || displayName.includes(keyword) || desc.includes(keyword)
    })
  }

  return list
})

function enabledToolCount(mod) {
  if (!mod.tools) return 0
  return mod.tools.filter(t => t.enabled).length
}

function handleGoDetail(mod) {
  if (mod.is_proxy) {
    router.push(`/proxy/${mod._proxy_id}`)
  } else {
    router.push({ name: 'ModuleDetail', params: { moduleName: mod.module_name } })
  }
}

function handleCardDblClick(mod) {
  handleGoDetail(mod)
}

function handleRowDblClick(row) {
  handleGoDetail(row)
}

async function fetchModules() {
  loading.value = true
  try {
    const [modRes, proxyRes] = await Promise.all([getModules(), getProxyServers()])
    let items = []
    if (modRes.Code === 12) {
      items = (modRes.Data || []).map(m => ({ ...m, _switching: false, _reloading: false, _exporting: false }))
    }
    if (proxyRes.Code === 12) {
      const proxies = (proxyRes.Data || []).map(s => ({
        module_name: `proxy:${s.id}`,
        display_name: s.name,
        description: s.description || '',
        loaded: !!s.enabled,
        is_external: false,
        is_proxy: true,
        _proxy_id: s.id,
        _proxy_transport: s.transport,
        _proxy_tool_count: s.tool_count || 0,
        _proxy_enabled_tool_count: s.enabled_tool_count || 0,
        tools: [],
        version: null,
        install_time: null,
        _switching: false,
        _reloading: false,
        _exporting: false,
      }))
      items = [...items, ...proxies]
    }
    modules.value = items
  } catch (e) {
    ElMessage.error(t('msg_fetch_modules_fail'))
  } finally {
    loading.value = false
  }
}

async function handleToggleModule(mod, loaded) {
  mod._switching = true
  try {
    if (mod.is_proxy) {
      const res = loaded ? await enableProxyServer(mod._proxy_id) : await disableProxyServer(mod._proxy_id)
      if (res.Code === 12) {
        ElMessage.success(res.Message?.Description || t('msg_op_success'))
        await fetchModules()
        // 确保在下一个 tick 更新视图状态
        await nextTick()
      } else {
        ElMessage.error(res.Message?.Description || t('msg_op_fail'))
        mod.loaded = !loaded
      }
      return
    }
    let res
    if (loaded) {
      res = await loadModule(mod.module_name, mod.config, mod.is_external)
    } else {
      res = await unloadModule(mod.module_name)
    }
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || t('msg_op_success'))
      await fetchModules()
      await nextTick()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_op_fail'))
      mod.loaded = !loaded
    }
  } catch (e) {
    ElMessage.error(t('msg_op_fail'))
    mod.loaded = !loaded
  } finally {
    mod._switching = false
  }
}

async function handleReload(mod) {
  mod._reloading = true
  try {
    const res = mod.is_proxy
      ? await syncProxyServer(mod._proxy_id)
      : await reloadModule(mod.module_name)
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || t('msg_reload_success'))
      await fetchModules()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_reload_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_reload_fail'))
  } finally {
    mod._reloading = false
  }
}

async function handleExport(mod) {
  mod._exporting = true
  try {
    const res = await exportModule(mod.module_name)

    // 创建下载链接
    // 注意：由于 axios 拦截器返回 response.data，res 已经是 blob 对象
    const blob = res instanceof Blob ? res : new Blob([res], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${mod.module_name.split('.')[0]}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success(t('msg_export_success'))
  } catch (e) {
    ElMessage.error(t('msg_export_fail'))
  } finally {
    mod._exporting = false
  }
}

async function handleScan() {
  scanning.value = true
  try {
    const res = await scanModules()
    if (res.Code === 12) {
      scanResults.value = res.Data || []
      showScanDialog.value = true
    }
  } catch (e) {
    ElMessage.error(t('msg_scan_fail'))
  } finally {
    scanning.value = false
  }
}

async function handleLoadScanned(row) {
  try {
    const res = await loadModule(row.module_name, null, row.is_external)
    if (res.Code === 12) {
      ElMessage.success(t('msg_load_success'))
      showScanDialog.value = false
      await fetchModules()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_load_fail'))
    }
  } catch (e) {
    ElMessage.error(t('msg_load_fail'))
  }
}

async function handleInstall(force = false) {
  if (uploadFiles.value.length === 0) {
    ElMessage.warning(t('msg_select_file'))
    return
  }
  installing.value = true
  try {
    const res = await installModule(uploadFiles.value[0].raw, force)
    if (res.Code === 12) {
      ElMessage.success(res.Message?.Description || t('msg_install_success'))
      showInstallDialog.value = false
      uploadFiles.value = []
      await fetchModules()
    } else if (res.Data?.exists) {
      installing.value = false
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
    installing.value = false
  }
}

async function handleDelete(mod) {
  try {
    await ElMessageBox.confirm(
      t('msg_delete_content', { name: mod.display_name || mod.module_name }),
      t('msg_delete_title'),
      { type: 'warning' }
    )
    const res = mod.is_proxy
      ? await deleteProxyServer(mod._proxy_id)
      : await deleteModule(mod.module_name)
    if (res.Code === 12) {
      ElMessage.success(t('msg_delete_success'))
      await fetchModules()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_delete_fail'))
    }
  } catch (e) {
    // cancelled
  }
}

// ---- 分组逻辑 ----
async function fetchGroups() {
  try {
    const res = await getGroups()
    if (res.Code === 12) {
      const allGroups = res.Data || []
      defaultGroup.value = allGroups.find(g => g.is_default) || null
      groups.value = allGroups.filter(g => !g.is_default)
    }
  } catch {}
}

async function loadGroupMembers(groupId) {
  if (!groupId) {
    groupMemberModuleNames.value = new Set()
    groupMemberProxyIds.value = new Set()
    return
  }
  try {
    const res = await getGroupMembers(groupId)
    if (res.Code === 12 && res.Data) {
      groupMemberModuleNames.value = new Set((res.Data.modules || []).map(m => m.module_name))
      groupMemberProxyIds.value = new Set((res.Data.proxies || []).map(p => p.id))
    }
  } catch {}
}

watch(selectedGroupId, (val) => {
  loadGroupMembers(val)
})

function openCreateGroupDialog() {
  editingGroup.value = null
  groupForm.value = { name: '', description: '' }
  showGroupFormDialog.value = true
}

function openEditGroupDialog(group) {
  editingGroup.value = group
  groupForm.value = { name: group.name, description: group.description || '' }
  showGroupFormDialog.value = true
}

async function handleSaveGroup() {
  if (!groupForm.value.name.trim()) return
  try {
    let res
    if (editingGroup.value) {
      res = await updateGroup(editingGroup.value.id, groupForm.value)
    } else {
      res = await createGroup(groupForm.value.name, groupForm.value.description)
    }
    if (res.Code === 12) {
      ElMessage.success(editingGroup.value ? t('msg_update_group_success') : t('msg_create_group_success'))
      showGroupFormDialog.value = false
      await fetchGroups()
    } else {
      ElMessage.error(res.Message?.Description || (editingGroup.value ? t('msg_update_group_fail') : t('msg_create_group_fail')))
    }
  } catch {
    ElMessage.error(editingGroup.value ? t('msg_update_group_fail') : t('msg_create_group_fail'))
  }
}

async function handleDeleteGroup(group) {
  try {
    await ElMessageBox.confirm(
      t('msg_delete_group_confirm', { name: group.name }),
      t('msg_delete_group_title'),
      { type: 'warning' }
    )
    const res = await deleteGroupApi(group.id)
    if (res.Code === 12) {
      ElMessage.success(t('msg_delete_group_success'))
      if (selectedGroupId.value === group.id) selectedGroupId.value = null
      await fetchGroups()
    } else {
      ElMessage.error(res.Message?.Description || t('msg_delete_group_fail'))
    }
  } catch {}
}

// 分组右键菜单
function openGroupContextMenu(event, group) {
  groupContextMenu.value = { visible: true, x: event.clientX, y: event.clientY, group }
  // 点击任意位置关闭
  const close = () => {
    groupContextMenu.value.visible = false
    document.removeEventListener('click', close)
  }
  setTimeout(() => document.addEventListener('click', close), 0)
}

function copyGroupId(group) {
  const id = group ? String(group.id) : ''
  navigator.clipboard.writeText(id)
  ElMessage.success(t('msg_group_id_copied'))
}

// 卡片上的分组 popover：加载当前模块的分组状态
async function loadModuleGroupState(mod) {
  modGroupChecked.value = {}
  try {
    const moduleName = mod.is_proxy ? null : mod.module_name
    const serverId = mod.is_proxy ? mod._proxy_id : null
    // 获取此模块/代理所属的所有分组
    const endpoint = mod.is_proxy
      ? `/proxy/servers/${serverId}/groups`
      : `/modules/${moduleName}/groups`
    const res = await (await fetch(`/api${endpoint}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` }
    })).json()
    if (res.Code === 12) {
      const belongIds = new Set((res.Data || []).map(g => g.id))
      const checked = {}
      for (const g of groups.value) {
        checked[g.id] = belongIds.has(g.id)
      }
      modGroupChecked.value = checked
    }
  } catch {}
}

// 根据分组 id 生成固定颜色
const GROUP_COLORS = ['#409EFF','#67C23A','#E6A23C','#F56C6C','#9B59B6','#1ABC9C','#E67E22','#3498DB']
function groupColor(groupId) {
  // 用 id 字符串的 charCode 累加取模，稳定映射颜色
  let hash = 0
  for (let i = 0; i < groupId.length; i++) hash = (hash + groupId.charCodeAt(i)) % GROUP_COLORS.length
  return GROUP_COLORS[hash]
}

// 判断当前模块是否已属于至少一个分组（popover 打开后根据 modGroupChecked 判断）
function hasAnyGroup(mod) {
  return Object.values(modGroupChecked.value).some(v => v)
}

// 勾选/取消勾选某个分组
async function handleToggleModGroup(mod, groupId, checked) {
  try {
    let res
    if (mod.is_proxy) {
      res = checked
        ? await addProxyToGroup(groupId, mod._proxy_id)
        : await removeProxyFromGroup(groupId, mod._proxy_id)
    } else {
      res = checked
        ? await addModuleToGroup(groupId, mod.module_name)
        : await removeModuleFromGroup(groupId, mod.module_name)
    }
    if (res.Code === 12) {
      modGroupChecked.value = { ...modGroupChecked.value, [groupId]: checked }
      await fetchGroups()
      if (selectedGroupId.value) await loadGroupMembers(selectedGroupId.value)
    } else {
      ElMessage.error(res.Message?.Description || t('msg_op_fail'))
    }
  } catch {
    ElMessage.error(t('msg_op_fail'))
  }
}

onMounted(() => {
  fetchModules()
  fetchGroups()
})
</script>

<style scoped>
.modules-page {
  width: 100%;
}

/* ---- 页面标题 ---- */
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

.module-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 210, 255, 0.1);
  color: #00afc8;
  border: 1px solid rgba(0, 210, 255, 0.25);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  padding: 1px 10px;
  min-width: 28px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ---- 搜索框 ---- */
.search-box {
  margin-right: 4px;
}

.search-box :deep(.el-input__wrapper) {
  border-radius: 6px;
}

/* ---- 视图切换 ---- */
.view-toggle-group {
  display: flex;
  border: 1px solid var(--border-control);
  border-radius: 6px;
  overflow: hidden;
  margin-right: 4px;
}

.view-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--bg-card);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.view-btn:hover {
  background: var(--bg-body);
  color: #409eff;
}

.view-btn.active {
  background: #409eff;
  color: #fff;
}

/* ---- 分组筛选栏 ---- */
.group-filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.group-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.group-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 14px;
  border-radius: 16px;
  border: 1px solid var(--border-control);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  line-height: 1.4;
}

.group-tab:hover {
  border-color: #409EFF;
  color: #409EFF;
  background: rgba(64, 158, 255, 0.04);
}

.group-tab.active {
  background: #409EFF;
  color: #fff;
  border-color: #409EFF;
}

.group-tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  padding: 0 6px;
  min-width: 18px;
  height: 18px;
}

.group-tab.active .group-tab-count {
  background: rgba(255, 255, 255, 0.25);
}

.group-tab-add {
  padding: 5px 10px;
  border-style: dashed;
  color: var(--text-muted);
}

.group-tab-add:hover {
  border-color: #409EFF;
  color: #409EFF;
  border-style: solid;
}

/* ---- 分组右键菜单 ---- */
.group-context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  min-width: 140px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--text-regular);
  cursor: pointer;
  transition: background 0.15s;
}

.context-menu-item:hover {
  background: rgba(64, 158, 255, 0.08);
  color: #409EFF;
}

.context-menu-item.context-menu-danger:hover {
  background: rgba(245, 108, 108, 0.08);
  color: #F56C6C;
}

.context-menu-divider {
  height: 1px;
  background: var(--border-default);
  margin: 4px 0;
}

/* ---- 分组分配 Popover 面板 ---- */
.gap-panel {
  padding: 0;
  user-select: none;
}

.gap-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px 10px;
  overflow: hidden;
}

.gap-header-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.gap-header-name {
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.gap-divider {
  height: 1px;
  background: var(--border-divider);
  margin: 0;
}

.gap-list {
  padding: 6px 6px;
  max-height: 220px;
  overflow-y: auto;
}

.gap-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}

.gap-item:hover {
  background: rgba(64, 158, 255, 0.07);
}

.gap-item-checked {
  background: rgba(64, 158, 255, 0.1) !important;
}

.gap-item-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.gap-item-label {
  font-size: 13px;
  color: var(--text-regular);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gap-item-checked .gap-item-label {
  color: #409EFF;
  font-weight: 500;
}

.gap-item-check {
  color: #409EFF;
  flex-shrink: 0;
}

.gap-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 18px 14px;
  color: var(--text-muted);
  font-size: 12px;
}

.gap-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  font-size: 13px;
  color: #409EFF;
  cursor: pointer;
  transition: background 0.15s;
}

.gap-footer:hover {
  background: rgba(64, 158, 255, 0.07);
}

/* 已分组的按钮高亮 */
.btn-grouped {
  border-color: #409EFF !important;
  color: #409EFF !important;
}

/* ---- 统计卡片 ---- */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 22px;
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

/* ---- 状态指示点 ---- */
.status-dot-sm {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  display: inline-block;
}

.dot-online {
  background: #67C23A;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.6);
}

.dot-offline {
  background: #DCDFE6;
}

/* ---- 卡片视图 ---- */
.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  align-items: stretch;
}

.module-card {
  border-top: 3px solid #DCDFE6;
  border-left: none;
  transition: all 0.25s;
  border-radius: 10px !important;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.module-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.1) !important;
}

.module-card.module-loaded {
  border-top-color: #67C23A;
}

.module-card.module-external {
  border-top-color: #E6A23C;
}

.module-card.module-loaded.module-external {
  border-top-color: #E6A23C;
}

.module-card.module-proxy {
  border-top-color: #409EFF;
}

.module-card.module-proxy.module-loaded {
  border-top-color: #409EFF;
}

.module-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.module-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.module-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif;
  letter-spacing: 0.02em;
}

.module-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.module-path {
  font-size: 11px;
  color: var(--text-subtle);
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.module-version {
  font-size: 11px;
  color: #409EFF;
  font-weight: 500;
}

.module-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 10px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex-shrink: 0;
}

.module-tools-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  background: var(--bg-secondary);
  padding: 4px 10px;
  border-radius: 6px;
  width: fit-content;
  flex-shrink: 0;
}

.tools-enabled {
  color: #67C23A;
  font-weight: 500;
}

.module-spacer {
  flex-grow: 1;
}

.module-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  box-sizing: border-box;
}

.module-actions {
  display: flex;
  gap: 8px;
  border-top: 1px solid var(--border-divider);
  padding-top: 12px;
  margin-top: auto;
  flex-shrink: 0;
}

/* ---- 列表视图 ---- */
.modules-table-wrap {
  background: var(--bg-card);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-default);
}

.modules-table {
  width: 100%;
}

.list-name-cell {
  display: flex;
  align-items: center;
}

.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
  align-items: center;
}

.table-actions .el-button {
  margin: 0;
}

/* ---- 分组表单对话框 ---- */
.group-dlg-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 4px 0;
}

.group-dlg-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.group-dlg-icon.icon-create {
  background: rgba(64, 158, 255, 0.12);
  color: #409EFF;
}

.group-dlg-icon.icon-edit {
  background: rgba(103, 194, 58, 0.12);
  color: #67C23A;
}

.group-dlg-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.3;
}

.group-dlg-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 3px;
}

.group-dlg-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px 0 4px;
}

.group-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-field-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-regular);
}

.required-mark {
  color: #F56C6C;
  margin-left: 3px;
}

.group-dlg-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
}
</style>

<style>
/* 分组 Popover 圆角美化（全局，因为 popper 渲染在 body 下） */
.group-assign-popper.el-popover {
  border-radius: 12px !important;
  overflow: hidden !important;
  padding: 0 !important;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.13) !important;
  border: 1px solid var(--border-control, #e4e7ed) !important;
}
</style>
