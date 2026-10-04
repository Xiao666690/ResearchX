<template>
  <div class="reader-workspace">
    <ResizablePanelGroup id="group_1" direction="horizontal" class="w-full h-full">
      <ResizablePanel id="panel-1" :default-size="64" :min-size="0" :collapsed-size="0" collapsible class="h-full min-w-0">
        <div class="w-full h-full">
          <pdfViewer :knowledge-i-d="knowledgeID" :document-i-d="documentID" @selection="onSelection" @loaded="readerReady = true" />
        </div>
      </ResizablePanel>
      <ResizableHandle with-handle class="reader-handle" />
      <ResizablePanel id="panel-2" :default-size="36" :min-size="0" :collapsed-size="0" collapsible class="h-full min-w-0">
        <div class="flex flex-col w-full h-full min-w-0 overflow-hidden">
          <ResizablePanelGroup id="group_2" direction="vertical" class="h-full min-w-0 w-full">
            <ResizablePanel id="panel-2-1" :default-size="50" :min-size="0" :collapsed-size="0" collapsible class="h-full min-h-0">
              <div class="flex flex-1 h-full min-w-0 overflow-hidden">
                <translateBox :knowledge-id="knowledgeID" :document-id="documentID" />
              </div>
            </ResizablePanel>
            <ResizableHandle with-handle class="reader-handle" />
            <ResizablePanel id="panel-2-2" :default-size="50" :min-size="0" :collapsed-size="0" collapsible class="h-full min-h-0">
              <div class="flex flex-1 h-full min-w-0 overflow-hidden">
                <chat class="flex-1" :knowledge-id="knowledgeID" :document-id="documentID" :selected-text="selectedText" :selected-page="selectedPage" @clear-selection="selectedText = ''" />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  </div>
</template>

<style scoped>
.reader-workspace { display: flex; flex: 1 1 0%; width: 100%; height: 100vh; min-width: 0; min-height: 0; overflow: clip; }
.reader-handle { z-index: 10; background: #d4d9e5; transition: background-color .18s ease, box-shadow .18s ease; }
.reader-handle:hover, .reader-handle:focus-visible { background: #6756c5; box-shadow: 0 0 0 3px rgba(103,86,197,.16); }
.reader-handle :deep(div) { width: 18px; height: 24px; color: #5548ad; background: #fff; border: 1px solid #a9a1d6; }
</style>

<script setup lang="ts">
import pdfViewer from '@/views/pdf/pdfViewer.vue'
import chat from '@/views/smallChat/chat.vue'
import translateBox from '@/views/translate/translateBox.vue'
import { useRoute } from 'vue-router'
import { recordReading } from '@/api/dashboard'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'

const route = useRoute()

const knowledgeID = route.params.knowledgeID as string
const documentID = route.params.documentID as string
const selectedText = ref('')
const selectedPage = ref(1)
const readerReady = ref(false)
const onSelection = (text: string, page: number) => {
  selectedText.value = text
  selectedPage.value = page
}

let readingTimer: ReturnType<typeof setInterval> | undefined
let lastReadingTick = Date.now()
const captureReading = () => {
  const now = Date.now()
  const seconds = Math.min(30, Math.floor((now - lastReadingTick) / 1000))
  lastReadingTick = now
  if (readerReady.value && seconds > 0 && document.visibilityState === 'visible' && document.hasFocus()) {
    recordReading(knowledgeID, documentID, seconds).catch(error => console.error('阅读时长记录失败', error))
  }
}
onMounted(() => { lastReadingTick = Date.now(); readingTimer = setInterval(captureReading, 15000) })
onBeforeUnmount(() => { clearInterval(readingTimer); captureReading() })
</script>
