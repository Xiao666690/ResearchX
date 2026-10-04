<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowRightLeft } from 'lucide-vue-next'
import { useWorkspaceModeStore } from '@/stores/workspaceMode'

const router = useRouter()
const store = useWorkspaceModeStore()

const switchMode = () => {
  store.setMode('research')
  router.push('/home/research')
}
</script>

<template>
  <button type="button" class="mode-switch" title="切换到深度研究" @click="switchMode">
    <ArrowRightLeft :size="15" />
    <span>研究模式</span>
  </button>
</template>

<style scoped>
.mode-switch { display: inline-flex; height: 38px; align-items: center; gap: 7px; padding: 0 12px; border: 1px solid transparent; border-radius: 11px; color: #65656b; background: #f3f3f4; font-size: 13px; font-weight: 500; transition: color .18s ease, background .18s ease, box-shadow .18s ease; }
.mode-switch:hover { color: #4f438c; background: #efedf6; box-shadow: inset 0 0 0 1px #e1ddea; }
.mode-switch:focus-visible { outline: 3px solid rgba(109,91,208,.14); outline-offset: 1px; }
</style>
