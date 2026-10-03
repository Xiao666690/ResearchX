import { computed, reactive } from 'vue'
import { defineStore } from 'pinia'
import { updateMemory } from '@/api/chat'
import { askQuestionStream, type CitationItem, type ExternalPaperResult, type SearchProgress } from '@/api/qa'
import { useChatHistoryStore } from './chatHistory'
import type { ChatDocumentSnapshot } from './chatHistory'
import { useDocumentListStore } from './documentList'
import { useMemoryStore } from './memory'
import { useModelStore } from './modelStore'

export type Message = {
  id?: number
  content: string
  role: 'user' | 'gpt' | 'system'
  model?: string
  modelLabel?: string
  createdAt?: number
  thinkingMs?: number
  durationMs?: number
  citations?: CitationItem[]
  externalPapers?: ExternalPaperResult
  searchStatus?: string
  searchState?: SearchProgress['state']
  searchSteps?: string[]
  status?: 'thinking' | 'streaming' | 'done' | 'error'
  documents?: ChatDocumentSnapshot[]
}

export const useMessageListStore = defineStore('messageList', () => {
  const state = reactive({
    messageList: <Array<Message>>[],
  })

  const messages = computed(() => state.messageList)

  function addUserMessage(message: Message) {
    const documentStore = useDocumentListStore()
    const userMessage: Message = {
      ...message,
      documents: documentStore.getSelectedSnapshots(),
      id: state.messageList.length,
      createdAt: Date.now(),
    }
    state.messageList.push(userMessage)
    saveHistorySnapshot()
    addGptMessage(userMessage.content, documentStore.getDocumentIDs())
  }

  function addSystemMessage(content: string) {
    state.messageList.push({
      id: state.messageList.length,
      content,
      role: 'system',
      createdAt: Date.now(),
    })
    saveHistorySnapshot()
  }

  function addGptMessage(question: string, ids: string[]) {
    const modelStore = useModelStore()
    const model = modelStore.currentModel
    const modelLabel = modelStore.getModelLabel(model)
    const newId = state.messageList.length
    const memory = useMemoryStore().getMemory
    let answer = ''
    let citations: CitationItem[] = []

    state.messageList.push({
      id: newId,
      content: '',
      role: 'gpt',
      model,
      modelLabel,
      createdAt: Date.now(),
      status: 'thinking',
    })

    function updateMessage(id: number, content: string) {
      if (!state.messageList[id]) {
        state.messageList.push({
          id,
          content,
          role: 'gpt',
          model,
          modelLabel,
          createdAt: Date.now(),
          status: 'streaming',
        })
      } else {
        if (state.messageList[id].thinkingMs == null) {
          state.messageList[id].thinkingMs = Date.now() - (state.messageList[id].createdAt || Date.now())
        }
        state.messageList[id].content += content
        state.messageList[id].status = 'streaming'
      }
    }

    askQuestionStream(
      question,
      ids,
      model,
      memory,
      (text) => {
        answer += text
        updateMessage(newId, text)
      },
      (cits) => {
        citations = cits
      },
      (progress) => {
        if (state.messageList[newId]) {
          const message = state.messageList[newId]
          message.searchStatus = progress.text
          message.searchState = progress.state
          if (progress.text && !message.searchSteps?.includes(progress.text)) {
            message.searchSteps = [...(message.searchSteps || []), progress.text]
          }
        }
      },
      (result) => {
        if (state.messageList[newId]) {
          state.messageList[newId].externalPapers = result
        }
        saveHistorySnapshot()
      },
    )
      .then(() => {
        if (state.messageList[newId]) {
          state.messageList[newId].citations = citations
          state.messageList[newId].status = 'done'
          state.messageList[newId].durationMs = Date.now() - (state.messageList[newId].createdAt || Date.now())
        }
        saveHistorySnapshot()
        return updateMemory(question, memory, answer)
      })
      .then((data: any) => {
        if (data?.context) {
          useMemoryStore().setMemory(data.context)
        }
        saveHistorySnapshot()
      })
      .catch((error) => {
        console.error(error)
        if (state.messageList[newId]) {
          state.messageList[newId].status = 'error'
          state.messageList[newId].durationMs ??= Date.now() - (state.messageList[newId].createdAt || Date.now())
        }
        addSystemMessage(`模型调用失败：${error?.message || error}`)
      })
  }

  function compressContextForModelSwitch(fromModel: string, toModel: string) {
    const recentMessages = state.messageList
      .filter(message => message.role !== 'system' && message.content.trim())
      .slice(-8)
      .map((message) => {
        const role = message.role === 'user' ? '用户' : '助手'
        return `${role}: ${message.content.trim()}`
      })
      .join('\n')
    const documents = useDocumentListStore().getDocumentSnapshots()
    const documentText = documents.length
      ? documents.map(item => item.documentName).join(', ')
      : '当前未绑定论文'

    const compressed = [
      `模型已从 ${fromModel} 切换为 ${toModel}。`,
      '以下是为降低跨模型上下文漂移而压缩后的对话记忆：',
      `当前论文上下文：${documentText}`,
      recentMessages || '暂无历史对话。',
    ].join('\n')

    useMemoryStore().setMemory(compressed.slice(-3000))
    saveHistorySnapshot()
  }

  function clearMessages() {
    state.messageList = []
    useMemoryStore().clearMemory()
    useDocumentListStore().clearDocuments()
    useChatHistoryStore().startNewSession()
  }

  function restoreMessages(messagesToRestore: Message[], memory = '') {
    state.messageList = messagesToRestore.filter(message => message.role === 'user' || message.role === 'gpt').map((message, index) => ({
      ...message,
      id: index,
    }))
    useMemoryStore().setMemory(memory)
  }

  function saveHistorySnapshot() {
    const firstUserMessage = state.messageList.find(message => message.role === 'user')
    const modelStore = useModelStore()
    useChatHistoryStore().saveSnapshot({
      title: firstUserMessage?.content.slice(0, 24) || '新聊天',
      model: modelStore.currentModel,
      modelLabel: modelStore.getModelLabel(modelStore.currentModel),
      memory: useMemoryStore().getMemory,
      summary: useMemoryStore().getMemory,
      documents: useDocumentListStore().getDocumentSnapshots(),
      selectedDocumentIDs: useDocumentListStore().getDocumentIDs(),
      messages: state.messageList.filter(message => message.role === 'user' || message.role === 'gpt'),
    })
  }

  return {
    state,
    messages,
    addUserMessage,
    addSystemMessage,
    clearMessages,
    restoreMessages,
    compressContextForModelSwitch,
    saveHistorySnapshot,
  }
})
