<template>
  <div class="translation-panel flex-col h-full w-full min-h-0 min-w-0 border">
    <div class="flex items-center justify-between p-2 border-b">
      <!-- <h1 class="text-xl font-bold">翻译</h1> -->
      <Tabs :default-value="route.query.tab === 'note' ? 'note' : 'translate'">
        <TabsList>
          <TabsTrigger value="translate" @click="displayTran">
            翻译
          </TabsTrigger>
          <TabsTrigger value="note" @click="displayNote">
            笔记
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
    <!-- Content area -->
    <div class="translation-body flex-grow min-h-0 overflow-hidden">
      <!-- Translate content -->
      <div v-show="TranDisplay" class="translation-scroll h-full overflow-auto p-4">
        <p class="mb-2 text-xs text-gray-500">选中左侧英文后自动使用本机模型翻译，不调用云端翻译 API。</p>
        <div v-if="sourceText" class="translation-text mb-3 rounded border bg-gray-50 p-3 text-sm">{{ displaySourceText }}</div>
        <div class="translation-text rounded border p-3 text-sm leading-relaxed">{{ displayTranslatedText || '请在论文中选中需要翻译的英文。' }}</div>
      </div>

      <!-- Note content -->
      <div v-if="!TranDisplay" class="translation-scroll note-scroll h-full overflow-auto p-4">
        <note class="w-full h-full" :knowledgeID="knowledgeID" :documentID="documentID"></note>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useStore } from 'vuex'
import note from '@/views/note/note.vue'
const route = useRoute()

const knowledgeID = route.params.knowledgeID as string
const documentID = route.params.documentID as string

const store = useStore()

const TranDisplay = ref(route.query.tab !== 'note')
watch(() => route.query.tab, value => { TranDisplay.value = value !== 'note' })

// 显示翻译文字
const translatedText = computed(() => {
  return store.getters.translatedText
})
const sourceText = computed(() => store.getters.selectedText)
// PDF 文本层保留原页面的窄列换行；展示时重排，才能随分栏宽度重新流动。
const displaySourceText = computed(() => String(sourceText.value || '')
  .replace(/-\s*\r?\n\s*/g, '')
  .replace(/\s+/g, ' ')
  .trim())
const displayTranslatedText = computed(() => String(translatedText.value || '')
  .replace(/\s+/g, ' ')
  .trim())

onMounted(() => {
  store.commit('setTranslatedText', '')
})


const displayTran = () => {
  TranDisplay.value = true
}

const displayNote = () => {
  TranDisplay.value = false
}
</script>

<style scoped>
.flex-col {
  display: flex;
  flex-direction: column;
}

.flex-grow {
  flex-grow: 1;
}
.translation-panel,
.translation-body,
.translation-scroll {
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
  width: 100%;
}
.translation-panel {
  contain: inline-size;
  overflow: clip;
}
.translation-text {
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-all;
}
/* 内嵌笔记：透明底，跟随面板背景（与全屏页一致，无卡片/底色） */
.note-scroll {
  background: transparent;
}
</style>
