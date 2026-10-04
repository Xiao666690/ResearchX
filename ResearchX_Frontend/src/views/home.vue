<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { LogOut, Plus } from 'lucide-vue-next'
import SideBar from '@/components/SideBar.vue'

const route = useRoute()
const router = useRouter()
const store = useStore()
const isCollapsed = ref(false)
const username = computed(() => localStorage.getItem('username') || '研究者')
const pageTitle = computed(() => {
  if (route.path.includes('/research')) return '深度研究'
  if (route.path.includes('/library')) return '论文资料库'
  if (route.path.includes('/chat')) return '智能问答'
  return '工作台'
})
const logout = async () => {
  await store.dispatch('logout')
  router.push('/login')
}
</script>

<template>
  <div id="home" class="app-shell">
    <SideBar :is-collapsed="isCollapsed" @toggle-collapse="isCollapsed = !isCollapsed" />
    <div class="app-content">
      <header class="app-topbar">
        <div class="location"><span>工作空间 / </span><strong>{{ pageTitle }}</strong></div>
        <div class="top-actions">
          <router-link to="/home/research" class="new-research"><Plus :size="15" /> 新建研究</router-link>
          <div class="profile"><span class="avatar">{{ username.slice(0, 1).toUpperCase() }}</span><span class="profile-name">{{ username }}</span></div>
          <button class="logout" type="button" title="退出登录" aria-label="退出登录" @click="logout"><LogOut :size="17" /></button>
        </div>
      </header>
      <router-view class="app-page" />
    </div>
  </div>
</template>

<style scoped src="./home-refined.css"></style>
