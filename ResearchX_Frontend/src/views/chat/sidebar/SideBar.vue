<template>
  <aside class="h-full border-l border-gray-100 bg-[#f9f9f9]">
    <div class="flex items-center justify-between gap-2 border-b border-gray-100 p-4">
      <div>
        <div class="text-sm font-semibold text-gray-900">历史会话</div>
        <div class="text-xs text-gray-500">当前账号本地保存</div>
      </div>
      <el-button size="small" @click="startNewChat">新聊天</el-button>
    </div>

    <div class="h-[calc(100%-73px)] overflow-y-auto p-3">
      <el-empty
        v-if="sessions.length === 0"
        description="暂无历史记录"
        :image-size="72"
      />

      <article
        v-for="session in sessions"
        :key="session.id"
        class="session-card mb-3 w-full rounded-md border border-gray-200 bg-white p-3 text-left transition hover:border-gray-300 hover:bg-gray-50"
        :class="{ active: historyStore.state.currentSessionId === session.id }"
        role="button"
        tabindex="0"
        @click="restoreSession(session)"
        @keydown.enter="restoreSession(session)"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
            {{ session.title }}
          </div>
          <div class="session-actions flex shrink-0 gap-1">
            <button type="button" title="重命名会话" @click.stop="renameSession(session)">
              <Pencil :size="13" />
            </button>
            <button type="button" title="总结当前会话" :disabled="summarizingId === session.id" @click.stop="summarizeSession(session)">
              <LoaderCircle v-if="summarizingId === session.id" :size="13" class="animate-spin" />
              <FileText v-else :size="13" />
            </button>
          </div>
        </div>
        <div class="mt-1 flex items-center justify-between gap-2 text-xs text-gray-500">
          <span>{{ session.modelLabel }}</span>
          <span>{{ formatTime(session.updatedAt) }}</span>
        </div>
        <div class="mt-2 text-xs text-gray-500">
          {{ session.documents.length ? `绑定 ${session.documents.length} 篇论文` : '未绑定论文' }}
        </div>
        <p class="session-summary">{{ visiblePreview(session) }}</p>
        <div
          v-if="session.documents.length"
          class="mt-2 truncate text-xs text-gray-400"
          :title="session.documents.map(item => item.documentName).join(', ')"
        >
          {{ session.documents.map(item => item.documentName).join(', ') }}
        </div>
      </article>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FileText, LoaderCircle, Pencil } from 'lucide-vue-next'
import { useChatHistoryStore, type ChatSession } from '@/stores/chatHistory'
import { useMessageListStore } from '@/stores/messageList'
import { useDocumentListStore } from '@/stores/documentList'
import { useModelStore, type ModelType } from '@/stores/modelStore'
import { useMemoryStore } from '@/stores/memory'
import { updateMemory } from '@/api/chat'

const historyStore = useChatHistoryStore()
const messageListStore = useMessageListStore()
const modelStore = useModelStore()
const memoryStore = useMemoryStore()
const sessions = computed(() => historyStore.sessionList)
const summarizingId = ref('')

function startNewChat() {
  messageListStore.clearMessages()
  ElMessage.success('已开启新聊天')
}

function restoreSession(session: ChatSession) {
  historyStore.useSession(session.id)
  modelStore.setModel(session.model as ModelType)
  messageListStore.restoreMessages(session.messages, session.memory)
  useDocumentListStore().restoreDocuments(session.documents || [], session.selectedDocumentIDs)
  ElMessage.success('已恢复历史会话')
}

function visiblePreview(session: ChatSession) {
  return session.messages.filter(message => (message.role === 'user' || message.role === 'gpt') && message.content.trim())
    .slice(-2).map(message => `${message.role === 'user' ? '提问' : '回答'}：${message.content.trim().slice(0, 100)}`).join('  ·  ')
}

async function renameSession(session: ChatSession) {
  try {
    const { value } = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', {
      inputValue: session.title,
      inputPlaceholder: '最多 60 个字符',
      inputValidator: value => Boolean(value?.trim()) || '会话名称不能为空',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    if (historyStore.renameSession(session.id, value)) {
      ElMessage.success('会话名称已更新')
    }
  } catch {
    // 用户取消时不提示错误。
  }
}

async function summarizeSession(session: ChatSession) {
  if (summarizingId.value) return
  const transcript = session.messages
    .filter(message => message.role !== 'system' && message.content.trim())
    .map(message => `${message.role === 'user' ? '用户' : '助手'}：${message.content.trim()}`)
    .join('\n')
  if (!transcript) {
    ElMessage.warning('当前会话暂无可总结内容')
    return
  }

  summarizingId.value = session.id
  try {
    const data: any = await updateMemory('', '', transcript)
    const summary = data?.context?.trim()
    if (!summary) throw new Error('模型未返回摘要')
    historyStore.updateSessionSummary(session.id, summary)
    if (historyStore.state.currentSessionId === session.id) {
      memoryStore.setMemory(summary)
      messageListStore.saveHistorySnapshot()
    }
    ElMessage.success('会话摘要已更新')
  } catch (error: any) {
    ElMessage.error(error?.message || '生成摘要失败')
  } finally {
    summarizingId.value = ''
  }
}

function formatTime(timestamp: number) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestamp))
}
</script>

<style scoped>
.session-card { cursor: pointer; }
.session-card.active { border-color: #cfc9e8; background: #f5f3fa; }
.session-actions { opacity: 0; transition: opacity .15s ease; }
.session-card:hover .session-actions,
.session-card:focus-within .session-actions { opacity: 1; }
.session-actions button { display: grid; width: 25px; height: 25px; place-items: center; border: 0; border-radius: 6px; color: #72727a; background: transparent; }
.session-actions button:hover { color: #55489d; background: #ece9f5; }
.session-actions button:disabled { cursor: wait; opacity: .55; }
.session-summary { display: -webkit-box; overflow: hidden; margin: 8px 0 0; color: #777780; font-size: 11px; line-height: 1.5; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
</style>
