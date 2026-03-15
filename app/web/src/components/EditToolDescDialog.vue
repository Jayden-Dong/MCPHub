<template>
  <el-dialog
    :model-value="visible"
    :title="t('dlg_edit_desc_title')"
    width="640px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:visible', $event)"
  >
    <div class="edit-desc-content">
      <div class="tool-info-bar">
        <el-icon class="tool-info-bar-icon"><Tools /></el-icon>
        <code class="tool-info-bar-name">{{ toolName }}</code>
        <span class="tool-info-bar-label">{{ t('label_tool_name') }}</span>
      </div>
      <div class="desc-edit-section">
        <div class="desc-edit-header">
          <span>{{ t('label_description') }}</span>
          <span class="desc-char-count">{{ modelValue?.length || 0 }} {{ t('char_count') }}</span>
        </div>
        <el-input
          :model-value="modelValue"
          type="textarea"
          :rows="6"
          resize="vertical"
          :placeholder="t('placeholder_desc')"
          @update:model-value="emit('update:modelValue', $event)"
        />
      </div>
    </div>
    <template #footer>
      <el-button @click="emit('update:visible', false)">{{ t('btn_cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="emit('save')">
        {{ t('btn_save_desc') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { Tools } from '@element-plus/icons-vue'
import { useI18n } from '../i18n.js'

const { t } = useI18n()

defineProps({
  visible: Boolean,
  toolName: String,
  modelValue: String,
  saving: Boolean,
})

const emit = defineEmits(['update:visible', 'update:modelValue', 'save'])
</script>

<style scoped>
.edit-desc-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tool-info-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0 10px;
  border-bottom: 1px solid var(--border-light);
}

.tool-info-bar-icon {
  color: var(--border-control);
  flex-shrink: 0;
}

.tool-info-bar-name {
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  color: var(--text-secondary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-info-bar-label {
  font-size: 12px;
  color: var(--border-control);
  flex-shrink: 0;
}

.desc-edit-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.desc-edit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.desc-char-count {
  font-size: 12px;
  color: var(--border-control);
}
</style>
