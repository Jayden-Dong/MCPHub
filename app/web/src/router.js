import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('./views/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    redirect: '/modules'
  },
  {
    path: '/modules',
    name: 'Modules',
    component: () => import('./views/ModulesView.vue')
  },
  {
    path: '/modules/:moduleName',
    name: 'ModuleDetail',
    component: () => import('./views/ModuleDetailView.vue'),
    props: true
  },
  {
    path: '/codegen',
    name: 'CodeGen',
    component: () => import('./views/CodeGenView.vue')
  },
  {
    path: '/proxy',
    name: 'Proxy',
    component: () => import('./views/ProxyView.vue')
  },
  {
    path: '/proxy/:serverId',
    name: 'ProxyDetail',
    component: () => import('./views/ProxyDetailView.vue'),
    props: true
  },
  {
    path: '/stats',
    name: 'Stats',
    component: () => import('./views/StatsView.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 鉴权配置状态
let authEnabled = null  // null 表示还未获取配置
let authConfigLoaded = false

// 获取鉴权配置
async function fetchAuthConfig() {
  try {
    const res = await fetch('/api/auth/config')
    const data = await res.json()
    authEnabled = data.enabled
  } catch {
    authEnabled = true // 默认需要登录
  }
  authConfigLoaded = true
}

// 路由守卫：根据配置决定是否需要登录
router.beforeEach(async (to, from, next) => {
  // 首次访问时获取鉴权配置
  if (!authConfigLoaded) {
    await fetchAuthConfig()
  }

  // 公开页面（如登录页）不需要验证
  if (to.meta.public) {
    const token = localStorage.getItem('token')
    // 已登录且启用鉴权时，访问登录页重定向到首页
    if (token && to.path === '/login' && authEnabled) {
      next('/')
    } else {
      next()
    }
    return
  }

  // 不需要鉴权时直接放行
  if (!authEnabled) {
    next()
    return
  }

  // 需要登录的页面
  const token = localStorage.getItem('token')
  if (!token) {
    next('/login')
  } else {
    next()
  }
})

// 导出获取鉴权状态的方法
export function isAuthEnabled() {
  return authEnabled
}

export default router