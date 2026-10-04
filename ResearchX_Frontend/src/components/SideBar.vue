<script setup lang="ts">
import { Menu, Plus } from 'lucide-vue-next'
import axios from 'axios'
import { getSidebarItems } from './utils/sidebar'
import researchXMark from '@/assets/img/researchx-mark.svg'

defineProps({ isCollapsed: Boolean })
const emit = defineEmits<{ (e: 'toggleCollapse'): void }>()
const route = useRoute()
const isActive = (link: string) => {
  if (link.includes('/library')) return ['/library', '/knowledge/', '/pdfInfo/'].some(part => route.path.includes(part))
  return route.path.toLowerCase().startsWith(link.toLowerCase())
}
const role = ref(localStorage.getItem('role') || '')
const sidebarItems = ref(getSidebarItems(role.value))

onMounted(async () => {
  if (role.value) return
  const token = localStorage.getItem('token')
  if (!token) return
  try {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'
    const { data } = await axios.get(`${base}/user/me`, {
      headers: { Authorization: `Bearer ${token}` }, timeout: 10000,
    })
    if (data?.data?.role) {
      role.value = data.data.role
      localStorage.setItem('role', data.data.role)
      if (data.data.workspace_lid) localStorage.setItem('workspaceLid', data.data.workspace_lid)
      sidebarItems.value = getSidebarItems(role.value)
    }
  } catch {
    // The workspace remains available with ordinary navigation.
  }
})
</script>

<template>
  <nav class="app-sidebar" :class="{ collapsed: isCollapsed }" aria-label="主导航">
    <div class="sidebar-topbar">
      <router-link to="/home/dashboard" class="brand" aria-label="ResearchX 概览">
        <img class="brand-mark" :src="researchXMark" alt="" />
        <span class="brand-copy"><strong>ResearchX</strong><small>研究工作空间</small></span>
      </router-link>
      <button type="button" class="collapse-toggle" :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'" @click="emit('toggleCollapse')"><Menu :size="18" /></button>
    </div>
    <div class="sidebar-section">工作空间</div>
    <div class="nav-list">
      <router-link v-for="item in sidebarItems" :key="item.title" :to="item.link" class="nav-item" :class="{ active: isActive(item.link) }" :title="isCollapsed ? item.title : undefined">
        <component :is="item.icon" :size="18" /><span>{{ item.title }}</span>
      </router-link>
    </div>
    <router-link class="research-shortcut" to="/home/research"><span class="shortcut-icon"><Plus :size="17" /></span><span class="shortcut-copy"><strong>新建研究</strong><small>从一个问题开始</small></span></router-link>
    <div class="sidebar-footer"><span class="footer-copy"><strong>ResearchX</strong><small>专注问题，也重视依据。</small></span></div>
  </nav>
</template>

<style scoped src="./SideBar-refined.css"></style>
