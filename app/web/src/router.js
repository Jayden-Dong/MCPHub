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

// 路由守卫：未登录跳转到登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  // 公开页面（如登录页）不需要验证
  if (to.meta.public) {
    // 已登录用户访问登录页，重定向到首页
    if (token && to.path === '/login') {
      next('/')
    } else {
      next()
    }
    return
  }

  // 需要登录的页面
  if (!token) {
    next('/login')
  } else {
    next()
  }
})

export default router
