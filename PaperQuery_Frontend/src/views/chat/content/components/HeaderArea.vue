<template>
  <div class="chat-header flex items-start justify-between gap-4 p-4">
    <div class="flex items-center gap-2">
      <model-box />
      <ModeSwitch />
    </div>

    <div class="min-w-0 flex-1 text-right">
      <div class="text-sm font-medium text-gray-900">
        {{ title }}
      </div>
      <div
        v-if="documents.length === 0"
        class="mt-1 text-xs text-amber-600"
      >
        尚未指定论文，当前为普通模型对话
      </div>
      <div
        v-else
        class="mt-2 flex flex-wrap justify-end gap-2"
      >
        <span
          v-for="document in documents"
          :key="document.documentID || document.documentName"
          class="document-chip max-w-[260px] truncate px-2 py-1 text-xs text-gray-700"
          :title="document.documentName"
        >
          {{ document.documentName }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDocumentListStore } from '@/stores/documentList'
import ModelBox from '../../components/ModelBox.vue'
import ModeSwitch from '@/components/ModeSwitch.vue'

const documentStore = useDocumentListStore()
const documents = computed(() => documentStore.state.documentList)

const title = computed(() => {
  if (documents.value.length === 0) return '当前未绑定论文'
  if (documents.value.length === 1) return '当前对话论文'
  return `当前对话已绑定 ${documents.value.length} 篇论文`
})
</script>

<style scoped>
.chat-header { border-bottom: 1px solid #eeeeef; background: rgba(255,255,255,.88); backdrop-filter: blur(14px); }
.document-chip { border: 1px solid #e7e7e9; border-radius: 8px; background: #f8f8f9; }
</style>
