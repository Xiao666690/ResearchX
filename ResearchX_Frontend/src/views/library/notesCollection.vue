<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteNote, getNoteCollection, type NoteEntry } from '@/api/dashboard'

const router = useRouter()
const notes = ref<NoteEntry[]>([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const deleting = ref('')
const grouped = computed(() => {
  const query = search.value.trim().toLowerCase()
  const result = new Map<string, NoteEntry[]>()
  for (const note of notes.value) {
    if (query && !`${note.knowledgeName} ${note.documentName} ${note.preview}`.toLowerCase().includes(query)) continue
    const group = result.get(note.knowledgeName) || []
    group.push(note)
    result.set(note.knowledgeName, group)
  }
  return [...result.entries()]
})
onMounted(async () => {
  try { notes.value = await getNoteCollection() }
  catch (cause: any) { error.value = cause?.message || '笔记集加载失败' }
  finally { loading.value = false }
})
const openNote = (note: NoteEntry) => router.push({ name: 'noteFullscreen',
  params: { knowledgeID: note.knowledgeID, documentID: note.documentID } })
const removeNote = async (note: NoteEntry) => {
  const key = `${note.knowledgeID}:${note.documentID}`
  try {
    await ElMessageBox.confirm(`确定删除《${note.documentName}》的笔记吗？论文文档不会被删除。`, '删除笔记', {
      type: 'warning', confirmButtonText: '删除笔记', cancelButtonText: '取消',
    })
  } catch { return }
  deleting.value = key
  try {
    await deleteNote(note.knowledgeID, note.documentID)
    notes.value = notes.value.filter(item => `${item.knowledgeID}:${item.documentID}` !== key)
    ElMessage.success('笔记已删除')
  } catch (cause: any) {
    ElMessage.error(cause?.response?.data?.detail || cause?.message || '删除笔记失败')
  } finally {
    deleting.value = ''
  }
}
</script>

<template>
  <main class="notes-page">
    <header>
      <div><p class="eyebrow">LIBRARY · NOTES</p><h1>论文笔记集</h1><p>按知识库整理已写笔记，点击可回到论文和对应笔记。</p></div>
      <button @click="router.push('/home/library')">返回论文库</button>
    </header>
    <input v-model="search" class="search" placeholder="搜索知识库、论文或笔记内容" />
    <p v-if="loading">正在加载笔记…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <p v-else-if="!grouped.length" class="empty">{{ notes.length ? '没有匹配的笔记' : '还没有已保存的论文笔记。打开一篇论文，切换到“笔记”即可开始。' }}</p>
    <section v-for="[knowledgeName, entries] in grouped" :key="knowledgeName" class="group">
      <h2>{{ knowledgeName }} <small>{{ entries.length }} 篇论文</small></h2>
      <div class="note-grid">
        <article v-for="entry in entries" :key="`${entry.knowledgeID}:${entry.documentID}`" class="note-card">
          <button class="note-open" @click="openNote(entry)">
            <strong>{{ entry.documentName }}</strong>
            <span>{{ entry.preview || '打开笔记' }}</span>
            <em>阅读论文并查看笔记 →</em>
          </button>
          <button class="note-delete" :disabled="deleting === `${entry.knowledgeID}:${entry.documentID}`" @click="removeNote(entry)">
            {{ deleting === `${entry.knowledgeID}:${entry.documentID}` ? '删除中…' : '删除笔记' }}
          </button>
        </article>
      </div>
    </section>
  </main>
</template>

<style scoped>
.notes-page { width: 100%; min-width: 0; padding: 36px clamp(22px, 3.8vw, 60px); color: #263b52; background: #f7f9fc; }
header { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
header h1 { font-size: 26px; font-weight: 700; } header p { color: #64748b; font-size: 13px; }
.eyebrow { color: #7290b4; font-size: 10px; font-weight: 700; letter-spacing: .12em; }
header button { border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 12px; background: white; white-space: nowrap; }
.search { width: min(100%, 560px); margin: 24px 0; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 9px; background: white; }
.group { margin: 10px 0 28px; }.group h2 { margin-bottom: 12px; font-size: 18px; font-weight: 650; }.group small { margin-left: 8px; color: #94a3b8; font-size: 12px; }
.note-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.note-card { display: flex; flex-direction: column; gap: 9px; text-align: left; padding: 16px; border: 1px solid #e2e8f0; border-radius: 12px; background: white; }
.note-card:hover { border-color: #b5cbe3; box-shadow: 0 8px 22px rgba(45, 82, 127, .07); }
.note-open { display: flex; flex: 1; flex-direction: column; gap: 9px; width: 100%; text-align: left; }
.note-open strong { font-size: 14px; }.note-open span { min-height: 40px; color: #64748b; font-size: 12px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }.note-open em { color: #3565a4; font-size: 12px; font-style: normal; }
.note-delete { align-self: flex-end; padding: 5px 8px; border-radius: 6px; color: #b42318; font-size: 12px; }
.note-delete:hover { background: #fef3f2; }.note-delete:disabled { cursor: wait; opacity: .5; }
.empty,.error { padding: 36px; color: #64748b; text-align: center; border: 1px dashed #cbd5e1; border-radius: 12px; }
</style>
