<template>
  <div class="params-expand">
    <template v-if="hasParams">
      <table class="params-table">
        <thead>
          <tr>
            <th>{{ t('col_param_name') }}</th>
            <th>{{ t('col_param_type') }}</th>
            <th>{{ t('col_param_required') }}</th>
            <th>{{ t('col_description') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(param, paramName) in properties" :key="paramName">
            <td><code>{{ paramName }}</code></td>
            <td><span class="param-type">{{ getParamType(param) }}</span></td>
            <td>
              <el-tag v-if="required.includes(paramName)" type="danger" size="small">{{ t('tag_required') }}</el-tag>
              <span v-else class="param-optional">{{ t('tag_optional') }}</span>
            </td>
            <td class="param-desc">
              <!-- 主描述 -->
              <div v-if="param.description" class="desc-main">{{ param.description }}</div>
              <!-- 补充信息：默认值、枚举值、约束条件 -->
              <div v-else class="desc-extra">
                <span v-if="param.default !== undefined" class="extra-item">
                  <span class="extra-label">默认值:</span>
                  <code class="extra-value">{{ formatDefaultValue(param.default) }}</code>
                </span>
                <span v-else-if="param.enum" class="extra-item">
                  <span class="extra-label">可选值:</span>
                  <code class="extra-value">{{ param.enum.join(' | ') }}</code>
                </span>
                <span v-else-if="param.const !== undefined" class="extra-item">
                  <span class="extra-label">固定值:</span>
                  <code class="extra-value">{{ formatDefaultValue(param.const) }}</code>
                </span>
                <span v-else-if="hasConstraints(param)" class="extra-item">
                  <span class="extra-label">约束:</span>
                  <code class="extra-value">{{ formatConstraints(param) }}</code>
                </span>
                <span v-else class="extra-placeholder">-</span>
              </div>
              <!-- 嵌套属性展示 -->
              <div v-if="param.properties || param.items?.properties" class="nested-props">
                <div v-for="(nested, nestedName) in (param.properties || param.items?.properties || {})" :key="nestedName" class="nested-item">
                  <code class="nested-name">{{ nestedName }}</code>
                  <span class="nested-type">({{ getParamType(nested) }})</span>
                  <span v-if="nested.description" class="nested-desc">{{ nested.description }}</span>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </template>
    <span v-else class="params-empty">{{ t('text_no_params') }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '../i18n.js'

const { t } = useI18n()

const props = defineProps({
  // 接受 { properties: {}, required: [] } 格式的 schema 对象
  schema: {
    type: Object,
    default: () => ({})
  }
})

const properties = computed(() => props.schema?.properties || {})
const required = computed(() => props.schema?.required || [])
const hasParams = computed(() => Object.keys(properties.value).length > 0)

function getParamType(param) {
  if (param.type) {
    if (param.type === 'array' && param.items?.type) {
      return `${param.type}<${param.items.type}>`
    }
    return param.type
  }
  if (param.anyOf) return param.anyOf.map(t => t.type).filter(Boolean).join(' | ')
  if (param.oneOf) return param.oneOf.map(t => t.type).filter(Boolean).join(' | ')
  if (param.allOf) return 'object'
  if (param.const !== undefined) return 'const'
  return 'any'
}

function formatDefaultValue(val) {
  if (val === null) return 'null'
  if (typeof val === 'string') return `"${val}"`
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

function hasConstraints(param) {
  return param.minLength !== undefined ||
         param.maxLength !== undefined ||
         param.minimum !== undefined ||
         param.maximum !== undefined ||
         param.pattern !== undefined ||
         param.minItems !== undefined ||
         param.maxItems !== undefined
}

function formatConstraints(param) {
  const parts = []
  if (param.minLength !== undefined) parts.push(`minLength=${param.minLength}`)
  if (param.maxLength !== undefined) parts.push(`maxLength=${param.maxLength}`)
  if (param.minimum !== undefined) parts.push(`min=${param.minimum}`)
  if (param.maximum !== undefined) parts.push(`max=${param.maximum}`)
  if (param.pattern !== undefined) parts.push(`pattern=${param.pattern}`)
  if (param.minItems !== undefined) parts.push(`minItems=${param.minItems}`)
  if (param.maxItems !== undefined) parts.push(`maxItems=${param.maxItems}`)
  return parts.join(', ')
}
</script>

<style scoped>
.params-expand {
  padding: 10px 16px 10px 48px;
  background: var(--bg-secondary, #f8f9fa);
}

.params-empty {
  font-size: 12px;
  color: var(--text-muted);
}

.params-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.params-table th {
  text-align: left;
  padding: 4px 10px;
  color: var(--text-muted);
  font-weight: 500;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}

.params-table td {
  padding: 5px 10px;
  vertical-align: top;
  border-bottom: 1px solid var(--border-lighter, #f0f0f0);
  color: var(--text-secondary);
}

.params-table tr:last-child td {
  border-bottom: none;
}

.params-table code {
  font-size: 12px;
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  color: var(--text-regular);
}

.param-type {
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  font-size: 11px;
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
  padding: 1px 5px;
  border-radius: 3px;
}

.param-optional {
  font-size: 11px;
  color: var(--text-muted);
}

.param-desc {
  color: var(--text-secondary);
  line-height: 1.5;
}

.desc-main {
  margin-bottom: 4px;
}

.desc-extra {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.extra-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.extra-label {
  color: var(--text-muted);
}

.extra-value {
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  font-size: 11px;
  background: rgba(64, 158, 255, 0.08);
  padding: 1px 4px;
  border-radius: 3px;
  color: #409EFF;
}

.extra-placeholder {
  color: var(--text-muted);
}

.nested-props {
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
  border-left: 2px solid #e4e7ed;
}

.nested-item {
  font-size: 11px;
  margin-bottom: 3px;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.nested-item:last-child {
  margin-bottom: 0;
}

.nested-name {
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  font-size: 11px;
  color: #606266;
}

.nested-type {
  color: #909399;
  font-size: 10px;
}

.nested-desc {
  color: #909399;
  font-size: 11px;
}
</style>
