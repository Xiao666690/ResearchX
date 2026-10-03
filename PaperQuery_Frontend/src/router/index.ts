import { createRouter, createWebHistory } from 'vue-router'
import progress from '@bassist/progress'
import routes from './routes'

// 配置进度条
progress.configure({ showSpinner: false })
progress.setColor('var(--c-brand)')

// 创建路由器实例
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: (_to, _from, savedPosition) => {
    return savedPosition ? savedPosition : { top: 0, left: 0 }
  },
})

// 导航守卫
router.beforeEach((to, _from, next) => {
  progress.start()

  // 从本地存储中获取用户登录状态
  const username = localStorage.getItem('username')

  const loggedIn = localStorage.getItem('token') && username
  
  // 检测用户是否登录 如果未登录则跳转到登录页面
  if (to.matched.some((record) => record.meta.requiresAuth) && !loggedIn) {
    console.log('未登录')
    next('/login')
    return
  }

  // 仅 admin 可访问的路由（如团队管理），普通用户跳回首页
  if (to.matched.some((record) => record.meta.role === 'admin')) {
    const role = localStorage.getItem('role')
    if (role !== 'admin') {
      next('/home/dashboard')
      return
    }
  }

  next()
})

router.afterEach(() => {
  // const { title } = to.meta
  document.title = `PaperAgent · Academic Research Workspace`
  progress.done()
})

export default router
