<template>
  <div id="home" class="app-shell flex min-h-screen">
    <SideBar
      :is-collapsed="isCollapsed"
      @toggle-collapse="isCollapsed = !isCollapsed"
    />
    <router-view class="min-w-0 flex-1" />
  </div>
</template>

<script setup lang="ts">
const isCollapsed = ref(false)
</script>

<style lang="less" scoped>
.app-shell { width: 100%; min-width: 0; overflow-x: clip; background: #f7f9ff; }
@media (max-width: 560px) {
  .app-shell { padding-bottom: 68px; }
}
</style>
