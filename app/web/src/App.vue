<template>
  <el-container class="app-container">
    <!-- 登录页面不显示 header -->
    <el-header v-if="!isLoginPage" class="app-header">
      <div class="header-left header-logo-link" @click="router.push('/modules')" title="返回模块管理">
        <div class="logo-icon">
          <el-icon :size="22" :color="isDark ? '#00d2ff' : '#409EFF'"><Connection /></el-icon>
        </div>
        <h1 class="app-title">MCP <span class="title-accent">HUB</span></h1>
      </div>
      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        :ellipsis="false"
        router
        class="header-menu"
      >
        <el-menu-item index="/modules">
          <el-icon><Box /></el-icon>
          <span>{{ t('nav_modules') }}</span>
        </el-menu-item>
        <el-menu-item index="/codegen">
          <el-icon><ChatDotRound /></el-icon>
          <span>{{ t('nav_codegen') }}</span>
        </el-menu-item>
        <el-menu-item index="/proxy">
          <el-icon><Share /></el-icon>
          <span>{{ t('nav_proxy') }}</span>
        </el-menu-item>
        <el-menu-item index="/stats">
          <el-icon><DataLine /></el-icon>
          <span>{{ t('nav_stats') }}</span>
        </el-menu-item>
      </el-menu>
      <div class="header-right">
        <!-- 状态指示器 -->
        <div class="status-indicator" :title="isConnected ? t('status_running') : t('status_disconnected')">
          <span :class="isConnected ? 'status-dot-pulse' : 'status-dot-offline'"></span>
        </div>

        <!-- 分隔线 -->
        <div class="header-divider"></div>

        <!-- 工具按钮组 -->
        <div class="header-btn-group">
          <button class="header-lang-btn" @click="toggleLocale" :title="locale === 'en' ? '切换中文' : 'Switch to English'">
            <span class="lang-label">{{ langLabel }}</span>
          </button>
          <button class="header-icon-btn" @click="toggleTheme" :title="isDark ? t('theme_light') : t('theme_dark')">
            <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>
        </div>

        <!-- 分隔线 -->
        <div class="header-divider"></div>

        <!-- 用户菜单 -->
        <el-dropdown trigger="click" @command="handleUserCommand">
          <div class="user-info">
            <el-icon :size="16"><User /></el-icon>
            <span class="username">{{ currentUser?.username || 'User' }}</span>
            <el-icon class="dropdown-arrow" :size="12"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">
                <el-icon><Key /></el-icon>
                {{ t('user_menu_change_password') }}
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>
                {{ t('user_menu_logout') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-main class="app-main" :class="{ 'login-main': isLoginPage }">
      <router-view />
    </el-main>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" :title="t('dlg_change_password_title')" width="500px">
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="auto">
        <el-form-item :label="t('label_old_password')" prop="oldPassword">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password :placeholder="t('placeholder_old_password')" />
        </el-form-item>
        <el-form-item :label="t('label_new_password')" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" show-password :placeholder="t('placeholder_new_password')" />
        </el-form-item>
        <el-form-item :label="t('label_confirm_password')" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password :placeholder="t('placeholder_confirm_password')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">{{ t('btn_cancel') }}</el-button>
        <el-button type="primary" @click="handleChangePassword">{{ t('btn_save_desc') }}</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Key, SwitchButton, ArrowDown } from '@element-plus/icons-vue'
import axios from 'axios'
import { useI18n } from './i18n.js'
import { changePassword } from './api/auth.js'

const { t, locale, toggleLocale } = useI18n()

// 当前语言标签
const langLabel = computed(() => locale.value === 'en' ? 'EN' : '中')

const route = useRoute()
const router = useRouter()
const isLoginPage = computed(() => route.path === '/login')
const activeMenu = computed(() => {
  if (route.path.startsWith('/codegen')) return '/codegen'
  if (route.path.startsWith('/proxy')) return '/proxy'
  if (route.path.startsWith('/stats')) return '/stats'
  return '/modules'
})

const isConnected = ref(true)
let heartbeatTimer = null

async function checkConnection() {
  try {
    await axios.get('/api/ping', { timeout: 5000 })
    isConnected.value = true
  } catch {
    isConnected.value = false
  }
}

// 主题管理
const isDark = ref(localStorage.getItem('theme') === 'dark')

function applyTheme(dark) {
  if (dark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  applyTheme(isDark.value)
}

// 用户管理
const currentUser = ref(null)

function loadUser() {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      currentUser.value = JSON.parse(userStr)
    }
  } catch {
    currentUser.value = null
  }
}

function handleUserCommand(command) {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'password') {
    passwordDialogVisible.value = true
  }
}

function handleLogout() {
  ElMessageBox.confirm(t('user_menu_logout') + '?', 'Confirm', {
    type: 'warning'
  }).then(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
  }).catch(() => {})
}

