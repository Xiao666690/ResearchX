<template>
  <div class="chat-workspace">
    <ResizablePanelGroup direction="horizontal" class="h-full w-full">
      <ResizablePanel :default-size="76" :min-size="45" class="min-w-0"><Content class="h-full min-w-0" /></ResizablePanel>
      <ResizableHandle with-handle class="chat-handle" />
      <ResizablePanel :default-size="24" :min-size="0" :collapsed-size="0" collapsible class="min-w-0"><SideBar class="h-full" /></ResizablePanel>
    </ResizablePanelGroup>
  </div>
</template>

<style scoped>
.chat-workspace { display: flex; height: calc(100vh - 72px); min-width: 0; overflow: hidden; background: #fff; }
.chat-handle { z-index: 10; background: #e2e8f0; transition: background-color .18s ease; }
.chat-handle:hover, .chat-handle:focus-visible { background: #8baccf; }
@media (max-width: 700px) { .chat-workspace { height: calc(100vh - 62px); } }
@media (max-width: 560px) { .chat-workspace { height: calc(100vh - 128px); } }
</style>

<script setup lang="ts">
import Content from './content/ContentView.vue'
import SideBar from './sidebar/SideBar.vue'
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'
// import { useMessageListStore } from '@/stores/messageList'
</script>
