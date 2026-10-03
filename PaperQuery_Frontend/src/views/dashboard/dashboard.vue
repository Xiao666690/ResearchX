<script setup lang="ts">
// import { Button } from '@/components/ui/button'
import TodayOverview from './TodayOverview.vue'
import { Button } from '@/components/ui/button'
import { useStore } from 'vuex'

const store = useStore()
const router = useRouter()

const logoutButton = () => {
  store.dispatch('logout')
  router.push('/login')
}
</script>

<template>
  <div class="dashboard-shell">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">概览</h1>
      <Button variant="outline" class="text-1xl" @click="logoutButton"
        >注销</Button
      >
    </div>
    <TodayOverview />
  </div>
</template>

<style scoped>
.dashboard-shell { width: 100%; max-width: 1600px; min-width: 0; margin: 0 auto; padding: 22px clamp(16px, 2.5vw, 40px) 48px; }
</style>
