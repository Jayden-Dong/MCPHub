<template>
  <el-table :data="tools" stripe>
    <!-- 展开入参 -->
    <el-table-column type="expand" width="36">
      <template #default="{ row }">
        <ToolParamsExpand :schema="getSchema(row)" />
      </template>
    </el-table-column>

    <!-- 工具启用开关 -->
    <el-table-column :label="t('col_status')" width="80">
      <template #default="{ row }">
        <el-switch
          :model-value="row.enabled"
          :active-value="1"
          :inactive-value="0"
          size="small"
          :disabled="disableSwitch"
          @change="(val) => emit('toggle-tool', row, val === 1)"
        />
      </template>
    </el-table-column>

    <!-- 主名称列 -->
    <el-table-column :label="primaryLabel" :width="primaryWidth">
      <template #default="{ row }">
        <div class="tool-name">
          <el-icon :color="row.enabled ? '#67C23A' : '#C0C4CC'"><Tools /></el-icon>
          <code>{{ getPrimaryName(row) }}</code>
        </div>
      </template>
    </el-table-column>

    <!-- 次要名称列 -->
    <el-table-column v-if="!hideSecondary" :label="secondaryLabel" :width="secondaryWidth">
      <template #default="{ row }">
        <code class="secondary-name">{{ getSecondaryName(row) }}</code>
      </template>
    </el-table-column>

    <!-- 描述 -->
    <el-table-column :label="t('col_description')">
      <template #default="{ row }">
        <div class="tool-desc">
          <span class="desc-badge" v-if="row.custom_desc" :title="t('tip_custom_desc')">★</span>
          <template v-if="displayDesc(row).length <= 80">
            {{ displayDesc(row) }}
          </template>
          <template v-else-if="expandedTools.has(getRowKey(row))">
            <span>{{ displayDesc(row) }}</span>
            <span class="desc-toggle" @click="expandedTools.delete(getRowKey(row))"> {{ t('text_collapse') }}</span>
          </template>
          <template v-else>
            <span>{{ displayDesc(row).substring(0, 80) }}...</span>
            <span class="desc-toggle" @click="expandedTools.add(getRowKey(row))"> {{ t('text_expand') }}</span>
          </template>
          <span v-if="showEditDesc" class="desc-edit-btn" @click="emit('edit-desc', row)">{{ t('btn_edit_desc') }}</span>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { reactive } from 'vue'
import { useI18n } from '../i18n.js'
import ToolParamsExpand from './ToolParamsExpand.vue'

const props = defineProps({
  tools: { type: Array, default: () => [] },
  primaryLabel: { type: String, required: true },
  secondaryLabel: { type: String, default: '' },
  primaryWidth: { type: [String, Number], default: 240 },
  secondaryWidth: { type: [String, Number], default: 200 },
  primaryField: { type: String, required: true },
  secondaryField: { type: String, default: '' },
  schemaField: { type: String, default: 'parameters' },
  rowKeyField: { type: String, default: 'name' },
  disableSwitch: { type: Boolean, default: false },
  showEditDesc: { type: Boolean, default: true },
  hideSecondary: { type: Boolean, default: false }
})

const emit = defineEmits(['toggle-tool', 'edit-desc'])

const { t } = useI18n()
const expandedTools = reactive(new Set())

function getPrimaryName(row) {
  return row[props.primaryField] || ''
}

function getSecondaryName(row) {
  return row[props.secondaryField] || ''
}

function getSchema(row) {
  return row[props.schemaField] || {}
}

function getRowKey(row) {
  return row[props.rowKeyField]
}

function displayDesc(row) {
  return (row.custom_desc || row.description || '').replace(/\n/g, ' ')
}
</script>

<style scoped>
.tool-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tool-name code {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
  color: var(--text-regular, var(--el-text-color-primary));
}

.secondary-name {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
  color: var(--text-muted, var(--el-text-color-secondary));
}

.tool-desc {
  display: flex;
  align-items: baseline;
  gap: 4px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--text-secondary, var(--el-text-color-regular));
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.desc-badge {
  color: var(--el-color-warning);
  font-size: 12px;
}

.desc-toggle {
  color: #409EFF;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  user-select: none;
}

.desc-toggle:hover {
  color: #337ecc;
}

.desc-edit-btn {
  color: #909399;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  user-select: none;
  margin-left: 6px;
  opacity: 0;
  transition: opacity 0.15s;
}

.tool-desc:hover .desc-edit-btn {
  opacity: 1;
}

.desc-edit-btn:hover {
  color: #409EFF;
}
</style>