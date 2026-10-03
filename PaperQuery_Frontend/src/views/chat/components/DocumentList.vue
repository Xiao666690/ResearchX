<template>
  <div v-if="documents.length" class="paper-selector" aria-label="本轮问答所用论文">
    <span class="selector-label">本轮论文</span>
    <div class="paper-options">
      <span v-for="(document, index) in documents" :key="document.documentID || index" class="paper-option" :class="{ selected: document.documentID && store.state.selectedDocumentIDs.includes(document.documentID) }">
        <button type="button" :title="`选择或取消 ${document.documentName}`" @click="document.documentID && store.toggleDocument(document.documentID)">
          <span class="selection-mark">{{ document.documentID && store.state.selectedDocumentIDs.includes(document.documentID) ? '✓' : '+' }}</span>
          {{ document.documentName }}
        </button>
        <button type="button" class="remove" :title="`移除 ${document.documentName}`" @click="store.deleteDocument(index)">×</button>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDocumentListStore } from '@/stores/documentList'
const store = useDocumentListStore()
const documents = computed(() => store.state.documentList)
</script>

<style scoped>
.paper-selector { display: flex; align-items: center; gap: 8px; width: 50%; min-width: 0; margin: 0 auto 8px; padding: 7px 9px; border: 1px solid #dad4f0; border-radius: 10px; background: #f7f5ff; }
.selector-label { flex: none; color: #6355a9; font-size: 11px; font-weight: 600; }
.paper-options { display: flex; min-width: 0; gap: 6px; overflow-x: auto; }
.paper-option { display: flex; flex: none; max-width: 220px; align-items: center; border: 1px solid #dedde5; border-radius: 7px; background: #fff; }
.paper-option.selected { border-color: #8071d6; background: #eeeafd; }
.paper-option button:first-child { overflow: hidden; padding: 4px 5px 4px 7px; color: #4d4b5b; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.selection-mark { margin-right: 3px; color: #6d5bd0; font-weight: 700; }
.remove { padding: 0 6px; color: #8b8b95; font-size: 15px; }.remove:hover { color: #ca3e57; }
@media(max-width: 900px) { .paper-selector { width: 90%; } }
</style>