// 修改密码
const passwordDialogVisible = ref(false)
const passwordFormRef = ref(null)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.value.newPassword) {
    callback(new Error(t('msg_password_mismatch')))
  } else {
    callback()
  }
}

const passwordRules = {
  oldPassword: [{ required: true, message: t('login_password_required'), trigger: 'blur' }],
  newPassword: [{ required: true, message: t('login_password_required'), trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: t('login_password_required'), trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function handleChangePassword() {
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    await changePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword)
    ElMessage.success(t('msg_password_changed'))
    passwordDialogVisible.value = false
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  } catch (error) {
    const detail = error.response?.data?.Message?.Description || t('msg_password_change_failed')
    ElMessage.error(detail)
  }
}

onMounted(() => {
  applyTheme(isDark.value)
  loadUser()
  checkConnection()
  heartbeatTimer = setInterval(checkConnection, 5000)
})

onUnmounted(() => {
  if (heartbeatTimer) clearInterval(heartbeatTimer)
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--bg-body);
  transition: background-color 0.3s ease;
}

:root {
  --el-font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

code, pre, .el-input__inner[readonly], kbd {
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  background: var(--header-bg);
  box-shadow: var(--header-shadow);
  padding: 0 24px;
  height: 60px !important;
  z-index: 100;
  position: relative;
  transition: background 0.3s ease, box-shadow 0.3s ease;
}

.app-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--header-border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-right: 40px;
  flex-shrink: 0;
}

.header-logo-link {
  cursor: pointer;
  border-radius: 8px;
  padding: 4px 8px;
  margin-left: -8px;
  transition: background 0.2s;
}

.header-logo-link:hover {
  background: var(--header-menu-hover-bg);
}

.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--logo-bg);
  border: 1px solid var(--logo-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s ease, border-color 0.3s ease;
}

.app-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--header-text);
  white-space: nowrap;
  letter-spacing: 1px;
}

.title-accent {
  color: var(--accent-color);
  text-shadow: var(--accent-shadow);
}

.header-menu {
  border-bottom: none !important;
  background: transparent !important;
  flex: 1;
}

.header-menu .el-menu-item {
  color: var(--header-menu-text) !important;
  background: transparent !important;
  border-bottom: 2px solid transparent !important;
  font-size: 14px;
  transition: all 0.2s;
  height: 60px;
  line-height: 60px;
}

.header-menu .el-menu-item:hover {
  color: var(--header-menu-hover) !important;
  background: var(--header-menu-hover-bg) !important;
}

.header-menu .el-menu-item.is-active {
  color: var(--accent-color) !important;
  border-bottom-color: var(--accent-color) !important;
  background: var(--header-menu-active-bg) !important;
}

.header-menu .el-menu-item .el-icon {
  margin-right: 6px;
}

.header-right {
  flex-shrink: 0;
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-divider {
  width: 1px;
  height: 20px;
  background: var(--header-btn-border);
  opacity: 0.5;
}

.header-btn-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.header-lang-btn {
  min-width: 36px;
  height: 32px;
  padding: 0 10px;
  background: var(--header-btn-bg);
  border: 1px solid var(--header-btn-border);
  color: var(--header-btn-text);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header-lang-btn .lang-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.header-lang-btn:hover {
  background: var(--header-btn-hover-bg);
  border-color: var(--accent-color);
  color: var(--accent-color);
  transform: translateY(-1px);
}

.header-icon-btn {
  width: 32px;
  height: 32px;
  background: var(--header-btn-bg);
  border: 1px solid var(--header-btn-border);
  color: var(--header-btn-text);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  flex-shrink: 0;
}

.header-icon-btn svg {
  width: 16px;
  height: 16px;
}

.header-icon-btn:hover {
  background: var(--header-btn-hover-bg);
  border-color: var(--accent-color);
  color: var(--accent-color);
  transform: translateY(-1px);
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--header-btn-bg);
  border: 1px solid var(--header-btn-border);
  border-radius: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--header-btn-text);
  background: var(--header-btn-bg);
  border: 1px solid var(--header-btn-border);
}

.user-info:hover {
  background: var(--header-btn-hover-bg);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.user-info .username {
  font-size: 13px;
  font-weight: 500;
}

.user-info .dropdown-arrow {
  margin-left: 2px;
  opacity: 0.6;
  transition: transform 0.2s;
}

.user-info:hover .dropdown-arrow {
  opacity: 1;
}

.status-dot-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67C23A;
  box-shadow: 0 0 8px #67C23A;
  animation: dot-pulse 2s ease-in-out infinite;
}

.status-dot-offline {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #F56C6C;
  box-shadow: 0 0 8px #F56C6C;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px #67C23A; }
  50% { opacity: 0.6; box-shadow: 0 0 14px #67C23A; }
}

.app-main {
  padding: 20px 24px;
  min-height: calc(100vh - 60px);
}

.app-main.login-main {
  padding: 0;
  min-height: 100vh;
}
</style>
