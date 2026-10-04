<template>
  <div class="paper-chat border">
    <header class="chat-header">
      <div><h1 class="text-lg font-bold">论文问答</h1><p class="text-xs text-gray-500">围绕当前论文提问；支持引用与外部学术检索</p></div>
      <div ref="modelPicker" class="model-picker">
        <button type="button" class="model-select" aria-label="选择模型" :aria-expanded="modelMenuOpen" aria-haspopup="menu" @click="modelMenuOpen = !modelMenuOpen" @keydown.esc="modelMenuOpen = false">
          {{ modelStore.getModelLabel(selectedModel) }} <span aria-hidden="true">⌄</span>
        </button>
        <div v-if="modelMenuOpen" class="model-menu" role="menu" @keydown.esc="modelMenuOpen = false">
          <button v-for="item in modelStore.modelOptions" :key="item.value" type="button" role="menuitemradio" :aria-checked="selectedModel === item.value" @click="selectedModel = item.value; modelMenuOpen = false">
            {{ item.label }} <span v-if="selectedModel === item.value" aria-hidden="true">✓</span>
          </button>
        </div>
      </div>
    </header>
    <main ref="messageContainer" class="chat-messages">
      <p v-if="!messages.length" class="text-sm text-gray-500">可以询问方法、实验和结论，也可以选中左侧段落后追问。</p>
      <div v-for="(message, index) in messages" :key="index" class="mb-3">
        <MessageBox v-bind="message" />
      </div>
    </main>
    <div v-if="selectedText" class="selected-quote">
      <span>已选第 {{ selectedPage }} 页：{{ selectedText.slice(0, 140) }}{{ selectedText.length > 140 ? '…' : '' }}</span>
      <button type="button" @click="emit('clear-selection')">×</button>
    </div>
    <form class="chat-composer" @submit.prevent="send">
      <textarea v-model="draft" rows="2" placeholder="询问这篇论文或探索相关研究…" @keydown.enter.exact.prevent="send" />
      <button type="submit" :disabled="sending || !draft.trim()">{{ sending ? '回答中…' : '发送' }}</button>
    </form>
  </div>
</template>

