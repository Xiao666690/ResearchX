<template>
  <nav class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-topbar">
      <router-link to="/home/dashboard" class="brand">
        <span class="brand-mark"><img :src="paperAgentMark" alt="" /></span>
        <span class="brand-copy"><strong>PaperAgent</strong></span>
      </router-link>
      <button
        type="button"
        class="collapse-toggle"
        :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
        @click="emit('toggleCollapse')"
      >
        <Menu :size="18" />
      </button>
    </div>

    <div class="nav-label">WORKSPACE</div>
    <div class="nav-list">
      <router-link
        v-for="item in sidebarItems"
        :key="item.title"
        :to="item.link"
        class="nav-item"
        :class="{ active: isActive(item.link) }"
      >
        <component :is="item.icon" :size="19" />
        <span>{{ item.title }}</span>
        <i v-if="isActive(item.link)" />
      </router-link>
    </div>

    <div class="sidebar-footer">
      <div class="status-orb"><CircleCheck :size="17" /></div>
      <div><strong>服务正常</strong></div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { getSidebarItems } from './utils/sidebar'
import { CircleCheck, Menu } from 'lucide-vue-next'
import paperAgentMark from '@/assets/img/paperagent-mark.png'
import axios from 'axios'

defineProps({
  isCollapsed: Boolean,
})

const emit = defineEmits<{ (e: 'toggleCollapse'): void }>()

const route = useRoute()
const isActive = (link: string) => {
  if (link.includes('/library')) {
    return ['/library', '/knowledge/', '/pdfInfo/'].some((part) => route.path.includes(part))
  }
  if (link.includes('/forum')) return route.path.includes('/forum')
  return route.path.toLowerCase().startsWith(link.toLowerCase())
}

// 按角色动态渲染侧边栏：仅 admin 显示「管理团队」
const role = ref(localStorage.getItem('role') || '')
const sidebarItems = ref(getSidebarItems(role.value))

// 老会话（功能上线前已登录）localStorage 中无 role，登录后拉取一次 /user/me 补齐
onMounted(async () => {
  if (role.value) return
  const token = localStorage.getItem('token')
  if (!token) return
  try {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'
    const { data } = await axios.get(`${base}/user/me`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 10000,
    })
    if (data?.data?.role) {
      role.value = data.data.role
      localStorage.setItem('role', data.data.role)
      if (data.data.workspace_lid) localStorage.setItem('workspaceLid', data.data.workspace_lid)
      sidebarItems.value = getSidebarItems(role.value)
    }
  } catch {
    // 拉取失败不阻塞界面，仍按无角色渲染（行为与改造前一致）
  }
})
</script>

<style scoped>
.app-sidebar { position: sticky; top: 0; z-index: 20; display: flex; flex: 0 0 224px; flex-direction: column; width: 224px; height: 100vh; padding: 18px 13px; border-right: 1px solid #e5e5e5; background: #f7f7f8; transition: width .3s ease-in-out, flex-basis .3s ease-in-out; }
.brand { display: flex; align-items: center; gap: 10px; padding: 5px 7px 25px; color: #202123; text-decoration: none; }.brand-mark { display: grid; place-items: center; width: 32px; height: 32px; overflow: hidden; border: 1px solid #dedee1; border-radius: 9px; background: #fff; }.brand-mark img { width: 27px; height: 27px; object-fit: contain; }.brand-copy strong { display: block; font-size: 17px; font-weight: 650; letter-spacing: -.025em; }
.nav-label { padding: 8px 12px; color: #99999e; font-size: 9px; font-weight: 600; letter-spacing: .1em; }.nav-list { display: flex; flex-direction: column; gap: 3px; }.nav-item { position: relative; display: flex; align-items: center; gap: 12px; height: 43px; padding: 0 12px; border-radius: 9px; color: #4f5054; font-size: 13px; font-weight: 500; text-decoration: none; transition: gap .3s ease-in-out, background .15s; }.nav-item:hover { color: #202123; background: #ededee; }.nav-item.active { color: #202123; background: #e7e7e8; }.nav-item.active svg { color: #6d5bd0; }.nav-item.active i { display: none; }
.sidebar-footer { display: flex; align-items: center; gap: 9px; margin-top: auto; padding: 10px; border-top: 1px solid #e1e1e3; background: transparent; }.status-orb { display: grid; place-items: center; width: 30px; height: 30px; color: #6d5bd0; }.sidebar-footer strong,.sidebar-footer span { display: block; }.sidebar-footer strong { color: #55555a; font-size: 10px; }.sidebar-footer span { margin-top: 3px; color: #929297; font-size: 8px; }.sidebar-footer span i { display: inline-block; width: 5px; height: 5px; margin-right: 4px; border-radius: 50%; background: #20a779; }
@media (max-width: 900px) { .app-sidebar { flex-basis: 76px; width: 76px; padding: 18px 11px; }.brand { justify-content: center; padding-bottom: 24px; }.brand-copy,.nav-label,.nav-item span,.nav-item.active i,.sidebar-footer > div:last-child { display: none; }.nav-item { justify-content: center; padding: 0; }.sidebar-footer { justify-content: center; padding: 8px; } }
@media (max-width: 560px) { .app-sidebar { position: fixed; top: auto; right: 0; bottom: 0; left: 0; flex-direction: row; width: 100%; height: 68px; padding: 7px 10px; border-top: 1px solid #e5e8f1; border-right: 0; }.brand,.nav-label,.sidebar-footer { display: none; }.nav-list { display: grid; flex: 1; grid-template-columns: repeat(5, 1fr); gap: 3px; }.nav-item { flex-direction: column; justify-content: center; gap: 3px; height: 54px; border-radius: 11px; font-size: 8px; }.nav-item span { display: block; }.nav-item.active i { display: none; } }

/* 顶栏：让折叠按钮靠右 */
.sidebar-topbar { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.collapse-toggle { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 9px; color: #4f5054; background: transparent; cursor: pointer; transition: background .15s, color .15s; }
.collapse-toggle:hover { color: #202123; background: #ededee; }

/* 文字显隐过渡基础：淡出 + 宽度收缩，跟随宽度同步 */
.brand-copy,
.nav-label,
.nav-item span,
.nav-item.active i,
.sidebar-footer > div:last-child {
  white-space: nowrap;
  overflow: hidden;
  transition: opacity .3s ease-in-out, max-width .3s ease-in-out;
}

/* 折叠态：收起为窄栏，只留图标（文字淡出收缩，平滑不跳变） */
.app-sidebar.collapsed { flex-basis: 76px; width: 76px; padding: 18px 11px; }
.app-sidebar.collapsed .brand { justify-content: center; padding-bottom: 24px; }
.app-sidebar.collapsed .nav-item {
  gap: 0;
}
.app-sidebar.collapsed .nav-item span {
  opacity: 0;
  max-width: 0;
  margin: 0;
  padding: 0;
}
.app-sidebar.collapsed .brand-copy,
.app-sidebar.collapsed .nav-label,
.app-sidebar.collapsed .nav-item.active i,
.app-sidebar.collapsed .sidebar-footer > div:last-child {
  opacity: 0;
  max-width: 0;
}
.app-sidebar.collapsed .nav-item { justify-content: center; padding: 0; }
.app-sidebar.collapsed .nav-item svg { margin: 0; }
.app-sidebar.collapsed .sidebar-footer { justify-content: center; padding: 8px; }
.app-sidebar.collapsed .sidebar-topbar { justify-content: center; }
.app-sidebar.collapsed .brand { display: none; }
</style>
