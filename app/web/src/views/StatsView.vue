<template>
  <div class="stats-page">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">{{ t('page_title_stats') }}</h2>
        <el-select v-model="timeRange" size="small" style="width: 120px; margin-left: 16px;" @change="fetchAllStats">
          <el-option :label="t('time_1h')" :value="1" />
          <el-option :label="t('time_24h')" :value="24" />
          <el-option :label="t('time_7d')" :value="168" />
        </el-select>
      </div>
      <div class="header-actions">
        <el-button @click="fetchAllStats" :loading="loading">
          <el-icon><Refresh /></el-icon> {{ t('btn_refresh') }}
        </el-button>
      </div>
    </div>

    <!-- 概览统计卡片 -->
    <el-row :gutter="16" class="overview-cards">
      <el-col :span="4">
        <div class="stat-card stat-card--primary">
          <div class="stat-value">{{ overview.total_calls || 0 }}</div>
          <div class="stat-label">{{ t('stat_total_calls') }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card stat-card--success">
          <div class="stat-value">{{ overview.today_calls || 0 }}</div>
          <div class="stat-label">{{ t('stat_today_calls') }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card stat-card--info">
          <div class="stat-value">{{ overview.success_rate || 0 }}%</div>
          <div class="stat-label">{{ t('stat_success_rate') }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card stat-card--warning">
          <div class="stat-value">{{ overview.avg_duration_ms || 0 }} ms</div>
          <div class="stat-label">{{ t('stat_avg_duration') }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card stat-card--purple">
          <div class="stat-value">{{ overview.active_tools || 0 }}</div>
          <div class="stat-label">{{ t('stat_active_tools') }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card stat-card--cyan">
          <div class="stat-value">{{ overview.active_modules || 0 }}</div>
          <div class="stat-label">{{ t('stat_active_modules') }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 24小时趋势图 -->
    <el-card shadow="never" class="chart-card">
      <template #header>
        <span class="card-title">{{ t('chart_hourly_trend') }}</span>
      </template>
      <div class="hourly-chart" v-if="overview.hourly_stats && overview.hourly_stats.length > 0">
        <div class="chart-bar" v-for="(item, idx) in overview.hourly_stats" :key="idx">
          <div class="bar-fill" :style="{ height: getBarHeight(item.count) + '%' }"></div>
          <span class="bar-label">{{ item.hour }}</span>
          <span class="bar-value">{{ item.count }}</span>
        </div>
      </div>
      <el-empty v-else :description="t('no_data')" :image-size="60" />
    </el-card>

    <el-row :gutter="20" class="rankings-row">
      <!-- 模块排行榜 -->
      <el-col :span="12">
        <el-card shadow="never" class="rank-card">
          <template #header>
            <div class="rank-header">
              <span class="card-title">{{ t('rank_modules') }}</span>
              <el-tag size="small" type="info">{{ moduleStats.length }} {{ t('units_items') }}</el-tag>
            </div>
          </template>
          <el-table :data="moduleStats" style="width: 100%" max-height="400" v-if="moduleStats.length > 0">
            <el-table-column type="index" width="50" :label="t('col_rank')" />
            <el-table-column prop="module_name" :label="t('col_module_name')" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="module-name">{{ formatModuleName(row.module_name) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="call_count" :label="t('col_calls')" width="90" sortable>
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.call_count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('col_success_rate')" width="100">
              <template #default="{ row }">
                <span :class="getSuccessRateClass(row)">{{ getSuccessRate(row) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="avg_duration_ms" :label="t('col_avg_time')" width="100">
              <template #default="{ row }">
                {{ row.avg_duration_ms ? row.avg_duration_ms.toFixed(1) : 0 }} ms
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else :description="t('no_call_data')" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 工具排行榜 -->
      <el-col :span="12">
        <el-card shadow="never" class="rank-card">
          <template #header>
            <div class="rank-header">
              <span class="card-title">{{ t('rank_tools') }}</span>
              <el-tag size="small" type="info">{{ toolStats.length }} {{ t('units_items') }}</el-tag>
            </div>
          </template>
          <el-table :data="toolStats" style="width: 100%" max-height="400" v-if="toolStats.length > 0">
            <el-table-column type="index" width="50" :label="t('col_rank')" />
            <el-table-column prop="tool_name" :label="t('col_tool_name')" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="tool-name">{{ formatToolName(row.tool_name) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="call_count" :label="t('col_calls')" width="90" sortable>
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.call_count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('col_success_rate')" width="100">
              <template #default="{ row }">
                <span :class="getSuccessRateClass(row)">{{ getSuccessRate(row) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="avg_duration_ms" :label="t('col_avg_time')" width="100">
              <template #default="{ row }">
                {{ row.avg_duration_ms ? row.avg_duration_ms.toFixed(1) : 0 }} ms
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else :description="t('no_call_data')" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近调用记录 -->
    <el-card shadow="never" class="recent-card">
      <template #header>
        <div class="rank-header">
          <span class="card-title">{{ t('recent_calls') }}</span>
          <el-tag size="small" type="info">{{ recentCalls.length }} {{ t('units_records') }}</el-tag>
        </div>
      </template>
      <el-table :data="recentCalls" style="width: 100%" max-height="300" v-if="recentCalls.length > 0">
        <el-table-column prop="timestamp_str" :label="t('col_time')" width="180" />
        <el-table-column prop="tool_name" :label="t('col_tool_name')" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="tool-name">{{ formatToolName(row.tool_name) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="module_name" :label="t('col_module_name')" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="module-name">{{ formatModuleName(row.module_name) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('col_status')" width="80">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" size="small">
              {{ row.success ? t('status_success') : t('status_fail') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" :label="t('col_duration')" width="100">
          <template #default="{ row }">
            {{ row.duration_ms ? row.duration_ms.toFixed(1) : 0 }} ms
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :description="t('no_call_data')" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getStatsOverview, getStatsModules, getStatsTools, getStatsRecent } from '../api/index.js'
import { useI18n } from '../i18n.js'

const { t } = useI18n()

const loading = ref(false)
const timeRange = ref(24)
const overview = ref({})
const moduleStats = ref([])
const toolStats = ref([])
const recentCalls = ref([])

let refreshTimer = null

async function fetchAllStats() {
  loading.value = true
  try {
    const [overviewRes, modulesRes, toolsRes, recentRes] = await Promise.all([
      getStatsOverview(timeRange.value),
      getStatsModules(timeRange.value),
      getStatsTools(timeRange.value),
      getStatsRecent()
    ])

    if (overviewRes.Code === 12) overview.value = overviewRes.Data || {}
    if (modulesRes.Code === 12) moduleStats.value = modulesRes.Data || []
    if (toolsRes.Code === 12) toolStats.value = toolsRes.Data || []
    if (recentRes.Code === 12) recentCalls.value = recentRes.Data || []
  } catch (e) {
    console.error('Failed to fetch stats:', e)
  } finally {
    loading.value = false
  }
}

function formatModuleName(name) {
  if (!name) return '-'
  // 截取最后一段作为显示名称
  const parts = name.split('.')
  return parts[parts.length - 1] || name
}

function formatToolName(name) {
  if (!name) return '-'
  // 去除前缀
  const prefix = 'mcp_'
  if (name.startsWith(prefix)) {
    return name.substring(prefix.length)
  }
  return name
}

function getSuccessRate(row) {
  if (!row.call_count || row.call_count === 0) return 0
  return ((row.success_count || 0) / row.call_count * 100).toFixed(1)
}

function getSuccessRateClass(row) {
  const rate = parseFloat(getSuccessRate(row))
  if (rate >= 95) return 'rate-success'
  if (rate >= 80) return 'rate-warning'
  return 'rate-danger'
}

function getBarHeight(count) {
  if (!overview.value.hourly_stats) return 0
  const maxCount = Math.max(...overview.value.hourly_stats.map(h => h.count), 1)
  return (count / maxCount) * 100
}

onMounted(() => {
  fetchAllStats()
  // 每30秒自动刷新
  refreshTimer = setInterval(fetchAllStats, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.stats-page {
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

/* 概览统计卡片 */
.overview-cards {
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-default);
  transition: transform 0.2s, box-shadow 0.2s, background-color 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}

.stat-card--primary .stat-value { color: #409EFF; }
.stat-card--success .stat-value { color: #67C23A; }
.stat-card--info .stat-value { color: #909399; }
.stat-card--warning .stat-value { color: #E6A23C; }
.stat-card--purple .stat-value { color: #9b59b6; }
.stat-card--cyan .stat-value { color: #00afc8; }

/* 图表卡片 */
.chart-card {
  margin-bottom: 20px;
  border-radius: 10px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.hourly-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 180px;
  padding: 10px 0;
  padding-bottom: 25px;
}

.chart-bar {
  flex: 1;
  height: 100%;
  position: relative;
}

.bar-fill {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  background: linear-gradient(180deg, #409EFF 0%, #a0cfff 100%);
  border-radius: 3px 3px 0 0;
  min-height: 2px;
  transition: height 0.3s;
}

.bar-label {
  position: absolute;
  bottom: -20px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
}

.bar-value {
  position: absolute;
  top: -18px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 10px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* 排行卡片 */
.rankings-row {
  margin-bottom: 20px;
}

.rank-card {
  border-radius: 10px;
  height: 100%;
}

.rank-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.module-name, .tool-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}

.rate-success { color: #67C23A; font-weight: 500; }
.rate-warning { color: #E6A23C; font-weight: 500; }
.rate-danger { color: #F56C6C; font-weight: 500; }

/* 最近调用卡片 */
.recent-card {
  border-radius: 10px;
}
</style>