<style scoped>
.paper-chat { display: flex; flex-direction: column; box-sizing: border-box; contain: inline-size; width: 100%; max-width: 100%; min-width: 0; min-height: 0; height: 100%; overflow: clip; background: white; }
.chat-header { position: relative; z-index: 20; display: flex; justify-content: space-between; align-items: center; gap: 8px; min-width: 0; padding: 10px 14px; border-bottom: 1px solid #e5e7eb; }
.model-picker { position: relative; flex: none; }
.model-select { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 112px; padding: 6px 9px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #1f2937; font-size: 12px; }
.model-menu { position: absolute; top: calc(100% + 5px); right: 0; z-index: 30; width: 142px; padding: 4px; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; color: #1f2937; box-shadow: 0 8px 24px #1f293726; }
.model-menu button { display: flex; justify-content: space-between; width: 100%; padding: 7px 8px; border-radius: 5px; text-align: left; font-size: 12px; }
.model-menu button:hover, .model-menu button[aria-checked='true'] { background: #f1effa; color: #5548ad; }
.chat-messages { flex: 1; min-width: 0; min-height: 0; max-width: 100%; overflow-x: hidden; overflow-y: auto; padding: 12px; }
.chat-messages > div { min-width: 0; max-width: 100%; }
.selected-quote { display: flex; justify-content: space-between; gap: 6px; min-width: 0; max-width: 100%; padding: 7px 12px; background: #f0f7ff; color: #475569; font-size: 12px; }
.selected-quote span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.selected-quote button { font-size: 18px; }
.chat-composer { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #e5e7eb; }
.chat-composer textarea { flex: 1; min-width: 0; resize: vertical; border: 1px solid #d1d5db; border-radius: 8px; padding: 7px; font-size: 13px; }
.chat-composer button { align-self: end; border-radius: 8px; background: #356fce; color: white; padding: 8px 12px; white-space: nowrap; }
.chat-composer button:disabled { opacity: .5; }
</style>

<script setup lang="ts">
import MessageBox from '@/views/chat/components/MessageBox.vue'
import { askQuestionStream, type CitationItem, type ExternalPaperResult, type SearchProgress } from '@/api/qa'
import { useModelStore, type ModelType } from '@/stores/modelStore'
import { getDocumentSummary } from '@/api/data'

const props = defineProps<{ knowledgeId: string; documentId: string; selectedText: string; selectedPage: number }>()
const emit = defineEmits<{ 'clear-selection': [] }>()
type PaperMessage = {
  role: 'user' | 'gpt' | 'system'; content: string; modelLabel?: string;
  citations?: CitationItem[]; externalPapers?: ExternalPaperResult;
  searchSteps?: string[]; searchState?: SearchProgress['state'];
  status?: 'thinking' | 'streaming' | 'done' | 'error'
  startedAt?: number; thinkingMs?: number; durationMs?: number
}
const modelStore = useModelStore()
const selectedModel = ref<ModelType>(modelStore.currentModel)
const modelMenuOpen = ref(false)
const modelPicker = ref<HTMLElement | null>(null)
const closeModelMenuOutside = (event: PointerEvent) => {
  if (!modelPicker.value?.contains(event.target as Node)) modelMenuOpen.value = false
}
const messages = ref<PaperMessage[]>([])
const draft = ref('')
const sending = ref(false)
const messageContainer = ref<HTMLElement | null>(null)
const storageKey = () => `paperquery:paper-chat:${localStorage.getItem('username') || 'guest'}:${props.documentId}`

const persist = () => {
  try { localStorage.setItem(storageKey(), JSON.stringify(messages.value)) } catch (error) { console.error('聊天记录保存失败', error) }
}
const restore = async () => {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey()) || '[]')
    if (Array.isArray(saved) && saved.length) {
      messages.value = saved.map((item: PaperMessage) => ({ ...item, status: item.status === 'thinking' || item.status === 'streaming' ? 'error' : item.status }))
      return
    }
  } catch (error) { console.error('聊天记录读取失败', error) }
  try {
    const response = await getDocumentSummary(props.knowledgeId, props.documentId)
    const summary = response.data?.summarize
    if (summary) { messages.value.push({ role: 'gpt', content: summary, modelLabel: '论文摘要', status: 'done' }); persist() }
  } catch (error) { console.info('尚无论文摘要', error) }
}

const send = async () => {
  const input = draft.value.trim()
  if (!input || sending.value) return
  const question = props.selectedText
    ? `${input}\n\n请结合当前论文第 ${props.selectedPage} 页选中的文字：\n“${props.selectedText}”`
    : input
  draft.value = ''
  emit('clear-selection')
  const context = messages.value.filter(item => item.role !== 'system' && item.content.trim()).slice(-6)
    .map(item => `${item.role === 'user' ? '用户' : '助手'}: ${item.content.slice(0, 800)}`).join('\n')
  messages.value.push({ role: 'user', content: question })
  const reply = reactive<PaperMessage>({ role: 'gpt', content: '', modelLabel: modelStore.getModelLabel(selectedModel.value), status: 'thinking', startedAt: Date.now() })
  messages.value.push(reply)
  persist()
  sending.value = true
  try {
    await askQuestionStream(question, [props.documentId], selectedModel.value, context,
      text => { if (reply.thinkingMs == null) reply.thinkingMs = Date.now() - (reply.startedAt || Date.now()); reply.content += text; reply.status = 'streaming'; scrollToBottom() },
      citations => { reply.citations = citations },
      progress => {
        reply.searchState = progress.state
        if (progress.text && !reply.searchSteps?.includes(progress.text)) reply.searchSteps = [...(reply.searchSteps || []), progress.text]
        scrollToBottom()
      },
      result => { reply.externalPapers = result; scrollToBottom() },
    )
    reply.status = 'done'
  } catch (error: any) {
    reply.status = 'error'
    reply.content ||= `请求失败：${error?.message || error}`
  } finally { reply.durationMs = Date.now() - (reply.startedAt || Date.now()); sending.value = false; persist(); scrollToBottom() }
}

const scrollToBottom = () => nextTick(() => { if (messageContainer.value) messageContainer.value.scrollTop = messageContainer.value.scrollHeight })
watch(() => props.documentId, () => { messages.value = []; restore() })
onMounted(() => { restore(); document.addEventListener('pointerdown', closeModelMenuOutside) })
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeModelMenuOutside))
</script>
